#!/usr/bin/env python3
"""Run the complete Reddit collection workflow.

This is the one-command reproducibility entry point:

1. Collect visible public submissions from a subreddit.
2. Discover original/source Reddit threads linked by those submissions.
3. Collect comments from those source threads.
4. Write a run manifest with commands, parameters, versions, and output paths.
"""

from __future__ import annotations

import argparse
import gzip
import json
import platform
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_USER_AGENT = (
    "reddit-foundthepost-content-analysis/0.1 "
    "(reproducible public collection; contact: local research script)"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    print(f"\n$ {shlex.join(command)}", flush=True)
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def latest_failure_logs(path: Path) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in read_jsonl(path):
        source_id = str(record.get("source_id", ""))
        if source_id:
            latest[source_id] = record
    return [record for record in latest.values() if "error" in record]


def resolve_output_path(root: Path, path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def write_dataset_readmes(
    snapshot_dir: Path,
    post_manifest: dict[str, Any],
    comment_manifest: dict[str, Any] | None,
) -> None:
    post_rows = read_jsonl(snapshot_dir / "posts_normalized.jsonl")
    created_values = [row.get("created_iso", "") for row in post_rows if row.get("created_iso")]
    source_payload_records = sum(1 for row in post_rows if row.get("source_title"))

    comment_count = comment_manifest.get("comment_count") if comment_manifest else None
    source_thread_count = (
        comment_manifest.get("source_thread_count") if comment_manifest else None
    )
    successful_source_count = (
        comment_manifest.get("successful_source_thread_count")
        if comment_manifest
        else None
    )
    failed_source_count = (
        comment_manifest.get("failed_source_thread_count") if comment_manifest else None
    )
    unresolved_more_count = (
        comment_manifest.get("unresolved_more_count") if comment_manifest else None
    )

    failure_logs = (
        latest_failure_logs(snapshot_dir / "source_comments" / "source_comment_fetch_log.jsonl")
        if comment_manifest
        else []
    )
    inaccessible_lines = "\n".join(
        f"- `{record.get('source_permalink') or record.get('source_id')}`: `{record.get('error')}`"
        for record in failure_logs
    )
    inaccessible_section = (
        f"\nInaccessible source threads:\n\n{inaccessible_lines}\n"
        if failure_logs
        else ""
    )

    snapshot_readme = f"""# r/foundthepost Snapshot

Collected by `scripts/run_full_collection.py`.

## Summary

- Subreddit: `r/{post_manifest.get("subreddit", "foundthepost")}`
- Public submissions collected: {post_manifest.get("post_count")}
- Unique submission IDs: {len({row.get("id") for row in post_rows})}
- Listing pages: {post_manifest.get("page_count")}
- Submission date range: {min(created_values)[:10] if created_values else ""} to {max(created_values)[:10] if created_values else ""} UTC
- Records with source post payloads: {source_payload_records}
- Unique linked source threads discovered for comment collection: {source_thread_count}
- Source threads with public comments collected: {successful_source_count}
- Normalized source comments collected: {comment_count}
- Inaccessible source threads: {failed_source_count}

## Recommended Files

Use `posts_normalized.csv` for post-level spreadsheet or qualitative coding
software. Use `posts_normalized.jsonl` if you want stable machine-readable
records without CSV quoting concerns. Some CSV fields contain embedded
newlines, so count rows with a CSV parser rather than plain line counts.

For source-post comments, use
`source_comments/source_comments_normalized.csv` or
`source_comments/source_comments_normalized.jsonl`.

Use `collection_run_manifest.json` for the exact commands and parameters that
produced this snapshot.

## Caveats

The source comment collection uses Reddit's public comments endpoint plus
`api/morechildren` expansion. It cannot recover deleted, removed, private,
quarantined, or otherwise inaccessible comments.{inaccessible_section}
Reddit returned {unresolved_more_count} hidden comment IDs that its public
`morechildren` endpoint did not resolve; these are tracked in
`source_comments/source_comment_fetch_log.jsonl`.
"""
    (snapshot_dir / "README.md").write_text(snapshot_readme, encoding="utf-8")

    if comment_manifest is None:
        return

    comments_readme = f"""# Source Comment Collection

Comments collected from the original/source Reddit posts linked by the
`r/foundthepost` submissions.

## Summary

- Unique linked source threads discovered: {source_thread_count}
- Publicly accessible source threads collected: {successful_source_count}
- Normalized comments collected: {comment_count}
- Inaccessible source threads: {failed_source_count}
- Unresolved `morechildren` IDs: {unresolved_more_count}
{inaccessible_section}
## Files

- `source_comments_normalized.csv`: comment-level table for analysis.
- `source_comments_normalized.jsonl`: normalized comment records without CSV
  quoting concerns.
- `source_comments_raw.jsonl.gz`: compressed raw Reddit `t1` comment payloads
  with `source_id`.
- `source_posts_for_comments.jsonl`: source-thread discovery and mapping back to
  the `foundthepost` submissions that referenced each source.
- `source_comment_fetch_log.jsonl`: per-source fetch stats, errors, and
  unresolved `morechildren` IDs.
- `source_comment_manifest.json`: collection summary and caveats.

## Key Join Fields

- `source_id`: Reddit submission ID for the original/source post.
- `comment_id`: Reddit comment ID.
- `foundthepost_ids`: semicolon-delimited `r/foundthepost` submission IDs that
  referenced the source thread.
- `source_permalink`: source post permalink.
"""
    comments_dir = snapshot_dir / "source_comments"
    comments_dir.mkdir(parents=True, exist_ok=True)
    (comments_dir / "README.md").write_text(comments_readme, encoding="utf-8")


def compress_raw_comments(comment_dir: Path) -> dict[str, Any]:
    raw_path = comment_dir / "source_comments_raw.jsonl"
    gz_path = comment_dir / "source_comments_raw.jsonl.gz"
    result = {
        "compressed": False,
        "raw_path": str(raw_path),
        "gzip_path": str(gz_path),
    }
    if not raw_path.exists():
        result["reason"] = "raw file not present"
        return result

    with raw_path.open("rb") as raw_handle, gzip.open(gz_path, "wb", compresslevel=9) as gz_handle:
        shutil.copyfileobj(raw_handle, gz_handle)
    raw_size = raw_path.stat().st_size
    gz_size = gz_path.stat().st_size
    raw_path.unlink()
    result.update(
        {
            "compressed": True,
            "raw_bytes": raw_size,
            "gzip_bytes": gz_size,
            "removed_raw": True,
        }
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subreddit", default="foundthepost")
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--post-delay-seconds", type=float, default=1.0)
    parser.add_argument("--comment-delay-seconds", type=float, default=1.5)
    parser.add_argument("--more-batch-size", type=int, default=100)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional page limit for testing the post collector.",
    )
    parser.add_argument(
        "--limit-sources",
        type=int,
        default=None,
        help="Optional source-thread limit for testing the comment collector.",
    )
    parser.add_argument(
        "--skip-comments",
        action="store_true",
        help="Only collect subreddit submissions.",
    )
    parser.add_argument(
        "--skip-morechildren",
        action="store_true",
        help="Do not expand Reddit hidden comment chunks.",
    )
    parser.add_argument(
        "--fail-on-comment-errors",
        action="store_true",
        help=(
            "Exit non-zero when any source thread fails. By default, inaccessible "
            "threads are logged in the manifest and the pipeline still completes."
        ),
    )
    parser.add_argument(
        "--comment-resume-attempts",
        type=int,
        default=2,
        help=(
            "Number of automatic --resume retries for the comment step when any "
            "source thread fails, useful for transient Reddit rate limits."
        ),
    )
    parser.add_argument(
        "--keep-uncompressed-raw-comments",
        action="store_true",
        help=(
            "Leave source_comments_raw.jsonl uncompressed. By default, the runner "
            "compresses it to source_comments_raw.jsonl.gz for GitHub publishing."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    started_at = utc_now()
    commands: list[dict[str, Any]] = []

    post_command = [
        sys.executable,
        "scripts/collect_reddit_posts.py",
        "--subreddit",
        args.subreddit,
        "--out-dir",
        args.out_dir,
        "--delay-seconds",
        str(args.post_delay_seconds),
        "--user-agent",
        args.user_agent,
    ]
    if args.max_pages is not None:
        post_command.extend(["--max-pages", str(args.max_pages)])

    post_result = run_command(post_command, root)
    commands.append(
        {
            "name": "collect_reddit_posts",
            "argv": post_command,
            "returncode": post_result.returncode,
        }
    )
    if post_result.returncode != 0:
        return post_result.returncode

    try:
        post_summary = json.loads(post_result.stdout)
    except json.JSONDecodeError as error:
        print(f"Could not parse post collector output: {error}", file=sys.stderr)
        return 1

    snapshot_dir = resolve_output_path(root, post_summary["out_dir"])
    post_manifest_path = snapshot_dir / "manifest.json"
    post_manifest = load_json(post_manifest_path)

    comment_manifest: dict[str, Any] | None = None
    comment_returncode: int | None = None
    raw_comment_compression: dict[str, Any] | None = None
    final_returncode = 0

    if not args.skip_comments:
        source_jsonl = snapshot_dir / "posts_normalized.jsonl"
        comment_out_dir = snapshot_dir / "source_comments"
        comment_command = [
            sys.executable,
            "scripts/collect_source_comments.py",
            "--source-jsonl",
            str(source_jsonl),
            "--out-dir",
            str(comment_out_dir),
            "--delay-seconds",
            str(args.comment_delay_seconds),
            "--more-batch-size",
            str(args.more_batch_size),
            "--user-agent",
            args.user_agent,
        ]
        if args.limit_sources is not None:
            comment_command.extend(["--limit-sources", str(args.limit_sources)])
        if args.skip_morechildren:
            comment_command.append("--skip-morechildren")

        comment_manifest_path = comment_out_dir / "source_comment_manifest.json"
        for attempt in range(args.comment_resume_attempts + 1):
            attempt_command = list(comment_command)
            if attempt > 0:
                attempt_command.append("--resume")

            comment_result = run_command(attempt_command, root)
            comment_returncode = comment_result.returncode
            commands.append(
                {
                    "name": "collect_source_comments",
                    "attempt": attempt + 1,
                    "argv": attempt_command,
                    "returncode": comment_result.returncode,
                }
            )

            if comment_manifest_path.exists():
                comment_manifest = load_json(comment_manifest_path)
            elif comment_result.returncode != 0:
                return comment_result.returncode

            failed_threads = (
                comment_manifest.get("failed_source_thread_count", 0)
                if comment_manifest
                else 0
            )
            if comment_result.returncode == 0 or failed_threads == 0:
                break

        if (
            comment_returncode != 0
            and args.fail_on_comment_errors
            and comment_manifest is not None
        ):
            final_returncode = comment_returncode

        if comment_manifest is not None and not args.keep_uncompressed_raw_comments:
            raw_comment_compression = compress_raw_comments(comment_out_dir)
            if raw_comment_compression.get("compressed"):
                comment_manifest.setdefault("outputs", {})[
                    "raw_comments"
                ] = "source_comments_raw.jsonl.gz"
                comment_manifest.setdefault("notes", []).append(
                    "source_comments_raw.jsonl was compressed to source_comments_raw.jsonl.gz by the runner for GitHub publishing."
                )
                comment_manifest_path.write_text(
                    json.dumps(comment_manifest, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

    run_manifest = {
        "pipeline": "collect_posts_then_source_comments",
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": utc_now().isoformat(),
        "working_directory": str(root),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "parameters": {
            "subreddit": args.subreddit,
            "out_dir": args.out_dir,
            "post_delay_seconds": args.post_delay_seconds,
            "comment_delay_seconds": args.comment_delay_seconds,
            "more_batch_size": args.more_batch_size,
            "max_pages": args.max_pages,
            "limit_sources": args.limit_sources,
            "skip_comments": args.skip_comments,
            "skip_morechildren": args.skip_morechildren,
            "fail_on_comment_errors": args.fail_on_comment_errors,
            "comment_resume_attempts": args.comment_resume_attempts,
            "keep_uncompressed_raw_comments": args.keep_uncompressed_raw_comments,
        },
        "commands": commands,
        "snapshot_dir": str(snapshot_dir),
        "post_manifest": "manifest.json",
        "source_comment_manifest": (
            "source_comments/source_comment_manifest.json"
            if comment_manifest is not None
            else None
        ),
        "post_count": post_manifest.get("post_count"),
        "source_thread_count": (
            comment_manifest.get("source_thread_count") if comment_manifest else None
        ),
        "source_comment_count": (
            comment_manifest.get("comment_count") if comment_manifest else None
        ),
        "source_comment_failed_thread_count": (
            comment_manifest.get("failed_source_thread_count")
            if comment_manifest
            else None
        ),
        "comment_returncode": comment_returncode,
        "raw_comment_compression": raw_comment_compression,
        "notes": [
            "This reproduces the collection method and output schema.",
            "Live Reddit data can change between runs due to edits, deletions, removals, votes, and new posts/comments.",
            "For bit-for-bit analysis, preserve the generated snapshot directory.",
        ],
    }
    (snapshot_dir / "collection_run_manifest.json").write_text(
        json.dumps(run_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_dataset_readmes(snapshot_dir, post_manifest, comment_manifest)

    print(
        json.dumps(
            {
                "snapshot_dir": str(snapshot_dir),
                "collection_run_manifest": str(
                    snapshot_dir / "collection_run_manifest.json"
                ),
                "post_count": run_manifest["post_count"],
                "source_thread_count": run_manifest["source_thread_count"],
                "source_comment_count": run_manifest["source_comment_count"],
                "source_comment_failed_thread_count": run_manifest[
                    "source_comment_failed_thread_count"
                ],
            },
            indent=2,
        )
    )
    return final_returncode


if __name__ == "__main__":
    sys.exit(main())
