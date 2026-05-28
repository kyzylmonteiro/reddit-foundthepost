# Annotation Guide

Use this guide with the broad Reddit identity-discovery annotation sheet.

## Primary File

Annotators should work from:

`review_posts_for_annotation.csv`

This is a Google Sheets-ready screening file with one row per candidate Reddit
post. The first columns are for human coding; the remaining columns are source
metadata and should be treated as read-only.

## Coding Columns

Fill only these columns unless the project lead asks otherwise:

- `annotator_id`: short stable name or initials for the annotator.
- `review_status`: `todo`, `in_progress`, `done`, or `skip`.
- `include_for_analysis`: `yes`, `no`, or `unsure`.
- `case_type`: short label for the kind of case.
- `confidence`: `high`, `medium`, or `low`.
- `needs_second_review`: `yes` or `no`.
- `duplicate_of_post_id`: if this row is a duplicate, enter the primary
  `post_id`; otherwise leave blank.
- `review_notes`: brief rationale or uncertainty.

Do not rename, delete, or reorder columns. `post_id` is the stable row key used
to merge annotations back into the dataset.

## Inclusion Rule

Mark `include_for_analysis = yes` when the post appears to describe someone
discovering, recognizing, confronting, sharing, or using the poster's Reddit
post/account in a way that connects Reddit activity back to the person who
posted it.

Mark `include_for_analysis = no` when the row is search noise, for example:

- "found out" does not refer to Reddit, a Reddit post, or a Reddit account.
- The post is only about finding information on Reddit, not identifying the
  poster.
- The post is a joke, bot/spam, deleted/inaccessible, or otherwise unusable.

Use `unsure` when the text or linked Reddit permalink needs a second look.

## Suggested `case_type` Labels

- `found_account`: someone found the poster's Reddit account.
- `found_post`: someone found a specific Reddit post.
- `used_post`: someone used, shared, or showed the Reddit post elsewhere.
- `recognized_poster`: someone inferred the poster's identity from Reddit
  content.
- `confronted_about_post`: someone confronted the poster about Reddit content.
- `screenshot_or_forwarded`: a screenshot/link was sent or circulated.
- `suspected_only`: the poster suspects discovery but it is not confirmed.
- `unrelated`: search hit is not about Reddit identity discovery.
- `duplicate`: duplicate or crosspost of another candidate.
- `inaccessible`: not enough accessible content to code.
- `other`: relevant but not covered by the labels above.

## Updating The Sheet

The easiest workflow is to import `review_posts_for_annotation.csv` into one
shared Google Sheet and let annotators edit the coding columns in place. They
do not need to reorganize the file.

If the annotations are exported later, export as CSV with the same columns and
keep `post_id` intact. That is enough to join annotations back to `posts.csv`,
`comments.csv`, and `author_comments.csv`.
