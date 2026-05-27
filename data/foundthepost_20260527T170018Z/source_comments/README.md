# Source Comment Collection

Comments collected from the original/source Reddit posts linked by the 80
`r/foundthepost` submissions.

## Summary

- Unique linked source threads discovered: 81
- Publicly accessible source threads collected: 80
- Normalized comments collected: 66,690
- Unique `source_id:comment_id` pairs: 66,690
- Source threads with comments in the final dataset: 80
- Inaccessible source thread: `1f7s7cb`
- Unresolved `morechildren` IDs: 9,637

The inaccessible thread is:

`https://www.reddit.com/r/u_Other_Salt3889/comments/1f7s7cb/my_wifes_posts/`

Reddit returned HTTP 403 for that source through the public JSON endpoint.

## Files

- `source_comments_normalized.csv`: comment-level table for analysis.
- `source_comments_normalized.jsonl`: normalized comment records without CSV
  quoting concerns.
- `source_comments_raw.jsonl.gz`: compressed raw Reddit `t1` comment payloads
  with `source_id`.
- `source_posts_for_comments.jsonl`: source-thread discovery and mapping back to
  the `foundthepost` submissions that referenced each source.
- `source_comment_fetch_log.jsonl`: per-source fetch stats, errors, and
  unresolved `morechildren` IDs.
- `source_comment_manifest.json`: collection summary and caveats.

## Key Join Fields

- `source_id`: Reddit submission ID for the original/source post.
- `comment_id`: Reddit comment ID.
- `foundthepost_ids`: semicolon-delimited `r/foundthepost` submission IDs that
  referenced the source thread.
- `source_permalink`: source post permalink.

## Caveats

The collector used Reddit's public comments endpoint plus `api/morechildren`
expansion. Deleted, removed, private, quarantined, or otherwise inaccessible
comments cannot be recovered. Some hidden comment IDs returned by Reddit's
comment listing did not resolve through `api/morechildren`; those IDs are
preserved in the fetch log.
