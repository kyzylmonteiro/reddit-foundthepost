#!/usr/bin/env python3
"""Classify Set 3 subreddit names without reading post content or using post counts as rules."""

from __future__ import annotations

import argparse
import math
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

PAGE_SIZE = 2_500

ROLEPLAY_WORD = re.compile(r"role[_-]?play(?:ing|ers?|s)?", re.IGNORECASE)
RP_TOKEN = re.compile(r"(?<![a-z])rp(?![a-z])", re.IGNORECASE)
RP_CAMEL = re.compile(r"RP(?=[A-FH-Z])")  # Exclude RPG, a gaming abbreviation.
RP_CONTEXT = re.compile(r"chat|partner|character|originalcharacter|text|erp|play", re.IGNORECASE)
MINOR_EXPLICIT = re.compile(
    r"^teenagers?|^teens?(?:$|[_-])|(?:^|[_-])under[_-]?18(?:$|[_-])",
    re.IGNORECASE,
)
TEEN_AMBIGUOUS_PREFIX = re.compile(r"^teen|[_-]teen", re.IGNORECASE)
TEEN_AMBIGUOUS_CAMEL = re.compile(r"[a-z]Teen")
GAMING = re.compile(r"gam(?:e|es|er|ers|ing)|rpg|minecraft|roblox|fortnite|pokemon", re.IGNORECASE)
MEME = re.compile(r"(?:^|[_-])memes?(?:$|[_-])|^memes?|memes?$|shitpost", re.IGNORECASE)
SEXUAL = re.compile(
    r"nsfw|porn|sexual|erotic|fetish|gonewild|onlyfans|hentai|nude|nudity|xxx|(?:^|[_-])sex(?:$|[_-])",
    re.IGNORECASE,
)
STORY = re.compile(r"stories|fiction|fanfic|writing|nosleep|creepypasta", re.IGNORECASE)
STORY_TOKEN = re.compile(r"(?:^|[_-])story(?:$|[_-])|^story|story$", re.IGNORECASE)


