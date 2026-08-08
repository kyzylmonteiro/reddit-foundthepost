# Set 2 — Broad Reddit Keyword Search

Reddit-wide search driven by the keyword workbook in
`data/keyword_search_combos/`. Not subreddit-specific: this searches all of
Reddit for phrases describing someone's Reddit content being discovered.

Set 1 (`data/set1_foundthepost_subreddit/`) is the earlier `r/foundthepost`
snapshot and is untouched by anything here.

## TL;DR

Three runs, one per voice, same script and same output schema:

| Run directory | Query source | Phrases |
| --- | --- | ---: |
| `first_person/` | the 5 category CSVs | 7,886 |
| `third_person_observer/` | `third_person_observer.csv` | 21,564 |
| `third_person_finder/` | `third_person_finder.csv` | 3,894 |

Each contains a dated `YYYYMMDD_broad_search_results/` folder with the same files
as the earlier broad search: `review_posts.csv`, `posts.csv`, `comments.csv`,
`author_comments.csv`, `manifest.json`, `search_pages.json`,
`comment_fetch_log.jsonl`, plus resume state.

**Comments: author only.** Runs use `--author-comments-only`, so only the
original poster's own comments are kept and the `morechildren` expansion is
skipped. Non-OP comments were judged not worth the collection cost.

## Status

Not yet collected. Reddit now returns **HTTP 403 Blocked** for unauthenticated
`.json` requests, so these runs need OAuth credentials:

```bash
export REDDIT_CLIENT_ID=...
export REDDIT_CLIENT_SECRET=...
```

Get them by creating a "script" app at <https://www.reddit.com/prefs/apps>.

## Commands

First person:

```bash
python3 scripts/search_identity_discovery.py \
  --out-dir data/set2_broad_keyword_search/first_person \
  --no-default-queries \
  --query-set first_person \
  --query-csv data/keyword_search_combos/general.csv \
  --query-csv data/keyword_search_combos/institutional_threats.csv \
  --query-csv data/keyword_search_combos/organizational_threats.csv \
  --query-csv data/keyword_search_combos/ambiguous_others.csv \
  --query-csv data/keyword_search_combos/interpersonal.csv \
  --author-comments-only \
  --max-pages-per-query 3
```

Third person observer:

```bash
python3 scripts/search_identity_discovery.py \
  --out-dir data/set2_broad_keyword_search/third_person_observer \
  --no-default-queries \
  --query-set third_person_observer \
  --query-csv data/keyword_search_combos/third_person_observer.csv \
  --author-comments-only \
  --max-pages-per-query 3
```

Third person finder:

```bash
python3 scripts/search_identity_discovery.py \
  --out-dir data/set2_broad_keyword_search/third_person_finder \
  --no-default-queries \
  --query-set third_person_finder \
  --query-csv data/keyword_search_combos/third_person_finder.csv \
  --author-comments-only \
  --max-pages-per-query 3
```

If a run stops, resume it with the same `--out-dir` plus `--resume`. Completed
searches and per-post comment fetches are reused, not repeated.

## Scale

33,344 phrases at 3 pages per query is roughly 100,000 search requests before any
post fetches. Reddit's OAuth limit is about 100 requests/minute, so a full
three-run sweep is on the order of a day of wall clock, resumable throughout.

To cut it down, lower `--max-pages-per-query` to 1 (about a third of the
requests), or run a subset of the query CSVs first. The observer set is by far
the largest and can be trimmed by filtering `third_person_observer.csv` to one
pronoun.

## Provenance In The Output

Every post row records which phrases surfaced it and what threat model those
phrases came from:

- `matched_query_groups`: which voice set(s) — `first_person`,
  `third_person_observer`, `third_person_finder`.
- `matched_queries`: the exact phrases that matched.
- `matched_categories`, `matched_target_terms`, `matched_templates`: threat-model
  provenance carried from the keyword CSVs.
- `search_rank_min`, `search_rank_all`: where the post ranked in each query.

The same columns appear on comment rows, so a post found by an `Institutional
Threats` phrase stays identifiable as such all the way through analysis.
