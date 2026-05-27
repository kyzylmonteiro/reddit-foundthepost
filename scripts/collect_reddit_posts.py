#!/usr/bin/env python3
"""Collect public Reddit submissions from a subreddit listing.

This uses Reddit's unauthenticated JSON listing endpoint. For small subreddits it
can capture the complete visible submission history; Reddit listing endpoints
may cap very large histories, so the manifest records pagination details.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REDDIT_BASE = "https://www.reddit.com"
DEFAULT_USER_AGENT = (
    "reddit-foundthepost-content-analysis/0.1 "
    "(public subreddit collection; contact: local research script)"
)


CSV_FIELDS = [
    "id",
    "fullname",
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
    "is_self",
    "is_gallery",
    "is_video",
    "post_hint",
    "link_flair_text",
    "score",
    "upvote_ratio",
    "num_comments",
    "over_18",
    "spoiler",
    "locked",
    "archived",
    "stickied",
    "distinguished",
    "removed_by_category",
    "crosspost_parent",
    "source_subreddit",
    "source_title",
    "source_selftext",
    "source_text_for_analysis",
    "source_author",
    "source_created_utc",
    "source_created_iso",
    "source_permalink",
    "source_url",
    "source_domain",
    "source_score",
    "source_num_comments",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(timestamp: float | int | None) -> str:
    if timestamp is None:
        return ""
    return datetime.fromtimestamp(float(timestamp), timezone.utc).isoformat()


def request_json(url: str, user_agent: str, retries: int = 4) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": user_agent})
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except HTTPError as error:
            if error.code == 429 and attempt < retries:
                retry_after = error.headers.get("Retry-After")
                delay = int(retry_after) if retry_after and retry_after.isdigit() else 10
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


def normalize_post(child: dict[str, Any]) -> dict[str, Any]:
    data = child.get("data", {})
    source = (data.get("crosspost_parent_list") or [{}])[0]
    permalink = data.get("permalink") or ""
    source_permalink = source.get("permalink") or ""
    title = data.get("title") or ""
    selftext = data.get("selftext") or ""
    source_title = source.get("title") or ""
    source_selftext = source.get("selftext") or ""
    return {
        "id": data.get("id") or "",
        "fullname": data.get("name") or "",
        "subreddit": data.get("subreddit") or "",
        "title": title,
        "selftext": selftext,
        "text_for_analysis": "\n\n".join(part for part in [title, selftext] if part),
        "author": data.get("author") or "",
        "created_utc": data.get("created_utc") or "",
        "created_iso": to_iso(data.get("created_utc")),
        "permalink": f"{REDDIT_BASE}{permalink}" if permalink.startswith("/") else permalink,
        "url": data.get("url") or "",
        "domain": data.get("domain") or "",
        "is_self": data.get("is_self"),
        "is_gallery": data.get("is_gallery", False),
        "is_video": data.get("is_video"),
        "post_hint": data.get("post_hint") or "",
        "link_flair_text": data.get("link_flair_text") or "",
        "score": data.get("score"),
        "upvote_ratio": data.get("upvote_ratio"),
        "num_comments": data.get("num_comments"),
        "over_18": data.get("over_18"),
        "spoiler": data.get("spoiler"),
        "locked": data.get("locked"),
        "archived": data.get("archived"),
        "stickied": data.get("stickied"),
        "distinguished": data.get("distinguished") or "",
        "removed_by_category": data.get("removed_by_category") or "",
        "crosspost_parent": data.get("crosspost_parent") or "",
        "source_subreddit": source.get("subreddit") or "",
        "source_title": source_title,
        "source_selftext": source_selftext,
        "source_text_for_analysis": "\n\n".join(
            part for part in [source_title, source_selftext] if part
        ),
        "source_author": source.get("author") or "",
        "source_created_utc": source.get("created_utc") or "",
        "source_created_iso": to_iso(source.get("created_utc")),
        "source_permalink": (
            f"{REDDIT_BASE}{source_permalink}"
            if source_permalink.startswith("/")
            else source_permalink
        ),
        "source_url": source.get("url") or "",
        "source_domain": source.get("domain") or "",
        "source_score": source.get("score"),
        "source_num_comments": source.get("num_comments"),
    }


def collect_posts(
    subreddit: str,
    user_agent: str,
    delay_seconds: float,
    max_pages: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    posts_by_id: dict[str, dict[str, Any]] = {}
    pages: list[dict[str, Any]] = []
    after = None
    page_number = 0

    while True:
        page_number += 1
        params = {"limit": "100", "raw_json": "1"}
        if after:
            params["after"] = after
        url = f"{REDDIT_BASE}/r/{subreddit}/new.json?{urlencode(params)}"
        payload = request_json(url, user_agent)
        listing = payload.get("data", {})
        children = listing.get("children", [])

        pages.append(
            {
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
            post_id = child.get("data", {}).get("id")
            if post_id:
                posts_by_id[post_id] = child

        after = listing.get("after")
        if not after or not children:
            break
        if max_pages is not None and page_number >= max_pages:
            break
        time.sleep(delay_seconds)

    posts = sorted(
        posts_by_id.values(),
        key=lambda child: child.get("data", {}).get("created_utc") or 0,
        reverse=True,
    )
    return posts, pages


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subreddit", default="foundthepost")
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional page limit for testing; each page contains up to 100 posts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now()
    subreddit = args.subreddit.strip().removeprefix("r/").strip("/")
    snapshot = started_at.strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir) / f"{subreddit}_{snapshot}"
    out_dir.mkdir(parents=True, exist_ok=True)

    posts, pages = collect_posts(
        subreddit=subreddit,
        user_agent=args.user_agent,
        delay_seconds=args.delay_seconds,
        max_pages=args.max_pages,
    )
    rows = [normalize_post(post) for post in posts]

    write_jsonl(out_dir / "posts_raw.jsonl", posts)
    write_jsonl(out_dir / "posts_normalized.jsonl", rows)
    write_csv(out_dir / "posts_normalized.csv", rows)

    manifest = {
        "subreddit": subreddit,
        "source": f"{REDDIT_BASE}/r/{subreddit}/new.json",
        "collector": Path(__file__).name,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": utc_now().isoformat(),
        "post_count": len(posts),
        "page_count": len(pages),
        "max_pages": args.max_pages,
        "delay_seconds": args.delay_seconds,
        "notes": [
            "Collected public submissions from Reddit's unauthenticated new.json listing.",
            "Deleted, removed, private, or otherwise inaccessible content is not recovered.",
            "Reddit listing endpoints can cap very large histories; inspect pages.json for pagination details.",
        ],
        "outputs": {
            "raw_jsonl": "posts_raw.jsonl",
            "normalized_jsonl": "posts_normalized.jsonl",
            "normalized_csv": "posts_normalized.csv",
            "pages": "pages.json",
        },
    }

    (out_dir / "pages.json").write_text(
        json.dumps(pages, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps({"out_dir": str(out_dir), **manifest}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
