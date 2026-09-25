# reddit-foundthepost

Public Reddit post/comment collection for content analysis of situations where
someone's Reddit post or account is discovered by someone else.

## Reddit Now Requires OAuth

Reddit answers **HTTP 403 Blocked** for unauthenticated requests to its public
`.json` endpoints. Every collection script in this repo used those endpoints, so
new collection needs OAuth credentials from a "script" app at
<https://www.reddit.com/prefs/apps>:

```bash
export REDDIT_CLIENT_ID=...
export REDDIT_CLIENT_SECRET=...
```

All four collection scripts share one OAuth client, `scripts/reddit_client.py`,
and read those two variables. Credentials are never written into a manifest;
each manifest records only `auth_mode`. Already-collected data is unaffected.

Check credentials before a long run:

```bash
python3 scripts/check_reddit_auth.py
```

It fetches a token, makes one real search, and reports the rate limit Reddit
returns.

## Data Sets

| Set | What | Status |
| --- | --- | --- |
| [set 1](data/set1_foundthepost_subreddit/) | `r/foundthepost` subreddit snapshot | collected |
| [set 2](data/set2_broad_keyword_search/) | Reddit-wide keyword search, 3 voices | pending credentials |
| [set 3](data/set3_arctic_keyword_search/) | Historical Arctic submissions, first- and third-person literal keyword search | collected; database in release |
| [keywords](data/keyword_search_combos/) | 33,344 search phrases by threat model | ready |

## Start Here

1. This `README.md` for the project map.
2. [`data/set1_foundthepost_subreddit/20260527_foundthepost_snapshot/README.md`](data/set1_foundthepost_subreddit/20260527_foundthepost_snapshot/README.md)
   for the tracked `r/foundthepost` snapshot and its analysis-ready files.
3. [`data/keyword_search_combos/README.md`](data/keyword_search_combos/README.md)
   for the keyword sets and what each CSV is for.
4. [`data/set2_broad_keyword_search/README.md`](data/set2_broad_keyword_search/README.md)
   for the broad-search runs and their commands.
