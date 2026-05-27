# reddit-foundthepost

Public post collection for content analysis of `r/foundthepost`.

## Reproduce

Run the full live collection workflow with:

```bash
python3 scripts/run_full_collection.py
```

See `REPRODUCIBILITY.md` for the two-step commands, resume behavior, and live
data caveats.

For broader Reddit-wide discovery outside `r/foundthepost`, see
`BROAD_REDDIT_SEARCH.md` and `scripts/search_identity_discovery.py`.

To run that broader scrape on GitHub's servers, open the **Broad Reddit
identity search** workflow in Actions, choose **Run workflow**, then download
the uploaded artifact when it finishes.

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
returned.

## Notes

The normalized post table includes both the `r/foundthepost` submission fields
and, when Reddit exposed it, source post fields from `crosspost_parent_list`.
Source comments are stored separately so post-level and comment-level analysis
can be joined by `source_id` or `foundthepost_ids`. Deleted, removed, private,
or otherwise inaccessible content is not recovered.
