#!/usr/bin/env python3
"""Collect comments from Reddit source posts linked by r/foundthepost records."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REDDIT_BASE = "https://www.reddit.com"
DEFAULT_USER_AGENT = (
    "reddit-foundthepost-content-analysis/0.1 "
    "(public source comment collection; contact: local research script)"
)

COMMENT_FIELDS = [
    "source_id",
    "source_fullname",
    "source_subreddit",
    "source_title",
    "source_permalink",
    "foundthepost_ids",
    "foundthepost_titles",
    "comment_id",
    "comment_fullname",
    "parent_id",
    "link_id",
    "depth",
    "author",
    "body",
    "created_utc",
    "created_iso",
    "score",
    "controversiality",
    "distinguished",
    "is_submitter",
    "stickied",
    "collapsed",
    "edited",
    "permalink",
]

REDDIT_POST_RE = re.compile(
    r"(?i)(?:(?:https?://)?(?:www\.|old\.|new\.|np\.)?reddit\.com)?"
    r"(?P<path>/r/(?P<subreddit>[^/\s\]\)]+)/comments/(?P<post_id>[a-z0-9]+)"
    r"(?:/[^\s\]\)]*)?)"
)


@dataclass
class SourceReference:
    source_id: str
    source_fullname: str
    source_subreddit: str = ""
    source_permalink: str = ""
    source_url: str = ""
    source_title: str = ""
    expected_num_comments: int | None = None
    foundthepost_ids: set[str] = field(default_factory=set)
    foundthepost_titles: dict[str, str] = field(default_factory=dict)
    reference_types: set[str] = field(default_factory=set)
    matched_urls: set[str] = field(default_factory=set)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(timestamp: float | int | str | None) -> str:
    if timestamp in (None, ""):
        return ""
    return datetime.fromtimestamp(float(timestamp), timezone.utc).isoformat()


def request_json(url: str, user_agent: str, retries: int = 6) -> Any:
    request = Request(url, headers={"User-Agent": user_agent})
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=45) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except HTTPError as error:
            if error.code == 429 and attempt < retries:
                retry_after = error.headers.get("Retry-After")
                delay = int(retry_after) if retry_after and retry_after.isdigit() else 60
                time.sleep(delay)
                continue
            if 500 <= error.code < 600 and attempt < retries:
                time.sleep(2**attempt)
                continue
            raise
        except (URLError, TimeoutError):
            if attempt < retries:
                time.sleep(2**attempt)
                continue
            raise
    raise RuntimeError(f"failed to fetch {url}")


def full_reddit_url(url_or_path: str) -> str:
    if not url_or_path:
        return ""
    clean = url_or_path.replace("\\_", "_")
    if clean.startswith("/"):
        return f"{REDDIT_BASE}{clean}"
    return clean


def find_reddit_post_links(text: str) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    if not text:
        return matches
    clean = text.replace("\\_", "_")
    for match in REDDIT_POST_RE.finditer(clean):
        path = match.group("path")
        matches.append(
            {
                "post_id": match.group("post_id").lower(),
                "subreddit": match.group("subreddit"),
                "url": full_reddit_url(path),
            }
        )
    return matches


def parse_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def merge_source(
    sources: dict[str, SourceReference],
    row: dict[str, Any],
    post_id: str,
    subreddit: str = "",
    permalink: str = "",
    url: str = "",
    reference_type: str = "",
) -> None:
    post_id = post_id.lower().removeprefix("t3_")
    if not post_id or post_id == str(row.get("id", "")).lower():
        return

    source = sources.setdefault(
        post_id,
        SourceReference(source_id=post_id, source_fullname=f"t3_{post_id}"),
    )
    if subreddit and not source.source_subreddit:
        source.source_subreddit = subreddit
    if permalink and not source.source_permalink:
        source.source_permalink = full_reddit_url(permalink)
    if url and not source.source_url:
        source.source_url = full_reddit_url(url)
    if row.get("source_title") and not source.source_title:
        source.source_title = row["source_title"]

    expected = parse_int(row.get("source_num_comments"))
    if expected is not None and source.expected_num_comments is None:
        source.expected_num_comments = expected

    foundthepost_id = str(row.get("id", ""))
    if foundthepost_id:
        source.foundthepost_ids.add(foundthepost_id)
        source.foundthepost_titles[foundthepost_id] = str(row.get("title", ""))
    if reference_type:
        source.reference_types.add(reference_type)
    if permalink:
        source.matched_urls.add(full_reddit_url(permalink))
    if url:
        source.matched_urls.add(full_reddit_url(url))


def discover_sources(rows: list[dict[str, Any]]) -> list[SourceReference]:
    sources: dict[str, SourceReference] = {}

    for row in rows:
        crosspost_parent = str(row.get("crosspost_parent", ""))
        if crosspost_parent.startswith("t3_"):
            merge_source(
                sources,
                row,
                crosspost_parent,
                subreddit=str(row.get("source_subreddit", "")),
                permalink=str(row.get("source_permalink", "")),
                url=str(row.get("source_url", "")) or str(row.get("url", "")),
                reference_type="crosspost_parent",
            )

        source_permalink = str(row.get("source_permalink", ""))
        for link in find_reddit_post_links(source_permalink):
            merge_source(
                sources,
                row,
                link["post_id"],
                subreddit=link["subreddit"],
                permalink=link["url"],
                reference_type="source_permalink",
            )

        row_url = str(row.get("url", ""))
        for link in find_reddit_post_links(row_url):
            if link["subreddit"].lower() == "foundthepost":
                continue
            merge_source(
                sources,
                row,
                link["post_id"],
                subreddit=link["subreddit"],
                permalink=link["url"],
                reference_type="linked_url",
            )

        selftext = str(row.get("selftext", ""))
        for link in find_reddit_post_links(selftext):
            if link["subreddit"].lower() == "foundthepost":
                continue
            merge_source(
                sources,
                row,
                link["post_id"],
                subreddit=link["subreddit"],
                permalink=link["url"],
                reference_type="selftext_link",
            )

    return sorted(sources.values(), key=lambda source: source.source_id)


def iter_comment_nodes(
    children: list[dict[str, Any]],
    depth: int,
    more_ids: set[str],
) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for child in children:
        kind = child.get("kind")
        data = child.get("data", {})
        if kind == "t1":
            comments.append(child)
            replies = data.get("replies")
            if isinstance(replies, dict):
                reply_children = replies.get("data", {}).get("children", [])
                comments.extend(iter_comment_nodes(reply_children, depth + 1, more_ids))
        elif kind == "more":
            for child_id in data.get("children", []) or []:
                if child_id:
                    more_ids.add(str(child_id).lower().removeprefix("t1_"))
    return comments


def normalize_comment(
    child: dict[str, Any],
    source: SourceReference,
    source_post: dict[str, Any],
) -> dict[str, Any]:
    data = child.get("data", {})
    permalink = data.get("permalink") or ""
    foundthepost_ids = sorted(source.foundthepost_ids)
    return {
        "source_id": source.source_id,
        "source_fullname": source.source_fullname,
        "source_subreddit": source_post.get("subreddit") or source.source_subreddit,
        "source_title": source_post.get("title") or source.source_title,
        "source_permalink": (
            full_reddit_url(source_post.get("permalink") or source.source_permalink)
        ),
        "foundthepost_ids": ";".join(foundthepost_ids),
        "foundthepost_titles": " | ".join(
            source.foundthepost_titles.get(post_id, "") for post_id in foundthepost_ids
        ),
        "comment_id": data.get("id") or "",
        "comment_fullname": data.get("name") or "",
        "parent_id": data.get("parent_id") or "",
        "link_id": data.get("link_id") or "",
        "depth": data.get("depth"),
        "author": data.get("author") or "",
        "body": data.get("body") or "",
        "created_utc": data.get("created_utc") or "",
        "created_iso": to_iso(data.get("created_utc")),
        "score": data.get("score"),
        "controversiality": data.get("controversiality"),
        "distinguished": data.get("distinguished") or "",
        "is_submitter": data.get("is_submitter"),
        "stickied": data.get("stickied"),
        "collapsed": data.get("collapsed"),
        "edited": data.get("edited"),
        "permalink": full_reddit_url(permalink),
    }


def fetch_morechildren(
    source_id: str,
    child_ids: list[str],
    user_agent: str,
) -> list[dict[str, Any]]:
    params = {
        "api_type": "json",
        "link_id": f"t3_{source_id}",
        "children": ",".join(child_ids),
        "raw_json": "1",
    }
    url = f"{REDDIT_BASE}/api/morechildren.json?{urlencode(params)}"
    payload = request_json(url, user_agent)
    return payload.get("json", {}).get("data", {}).get("things", [])


def collect_source_comments(
    source: SourceReference,
    user_agent: str,
    delay_seconds: float,
    more_batch_size: int,
    expand_morechildren: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    params = {"limit": "500", "depth": "10", "raw_json": "1"}
    url = f"{REDDIT_BASE}/comments/{source.source_id}.json?{urlencode(params)}"
    payload = request_json(url, user_agent)
    time.sleep(delay_seconds)

    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError("unexpected comments response shape")

    post_children = payload[0].get("data", {}).get("children", [])
    source_post = post_children[0].get("data", {}) if post_children else {}
    if source_post.get("id"):
        source.source_id = source_post["id"]
        source.source_fullname = source_post.get("name") or f"t3_{source.source_id}"
    if source_post.get("subreddit"):
        source.source_subreddit = source_post["subreddit"]
    if source_post.get("permalink"):
        source.source_permalink = full_reddit_url(source_post["permalink"])
    if source_post.get("title"):
        source.source_title = source_post["title"]

    seen_comment_ids: set[str] = set()
    more_ids: set[str] = set()
    raw_comments: list[dict[str, Any]] = []

    comment_children = payload[1].get("data", {}).get("children", [])
    for child in iter_comment_nodes(comment_children, 0, more_ids):
        comment_id = child.get("data", {}).get("id")
        if comment_id and comment_id not in seen_comment_ids:
            seen_comment_ids.add(comment_id)
            raw_comments.append(child)

    attempted_more_ids: set[str] = set()
    if expand_morechildren:
        queue = deque(sorted(more_ids - seen_comment_ids))
        queued_more_ids = set(queue)

        while queue:
            batch: list[str] = []
            while queue and len(batch) < more_batch_size:
                child_id = queue.popleft()
                queued_more_ids.discard(child_id)
                if child_id not in seen_comment_ids and child_id not in attempted_more_ids:
                    batch.append(child_id)

            if not batch:
                continue

            attempted_more_ids.update(batch)
            things = fetch_morechildren(source.source_id, batch, user_agent)
            time.sleep(delay_seconds)

            nested_more_ids: set[str] = set()
            for child in iter_comment_nodes(things, 0, nested_more_ids):
                comment_id = child.get("data", {}).get("id")
                if comment_id and comment_id not in seen_comment_ids:
                    seen_comment_ids.add(comment_id)
                    raw_comments.append(child)

            for child_id in nested_more_ids:
                if (
                    child_id not in seen_comment_ids
                    and child_id not in attempted_more_ids
                    and child_id not in queued_more_ids
                ):
                    queue.append(child_id)
                    queued_more_ids.add(child_id)

    normalized = [
        normalize_comment(child, source=source, source_post=source_post)
        for child in raw_comments
    ]
    unresolved_more_ids = sorted(attempted_more_ids - seen_comment_ids)
    thread_log = {
        "source_id": source.source_id,
        "source_fullname": source.source_fullname,
        "source_subreddit": source.source_subreddit,
        "source_title": source.source_title,
        "source_permalink": source.source_permalink,
        "foundthepost_ids": sorted(source.foundthepost_ids),
        "reference_types": sorted(source.reference_types),
        "expected_num_comments": source.expected_num_comments,
        "reported_num_comments": source_post.get("num_comments"),
        "collected_comment_count": len(normalized),
        "initial_more_ids": len(more_ids),
        "attempted_more_ids": len(attempted_more_ids),
        "unresolved_more_ids": unresolved_more_ids,
        "unresolved_more_count": len(unresolved_more_ids),
        "fetch_url": url,
    }
    return thread_log, raw_comments, normalized


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_latest_logs(path: Path) -> dict[str, dict[str, Any]]:
    logs: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return logs
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            source_id = str(record.get("source_id", ""))
            if source_id:
                logs[source_id] = record
    return logs


def count_jsonl_records(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def write_jsonl_record(handle: Any, record: dict[str, Any]) -> None:
    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
    handle.write("\n")
    handle.flush()


def source_to_record(source: SourceReference) -> dict[str, Any]:
    foundthepost_ids = sorted(source.foundthepost_ids)
    return {
        "source_id": source.source_id,
        "source_fullname": source.source_fullname,
        "source_subreddit": source.source_subreddit,
        "source_permalink": source.source_permalink,
        "source_url": source.source_url,
        "source_title": source.source_title,
        "expected_num_comments": source.expected_num_comments,
        "foundthepost_ids": foundthepost_ids,
        "foundthepost_titles": {
            post_id: source.foundthepost_titles.get(post_id, "")
            for post_id in foundthepost_ids
        },
        "reference_types": sorted(source.reference_types),
        "matched_urls": sorted(source.matched_urls),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-jsonl",
        required=True,
        help="Normalized foundthepost posts JSONL from the post collector.",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory. Defaults to SOURCE_JSONL parent / source_comments.",
    )
    parser.add_argument("--delay-seconds", type=float, default=0.25)
    parser.add_argument("--more-batch-size", type=int, default=100)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--limit-sources",
        type=int,
        default=None,
        help="Optional source-thread limit for testing.",
    )
    parser.add_argument(
        "--skip-morechildren",
        action="store_true",
        help="Only collect the initial comments tree; leave hidden morechildren unresolved.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Append to an existing output directory and skip source threads already fetched successfully.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_jsonl = Path(args.source_jsonl)
    out_dir = Path(args.out_dir) if args.out_dir else source_jsonl.parent / "source_comments"
    out_dir.mkdir(parents=True, exist_ok=True)

    started_at = utc_now()
    rows = read_jsonl(source_jsonl)
    sources = discover_sources(rows)
    if args.limit_sources is not None:
        sources = sources[: args.limit_sources]

    log_path = out_dir / "source_comment_fetch_log.jsonl"
    previous_logs = read_latest_logs(log_path) if args.resume else {}
    completed_source_ids = {
        source_id for source_id, log in previous_logs.items() if "error" not in log
    }
    sources_to_collect = [
        source for source in sources if source.source_id not in completed_source_ids
    ]
    source_indices = {
        source.source_id: index for index, source in enumerate(sources, start=1)
    }

    with (out_dir / "source_posts_for_comments.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for source in sources:
            write_jsonl_record(handle, source_to_record(source))

    total_comments = 0
    successful_sources = 0
    failed_sources = 0
    logs: list[dict[str, Any]] = []
    raw_mode = "a" if args.resume else "w"
    csv_mode = "a" if args.resume else "w"
    log_mode = "a" if args.resume else "w"
    csv_path = out_dir / "source_comments_normalized.csv"
    should_write_csv_header = not (
        args.resume and csv_path.exists() and csv_path.stat().st_size > 0
    )

    with (
        (out_dir / "source_comments_raw.jsonl").open(
            raw_mode, encoding="utf-8"
        ) as raw_handle,
        (out_dir / "source_comments_normalized.jsonl").open(
            raw_mode, encoding="utf-8"
        ) as normalized_handle,
        csv_path.open(
            csv_mode, encoding="utf-8", newline=""
        ) as csv_handle,
        log_path.open(log_mode, encoding="utf-8") as log_handle,
    ):
        writer = csv.DictWriter(csv_handle, fieldnames=COMMENT_FIELDS)
        if should_write_csv_header:
            writer.writeheader()

        for source in sources_to_collect:
            index = source_indices[source.source_id]
            try:
                thread_log, raw_comments, normalized_comments = collect_source_comments(
                    source=source,
                    user_agent=args.user_agent,
                    delay_seconds=args.delay_seconds,
                    more_batch_size=args.more_batch_size,
                    expand_morechildren=not args.skip_morechildren,
                )
                successful_sources += 1
                total_comments += len(normalized_comments)

                for child in raw_comments:
                    write_jsonl_record(
                        raw_handle,
                        {"source_id": source.source_id, "comment": child},
                    )
                for comment in normalized_comments:
                    write_jsonl_record(normalized_handle, comment)
                    writer.writerow(comment)
                csv_handle.flush()
            except Exception as error:  # noqa: BLE001 - logged for collection audit.
                failed_sources += 1
                thread_log = {
                    "source_id": source.source_id,
                    "source_fullname": source.source_fullname,
                    "source_subreddit": source.source_subreddit,
                    "source_permalink": source.source_permalink,
                    "foundthepost_ids": sorted(source.foundthepost_ids),
                    "reference_types": sorted(source.reference_types),
                    "expected_num_comments": source.expected_num_comments,
                    "collected_comment_count": 0,
                    "error": repr(error),
                }

            thread_log["source_index"] = index
            thread_log["source_total"] = len(sources)
            logs.append(thread_log)
            write_jsonl_record(log_handle, thread_log)
            print(
                f"[{index}/{len(sources)}] {source.source_id}: "
                f"{thread_log.get('collected_comment_count', 0)} comments",
                file=sys.stderr,
                flush=True,
            )

    final_logs = read_latest_logs(log_path)
    total_comments = count_jsonl_records(out_dir / "source_comments_normalized.jsonl")
    successful_sources = sum(
        1
        for source in sources
        if source.source_id in final_logs and "error" not in final_logs[source.source_id]
    )
    failed_sources = sum(
        1
        for source in sources
        if source.source_id in final_logs and "error" in final_logs[source.source_id]
    )
    unresolved_more_count = sum(
        int(final_logs.get(source.source_id, {}).get("unresolved_more_count", 0))
        for source in sources
    )

    manifest = {
        "source_jsonl": str(source_jsonl),
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": utc_now().isoformat(),
        "source_thread_count": len(sources),
        "source_thread_count_this_run": len(sources_to_collect),
        "skipped_completed_source_thread_count": len(completed_source_ids),
        "successful_source_thread_count": successful_sources,
        "failed_source_thread_count": failed_sources,
        "comment_count": total_comments,
        "delay_seconds": args.delay_seconds,
        "more_batch_size": args.more_batch_size,
        "expanded_morechildren": not args.skip_morechildren,
        "resumed": args.resume,
        "unresolved_more_count": unresolved_more_count,
        "outputs": {
            "source_posts": "source_posts_for_comments.jsonl",
            "raw_comments": "source_comments_raw.jsonl",
            "normalized_jsonl": "source_comments_normalized.jsonl",
            "normalized_csv": "source_comments_normalized.csv",
            "fetch_log": "source_comment_fetch_log.jsonl",
        },
        "notes": [
            "Collected comments from Reddit source threads linked by the foundthepost records.",
            "Includes crosspost parents, direct Reddit post/comment links, and Reddit links found in selftext.",
            "Deleted, removed, private, quarantined, or otherwise inaccessible comments cannot be recovered.",
            "unresolved_more_count records comment IDs Reddit's public morechildren endpoint did not return.",
        ],
    }
    (out_dir / "source_comment_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({"out_dir": str(out_dir), **manifest}, indent=2))
    return 0 if failed_sources == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
