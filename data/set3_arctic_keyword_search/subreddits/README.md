# Set 3 subreddit counts

Every subreddit name stored in the [Set 3 matched-post database](../README.md) is listed in the linked Markdown tables below. Counts are unique matched posts in this dataset, not the total number of posts in each subreddit. Names are grouped case insensitively; the most common stored spelling is displayed. Descriptions are intentionally blank until a later metadata collection pass. No Reddit API requests were made.

| Measure | Count |
| --- | ---: |
| Matched posts in Set 3 | 2,809,926 |
| Posts with a subreddit name | 2,809,918 |
| Posts without a subreddit name | 8 |
| Distinct subreddit names | 141,948 |
| Matched posts in the top 100 subreddits | 878,673 |
| Subreddits with at least 100 matched posts | 3,668 |
| Matched posts in those subreddits | 2,051,748 |
| Subreddits with one matched post | 77,968 |

## All subreddits

Sorted by matched-post count, highest first. Each page has at most 5,000 rows. The description column is empty on every page.

| Ranks | Markdown table |
| ---: | --- |
| 1–5,000 | [Page 1](pages/0001.md) |
| 5,001–10,000 | [Page 2](pages/0002.md) |
| 10,001–15,000 | [Page 3](pages/0003.md) |
| 15,001–20,000 | [Page 4](pages/0004.md) |
| 20,001–25,000 | [Page 5](pages/0005.md) |
| 25,001–30,000 | [Page 6](pages/0006.md) |
| 30,001–35,000 | [Page 7](pages/0007.md) |
| 35,001–40,000 | [Page 8](pages/0008.md) |
| 40,001–45,000 | [Page 9](pages/0009.md) |
| 45,001–50,000 | [Page 10](pages/0010.md) |
| 50,001–55,000 | [Page 11](pages/0011.md) |
| 55,001–60,000 | [Page 12](pages/0012.md) |
| 60,001–65,000 | [Page 13](pages/0013.md) |
| 65,001–70,000 | [Page 14](pages/0014.md) |
| 70,001–75,000 | [Page 15](pages/0015.md) |
| 75,001–80,000 | [Page 16](pages/0016.md) |
| 80,001–85,000 | [Page 17](pages/0017.md) |
| 85,001–90,000 | [Page 18](pages/0018.md) |
| 90,001–95,000 | [Page 19](pages/0019.md) |
| 95,001–100,000 | [Page 20](pages/0020.md) |
| 100,001–105,000 | [Page 21](pages/0021.md) |
| 105,001–110,000 | [Page 22](pages/0022.md) |
| 110,001–115,000 | [Page 23](pages/0023.md) |
| 115,001–120,000 | [Page 24](pages/0024.md) |
| 120,001–125,000 | [Page 25](pages/0025.md) |
| 125,001–130,000 | [Page 26](pages/0026.md) |
| 130,001–135,000 | [Page 27](pages/0027.md) |
| 135,001–140,000 | [Page 28](pages/0028.md) |
| 140,001–141,948 | [Page 29](pages/0029.md) |

## Method

Counted rows in the database's `posts` table by `subreddit` after trimming surrounding whitespace and case folding. The database has one row per matched Reddit post. Blank or null names are counted separately above. The pages contain only aggregate counts and subreddit names; no post titles or bodies were read.

The source field also contains some legacy or profile-community labels; a link may no longer resolve to a public subreddit.

Regenerate from the downloaded Set 3 SQLite database with:

```bash
python3 scripts/build_subreddit_catalog.py \
  arctic_keyword_matches.sqlite \
  --output data/set3_arctic_keyword_search/subreddits
```
