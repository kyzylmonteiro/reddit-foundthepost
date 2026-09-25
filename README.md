# Reddit post and account discovery: Arctic keyword search

This repository's primary dataset is **Set 3**: Reddit submissions from
[`Dk587/arctic`](https://huggingface.co/datasets/Dk587/arctic) whose titles or
bodies contain phrases about someone discovering, recognizing, tracing, sharing,
or confronting a person about their Reddit activity. The search produced
**2,809,926 matched posts**. It includes submissions only, not comments.

The [Set 3 dataset README](data/set3_arctic_keyword_search/README.md) gives the
full keyword rationale, field descriptions, SQL examples, and verification
details. Earlier [Set 1](data/set1_foundthepost_subreddit/20260527_foundthepost_snapshot/README.md)
and [Set 2](https://github.com/kyzylmonteiro/reddit-foundthepost/tree/set2-broad-keyword-search)
work remains in the repository; see [Earlier collections](#earlier-collections).

## Get the data

| File | Contents |
| --- | --- |
| [Keyword CSV](data/set3_arctic_keyword_search/keywords_all_perspectives.csv) | 29,841 first- and third-person search phrases, with perspective and provenance |
| [SQLite database download](https://github.com/kyzylmonteiro/reddit-foundthepost/releases/download/set3-arctic-2026-09-20/arctic_keyword_matches.sqlite.zst) | Matched posts, title and body, metadata, keyword matches, extracted Reddit links, and source-shard audit |

The database is a GitHub release asset because the uncompressed SQLite file is
8,863,924,224 bytes. Its compressed archive is 1,992,017,167 bytes. Download
and decompress it with [Zstandard](https://github.com/facebook/zstd):

```bash
curl -L -o arctic_keyword_matches.sqlite.zst \
  https://github.com/kyzylmonteiro/reddit-foundthepost/releases/download/set3-arctic-2026-09-20/arctic_keyword_matches.sqlite.zst
shasum -a 256 arctic_keyword_matches.sqlite.zst
zstd -d arctic_keyword_matches.sqlite.zst -o arctic_keyword_matches.sqlite
sqlite3 arctic_keyword_matches.sqlite 'PRAGMA integrity_check;'
```

The expected archive SHA-256 is
`929546f53a38242bf954742aa9c00e9c412c8ad2b690496241c0a7d2c61bc280`.
Allow about 11 GB of free disk space for both archive and database.

## Coverage and results

Set 3 searched 1,232,412,787 submissions in 2,533 Parquet shards published by
`Dk587/arctic` at collection time. The database contains 2,809,926 unique
matched posts, 2,824,422 post-to-keyword match records, and 2,659,819 extracted
Reddit-link records.

| Source year | Matched posts |
| ---: | ---: |
| 2005 | 0 |
| 2006 | 15 |
| 2007 | 50 |
| 2008 | 170 |
| 2009 | 1,815 |
| 2010 | 8,361 |
| 2011 | 33,985 |
| 2012 | 88,139 |
| 2013 | 91,184 |
| 2017 | 18,537 |
| 2018 | 21,288 |
| 2019 | 41,419 |
| 2023 | 81,326 |
| 2024 | 1,101,148 |
| 2025 | 1,143,130 |
| 2026 through February | 179,359 |

Only some months were available for 2013, 2017–2019, and 2023. Submission
shards for 2014–2016 and 2020–2022 had not been published in this Hugging Face
dataset, so those years have no Set 3 results. Its dataset card lists those
months under [“Remaining months”](https://huggingface.co/datasets/Dk587/arctic#remaining-months-280-pairs),
which describes work awaiting conversion and upload. Check the current
[`data/submissions` file tree](https://huggingface.co/datasets/Dk587/arctic/tree/main/data/submissions)
for newly published shards.

## What each matched post retains

The `posts` table stores the Reddit ID, timestamp, subreddit, title, body
(`selftext`), flair, score, comment count, NSFW flag, submitted URL, permalink,
and source shard. A link post can have an empty body. The
`post_keyword_matches` table records each matching phrase and whether it
appeared in the title, body, or both. The `post_links` table records Reddit URLs
found in the title, body, or submitted URL, including possible references to
another post. `processed_files` records the source shards searched.

The [dataset README](data/set3_arctic_keyword_search/README.md#database-tables)
describes all tables and gives example joins and queries.

## Keywords and search method

The starting catalog was a supplied CSV with 7,886 unique first-person phrases
organized by threat model. We added the 19 phrases provided with the request,
85 coverage phrases for account tracing, screenshots, throwaways, recognition,
confrontation, and related cases, then generated neutral, feminine, and masculine
third-person variants. After case-insensitive deduplication, the final CSV has
7,989 first-person and 21,852 third-person phrases.

Every submission's title and body were searched separately after Unicode NFKC
normalization, case folding, and whitespace collapsing. Matching used literal
substring search with an Aho–Corasick automaton. Multiple matches on one post
were retained. This was a basic keyword search, with no semantic classifier or
manual reading of posts during selection. The source Parquet files were handled
one shard at a time and removed locally after successful processing.

These are **candidate posts**, not verified accounts of discovery or harm.
Broad phrases can produce false positives; implicit accounts, other languages,
and unlisted wording can be missed. A Reddit link in a post does not by itself
prove that the post is a repost or quotation. Use `posts` for unique-post counts
and `post_keyword_matches` for phrase-level counts.

## Earlier collections

- [Set 1](data/set1_foundthepost_subreddit/20260527_foundthepost_snapshot/README.md)
  is a snapshot of `r/foundthepost`: 80 subreddit submissions and 66,690
  normalized comments from linked source posts.
- The [Set 2 broad-search branch](https://github.com/kyzylmonteiro/reddit-foundthepost/tree/set2-broad-keyword-search)
  documents a Reddit-wide search design with first-person, observer, and finder
  voices. Its [README](https://github.com/kyzylmonteiro/reddit-foundthepost/blob/set2-broad-keyword-search/data/set2_broad_keyword_search/README.md)
  records the planned runs and OAuth requirement. No Set 2 result tables are
  tracked in this repository.
- The [Set 3 branch](https://github.com/kyzylmonteiro/reddit-foundthepost/tree/set3-arctic-keyword-search)
  preserves the initial Arctic publication. `main` is the cumulative branch.

The older collection scripts and documentation remain available for
reproducibility. They do not generate the Set 3 database; its documented search
method and published database are the reference for Set 3 analysis.
