# Reproducibility

This project uses live Reddit public JSON endpoints. The scripts reproduce the
collection method and output schema, but future runs may not be bit-for-bit
identical because Reddit content can be edited, deleted, removed, made private,
rescored, or newly added.

For bit-for-bit analysis of the dataset already collected, use the preserved
snapshot directory:

`data/20260527_foundthepost_snapshot/`

## One-Command Collection

Run the full post + source-comment workflow:

```bash
python3 scripts/run_full_collection.py
```

This creates:

```text
data/<YYYYMMDD>_foundthepost_snapshot/
  posts_raw.jsonl
  posts_normalized.jsonl
  posts_normalized.csv
  pages.json
  manifest.json
  collection_run_manifest.json
  source_comments/
    source_posts_for_comments.jsonl
    source_comments_raw.jsonl.gz
    source_comments_normalized.jsonl
    source_comments_normalized.csv
    source_comment_fetch_log.jsonl
    source_comment_manifest.json
```

If the same collection is run more than once on a date, the script adds a
numeric suffix such as `_2`.

The runner writes `collection_run_manifest.json` with the exact commands,
parameters, Python version, platform string, output paths, and summary counts.
By default it also tries the comment step again with `--resume` up to two times
when a source-thread failure is logged, which helps recover from transient
Reddit rate limits.

The live pipeline writes an uncompressed `source_comments_raw.jsonl`. Before
publishing to GitHub, compress it with `gzip -9 source_comments_raw.jsonl`; this
repository tracks `source_comments_raw.jsonl.gz` and ignores the uncompressed
copy because it is larger than GitHub's normal file limit.

## Step 1: Collect r/foundthepost Posts

```bash
python3 scripts/collect_reddit_posts.py \
  --subreddit foundthepost \
  --out-dir data \
  --delay-seconds 1.0
```

The command prints the snapshot directory. Use its `posts_normalized.jsonl` as
the input to the comment collector.

## Step 2: Collect Source-Post Comments

Replace `<SNAPSHOT_DIR>` with the directory printed by step 1:

```bash
python3 scripts/collect_source_comments.py \
  --source-jsonl <SNAPSHOT_DIR>/posts_normalized.jsonl \
  --out-dir <SNAPSHOT_DIR>/source_comments \
  --delay-seconds 1.5 \
  --more-batch-size 100
```

The comment collector discovers source Reddit threads from formal crossposts,
direct Reddit post/comment links, and Reddit links inside `selftext`.

## Resume After Rate Limits

If Reddit rate-limits a long comment collection, rerun the same command with
`--resume`. Successful source threads already written to the output directory
are skipped; failed source threads are retried.

```bash
python3 scripts/collect_source_comments.py \
  --source-jsonl <SNAPSHOT_DIR>/posts_normalized.jsonl \
  --out-dir <SNAPSHOT_DIR>/source_comments \
  --delay-seconds 1.5 \
  --more-batch-size 100 \
  --resume
```

The standalone comment collector exits non-zero if any source thread fails,
even when the failure is an inaccessible Reddit thread that was logged
successfully. Inspect `source_comment_manifest.json` and
`source_comment_fetch_log.jsonl` for final status.

## Dependencies

Python 3.9+ is sufficient. The collection scripts use only the Python standard
library.
