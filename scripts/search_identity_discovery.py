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
    "post_id",
    "fullname",
    "reddit_kind",
    "subreddit_id",
    "subreddit_name_prefixed",
    "author_fullname",
    "retrieved_at_utc",
    "search_sort",
    "search_time_filter",
    "search_rank_min",
    "search_rank_all",
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
    "post_reddit_kind",
    "post_permalink",
    "subreddit_id",
    "subreddit_name_prefixed",
    "author_fullname",
    "retrieved_at_utc",
    "search_sort",
    "search_time_filter",
    "post_search_rank_min",
    "post_search_rank_all",
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

REVIEW_POST_FIELDS = [
    "include_for_analysis",
    "review_status",
    "case_type",
    "review_notes",
    "post_id",
    "post_fullname",
    "subreddit",
    "created_iso",
    "title",
    "selftext_excerpt",
    "author_comment_excerpt",
    "matched_queries",
    "matched_query_groups",
    "search_rank_min",
    "permalink",
    "score",
    "upvote_ratio",
    "estimated_upvotes",
    "estimated_downvotes",
    "num_comments_reported",
    "comments_collected",
    "author_comments_collected",
    "comment_fetch_error",
]

RUN_STATE_FILE = "run_state.json"
SEARCH_RECORDS_FILE = "search_records.jsonl"
POST_COMMENT_STATS_FILE = "post_comment_stats.json"


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

            for child_index, child in enumerate(children, start=1):
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
                        "search_ranks": [],
                    },
                )
                record["matched_queries"].add(query)
                record["matched_query_groups"].add(query_spec["group"])
                record["search_ranks"].append(
                    {
                        "query_group": query_spec["group"],
                        "query": query,
                        "rank": ((page_number - 1) * 100) + child_index,
                        "page_number": page_number,
                        "page_rank": child_index,
                    }
                )

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


def search_rank_min(record: dict[str, Any]) -> str:
    ranks = [rank["rank"] for rank in record.get("search_ranks", []) if rank.get("rank")]
    return str(min(ranks)) if ranks else ""


def search_rank_all_json(record: dict[str, Any]) -> str:
    return json.dumps(
        record.get("search_ranks", []),
        ensure_ascii=False,
        sort_keys=True,
    )


def reddit_kind(fullname: str) -> str:
    return fullname.split("_", 1)[0] if "_" in fullname else ""


def sheet_text(value: Any, max_chars: int = 1200) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    if len(text) > max_chars:
        text = f"{text[: max_chars - 3]}..."
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def author_comment_excerpt(
    post_id: str,
    author_comment_rows: list[dict[str, Any]],
    max_chars: int = 1200,
) -> str:
    snippets = []
    for row in author_comment_rows:
        if row.get("post_id") != post_id:
            continue
        created = row.get("created_iso") or ""
        body = sheet_text(row.get("body", ""), max_chars=300)
        snippets.append(f"{created}: {body}" if created else body)
        if len(" | ".join(snippets)) >= max_chars:
            break
    return sheet_text(" | ".join(snippets), max_chars=max_chars)