5. [`data/set3_arctic_keyword_search/README.md`](data/set3_arctic_keyword_search/README.md)
   for the historical post-only dataset, keyword rationale, schema, counts, and
   [database download](https://github.com/kyzylmonteiro/reddit-foundthepost/releases/tag/set3-arctic-2026-09-20).
6. [`BROAD_REDDIT_SEARCH.md`](BROAD_REDDIT_SEARCH.md) for the search collector,
   output tables, and join keys.
7. [`ANNOTATION_GUIDE.md`](ANNOTATION_GUIDE.md) if you are preparing or using
   the human annotation sheet.
8. [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) only when rerunning the
   `r/foundthepost` collection or checking exact collection commands.

You should not need to open every script to understand the data. The scripts
are here for reproducibility; the per-dataset README files and manifests are
the main documentation for analysis.

## What Is In This Repo

- **Set 1**: a tracked `r/foundthepost` snapshot with 80 public subreddit
  submissions and 66,690 normalized comments from linked source posts.
- **Set 2**: a Reddit-wide keyword search across all of Reddit, run separately
  for first-person, third-person observer, and finder voices. Author comments
  only.
- **Set 3**: 2,809,926 matched submissions from 2,533 Arctic Parquet shards
  (published shards from 2005–2013, 2017–2019, and 2023–February 2026;
  some months are missing). Posts only,
  with original title and body, metadata, keyword matches, and extracted Reddit
  links. The 29,841-phrase CSV is tracked here; the 8.3 GiB SQLite database is
  [downloadable as a compressed release asset](https://github.com/kyzylmonteiro/reddit-foundthepost/releases/tag/set3-arctic-2026-09-20).
- **Keyword sets**: 33,344 search phrases organized by threat model, converted
  from the source workbook and extended with generated third-person variants.
- Reproducible Python scripts for all of the above.

## What Is Local Only

Broad-search output is large, so per-post comment checkpoints and saved raw
search records are ignored by git. The analysis tables are tracked.

An earlier exploratory scrape lived at
`data/broad_identity_search/20260528_broad_search_results/` and is not part of
this clone. Its annotation sheet, `review_posts_for_annotation.csv`, was
produced outside the repo; no script in the repo generates it. See
[`ANNOTATION_GUIDE.md`](ANNOTATION_GUIDE.md).

If you are receiving this repo with a Box link, use the Box file as the exact
dataset for annotation. Rerunning a search reproduces the collection method and
output schema, but Reddit search/results can change, so a fresh run should be
treated as a comparable new scrape rather than an exact copy of the Box upload.

## Reproduce

Set 2, the Reddit-wide keyword search — see
[`data/set2_broad_keyword_search/README.md`](data/set2_broad_keyword_search/README.md)
for the three run commands.

Set 1, the `r/foundthepost` collection:

```bash
python3 scripts/run_full_collection.py
```

See `REPRODUCIBILITY.md` for the two-step commands, resume behavior, and live
data caveats. Note this path currently fails against Reddit's 403 on anonymous
requests.

## Current Snapshot

Set 1's enriched snapshot:

`data/set1_foundthepost_subreddit/20260527_foundthepost_snapshot/`

It contains 80 public submissions collected from Reddit's unauthenticated
`new.json` listing on 2026-05-27, back when that endpoint was open. Reddit
returned one page with no pagination token, so this appears to cover the
currently visible subreddit submission history.

Source-post comments were also collected for 81 unique linked source threads.
The public Reddit JSON endpoints returned comments for 80 of those threads,
yielding 66,690 normalized source-comment records.

## Files

Scripts:

- `scripts/reddit_client.py` is the shared OAuth Reddit client used by every
  collector.
- `scripts/check_reddit_auth.py` verifies credentials and reports rate limits.
- `scripts/collect_reddit_posts.py` collects public submissions and writes a
  date-stamped snapshot under `data/`. Set 1 only.
- `scripts/collect_source_comments.py` collects comments from source Reddit
  posts linked by the normalized post table. Set 1 only.
- `scripts/run_full_collection.py` runs both collection steps and writes a
  `collection_run_manifest.json` with commands and parameters.
- `scripts/search_identity_discovery.py` searches Reddit-wide for identity
  discovery keywords and writes post/comment CSVs. Set 2. Supports OAuth,
  keyword CSVs via `--query-csv`, and `--author-comments-only`.
- `scripts/xlsx_to_csv.py` converts an `.xlsx` workbook to one CSV per sheet.
- `scripts/build_third_person_queries.py` generates the third-person keyword
  sets from the first-person workbook.

Set 1 snapshot files:

- `posts_normalized.csv` is the analysis-friendly table.
- `posts_normalized.jsonl` is the same normalized data as newline-delimited
  JSON.
- `posts_raw.jsonl` keeps the raw listing child payloads returned by Reddit.
- `pages.json` records pagination metadata.
- `manifest.json` records collection timing, counts, and caveats.
- `source_comments/` contains flattened comments from linked source posts.

## Broad Search Artifacts

`scripts/search_identity_discovery.py` writes one timestamped folder per run.
Use `review_posts.csv` for Google Sheets/manual coding: one row per candidate
post, compact text excerpts, links, matched keywords, scores, and blank review
columns. `posts.csv` keeps the richer post metadata and rehydration IDs.
`comments.csv` contains every collected comment; `author_comments.csv` is the
OP-only subset for fast follow-up. Under `--author-comments-only` both files
hold only the post author's comments, and `manifest.json` records
`comments_scope: author_only`. `manifest.json`, `search_pages.json`, and
`comment_fetch_log.jsonl` explain exactly how the run was made and what Reddit
returned. If a local broad scrape is interrupted, rerun
`python3 scripts/search_identity_discovery.py --resume`; the script uses
`run_state.json` and `comment_checkpoints/` to skip work it already finished.

## Notes

The normalized post table includes both the `r/foundthepost` submission fields
and, when Reddit exposed it, source post fields from `crosspost_parent_list`.
Source comments are stored separately so post-level and comment-level analysis
can be joined by `source_id` or `foundthepost_ids`. Deleted, removed, private,
or otherwise inaccessible content is not recovered.
