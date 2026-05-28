# reddit-foundthepost

Public Reddit post/comment collection for content analysis of situations where
someone's Reddit post or account is discovered by someone else.

## Start Here

If you are new to the repo, read files in this order:

1. This `README.md` for the project map and what is already included.
2. [`data/foundthepost_20260527T170018Z/README.md`](data/foundthepost_20260527T170018Z/README.md)
   for the tracked `r/foundthepost` snapshot and its analysis-ready files.
3. [`BROAD_REDDIT_SEARCH.md`](BROAD_REDDIT_SEARCH.md) for the Reddit-wide
   keyword search, the larger local scrape, output tables, and join keys.
4. [`ANNOTATION_GUIDE.md`](ANNOTATION_GUIDE.md) if you are preparing or using
   the human annotation sheet.
5. [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) only when rerunning the
   `r/foundthepost` collection or checking exact collection commands.

You should not need to open every script to understand the data. The scripts
are here for reproducibility; the per-dataset README files and manifests are
the main documentation for analysis.

## What Is In This Repo

- A tracked `r/foundthepost` snapshot with 80 public subreddit submissions and
  66,690 normalized comments from linked source posts.
- Reproducible Python scripts for collecting the subreddit snapshot and source
  comments.
- A Reddit-wide keyword-search collector for finding broader identity-discovery
  cases outside `r/foundthepost`.

## What Is Local Only

The full Reddit-wide scrape is large, so it is ignored by git and is not part
of a normal GitHub push. On this machine, the latest full local run is:

`data/broad_identity_search/20260528_broad_search_results/`

Start with its `review_posts.csv` for manual coding in Google Sheets. See
[`BROAD_REDDIT_SEARCH.md`](BROAD_REDDIT_SEARCH.md) for links, table structure,
and join keys. For human annotators, use `review_posts_for_annotation.csv`
instead; it keeps the coding columns at the front so annotators can update the
sheet without reorganizing it.

If you are receiving this repo with a Box link, use the Box file as the exact
dataset for annotation. Rerunning the Reddit-wide script reproduces the
collection method and output schema, but Reddit search/results can change, so
a fresh run should be treated as a comparable new scrape rather than an exact
copy of the Box upload.

## Reproduce

Run the full live collection workflow with:

```bash
python3 scripts/run_full_collection.py
```

See `REPRODUCIBILITY.md` for the two-step commands, resume behavior, and live
data caveats.

For broader Reddit-wide discovery outside `r/foundthepost`, see
`BROAD_REDDIT_SEARCH.md` and `scripts/search_identity_discovery.py`.

## Current Snapshot

Latest enriched snapshot:

`data/foundthepost_20260527T170018Z/`

It contains 80 public submissions collected from Reddit's unauthenticated
`new.json` listing on 2026-05-27. Reddit returned one page with no pagination
token, so this appears to cover the currently visible subreddit submission
history.

Source-post comments were also collected for 81 unique linked source threads.
The public Reddit JSON endpoints returned comments for 80 of those threads,
yielding 66,690 normalized source-comment records.

## Files

- `scripts/collect_reddit_posts.py` collects public submissions and writes a
  timestamped snapshot under `data/`.
- `scripts/collect_source_comments.py` collects comments from source Reddit
  posts linked by the normalized post table.
- `scripts/run_full_collection.py` runs both collection steps and writes a
  `collection_run_manifest.json` with commands and parameters.
- `scripts/search_identity_discovery.py` searches Reddit-wide for identity
  discovery keywords and writes post/comment CSVs.
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
OP-only subset for fast follow-up. `manifest.json`, `search_pages.json`, and
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
