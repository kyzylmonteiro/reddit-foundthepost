# Broad Reddit Identity-Discovery Search

## Goal

Find Reddit posts outside `r/foundthepost` where someone reports that another
person discovered, recognized, or used the poster's Reddit post/account in a
way that linked the online post back to the original poster's offline identity.

This is broader than the `r/foundthepost` snapshot. It searches Reddit-wide for
candidate phrases, deduplicates posts across queries, then fetches each post's
comment tree so we can inspect both the full discussion and the original
poster's own replies.

## Caveats

Reddit search is a discovery method, not a complete corpus. Results can vary
over time as posts are edited, removed, deleted, rescored, or newly indexed.
Broad phrases like `"found out"` are expected to be noisy; they are included
because they may recover cases that do not explicitly say "found my post".
Downvotes are not directly exposed by Reddit's public JSON endpoints, so the
script records `score`, `upvote_ratio`, and estimated up/downvote counts derived
from those fields.

Wildcard searches like `Reddit*` are represented as explicit phrase expansions
because Reddit's public search behavior for wildcard syntax is inconsistent.

## Keyword Groups

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

Or run it on GitHub's servers from the **Broad Reddit identity search** workflow
in the repository's Actions tab. The workflow uploads the timestamped output
folder as a downloadable artifact. Before using the workflow, add repository
secrets `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`; hosted runners use Reddit
OAuth because unauthenticated Reddit JSON requests can be blocked.

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
