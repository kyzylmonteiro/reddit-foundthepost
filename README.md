# reddit-foundthepost

Public post collection for content analysis of `r/foundthepost`.

## Reproduce

Run the full live collection workflow with:

```bash
python3 scripts/run_full_collection.py
```

See `REPRODUCIBILITY.md` for the two-step commands, resume behavior, and live
data caveats.

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
- `posts_normalized.csv` is the analysis-friendly table.
- `posts_normalized.jsonl` is the same normalized data as newline-delimited
  JSON.
- `posts_raw.jsonl` keeps the raw listing child payloads returned by Reddit.
- `pages.json` records pagination metadata.
- `manifest.json` records collection timing, counts, and caveats.
- `source_comments/` contains flattened comments from linked source posts.

## Notes

The normalized post table includes both the `r/foundthepost` submission fields
and, when Reddit exposed it, source post fields from `crosspost_parent_list`.
Source comments are stored separately so post-level and comment-level analysis
can be joined by `source_id` or `foundthepost_ids`. Deleted, removed, private,
or otherwise inaccessible content is not recovered.
