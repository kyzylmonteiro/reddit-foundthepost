# Broad Reddit Identity-Discovery Search

## Goal

Find Reddit posts outside `r/foundthepost` where someone reports that another
person discovered, recognized, or used the poster's Reddit post/account in a
way that linked the online post back to the original poster's offline identity.

This is broader than the `r/foundthepost` snapshot. It searches Reddit-wide for
candidate phrases, deduplicates posts across queries, then fetches each post's
comment tree so we can inspect both the full discussion and the original
poster's own replies.

## Authentication Is Now Required

Reddit answers **HTTP 403 Blocked** for unauthenticated requests to its `.json`
endpoints. The script therefore runs over OAuth against `oauth.reddit.com`:

```bash
export REDDIT_CLIENT_ID=...
export REDDIT_CLIENT_SECRET=...
```

Create a "script" app at <https://www.reddit.com/prefs/apps> to get them, or
pass `--client-id` / `--client-secret`. Without credentials the script warns at
startup and exits 3 on the first blocked request. `manifest.json` records which
mode a run used in `auth_mode`.

## Caveats

Reddit search is a discovery method, not a complete corpus. Results can vary
over time as posts are edited, removed, deleted, rescored, or newly indexed.
Broad phrases like `"found out"` are expected to be noisy; they are included
because they may recover cases that do not explicitly say "found my post".
Downvotes are not directly exposed by Reddit's JSON endpoints, so the script
records `score`, `upvote_ratio`, and estimated up/downvote counts derived from
those fields.

Wildcard searches like `Reddit*` are represented as explicit phrase expansions
because Reddit's search behavior for wildcard syntax is inconsistent.

## Keyword Sources

Two ways to supply phrases:

1. **Keyword CSVs** (`--query-csv`), the current approach. 33,344 phrases across
   three voices, documented in
   [`data/keyword_search_combos/README.md`](data/keyword_search_combos/README.md).
   Any CSV with a `Search Phrase` column works; optional `Category`,
   `Target Term`, and `Template` columns are carried into the output tables as
   `matched_categories`, `matched_target_terms`, and `matched_templates`. Label
   a set with `--query-set`, which lands in `matched_query_groups`.
2. **The built-in list** below, 20 phrases, used when no `--query-csv` is given.
   Pass `--no-default-queries` to suppress it.

## Comment Scope

`--author-comments-only` keeps just the post author's comments and skips the
`morechildren` expansion, which is where most collection time goes. It is still
one comments request per post. Tradeoff: author replies buried in collapsed
"load more" chains are missed. `comment_fetch_log.jsonl` still records the full
fetched tree size in `collected_comment_count`, so what was skipped stays
visible.

## Built-in Keyword Groups

High-precision phrases:

- `"found my post"`
- `"found this post"`
- `"found my account"`
- `"found my reddit account"`
- `"found my throwaway"`
- `"found out I posted"`
- `"figured out it was me"`
- `"recognized my post"`
- `"confronted me about my post"`
- `"sent me a screenshot"`

User-requested additions and expansions:

- `"found out"`
- `"found my reddit"`
- `"found my reddit post"`
- `"found my reddit username"`
- `"used my post"`
- `"used my reddit post"`
- `"discovered my reddit"`
- `"discovered my reddit account"`
- `"discovered my account"`
- `"discovered my post"`

## Output Tables

Run:

```bash
python3 scripts/search_identity_discovery.py
```

If the run is stopped during comment collection, continue from the latest
checkpointed folder with:

```bash
python3 scripts/search_identity_discovery.py --resume
```

To resume a specific run, pass its timestamped folder as `--out-dir` with
`--resume`.

The script creates a timestamped directory under `data/broad_identity_search/`
with:

- `posts.csv`: one row per deduplicated post, including timestamp, subreddit,
  post/author flair fields, score, upvote ratio, estimated up/downvotes, link,
  durable Reddit IDs, matched queries, search-rank provenance, and comment
  collection counts.
- `review_posts.csv`: compact, single-line post table for Google Sheets/manual
  review, with blank coding columns and short text/comment excerpts.
- `comments.csv`: one row per collected comment, including timestamp, author,
  body, score, Reddit comment/link/parent IDs, permalink, search provenance,
  and whether the comment was written by the post author.
- `author_comments.csv`: filtered subset of `comments.csv` where the comment
  author is the original post author.
- `search_pages.json`: per-query Reddit search pagination metadata.
- `comment_fetch_log.jsonl`: per-post comment fetch status and unresolved
  `morechildren` counts.
- `manifest.json`: parameters, query list, counts, and caveats.
- `run_state.json`, `search_records.jsonl`, `post_comment_stats.json`, and
  `comment_checkpoints/`: resume state so completed post/comment fetches are
  reused rather than collected again.

## Box Dataset Versus Rerunning

Use the Box upload as the exact dataset for annotation and shared analysis.
The Reddit-wide search uses live Reddit public endpoints, so rerunning the
script later can produce different posts, scores, removals, comments, or search
rankings. A rerun is reproducible in method and schema, not guaranteed to match
the Box data row for row.

To make a comparable new scrape using the same broad-run settings as the Box
dataset:

```bash
python3 scripts/search_identity_discovery.py \
  --max-pages-per-query 3 \
  --max-posts 0 \
  --skip-morechildren
```

If interrupted:

```bash
python3 scripts/search_identity_discovery.py --resume
```

Important rehydration/provenance columns:

- Post IDs: `post_id`, `fullname`, `reddit_kind`, `subreddit_id`,
  `subreddit_name_prefixed`, `author_fullname`, `permalink`.
- Comment IDs: `comment_id`, `comment_fullname`, `link_id`, `parent_id`,
  `post_id`, `post_fullname`, `author_fullname`, `permalink`.
- Collection provenance: `retrieved_at_utc`, `search_sort`,
  `search_time_filter`, `matched_queries`, `matched_query_groups`,
  `search_rank_min`, `search_rank_all`.
- `search_rank_all` is JSON listing every query that surfaced the post and its
  rank within that query's result pages.

## Current Runs

Set 2 runs live under `data/set2_broad_keyword_search/`, one directory per
voice, each holding a dated `YYYYMMDD_broad_search_results/` folder. See
[`data/set2_broad_keyword_search/README.md`](data/set2_broad_keyword_search/README.md)
for the exact commands.

An earlier exploratory scrape at
`data/broad_identity_search/20260528_broad_search_results/` is local-only and
not present in a fresh clone.

Join map:

- `review_posts.post_id` joins to `posts.post_id`.
- `comments.post_id` joins to `posts.post_id`.
- `author_comments.post_id` joins to `posts.post_id`.
- `author_comments.comment_fullname` joins to `comments.comment_fullname`.

For most analysis, keep `posts.csv` and `comments.csv` separate and join on
`post_id` only when needed. A one-row-per-comment joined table is possible, but
it repeats post metadata across every comment row and is less convenient in
Google Sheets.

## Recommended First Run

The full default query set can be large, especially because of `"found out"`.
For a pilot run:

```bash
python3 scripts/search_identity_discovery.py \
  --max-pages-per-query 1 \
  --max-posts 50
```

For a larger collection, increase `--max-pages-per-query` or omit `--max-posts`.
Use `--sort new` for recency-oriented discovery, or keep the default
`--sort relevance` for phrase-matching discovery.

To test one phrase without the default list:

```bash
python3 scripts/search_identity_discovery.py \
  --no-default-queries \
  --query "found my post" \
  --max-pages-per-query 1 \
  --max-posts 10
```