def normalize_post(
    record: dict[str, Any],
    comment_stats: dict[str, Any],
    retrieved_at_utc: str,
    search_sort: str,
    search_time_filter: str,
) -> dict[str, Any]:
    data = record["raw"].get("data", {})
    title = data.get("title") or ""
    selftext = data.get("selftext") or ""
    estimated_upvotes, estimated_downvotes = estimate_votes(
        data.get("score"),
        data.get("upvote_ratio"),
    )
    permalink = data.get("permalink") or ""
    fullname = data.get("name") or ""
    return {
        "id": data.get("id") or "",
        "post_id": data.get("id") or "",
        "fullname": fullname,
        "reddit_kind": reddit_kind(fullname),
        "subreddit_id": data.get("subreddit_id") or "",
        "subreddit_name_prefixed": data.get("subreddit_name_prefixed") or "",
        "author_fullname": data.get("author_fullname") or "",
        "retrieved_at_utc": retrieved_at_utc,
        "search_sort": search_sort,
        "search_time_filter": search_time_filter,
        "search_rank_min": search_rank_min(record),
        "search_rank_all": search_rank_all_json(record),
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


def normalize_review_post(
    post_row: dict[str, Any],
    author_comment_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    post_id = post_row.get("post_id", "")
    return {
        "include_for_analysis": "",
        "review_status": "",
        "case_type": "",
        "review_notes": "",
        "post_id": post_id,
        "post_fullname": post_row.get("fullname", ""),
        "subreddit": post_row.get("subreddit", ""),
        "created_iso": post_row.get("created_iso", ""),
        "title": sheet_text(post_row.get("title", ""), max_chars=500),
        "selftext_excerpt": sheet_text(post_row.get("selftext", ""), max_chars=1200),
        "author_comment_excerpt": author_comment_excerpt(post_id, author_comment_rows),
        "matched_queries": post_row.get("matched_queries", ""),
        "matched_query_groups": post_row.get("matched_query_groups", ""),
        "search_rank_min": post_row.get("search_rank_min", ""),
        "permalink": post_row.get("permalink", ""),
        "score": post_row.get("score", ""),
        "upvote_ratio": post_row.get("upvote_ratio", ""),
        "estimated_upvotes": post_row.get("estimated_upvotes", ""),
        "estimated_downvotes": post_row.get("estimated_downvotes", ""),
        "num_comments_reported": post_row.get("num_comments_reported", ""),
        "comments_collected": post_row.get("comments_collected", ""),
        "author_comments_collected": post_row.get("author_comments_collected", ""),
        "comment_fetch_error": post_row.get("comment_fetch_error", ""),
    }


def normalize_comment(
    child: dict[str, Any],
    record: dict[str, Any],
    retrieved_at_utc: str,
    search_sort: str,
    search_time_filter: str,
) -> dict[str, Any]:
    data = child.get("data", {})
    post_data = record["raw"].get("data", {})
    post_author = post_data.get("author") or ""
    author = data.get("author") or ""
    permalink = data.get("permalink") or ""
    post_permalink = post_data.get("permalink") or ""
    post_fullname = post_data.get("name") or ""
    is_author_comment = bool(data.get("is_submitter")) or (
        bool(author) and author == post_author
    )
    return {
        "post_id": post_data.get("id") or "",
        "post_fullname": post_fullname,
        "post_reddit_kind": reddit_kind(post_fullname),
        "post_permalink": full_reddit_url(post_permalink),
        "subreddit_id": data.get("subreddit_id") or post_data.get("subreddit_id") or "",
        "subreddit_name_prefixed": (
            data.get("subreddit_name_prefixed")
            or post_data.get("subreddit_name_prefixed")
            or ""
        ),
        "author_fullname": data.get("author_fullname") or "",
        "retrieved_at_utc": retrieved_at_utc,
        "search_sort": search_sort,
        "search_time_filter": search_time_filter,
        "post_search_rank_min": search_rank_min(record),
        "post_search_rank_all": search_rank_all_json(record),
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


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def ensure_csv_header(path: Path, fieldnames: list[str]) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=fieldnames).writeheader()


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def record_to_json(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw": record["raw"],
        "matched_queries": sorted(record.get("matched_queries", [])),
        "matched_query_groups": sorted(record.get("matched_query_groups", [])),
        "search_ranks": record.get("search_ranks", []),
    }


def record_from_json(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw": row["raw"],
        "matched_queries": set(row.get("matched_queries", [])),
        "matched_query_groups": set(row.get("matched_query_groups", [])),
        "search_ranks": row.get("search_ranks", []),
    }


def write_search_records(path: Path, records: list[dict[str, Any]]) -> None:
    write_jsonl(path, [record_to_json(record) for record in records])


def read_search_records(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(record_from_json(json.loads(line)))
    return records


def stats_from_logs(logs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    stats = {}
    for post_id, log in logs.items():
        stats[post_id] = {
            "comments_collected": log.get("collected_comment_count", 0),
            "author_comments_collected": log.get("author_comment_count", 0),
        }
        if log.get("error"):
            stats[post_id]["comment_fetch_error"] = log["error"]
    return stats


def resolve_resume_dir(out_dir_arg: str) -> Path:
    path = Path(out_dir_arg)
    if (path / RUN_STATE_FILE).exists():
        return path

    if not path.exists():
        raise FileNotFoundError(f"No such output directory to resume: {path}")

    candidates = [
        candidate
        for candidate in path.glob("identity_search_*")
        if candidate.is_dir() and (candidate / RUN_STATE_FILE).exists()
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No resumable identity_search_* directory found under {path}"
        )

    incomplete = []
    complete = []
    for candidate in candidates:
        state = read_json(candidate / RUN_STATE_FILE)
        if state.get("status") == "complete":
            complete.append(candidate)
        else:
            incomplete.append(candidate)
    return sorted(incomplete or complete)[-1]


def state_value(state: dict[str, Any], key: str, fallback: Any) -> Any:
    return state[key] if key in state else fallback


def checkpoint_paths(chunk_dir: Path, post_id: str) -> dict[str, Path]:
    return {
        "comments": chunk_dir / f"{post_id}.comments.csv",
        "author_comments": chunk_dir / f"{post_id}.author_comments.csv",
        "log": chunk_dir / f"{post_id}.log.json",
    }


def atomic_write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
) -> None:
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    write_csv(tmp_path, fieldnames, rows)
    tmp_path.replace(path)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    write_json(tmp_path, payload)
    tmp_path.replace(path)


def write_post_checkpoint(
    chunk_dir: Path,
    post_id: str,
    comments: list[dict[str, Any]],
    author_comments: list[dict[str, Any]],
    log: dict[str, Any],
) -> None:
    paths = checkpoint_paths(chunk_dir, post_id)
    atomic_write_csv(paths["comments"], COMMENT_FIELDS, comments)
    atomic_write_csv(paths["author_comments"], COMMENT_FIELDS, author_comments)
    atomic_write_json(paths["log"], log)


def read_checkpoint_logs(chunk_dir: Path) -> dict[str, dict[str, Any]]:
    logs = {}
    if not chunk_dir.exists():
        return logs
    for log_path in sorted(chunk_dir.glob("*.log.json")):
        log = read_json(log_path)
        post_id = str(log.get("post_id", ""))
        if post_id:
            logs[post_id] = log
    return logs


def copy_csv_body(source_path: Path, writer: csv.DictWriter) -> int:
    if not source_path.exists():
        return 0
    copied = 0
    with source_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            writer.writerow(row)
            copied += 1
    return copied


def merge_comment_checkpoints(
    records: list[dict[str, Any]],
    chunk_dir: Path,
    comments_path: Path,
    author_comments_path: Path,
    log_path: Path,
) -> tuple[int, int, list[dict[str, Any]]]:
    comment_count = 0
    author_comment_count = 0
    logs = []

    with comments_path.open("w", encoding="utf-8", newline="") as comments_handle:
        writer = csv.DictWriter(comments_handle, fieldnames=COMMENT_FIELDS)
        writer.writeheader()
        for record in records:
            post_id = record["raw"].get("data", {}).get("id", "")
            if not post_id:
                continue
            paths = checkpoint_paths(chunk_dir, post_id)
            comment_count += copy_csv_body(paths["comments"], writer)

    with author_comments_path.open(
        "w", encoding="utf-8", newline=""
    ) as author_handle:
        writer = csv.DictWriter(author_handle, fieldnames=COMMENT_FIELDS)
        writer.writeheader()
        for record in records:
            post_id = record["raw"].get("data", {}).get("id", "")
            if not post_id:
                continue
            paths = checkpoint_paths(chunk_dir, post_id)
            author_comment_count += copy_csv_body(paths["author_comments"], writer)

    with log_path.open("w", encoding="utf-8") as handle:
        for record in records:
            post_id = record["raw"].get("data", {}).get("id", "")
            if not post_id:
                continue
            log_file = checkpoint_paths(chunk_dir, post_id)["log"]
            if not log_file.exists():
                continue
            log = read_json(log_file)
            logs.append(log)
            handle.write(json.dumps(log, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    return comment_count, author_comment_count, logs


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
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume the latest run_state.json under --out-dir, or resume "
            "--out-dir directly when it is a timestamped run directory."
        ),
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="When resuming, retry posts whose previous comment fetch logged an error.",
    )
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
    now = utc_now()

    if args.resume:
        try:
            out_dir = resolve_resume_dir(args.out_dir)
        except FileNotFoundError as error:
            print(str(error), file=sys.stderr)
            return 2
        state = read_json(out_dir / RUN_STATE_FILE)
        started_at_utc = state.get("started_at_utc", now.isoformat())
        retrieved_at_utc = state.get("retrieved_at_utc", started_at_utc)
        query_specs = state.get("query_specs") or unique_query_specs(
            args.query,
            include_defaults=not args.no_default_queries,
        )
        sort = state_value(state, "sort", args.sort)
        time_filter = state_value(state, "time_filter", args.time_filter)
        max_pages_per_query = int(
            state_value(state, "max_pages_per_query", args.max_pages_per_query)
        )
        max_posts = int(state_value(state, "max_posts", args.max_posts))
        skip_comments = bool(state_value(state, "skip_comments", args.skip_comments))
        skip_morechildren = bool(
            state_value(state, "skip_morechildren", args.skip_morechildren)
        )
        more_batch_size = int(state_value(state, "more_batch_size", args.more_batch_size))
        print(f"Resuming {out_dir}", file=sys.stderr, flush=True)
    else:
        started_at_utc = now.isoformat()
        retrieved_at_utc = started_at_utc
        snapshot = now.strftime("identity_search_%Y%m%dT%H%M%SZ")
        out_dir = Path(args.out_dir) / snapshot
        out_dir.mkdir(parents=True, exist_ok=True)
        query_specs = unique_query_specs(
            args.query,
            include_defaults=not args.no_default_queries,
        )
        sort = args.sort
        time_filter = args.time_filter
        max_pages_per_query = args.max_pages_per_query
        max_posts = args.max_posts
        skip_comments = args.skip_comments
        skip_morechildren = args.skip_morechildren
        more_batch_size = args.more_batch_size

    if not query_specs:
        print("No queries to run. Remove --no-default-queries or pass --query.", file=sys.stderr)
        return 2

    state_payload = {
        "schema_version": "2",
        "status": "searching",
        "started_at_utc": started_at_utc,
        "retrieved_at_utc": retrieved_at_utc,
        "last_updated_at_utc": utc_now().isoformat(),
        "query_specs": query_specs,
        "sort": sort,
        "time_filter": time_filter,
        "max_pages_per_query": max_pages_per_query,
        "max_posts": max_posts,
        "skip_comments": skip_comments,
        "skip_morechildren": skip_morechildren,
        "more_batch_size": more_batch_size,
    }
    write_json(out_dir / RUN_STATE_FILE, state_payload)

    search_records_path = out_dir / SEARCH_RECORDS_FILE
    search_pages_path = out_dir / "search_pages.json"
    if args.resume and search_records_path.exists():
        records = read_search_records(search_records_path)
        search_pages = (
            json.loads(search_pages_path.read_text(encoding="utf-8"))
            if search_pages_path.exists()
            else []
        )
        print(
            f"Loaded {len(records)} saved search records",
            file=sys.stderr,
            flush=True,
        )
    else:
        posts_by_id, search_pages = search_posts(
            query_specs=query_specs,
            user_agent=args.user_agent,
            sort=sort,
            time_filter=time_filter,
            max_pages_per_query=max_pages_per_query,
            delay_seconds=args.search_delay_seconds,
        )

        records = sorted(
            posts_by_id.values(),
            key=lambda record: record["raw"].get("data", {}).get("created_utc") or 0,
            reverse=True,
        )
        if max_posts > 0:
            records = records[:max_posts]
        write_search_records(search_records_path, records)
        search_pages_path.write_text(
            json.dumps(search_pages, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    chunk_dir = out_dir / "comment_checkpoints"
    chunk_dir.mkdir(exist_ok=True)
    comments_path = out_dir / "comments.csv"
    author_comments_path = out_dir / "author_comments.csv"
    log_path = out_dir / "comment_fetch_log.jsonl"
    stats_path = out_dir / POST_COMMENT_STATS_FILE
    checkpoint_logs = read_checkpoint_logs(chunk_dir)
    post_comment_stats: dict[str, dict[str, Any]] = read_json(stats_path)
    if not post_comment_stats:
        post_comment_stats = stats_from_logs(checkpoint_logs)

    record_post_ids = [
        record["raw"].get("data", {}).get("id", "")
        for record in records
        if record["raw"].get("data", {}).get("id")
    ]
    completed_post_count = sum(1 for post_id in record_post_ids if post_id in checkpoint_logs)
    state_payload.update(
        {
            "status": "collecting_comments" if not skip_comments else "finalizing",
            "post_count_planned": len(record_post_ids),
            "completed_post_count": completed_post_count,
            "last_updated_at_utc": utc_now().isoformat(),
        }
    )
    write_json(out_dir / RUN_STATE_FILE, state_payload)

    if not skip_comments:
        for index, record in enumerate(records, start=1):
            post_data = record["raw"].get("data", {})
            post_id = post_data.get("id")
            if not post_id:
                continue
            previous_log = checkpoint_logs.get(post_id)
            if previous_log and (not previous_log.get("error") or not args.retry_errors):
                print(
                    f"[{index}/{len(records)}] {post_id}: "
                    f"{previous_log.get('collected_comment_count', 0)} comments "
                    "(checkpoint)",
                    file=sys.stderr,
                    flush=True,
                )
                continue

            try:
                raw_comments, comment_log = collect_comments(
                    post_id=post_id,
                    user_agent=args.user_agent,
                    delay_seconds=args.comment_delay_seconds,
                    more_batch_size=more_batch_size,
                    expand_morechildren=not skip_morechildren,
                )
                normalized_comments = [
                    normalize_comment(
                        child,
                        record,
                        retrieved_at_utc=retrieved_at_utc,
                        search_sort=sort,
                        search_time_filter=time_filter,
                    )
                    for child in raw_comments
                ]
                author_comments = [
                    row for row in normalized_comments if row["is_author_comment"]
                ]
                post_comment_stats[post_id] = {
                    "comments_collected": len(normalized_comments),
                    "author_comments_collected": len(author_comments),
                }
                comment_log["status"] = "success"
                comment_log["author_comment_count"] = len(author_comments)
            except Exception as error:  # noqa: BLE001 - logged for collection audit.
                normalized_comments = []
                author_comments = []
                comment_log = {
                    "post_id": post_id,
                    "collected_comment_count": 0,
                    "author_comment_count": 0,
                    "status": "error",
                    "error": repr(error),
                }
                post_comment_stats[post_id] = {
                    "comments_collected": 0,
                    "author_comments_collected": 0,
                    "comment_fetch_error": repr(error),
                }

            comment_log["post_index"] = index
            comment_log["post_total"] = len(records)
            write_post_checkpoint(
                chunk_dir,
                post_id,
                normalized_comments,
                author_comments,
                comment_log,
            )
            checkpoint_logs[post_id] = comment_log
            write_json(stats_path, post_comment_stats)
            state_payload.update(
                {
                    "completed_post_count": sum(
                        1 for candidate in record_post_ids if candidate in checkpoint_logs
                    ),
                    "last_updated_at_utc": utc_now().isoformat(),
                }
            )
            write_json(out_dir / RUN_STATE_FILE, state_payload)
            print(
                f"[{index}/{len(records)}] {post_id}: "
                f"{comment_log.get('collected_comment_count', 0)} comments",
                file=sys.stderr,
                flush=True,
            )
    else:
        ensure_csv_header(comments_path, COMMENT_FIELDS)
        ensure_csv_header(author_comments_path, COMMENT_FIELDS)
        log_path.write_text("", encoding="utf-8")
        write_json(stats_path, post_comment_stats)

    if not skip_comments:
        comment_count, author_comment_count, comment_logs = merge_comment_checkpoints(
            records,
            chunk_dir,
            comments_path,
            author_comments_path,
            log_path,
        )
    else:
        comment_count = count_csv_rows(comments_path)
        author_comment_count = count_csv_rows(author_comments_path)
        comment_logs = []

    post_rows = [
        normalize_post(
            record,
            post_comment_stats.get(
                record["raw"].get("data", {}).get("id", ""),
                {},
            ),
            retrieved_at_utc=retrieved_at_utc,
            search_sort=sort,
            search_time_filter=time_filter,
        )
        for record in records
    ]

    write_csv(out_dir / "posts.csv", POST_FIELDS, post_rows)
    author_comment_rows = read_csv_rows(author_comments_path)
    review_rows = [
        normalize_review_post(post_row, author_comment_rows)
        for post_row in post_rows
    ]
    write_csv(out_dir / "review_posts.csv", REVIEW_POST_FIELDS, review_rows)

    manifest = {
        "schema_version": "2",
        "started_at_utc": started_at_utc,
        "retrieved_at_utc": retrieved_at_utc,
        "finished_at_utc": utc_now().isoformat(),
        "source": "Reddit public search and comments JSON endpoints",
        "resumed": args.resume,
        "query_specs": query_specs,
        "sort": sort,
        "time_filter": time_filter,
        "max_pages_per_query": max_pages_per_query,
        "max_posts": max_posts,
        "search_delay_seconds": args.search_delay_seconds,
        "comment_delay_seconds": args.comment_delay_seconds,
        "more_batch_size": args.more_batch_size,
        "skip_morechildren": args.skip_morechildren,
        "retry_errors": args.retry_errors,
        "post_count": len(post_rows),
        "comment_count": comment_count,
        "author_comment_count": author_comment_count,
        "comment_fetch_error_count": sum(1 for log in comment_logs if "error" in log),
        "outputs": {
            "review_posts": "review_posts.csv",
            "posts": "posts.csv",
            "comments": "comments.csv",
            "author_comments": "author_comments.csv",
            "search_pages": "search_pages.json",
            "comment_fetch_log": "comment_fetch_log.jsonl",
            "run_state": RUN_STATE_FILE,
            "search_records": SEARCH_RECORDS_FILE,
            "post_comment_stats": POST_COMMENT_STATS_FILE,
            "comment_checkpoints": "comment_checkpoints/",
        },
        "schemas": {
            "review_posts": REVIEW_POST_FIELDS,
            "posts": POST_FIELDS,
            "comments": COMMENT_FIELDS,
            "author_comments": COMMENT_FIELDS,
        },
        "notes": [
            "Use --resume to continue a stopped run from run_state.json and per-post comment checkpoints.",
            "review_posts.csv is optimized for manual review in Google Sheets; long text is single-line and truncated.",
            "Reddit search is not guaranteed to be exhaustive or stable over time.",
            "Queries are exact phrase searches; Reddit wildcard-style phrases are expanded explicitly.",
            "Post up/downvotes are estimates derived from score and upvote_ratio because Reddit does not expose exact up/downvote counts.",
            "author_comments.csv contains comments where Reddit marked is_submitter or the comment author matches the post author.",
        ],
    }
    write_json(out_dir / "manifest.json", manifest)
    state_payload.update(
        {
            "status": "complete",
            "completed_post_count": len(record_post_ids),
            "last_updated_at_utc": utc_now().isoformat(),
            "manifest": "manifest.json",
        }
    )
    write_json(out_dir / RUN_STATE_FILE, state_payload)

    print(json.dumps({"out_dir": str(out_dir), **manifest}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
