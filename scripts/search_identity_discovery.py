#!/usr/bin/env python3
"""Search Reddit-wide for identity-discovery candidate posts and comments."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REDDIT_BASE = "https://www.reddit.com"
DEFAULT_USER_AGENT = (
    "reddit-foundthepost-content-analysis/0.1 "
    "(broad public Reddit identity-discovery search; contact: local research script)"
)

DEFAULT_QUERY_GROUPS = [
    {
        "group": "high_precision",
        "queries": [
            "found my post",
            "found this post",
            "found my account",
            "found my reddit account",
            "found my throwaway",
            "found out I posted",
            "figured out it was me",
            "recognized my post",
            "confronted me about my post",
            "sent me a screenshot",
        ],
    },
    {
        "group": "user_requested",
        "queries": [
            "found out",
            "used my post",
            "used my reddit post",
            "discovered my account",
            "discovered my post",
        ],
    },
    {
        "group": "reddit_wildcard_expansion",
        "queries": [
            "found my reddit",
            "found my reddit post",
            "found my reddit username",
            "discovered my reddit",
            "discovered my reddit account",
        ],
    },
]

POST_FIELDS = [
    "id",
    "fullname",
    "matched_query_groups",
    "matched_queries",
    "subreddit",
    "title",
    "selftext",
    "text_for_analysis",
    "author",
    "created_utc",
    "created_iso",
    "permalink",
    "url",
    "domain",
    "link_flair_text",
    "link_flair_css_class",
    "link_flair_type",
    "link_flair_richtext",
    "author_flair_text",
    "score",
    "upvote_ratio",
    "estimated_upvotes",
    "estimated_downvotes",
    "num_comments_reported",
    "comments_collected",
    "author_comments_collected",
    "over_18",
    "spoiler",
    "locked",
    "archived",
    "stickied",
    "removed_by_category",
    "comment_fetch_error",
]

COMMENT_FIELDS = [
    "post_id",
    "post_fullname",
    "matched_query_groups",
    "matched_queries",
    "subreddit",
    "post_title",
    "post_author",
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
    "is_author_comment",
    "stickied",
    "collapsed",
    "edited",
    "permalink",
]


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
                return json.loads(response.read().decode("utf-8"))
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
        except (TimeoutError, URLError):
            if attempt < retries:
                time.sleep(2**attempt)
                continue
            raise
    raise RuntimeError(f"failed to fetch {url}")


def full_reddit_url(url_or_path: str) -> str:
    if not url_or_path:
        return ""
    if url_or_path.startswith("/"):
        return f"{REDDIT_BASE}{url_or_path}"
    return url_or_path


def exact_query(query: str) -> str:
    return f'"{query}"'


def unique_query_specs(
    extra_queries: list[str],
    include_defaults: bool,
) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    seen: set[str] = set()
    if include_defaults:
        for group in DEFAULT_QUERY_GROUPS:
            for query in group["queries"]:
                key = query.lower()
                if key not in seen:
                    seen.add(key)
                    specs.append({"group": group["group"], "query": query})
    for query in extra_queries:
        clean = query.strip().strip('"')
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            specs.append({"group": "extra_cli", "query": clean})
    return specs


def estimate_votes(score: Any, upvote_ratio: Any) -> tuple[str, str]:
    try:
        score_value = float(score)
        ratio = float(upvote_ratio)
    except (TypeError, ValueError):
        return "", ""

    denominator = (2 * ratio) - 1
    if denominator <= 0 or score_value < 0:
        return "", ""
    if score_value == 0:
        return "0", "0"

    total_votes = score_value / denominator
    estimated_upvotes = max(0, round(ratio * total_votes))
    estimated_downvotes = max(0, round((1 - ratio) * total_votes))
    return str(estimated_upvotes), str(estimated_downvotes)


def search_posts(
    query_specs: list[dict[str, str]],
    user_agent: str,
    sort: str,
    time_filter: str,
    max_pages_per_query: int,
    delay_seconds: float,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    posts_by_id: dict[str, dict[str, Any]] = {}
    pages: list[dict[str, Any]] = []

    for query_spec in query_specs:
        query = query_spec["query"]
        search_query = exact_query(query)
        after = None
        page_number = 0

        while True:
            page_number += 1
            params = {
                "q": search_query,
                "sort": sort,
                "t": time_filter,
                "limit": "100",
                "raw_json": "1",
                "type": "link",
            }
            if after:
                params["after"] = after
            url = f"{REDDIT_BASE}/search.json?{urlencode(params)}"
            payload = request_json(url, user_agent)
            listing = payload.get("data", {})
            children = listing.get("children", [])

            pages.append(
                {
                    "query_group": query_spec["group"],
                    "query": query,
                    "search_query": search_query,
                    "page_number": page_number,
                    "url": url,
                    "after_in": after,
                    "after_out": listing.get("after"),
                    "dist": listing.get("dist"),
                    "child_fullnames": [
                        child.get("data", {}).get("name", "") for child in children
                    ],
                }
            )

            for child in children:
                data = child.get("data", {})
                post_id = data.get("id")
                if not post_id:
                    continue
                record = posts_by_id.setdefault(
                    post_id,
                    {
                        "raw": child,
                        "matched_queries": set(),
                        "matched_query_groups": set(),
                    },
                )
                record["matched_queries"].add(query)
                record["matched_query_groups"].add(query_spec["group"])

            after = listing.get("after")
            if not after or not children:
                break
            if page_number >= max_pages_per_query:
                break
            time.sleep(delay_seconds)

        time.sleep(delay_seconds)

    return posts_by_id, pages


def iter_comment_nodes(
    children: list[dict[str, Any]],
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
                comments.extend(
                    iter_comment_nodes(
                        replies.get("data", {}).get("children", []),
                        more_ids,
                    )
                )
        elif kind == "more":
            for child_id in data.get("children", []) or []:
                if child_id:
                    more_ids.add(str(child_id).lower().removeprefix("t1_"))
    return comments


def fetch_morechildren(
    post_id: str,
    child_ids: list[str],
    user_agent: str,
) -> list[dict[str, Any]]:
    params = {
        "api_type": "json",
        "link_id": f"t3_{post_id}",
        "children": ",".join(child_ids),
        "raw_json": "1",
    }
    url = f"{REDDIT_BASE}/api/morechildren.json?{urlencode(params)}"
    payload = request_json(url, user_agent)
    return payload.get("json", {}).get("data", {}).get("things", [])


def collect_comments(
    post_id: str,
    user_agent: str,
    delay_seconds: float,
    more_batch_size: int,
    expand_morechildren: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {"limit": "500", "depth": "10", "raw_json": "1"}
    url = f"{REDDIT_BASE}/comments/{post_id}.json?{urlencode(params)}"
    payload = request_json(url, user_agent)
    time.sleep(delay_seconds)

    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError("unexpected comments response shape")

    more_ids: set[str] = set()
    seen_comment_ids: set[str] = set()
    raw_comments: list[dict[str, Any]] = []

    for child in iter_comment_nodes(payload[1].get("data", {}).get("children", []), more_ids):
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
            nested_more_ids: set[str] = set()
            for child in iter_comment_nodes(
                fetch_morechildren(post_id, batch, user_agent),
                nested_more_ids,
            ):
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
            time.sleep(delay_seconds)

    log = {
        "post_id": post_id,
        "fetch_url": url,
        "collected_comment_count": len(raw_comments),
        "initial_more_ids": len(more_ids),
        "attempted_more_ids": len(attempted_more_ids),
        "unresolved_more_count": len(attempted_more_ids - seen_comment_ids),
        "unresolved_more_ids": sorted(attempted_more_ids - seen_comment_ids),
    }
    return raw_comments, log


def normalize_post(record: dict[str, Any], comment_stats: dict[str, Any]) -> dict[str, Any]:
    data = record["raw"].get("data", {})
    title = data.get("title") or ""
    selftext = data.get("selftext") or ""
    estimated_upvotes, estimated_downvotes = estimate_votes(
        data.get("score"),
        data.get("upvote_ratio"),
    )
    permalink = data.get("permalink") or ""
    return {
        "id": data.get("id") or "",
        "fullname": data.get("name") or "",
        "matched_query_groups": ";".join(sorted(record["matched_query_groups"])),
        "matched_queries": ";".join(sorted(record["matched_queries"])),
        "subreddit": data.get("subreddit") or "",
        "title": title,
        "selftext": selftext,
        "text_for_analysis": "\n\n".join(part for part in [title, selftext] if part),
        "author": data.get("author") or "",
        "created_utc": data.get("created_utc") or "",
        "created_iso": to_iso(data.get("created_utc")),
        "permalink": full_reddit_url(permalink),
        "url": data.get("url") or "",
        "domain": data.get("domain") or "",
        "link_flair_text": data.get("link_flair_text") or "",
        "link_flair_css_class": data.get("link_flair_css_class") or "",
        "link_flair_type": data.get("link_flair_type") or "",
        "link_flair_richtext": json.dumps(
            data.get("link_flair_richtext") or [],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "author_flair_text": data.get("author_flair_text") or "",
        "score": data.get("score"),
        "upvote_ratio": data.get("upvote_ratio"),
        "estimated_upvotes": estimated_upvotes,
        "estimated_downvotes": estimated_downvotes,
        "num_comments_reported": data.get("num_comments"),
        "comments_collected": comment_stats.get("comments_collected", 0),
        "author_comments_collected": comment_stats.get("author_comments_collected", 0),
        "over_18": data.get("over_18"),
        "spoiler": data.get("spoiler"),
        "locked": data.get("locked"),
        "archived": data.get("archived"),
        "stickied": data.get("stickied"),
        "removed_by_category": data.get("removed_by_category") or "",
        "comment_fetch_error": comment_stats.get("comment_fetch_error", ""),
    }


def normalize_comment(child: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    data = child.get("data", {})
    post_data = record["raw"].get("data", {})
    post_author = post_data.get("author") or ""
    author = data.get("author") or ""
    permalink = data.get("permalink") or ""
    is_author_comment = bool(data.get("is_submitter")) or (
        bool(author) and author == post_author
    )
    return {
        "post_id": post_data.get("id") or "",
        "post_fullname": post_data.get("name") or "",
        "matched_query_groups": ";".join(sorted(record["matched_query_groups"])),
        "matched_queries": ";".join(sorted(record["matched_queries"])),
        "subreddit": post_data.get("subreddit") or "",
        "post_title": post_data.get("title") or "",
        "post_author": post_author,
        "comment_id": data.get("id") or "",
        "comment_fullname": data.get("name") or "",
        "parent_id": data.get("parent_id") or "",
        "link_id": data.get("link_id") or "",
        "depth": data.get("depth"),
        "author": author,
        "body": data.get("body") or "",
        "created_utc": data.get("created_utc") or "",
        "created_iso": to_iso(data.get("created_utc")),
        "score": data.get("score"),
        "controversiality": data.get("controversiality"),
        "distinguished": data.get("distinguished") or "",
        "is_submitter": data.get("is_submitter"),
        "is_author_comment": is_author_comment,
        "stickied": data.get("stickied"),
        "collapsed": data.get("collapsed"),
        "edited": data.get("edited"),
        "permalink": full_reddit_url(permalink),
    }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="data/broad_identity_search")
    parser.add_argument("--sort", default="relevance", choices=["relevance", "hot", "top", "new", "comments"])
    parser.add_argument("--time-filter", default="all", choices=["hour", "day", "week", "month", "year", "all"])
    parser.add_argument("--max-pages-per-query", type=int, default=3)
    parser.add_argument("--max-posts", type=int, default=0, help="0 means no cap after deduplication.")
    parser.add_argument("--search-delay-seconds", type=float, default=1.0)
    parser.add_argument("--comment-delay-seconds", type=float, default=1.5)
    parser.add_argument("--more-batch-size", type=int, default=100)
    parser.add_argument("--skip-comments", action="store_true")
    parser.add_argument("--skip-morechildren", action="store_true")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Add an extra exact-phrase query. May be repeated.",
    )
    parser.add_argument(
        "--no-default-queries",
        action="store_true",
        help="Use only --query values instead of the built-in keyword list.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now()
    snapshot = started_at.strftime("identity_search_%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir) / snapshot
    out_dir.mkdir(parents=True, exist_ok=True)

    query_specs = unique_query_specs(
        args.query,
        include_defaults=not args.no_default_queries,
    )
    if not query_specs:
        print("No queries to run. Remove --no-default-queries or pass --query.", file=sys.stderr)
        return 2
    posts_by_id, search_pages = search_posts(
        query_specs=query_specs,
        user_agent=args.user_agent,
        sort=args.sort,
        time_filter=args.time_filter,
        max_pages_per_query=args.max_pages_per_query,
        delay_seconds=args.search_delay_seconds,
    )

    records = sorted(
        posts_by_id.values(),
        key=lambda record: record["raw"].get("data", {}).get("created_utc") or 0,
        reverse=True,
    )
    if args.max_posts > 0:
        records = records[: args.max_posts]

    comment_rows: list[dict[str, Any]] = []
    author_comment_rows: list[dict[str, Any]] = []
    comment_logs: list[dict[str, Any]] = []
    post_comment_stats: dict[str, dict[str, Any]] = {}

    if not args.skip_comments:
        for index, record in enumerate(records, start=1):
            post_data = record["raw"].get("data", {})
            post_id = post_data.get("id")
            if not post_id:
                continue
            try:
                raw_comments, comment_log = collect_comments(
                    post_id=post_id,
                    user_agent=args.user_agent,
                    delay_seconds=args.comment_delay_seconds,
                    more_batch_size=args.more_batch_size,
                    expand_morechildren=not args.skip_morechildren,
                )
                normalized_comments = [
                    normalize_comment(child, record) for child in raw_comments
                ]
                author_comments = [
                    row for row in normalized_comments if row["is_author_comment"]
                ]
                comment_rows.extend(normalized_comments)
                author_comment_rows.extend(author_comments)
                post_comment_stats[post_id] = {
                    "comments_collected": len(normalized_comments),
                    "author_comments_collected": len(author_comments),
                }
            except Exception as error:  # noqa: BLE001 - logged for collection audit.
                comment_log = {
                    "post_id": post_id,
                    "collected_comment_count": 0,
                    "error": repr(error),
                }
                post_comment_stats[post_id] = {
                    "comments_collected": 0,
                    "author_comments_collected": 0,
                    "comment_fetch_error": repr(error),
                }

            comment_log["post_index"] = index
            comment_log["post_total"] = len(records)
            comment_logs.append(comment_log)
            print(
                f"[{index}/{len(records)}] {post_id}: "
                f"{comment_log.get('collected_comment_count', 0)} comments",
                file=sys.stderr,
                flush=True,
            )

    post_rows = [
        normalize_post(
            record,
            post_comment_stats.get(
                record["raw"].get("data", {}).get("id", ""),
                {},
            ),
        )
        for record in records
    ]

    write_csv(out_dir / "posts.csv", POST_FIELDS, post_rows)
    write_csv(out_dir / "comments.csv", COMMENT_FIELDS, comment_rows)
    write_csv(out_dir / "author_comments.csv", COMMENT_FIELDS, author_comment_rows)
    (out_dir / "search_pages.json").write_text(
        json.dumps(search_pages, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_jsonl(out_dir / "comment_fetch_log.jsonl", comment_logs)

    manifest = {
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": utc_now().isoformat(),
        "source": "Reddit public search and comments JSON endpoints",
        "query_specs": query_specs,
        "sort": args.sort,
        "time_filter": args.time_filter,
        "max_pages_per_query": args.max_pages_per_query,
        "max_posts": args.max_posts,
        "post_count": len(post_rows),
        "comment_count": len(comment_rows),
        "author_comment_count": len(author_comment_rows),
        "comment_fetch_error_count": sum(1 for log in comment_logs if "error" in log),
        "outputs": {
            "posts": "posts.csv",
            "comments": "comments.csv",
            "author_comments": "author_comments.csv",
            "search_pages": "search_pages.json",
            "comment_fetch_log": "comment_fetch_log.jsonl",
        },
        "notes": [
            "Reddit search is not guaranteed to be exhaustive or stable over time.",
            "Queries are exact phrase searches; Reddit wildcard-style phrases are expanded explicitly.",
            "Post up/downvotes are estimates derived from score and upvote_ratio because Reddit does not expose exact up/downvote counts.",
            "author_comments.csv contains comments where Reddit marked is_submitter or the comment author matches the post author.",
        ],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps({"out_dir": str(out_dir), **manifest}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
