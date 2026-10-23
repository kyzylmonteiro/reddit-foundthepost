#!/usr/bin/env python3
"""Build a browsable Markdown catalog of Set 3 matched-post counts."""

from __future__ import annotations

import argparse
import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote


PAGE_SIZE = 5_000


def read_counts(database: Path) -> tuple[list[tuple[str, int]], int, int]:
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        total_posts = connection.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        unnamed_posts = connection.execute(
            "SELECT COUNT(*) FROM posts "
            "WHERE subreddit IS NULL OR trim(subreddit) = ''"
        ).fetchone()[0]
        variants = connection.execute(
            "SELECT trim(subreddit), COUNT(*) FROM posts "
            "WHERE subreddit IS NOT NULL AND trim(subreddit) <> '' "
            "GROUP BY trim(subreddit)"
        ).fetchall()
    finally:
        connection.close()

    grouped: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for label, count in variants:
        grouped[label.casefold()].append((label, count))

    counts = []
    for labels in grouped.values():
        # Reddit names are case insensitive. Retain the most common spelling.
        display = sorted(labels, key=lambda item: (-item[1], item[0].casefold(), item[0]))[0][0]
        counts.append((display, sum(count for _, count in labels)))
    counts.sort(key=lambda item: (-item[1], item[0].casefold(), item[0]))

    assert sum(count for _, count in counts) + unnamed_posts == total_posts
    return counts, unnamed_posts, total_posts


def table_row(rank: int, name: str, count: int) -> str:
    safe_name = name.replace("|", "\\|")
    url = "https://www.reddit.com/r/" + quote(name, safe="") + "/"
    return f"| {rank:,} | [r/{safe_name}]({url}) | {count:,} |  |\n"


def write_catalog(output: Path, counts: list[tuple[str, int]], unnamed: int, total: int) -> None:
    pages = output / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    page_count = math.ceil(len(counts) / PAGE_SIZE)

    for page_number in range(1, page_count + 1):
        start = (page_number - 1) * PAGE_SIZE
        end = min(start + PAGE_SIZE, len(counts))
        path = pages / f"{page_number:04d}.md"
        with path.open("w", encoding="utf-8", newline="\n") as file:
            file.write(f"# Set 3 subreddits: ranks {start + 1:,}–{end:,}\n\n")
            file.write("Counts are matched posts in Set 3, not all Reddit posts. ")
            file.write("Descriptions have not been fetched and are intentionally blank.\n\n")
            file.write("| Rank | Subreddit | Matched posts | Description |\n")
            file.write("| ---: | --- | ---: | --- |\n")
            for index in range(start, end):
                name, count = counts[index]
                file.write(table_row(index + 1, name, count))

    one_post = sum(count == 1 for _, count in counts)
    with (output / "README.md").open("w", encoding="utf-8", newline="\n") as file:
        file.write("# Set 3 subreddit counts\n\n")
        file.write("Every subreddit name stored in the [Set 3 matched-post database](../README.md) ")
        file.write("is listed in the linked Markdown tables below. Counts are unique matched ")
        file.write("posts in this dataset, not the total number of posts in each subreddit. ")
        file.write("Names are grouped case insensitively; the most common stored spelling ")
        file.write("is displayed. Descriptions are intentionally blank until a later ")
        file.write("metadata collection pass. No Reddit API requests were made.\n\n")
        file.write("The [classification tables](classified/README.md) include every named entry, ")
        file.write("including communities with only one matched post. **No minimum matched-post ")
        file.write("count or top-100 cutoff is applied.** Counts are for context only.\n\n")
        file.write("## Filtering conditions\n\n")
        file.write("- **REMOVE:** Clear roleplaying names (`roleplay`, `roleplaying`, or ")
        file.write("contextual `RP`) and names clearly indicating minors (`teen`, `teens`, ")
        file.write("`teenagers`, or `under18`). Banned, private, or otherwise inaccessible ")
        file.write("communities should also be removed **once their status is verified**; ")
        file.write("access status has not yet been checked. Gaming-related name ")
        file.write("combinations are sent to REVIEW rather than automatically removed.\n")
        file.write("- **REVIEW, not automatic removal:** Names suggesting memes, sexual/NSFW ")
        file.write("content, fiction/stories, or ambiguous teen/RP meanings. Descriptions ")
        file.write("are not available yet to confirm these categories.\n")
        file.write("- **KEEP:** Other subreddit names remain eligible. Gaming communities ")
        file.write("are not removed merely for being about games. KEEP is provisional ")
        file.write("until access status and descriptions can be checked.\n")
        file.write("- **Separate profiles:** Entries beginning with `u_` represent user ")
        file.write("profiles, not subreddits, and are preserved outside subreddit ")
        file.write("filtering.\n\n")
        file.write("Name matching is case-insensitive and uses boundaries for short ")
        file.write("terms to limit false positives. Each classification row records its ")
        file.write("category, decision, and reason. No post titles or bodies are read.\n\n")
        file.write("| Measure | Count |\n| --- | ---: |\n")
        file.write(f"| Matched posts in Set 3 | {total:,} |\n")
        file.write(f"| Posts with a subreddit name | {total - unnamed:,} |\n")
        file.write(f"| Posts without a subreddit name | {unnamed:,} |\n")
        file.write(f"| Distinct subreddit names | {len(counts):,} |\n")
        file.write(f"| Subreddits with one matched post | {one_post:,} |\n\n")
        file.write("## All subreddits\n\n")
        file.write("Sorted by matched-post count, highest first. Each page has at most ")
        file.write(f"{PAGE_SIZE:,} rows. The description column is empty on every page.\n\n")
        file.write("| Ranks | Markdown table |\n| ---: | --- |\n")
        for page_number in range(1, page_count + 1):
            start = (page_number - 1) * PAGE_SIZE + 1
            end = min(page_number * PAGE_SIZE, len(counts))
            file.write(f"| {start:,}–{end:,} | [Page {page_number}](pages/{page_number:04d}.md) |\n")
        file.write("\n## Method\n\n")
        file.write("Counted rows in the database's `posts` table by `subreddit` after ")
        file.write("trimming surrounding whitespace and case folding. The database has ")
        file.write("one row per matched Reddit post. Blank or null names are counted ")
        file.write("separately above. The pages contain only aggregate counts and ")
        file.write("subreddit names; no post titles or bodies were read.\n\n")
        file.write("The source field also contains some legacy or profile-community ")
        file.write("labels; a link may no longer resolve to a public subreddit.\n\n")
        file.write("Regenerate from the downloaded Set 3 SQLite database with:\n\n")
        file.write("```bash\npython3 scripts/build_subreddit_catalog.py \\\n")
        file.write("  arctic_keyword_matches.sqlite \\\n")
        file.write("  --output data/set3_arctic_keyword_search/subreddits\n```\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Set 3 SQLite database")
    parser.add_argument("--output", required=True, type=Path, help="Markdown catalog directory")
    args = parser.parse_args()
    counts, unnamed, total = read_counts(args.database)
    write_catalog(args.output, counts, unnamed, total)
    print(f"Wrote {len(counts):,} subreddit counts across {math.ceil(len(counts) / PAGE_SIZE)} pages")


if __name__ == "__main__":
    main()
