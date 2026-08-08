#!/usr/bin/env python3
"""Convert an .xlsx workbook to one CSV per worksheet.

Uses only the Python standard library, so it runs with the same dependency
footprint as the collection scripts. An .xlsx file is a zip archive of XML
parts; this reads the shared string table and each worksheet directly.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"main": MAIN_NS, "rel": REL_NS, "pkg": PKG_REL_NS}

CELL_REF_RE = re.compile(r"^([A-Z]+)(\d+)$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def column_index(cell_ref: str) -> int:
    """Return the zero-based column index for a cell reference such as ``AB12``."""
    match = CELL_REF_RE.match(cell_ref or "")
    if not match:
        return -1
    index = 0
    for character in match.group(1):
        index = index * 26 + (ord(character) - ord("A") + 1)
    return index - 1


def slugify(name: str) -> str:
    """Turn a worksheet name into a lowercase, underscore-separated file stem."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_only.lower()).strip("_")
    return slug or "sheet"


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall("main:si", NS)
    ]


def read_worksheet_targets(archive: zipfile.ZipFile) -> list[dict[str, str]]:
    """Return worksheet names in workbook order with their archive paths."""
    relationships: dict[str, str] = {}
    rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relationship in rels_root.findall("pkg:Relationship", NS):
        relationships[relationship.get("Id", "")] = relationship.get("Target", "")

    sheets: list[dict[str, str]] = []
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    for sheet in workbook.find("main:sheets", NS) or []:
        target = relationships.get(sheet.get(f"{{{REL_NS}}}id", ""), "")
        if not target:
            continue
        path = target.lstrip("/")
        if not path.startswith("xl/"):
            path = f"xl/{path}"
        sheets.append(
            {
                "name": sheet.get("name", ""),
                "path": path,
                "state": sheet.get("state", "visible"),
            }
        )
    return sheets


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        inline = cell.find("main:is", NS)
        if inline is None:
            return ""
        return "".join(node.text or "" for node in inline.iter(f"{{{MAIN_NS}}}t"))

    value = cell.find("main:v", NS)
    if value is None or value.text is None:
        return ""
    raw = value.text

    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return ""
    if cell_type == "b":
        return "TRUE" if raw == "1" else "FALSE"
    if cell_type == "e":
        return raw
    return raw


def worksheet_rows(
    archive: zipfile.ZipFile,
    path: str,
    shared_strings: list[str],
) -> list[list[str]]:
    worksheet = ET.fromstring(archive.read(path))
    sheet_data = worksheet.find("main:sheetData", NS)
    rows: list[list[str]] = []
    if sheet_data is None:
        return rows

    for row in sheet_data.findall("main:row", NS):
        values: list[str] = []
        for cell in row.findall("main:c", NS):
            index = column_index(cell.get("r", ""))
            if index < 0:
                index = len(values)
            while len(values) < index:
                values.append("")
            values.append(cell_value(cell, shared_strings))
        rows.append(values)

    width = max((len(row) for row in rows), default=0)
    for row in rows:
        while len(row) < width:
            row.append("")
    return rows


def convert(
    xlsx_path: Path,
    out_dir: Path,
    include_hidden: bool,
) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []

    with zipfile.ZipFile(xlsx_path) as archive:
        shared_strings = read_shared_strings(archive)
        used_stems: set[str] = set()

        for sheet in read_worksheet_targets(archive):
            if sheet["state"] != "visible" and not include_hidden:
                continue

            stem = slugify(sheet["name"])
            candidate = stem
            suffix = 2
            while candidate in used_stems:
                candidate = f"{stem}_{suffix}"
                suffix += 1
            used_stems.add(candidate)

            rows = worksheet_rows(archive, sheet["path"], shared_strings)
            csv_path = out_dir / f"{candidate}.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerows(rows)

            summaries.append(
                {
                    "sheet_name": sheet["name"],
                    "sheet_state": sheet["state"],
                    "csv": csv_path.name,
                    "row_count": len(rows),
                    "data_row_count": max(len(rows) - 1, 0),
                    "column_count": max((len(row) for row in rows), default=0),
                    "header": rows[0] if rows else [],
                }
            )

    return summaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", help="Path to the .xlsx workbook.")
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory. Defaults to the workbook's directory.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Also convert worksheets Excel marked hidden or very hidden.",
    )
    parser.add_argument(
        "--manifest",
        default="",
        help="Optional path for a JSON conversion manifest.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    xlsx_path = Path(args.xlsx)
    if not xlsx_path.exists():
        print(f"No such workbook: {xlsx_path}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else xlsx_path.parent
    started_at = utc_now()
    sheets = convert(xlsx_path, out_dir, include_hidden=args.include_hidden)

    manifest = {
        "source_workbook": xlsx_path.name,
        "converter": Path(__file__).name,
        "converted_at_utc": started_at.isoformat(),
        "out_dir": str(out_dir),
        "sheet_count": len(sheets),
        "total_data_rows": sum(sheet["data_row_count"] for sheet in sheets),
        "sheets": sheets,
        "notes": [
            "One CSV per worksheet, written in workbook order with the original header row.",
            "Cell values are taken as stored text; no formatting or formulas are applied.",
        ],
    }

    if args.manifest:
        Path(args.manifest).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
