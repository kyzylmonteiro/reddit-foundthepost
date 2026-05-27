# r/foundthepost Snapshot

Collected by `scripts/run_full_collection.py` on 2026-05-27.

## Summary

- Subreddit: `r/foundthepost`
- Public submissions collected: 80
- Unique submission IDs: 80
- Listing pages: 1
- Pagination token after first page: none
- Submission date range: 2022-09-23 to 2025-12-15 UTC
- Records with source post payloads: 73
- Unique linked source threads discovered for comment collection: 81
- Source threads with public comments collected: 80
- Normalized source comments collected: 66,690
- Inaccessible source threads: 1

## Recommended Files

Use `posts_normalized.csv` for post-level spreadsheet or qualitative coding
software. Use `posts_normalized.jsonl` if you want stable machine-readable
records without CSV quoting concerns. Some CSV fields contain embedded
newlines, so count rows with a CSV parser rather than plain line counts.

For source-post comments, use
`source_comments/source_comments_normalized.csv` or
`source_comments/source_comments_normalized.jsonl`.
The raw source comment payloads are stored as
`source_comments/source_comments_raw.jsonl.gz`.

Use `collection_run_manifest.json` for the exact commands and parameters that
produced this snapshot.

## Key Post Columns

- `title`, `selftext`, `text_for_analysis`: the `r/foundthepost` submission.
- `link_flair_text`: subreddit flair category.
- `permalink`, `url`: local submission permalink and linked target.
- `source_title`, `source_selftext`, `source_text_for_analysis`: original
  source post content when Reddit included a crosspost payload.
- `source_subreddit`, `source_permalink`, `source_url`: source context fields.

## Caveats

The source comment collection uses Reddit's public comments endpoint plus
`api/morechildren` expansion. It cannot recover deleted, removed, private,
quarantined, or otherwise inaccessible comments. The source thread
`https://www.reddit.com/r/u_Other_Salt3889/comments/1f7s7cb/my_wifes_posts/`
returned HTTP 403 through the public JSON endpoint.

Reddit returned 9,637 hidden comment IDs that its public `morechildren`
endpoint did not resolve; these are tracked in
`source_comments/source_comment_fetch_log.jsonl`.
