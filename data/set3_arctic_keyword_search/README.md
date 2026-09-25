# Arctic Reddit keyword-search dataset

This directory contains Reddit submissions selected from the Hugging Face dataset
[`Dk587/arctic`](https://huggingface.co/datasets/Dk587/arctic) using a documented
literal keyword search.

## Files and download

- [`keywords_all_perspectives.csv`](keywords_all_perspectives.csv) — 29,841 deduplicated search phrases
  with perspective and provenance.
- [`arctic_keyword_matches.sqlite.zst`](https://github.com/kyzylmonteiro/reddit-foundthepost/releases/download/set3-arctic-2026-09-20/arctic_keyword_matches.sqlite.zst) — compressed SQLite database of matched post metadata, title, body,
  keyword matches, and extracted Reddit links. The 1,992,017,167-byte archive is a
  GitHub release asset, not a Git-tracked file; the uncompressed database is
  8,863,924,224 bytes.

Download and decompress with [Zstandard](https://github.com/facebook/zstd):

```bash
curl -L -o arctic_keyword_matches.sqlite.zst \
  https://github.com/kyzylmonteiro/reddit-foundthepost/releases/download/set3-arctic-2026-09-20/arctic_keyword_matches.sqlite.zst
shasum -a 256 arctic_keyword_matches.sqlite.zst
zstd -d arctic_keyword_matches.sqlite.zst -o arctic_keyword_matches.sqlite
sqlite3 arctic_keyword_matches.sqlite 'PRAGMA integrity_check;'
```

Expected archive SHA-256: `929546f53a38242bf954742aa9c00e9c412c8ad2b690496241c0a7d2c61bc280`.
Allow about 11 GB of free space to hold both the archive and decompressed database.

## Coverage and totals

The source contained 2,533 Parquet shards and 1,232,412,787 submission rows.
All submission shards published in `Dk587/arctic` at collection time were searched.
The published shards covered 2005–2013, 2017–2019, 2023–2025, and
January–February 2026, with only some months available in 2013, 2017–2019,
and 2023. The 2014–2016 and 2020–2022 submission shards had not been published
there, so Set 3 has no results for those years. The dataset card's
[“Remaining months” table](https://huggingface.co/datasets/Dk587/arctic#remaining-months-280-pairs)
lists source archive months awaiting conversion/upload; it is not a list of
downloadable Parquet files. To assess coverage, check the dataset's current
[`data/submissions` file tree](https://huggingface.co/datasets/Dk587/arctic/tree/main/data/submissions)
or its committed-month [`stats.csv`](https://huggingface.co/datasets/Dk587/arctic/blob/main/stats.csv).

The final database contains:

- 2,809,926 matched posts
- 2,824,422 post-to-keyword match records
- 2,659,819 extracted Reddit-link records
- Original title and body for every matched post
- Submitted URL and constructed Reddit permalink
- Timestamp, subreddit, flair fields, score, comment count, NSFW flag, Reddit IDs,
  source shard, and search provenance

Matched posts by source year:

| Year | Posts |
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

## Keyword rationale

The keyword catalog was designed to capture first-person and third-person accounts
of someone discovering, recognizing, tracing, sharing, or confronting a person about
their Reddit activity.

The starting source was the supplied CSV named `Keyword Search Combos_ FIRST PERSON
(by threat model) - All first person searches.csv`, which contained 7,886 unique
phrases grouped around threat actors such as courts, employers, family members,
partners, landlords, schools, authorities, and strangers.

The catalog was expanded in three ways:

1. The 19 phrases supplied directly with the request were added, including phrases
   such as `found my reddit account`, `recognized my post`, and `confronted me about
   my post`.
2. Eighty-five contextual coverage phrases were added for common gaps: identity
   linking and tracing, post or comment history, alternate/throwaway/burner accounts,
   screenshots, confrontation, reporting, recognition, and doxxing.
3. Phrases containing first-person pronouns were converted into neutral, feminine,
   and masculine third-person variants. Examples include `my → their/her/his`,
   `me → them/her/him`, and `I → they/she/he`.

After case-insensitive deduplication, the catalog contains:

- 7,989 first-person phrases
- 21,852 third-person phrases
- 29,841 phrases in total

Each CSV row contains:

- `keyword_id` — stable identifier derived from perspective and normalized phrase
- `keyword` — searched phrase
- `perspective` — `first_person` or `third_person`
- `pronoun_variant` — first-person, neutral, feminine, or masculine form
- `source` — attached CSV, directly supplied phrase, coverage addition, or derivation
- `source_phrase` — original phrase from which a variant was created

## Search method

The title and self-text of every submission were searched separately. Text and
keywords were normalized with Unicode NFKC normalization, case folding, and
whitespace collapsing. Matching was a literal substring search using an
Aho–Corasick automaton. It was not a semantic classifier, fuzzy search, stemming
algorithm, or manual review.

The database records whether each keyword matched the title, self-text, or both.
Multiple matched keywords are retained for the same post. Source Parquet files were
processed one shard at a time and deleted after their database transaction succeeded.

Reddit and `redd.it` URLs present in a matched title, body, or submitted URL were
extracted automatically into `post_links`. This supports identifying quoted posts,
cross-references, or repost-like submissions without manually interpreting content.

## Database tables

### `posts`

One row per matched Reddit submission. Important columns include `post_id`,
`reddit_fullname`, `created_utc`, `created_at`, `subreddit`, `link_flair_text`,
`author_flair_text`, `score`, `num_comments`, `over_18`, `permalink`, `title`,
`selftext`, `submitted_url`, `source_dataset`, and `source_file`.

### `keywords`

The keyword catalog embedded in the database. It mirrors the final keyword CSV.

### `post_keyword_matches`

Many-to-many relationship between posts and keywords. It records title/body match
location and the normalization/search method.

### `post_links`

Reddit URLs extracted from matched titles, bodies, and submitted URLs. `link_origin`
identifies the field containing the URL.

### `processed_files`

Audit record for every source shard, including byte size, source-row count, matched
post count, and processing timestamp.

### `content_backfills`

Audit record for the 2005–2013 content backfill.

## Example queries

Count matches by year:

```sql
SELECT substr(created_at, 1, 4) AS year, COUNT(*) AS posts
FROM posts
GROUP BY year
ORDER BY year;
```

Retrieve posts and their matched phrases:

```sql
SELECT
  p.post_id,
  p.created_at,
  p.subreddit,
  p.title,
  p.permalink,
  k.keyword,
  k.perspective,
  m.matched_in_title,
  m.matched_in_selftext
FROM posts AS p
JOIN post_keyword_matches AS m USING (post_id)
JOIN keywords AS k USING (keyword_id);
```

Retrieve referenced Reddit links:

```sql
SELECT p.post_id, p.permalink, l.url, l.link_origin
FROM posts AS p
JOIN post_links AS l USING (post_id);
```

## Interpretation limitations

- A literal match is a candidate result, not proof that account discovery or harm
  occurred. Broad phrases such as `found out` can produce substantial false positives.
- The catalog improves recall through many variants, but cannot cover every spelling,
  euphemism, typo, language, or implicit description.
- No semantic relevance scoring or manual validation was performed.
- A post may match several overlapping phrases. Use `posts` for unique-post counts and
  `post_keyword_matches` for phrase-level counts.
- Extracted links indicate that a Reddit URL appeared in a stored field; they do not
  by themselves prove that a submission is a repost or quotation.
- Counts reflect the contents of the source dataset at the time of collection and the
  available source years listed above.

## Relationship to [Set 2](https://github.com/kyzylmonteiro/reddit-foundthepost/tree/set2-broad-keyword-search)

Set 2's planned collector searches live Reddit with three keyword perspectives
and collects author comments. Set 3 searches the historical Arctic submission
corpus only: it stores posts, not comments, and its first-/third-person catalog
does not include Set 2's finder-voice phrases. The two collection methods and
their available time ranges differ, so Set 2's retrieved posts cannot be
assumed to be a subset of Set 3's
without a post-ID comparison of actual Set 2 output. Their data schemas also differ;
use Reddit post IDs to join or deduplicate across sets.

## Verification

The final SQLite integrity check returned `ok`. Every matched post has a stored title
and body, every one of the 2,533 source shards has a processing audit record, and no
downloaded Parquet or partial-download files remain in the project.