def read_counts(database: Path) -> tuple[list[tuple[str, int]], int, int]:
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        total_posts = connection.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        unnamed_posts = connection.execute(
            "SELECT COUNT(*) FROM posts WHERE subreddit IS NULL OR trim(subreddit) = ''"
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
        display = sorted(labels, key=lambda item: (-item[1], item[0].casefold(), item[0]))[0][0]
        counts.append((display, sum(count for _, count in labels)))
    counts.sort(key=lambda item: (-item[1], item[0].casefold(), item[0]))

    assert sum(count for _, count in counts) + unnamed_posts == total_posts
    return counts, unnamed_posts, total_posts


@dataclass(frozen=True)
class Row:
    name: str
    posts: int
    category: str
    decision: str
    reason: str
    group: str


def classify(name: str, posts: int) -> Row:
    # The count is carried into the output, but never read by a decision rule.
    lower = name.casefold()
    if lower.startswith("u_"):
        return Row(name, posts, "USER_PROFILE", "KEEP", "Profile entry; no subreddit rules applied", "profiles")

    sexual = bool(SEXUAL.search(name))
    gaming = bool(GAMING.search(name))
    roleplay_word = bool(ROLEPLAY_WORD.search(name))
    rp_token = bool(RP_TOKEN.search(name) or lower.endswith("rp") or RP_CAMEL.search(name))
    minor = bool(MINOR_EXPLICIT.search(name))
    teen_ambiguous = bool(
        TEEN_AMBIGUOUS_PREFIX.search(name)
        or TEEN_AMBIGUOUS_CAMEL.search(name)
        or "teenager" in lower
    )

    if minor:
        return Row(name, posts, "MINORS_NAME_MATCH", "REMOVE", "Teenager/teen token or under-18 name match", "remove")
    if roleplay_word and not gaming:
        return Row(name, posts, "ROLEPLAY_NAME_MATCH", "REMOVE", "Explicit roleplay name match", "remove")
    if rp_token and (RP_CONTEXT.search(name) or sexual) and not gaming:
        return Row(name, posts, "ROLEPLAY_NAME_MATCH", "REMOVE", "RP token plus roleplay context in name", "remove")

    review: list[tuple[str, str]] = []
    if teen_ambiguous and not minor:
        review.append(("TEEN_AMBIGUOUS", "Teen substring is ambiguous"))
    if roleplay_word and gaming:
        review.append(("ROLEPLAY_GAMING_AMBIGUOUS", "Roleplay plus gaming; gaming exception"))
    elif rp_token and not ((RP_CONTEXT.search(name) or sexual) and not gaming):
        review.append(("RP_AMBIGUOUS", "RP acronym is ambiguous"))
    if MEME.search(name):
        review.append(("MEME_NAME_MATCH", "Meme or shitpost name match"))
    if sexual:
        review.append(("SEXUAL_NSFW_NAME_MATCH", "Sexual or NSFW name match"))
    if STORY.search(name) or (STORY_TOKEN.search(name) and "history" not in lower):
        review.append(("FICTION_STORY_NAME_MATCH", "Story, fiction, or writing name match"))

    if review:
        return Row(
            name, posts,
            "; ".join(category for category, _ in review),
            "REVIEW",
            "; ".join(reason for _, reason in review),
            "review",
        )
    if gaming:
        return Row(name, posts, "GAMING_NAME_MATCH", "KEEP", "Gaming name match; no exclusion rule", "keep")
    return Row(name, posts, "NO_NAME_RULE_MATCH", "KEEP", "No name rule matched", "keep")


def markdown_row(row: Row) -> str:
    label = row.name.replace("|", "\\|")
    if row.group == "profiles":
        url = "https://www.reddit.com/user/" + quote(row.name[2:], safe="") + "/"
    else:
        url = "https://www.reddit.com/r/" + quote(row.name, safe="") + "/"
    return (
        f"| [r/{label}]({url}) | {row.posts:,} | {row.category} | "
        f"{row.decision} | {row.reason} |\n"
    )


def write_pages(output: Path, group: str, rows: list[Row]) -> int:
    directory = output / group
    directory.mkdir(parents=True, exist_ok=True)
    pages = math.ceil(len(rows) / PAGE_SIZE)
    for page in range(1, pages + 1):
        start = (page - 1) * PAGE_SIZE
        end = min(page * PAGE_SIZE, len(rows))
        with (directory / f"{page:04d}.md").open("w", encoding="utf-8", newline="\n") as file:
            file.write(f"# {group.title()}: entries {start + 1:,}–{end:,}\n\n")
            file.write("Decisions are based on subreddit names only.\n\n")
            file.write("| Entry | Matched posts | Classification | Decision | Reason |\n")
            file.write("| --- | ---: | --- | --- | --- |\n")
            for row in rows[start:end]:
                file.write(markdown_row(row))
    return pages


def write_index(output: Path, groups: dict[str, list[Row]], unnamed: int, total: int) -> None:
    output.mkdir(parents=True, exist_ok=True)
    classified = output / "classified"
    page_counts = {group: write_pages(classified, group, rows) for group, rows in groups.items()}
    all_rows = [row for rows in groups.values() for row in rows]
    assert sum(row.posts for row in all_rows) + unnamed == total
    assert len({row.name.casefold() for row in all_rows}) == len(all_rows)
    with (output / "README.md").open("w", encoding="utf-8", newline="\n") as file:
        file.write("# Set 3 subreddit catalog\n\n")
        file.write("Every named entry in the [Set 3 matched-post database](../README.md) ")
        file.write("is listed once, with its matched-post count, name-based category, ")
        file.write("decision, and reason. Counts describe the matched posts; they do ")
        file.write("not determine the decision.\n\n")
        file.write("## Name-based filtering\n\n")
        file.write("- **REMOVE:** Names clearly indicating roleplay or minors.\n")
        file.write("- **REVIEW:** Names suggesting memes, sexual/NSFW content, fiction or ")
        file.write("stories, or ambiguous teen/RP meanings. Gaming-related roleplay ")
        file.write("names are reviewed rather than automatically removed.\n")
        file.write("- **User profiles:** `u_` entries are listed separately and are not ")
        file.write("subject to subreddit rules.\n\n")
        file.write("Other subreddit names remain in the catalog as unflagged entries; ")
        file.write("gaming alone is not an exclusion. Matching is case-insensitive ")
        file.write("with token boundaries for short terms.\n\n")
        file.write("| Group | Entries | Matched posts |\n| --- | ---: | ---: |\n")
        for group in ("review", "remove", "profiles", "keep"):
            rows = groups[group]
            label = "Other subreddit names" if group == "keep" else group.title()
            file.write(f"| {label} | {len(rows):,} | {sum(row.posts for row in rows):,} |\n")
        file.write(f"| No subreddit name | — | {unnamed:,} |\n")
        file.write(f"| **Total** | **{len(all_rows):,}** | **{total:,}** |\n\n")
        file.write("## Tables\n\n")
        for group in ("review", "remove", "profiles", "keep"):
            label = "Other subreddit names" if group == "keep" else group.title()
            file.write(f"### {label}\n\n")
            file.write("| Entries | Page |\n| ---: | --- |\n")
            for page in range(1, page_counts[group] + 1):
                start = (page - 1) * PAGE_SIZE + 1
                end = min(page * PAGE_SIZE, len(groups[group]))
                link_label = "other" if group == "keep" else group
                file.write(f"| {start:,}–{end:,} | [{link_label} {page}](classified/{group}/{page:04d}.md) |\n")
            file.write("\n")
        file.write("Regenerate from the Set 3 SQLite database with:\n\n")
        file.write("```bash\npython3 scripts/classify_subreddits.py \\\n")
        file.write("  arctic_keyword_matches.sqlite \\\n")
        file.write("  --output data/set3_arctic_keyword_search/subreddits\n```\n")

    with (classified / "README.md").open("w", encoding="utf-8", newline="\n") as file:
        file.write("# Set 3 subreddit tables\n\n")
        file.write("The [subreddit catalog](../README.md) is the main index for ")
        file.write("these category pages and their filtering rules.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    counts, unnamed, total = read_counts(args.database)
    groups: dict[str, list[Row]] = {name: [] for name in ("keep", "review", "remove", "profiles")}
    for name, posts in counts:
        row = classify(name, posts)
        groups[row.group].append(row)
    write_index(args.output, groups, unnamed, total)
    print(" ".join(f"{group}={len(rows):,}" for group, rows in groups.items()))


if __name__ == "__main__":
    main()
