#!/usr/bin/env python3
"""Generate third-person search phrases from the first-person keyword workbook.

The workbook in `data/keyword_search_combos/` is written entirely in the voice of
the person whose Reddit content was discovered ("My boss found my post"). This
script derives two complementary third-person sets from it, reusing the same
target terms, templates, and threat-model categories:

observer
    The same event narrated about somebody else, by swapping first-person
    pronouns for third-person ones ("Her boss found her post"). Phrases with no
    first-person marker are skipped because the swap would leave them unchanged.

finder
    The discovering party telling the story instead ("I found my boss's Reddit
    account"). Built from each target term's possessive form. Institutional
    targets are excluded by default because "I found the court's account" is not
    a thing anybody posts.

Standard library only, matching the collection scripts.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


CATEGORY_SHEETS = {
    "general.csv": "General",
    "institutional_threats.csv": "Institutional Threats",
    "organizational_threats.csv": "Organizational Threats",
    "ambiguous_others.csv": "Ambiguous Others",
    "interpersonal.csv": "Interpersonal",
}

INSTITUTIONAL_SHEET = "institutional_threats.csv"

FIRST_PERSON_MARKER_RE = re.compile(r"\b(my|i|me|mine)\b", re.IGNORECASE)

# Ordered so longer forms are replaced before their prefixes.
PRONOUN_MAP = {
    "her": {"my": "her", "i": "she", "me": "her", "mine": "hers"},
    "his": {"my": "his", "i": "he", "me": "him", "mine": "his"},
    "their": {"my": "their", "i": "they", "me": "them", "mine": "theirs"},
}

SUBJECT_LEARNING_TEMPLATE = "found my [obj]"
SUBJECT_RE = re.compile(r"^(.*?)\s+found my\b")

FINDER_OBJECT_TEMPLATES = [
    "I found [poss] [obj]",
    "Found [poss] [obj]",
    "I saw [poss] [obj]",
    "I recognized [poss] [obj]",
    "I came across [poss] [obj]",
    "I stumbled across [poss] [obj]",
    "Is this [poss] [obj]",
]

FINDER_OBJECTS = [
    "post",
    "posts",
    "comment",
    "account",
    "Reddit",
    "profile",
    "thread",
    "username",
]

FINDER_TARGET_TEMPLATES = [
    "I found out [subj_lower] posts on Reddit",
    "I found out [subj_lower] is on Reddit",
    "I think [subj_lower] is a redditor",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_workbook_rows(keyword_dir: Path) -> list[dict[str, str]]:
    """Read the per-sheet CSVs, normalizing Category across sheets."""
    rows: list[dict[str, str]] = []
    for filename, category in CATEGORY_SHEETS.items():
        path = keyword_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing keyword sheet: {path}")
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    {
                        "sheet": filename,
                        "category": (row.get("Category") or category).strip(),
                        "target_term": (row.get("Target Term") or "").strip(),
                        "template": (row.get("Template") or "").strip(),
                        "phrase": (row.get("Search Phrase") or "").strip(),
                    }
                )
    return rows


def swap_pronouns(phrase: str, pronoun: str) -> str:
    """Replace first-person pronouns, keeping casing natural for the new word.

    "I" is always capitalized in English, so its casing carries no information
    about sentence position. Capitalization is therefore driven by where the
    match falls, and only then by the source word's own casing.
    """
    mapping = PRONOUN_MAP[pronoun]

    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        replacement = mapping[word.lower()]
        if match.start() == 0:
            return replacement.capitalize()
        if word.lower() == "i":
            return replacement
        if word.isupper() and len(word) > 1:
            return replacement.upper()
        if word[0].isupper():
            return replacement.capitalize()
        return replacement

    return FIRST_PERSON_MARKER_RE.sub(replace, phrase)


def build_observer_rows(
    rows: list[dict[str, str]],
    pronouns: list[str],
) -> tuple[list[dict[str, str]], int]:
    generated: list[dict[str, str]] = []
    seen: set[str] = set()
    skipped = 0

    for row in rows:
        phrase = row["phrase"]
        if not phrase:
            continue
        if not FIRST_PERSON_MARKER_RE.search(phrase):
            skipped += 1
            continue
        for pronoun in pronouns:
            converted = swap_pronouns(phrase, pronoun)
            key = converted.lower()
            if converted == phrase or key in seen:
                continue
            seen.add(key)
            generated.append(
                {
                    "Category": row["category"],
                    "Target Term": row["target_term"],
                    "Template": row["template"],
                    "Pronoun": pronoun,
                    "Search Phrase": converted,
                    "Source Phrase": phrase,
                }
            )
    return generated, skipped


def learn_subject_forms(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Recover each target term's natural subject form from the workbook itself."""
    counters: dict[str, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    meta: dict[str, dict[str, str]] = {}

    for row in rows:
        target = row["target_term"]
        if not target or row["template"] != SUBJECT_LEARNING_TEMPLATE:
            continue
        match = SUBJECT_RE.match(row["phrase"])
        if not match:
            continue
        counters[target][match.group(1)] += 1
        meta.setdefault(
            target, {"category": row["category"], "sheet": row["sheet"]}
        )

    subjects: dict[str, dict[str, str]] = {}
    for target, counter in counters.items():
        subjects[target] = {
            "subject": counter.most_common(1)[0][0],
            "category": meta[target]["category"],
            "sheet": meta[target]["sheet"],
        }
    return subjects


def possessive(subject: str) -> str:
    """Turn a learned subject form into a possessive phrase.

    Plural nouns ending in s take a bare apostrophe ("my parents' post"), but
    singular nouns ending in ss do not ("my boss's post").
    """
    lowered = subject[0].lower() + subject[1:] if subject else subject
    if lowered.endswith("ss"):
        return f"{lowered}'s"
    return f"{lowered}'" if lowered.endswith("s") else f"{lowered}'s"


def build_finder_rows(
    subjects: dict[str, dict[str, str]],
    include_institutional: bool,
) -> list[dict[str, str]]:
    generated: list[dict[str, str]] = []
    seen: set[str] = set()

    for target in sorted(subjects):
        info = subjects[target]
        if info["sheet"] == INSTITUTIONAL_SHEET and not include_institutional:
            continue

        subject = info["subject"]
        subject_lower = subject[0].lower() + subject[1:] if subject else subject
        poss = possessive(subject)

        for template in FINDER_OBJECT_TEMPLATES:
            for obj in FINDER_OBJECTS:
                phrase = template.replace("[poss]", poss).replace("[obj]", obj)
                key = phrase.lower()
                if key in seen:
                    continue
                seen.add(key)
                generated.append(
                    {
                        "Category": info["category"],
                        "Target Term": target,
                        "Template": template,
                        "Object": obj,
                        "Search Phrase": phrase,
                    }
                )

        for template in FINDER_TARGET_TEMPLATES:
            phrase = template.replace("[subj_lower]", subject_lower)
            key = phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            generated.append(
                {
                    "Category": info["category"],
                    "Target Term": target,
                    "Template": template,
                    "Object": "",
                    "Search Phrase": phrase,
                }
            )

    return generated


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keyword-dir",
        default="data/keyword_search_combos",
        help="Directory holding the converted workbook CSVs.",
    )
    parser.add_argument(
        "--pronouns",
        default="her,his,their",
        help="Comma-separated observer pronouns to generate.",
    )
    parser.add_argument(
        "--include-institutional-finder",
        action="store_true",
        help="Also build finder-voice phrases for institutional targets.",
    )
    parser.add_argument(
        "--manifest",
        default="",
        help="Optional path for a JSON generation manifest.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    keyword_dir = Path(args.keyword_dir)
    pronouns = [item.strip() for item in args.pronouns.split(",") if item.strip()]
    unknown = [item for item in pronouns if item not in PRONOUN_MAP]
    if unknown:
        print(f"Unknown pronoun(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    try:
        rows = load_workbook_rows(keyword_dir)
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 2

    observer_rows, skipped = build_observer_rows(rows, pronouns)
    subjects = learn_subject_forms(rows)
    finder_rows = build_finder_rows(
        subjects,
        include_institutional=args.include_institutional_finder,
    )

    observer_path = keyword_dir / "third_person_observer.csv"
    finder_path = keyword_dir / "third_person_finder.csv"
    write_csv(
        observer_path,
        ["Category", "Target Term", "Template", "Pronoun", "Search Phrase", "Source Phrase"],
        observer_rows,
    )
    write_csv(
        finder_path,
        ["Category", "Target Term", "Template", "Object", "Search Phrase"],
        finder_rows,
    )

    manifest = {
        "generator": Path(__file__).name,
        "generated_at_utc": utc_now().isoformat(),
        "source_sheets": sorted(CATEGORY_SHEETS),
        "source_phrase_count": len(rows),
        "observer": {
            "csv": observer_path.name,
            "phrase_count": len(observer_rows),
            "pronouns": pronouns,
            "skipped_no_first_person_marker": skipped,
        },
        "finder": {
            "csv": finder_path.name,
            "phrase_count": len(finder_rows),
            "target_terms": len(
                {row["Target Term"] for row in finder_rows}
            ),
            "object_templates": FINDER_OBJECT_TEMPLATES,
            "target_templates": FINDER_TARGET_TEMPLATES,
            "objects": FINDER_OBJECTS,
            "institutional_targets_included": args.include_institutional_finder,
        },
        "notes": [
            "Observer phrases swap first-person pronouns in the workbook phrases; phrases with no first-person marker are skipped because the swap is a no-op.",
            "Finder phrases use each target term's subject form as learned from the workbook's 'found my [obj]' rows.",
            "Institutional targets are excluded from finder voice by default.",
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
