# Set 3 subreddit catalog

Every named entry in the [Set 3 matched-post database](../README.md) is listed once, with its matched-post count, name-based category, decision, and reason. Counts describe the matched posts; they do not determine the decision.

## Name-based filtering

- **REMOVE:** Names clearly indicating roleplay or minors.
- **REVIEW:** Names suggesting memes, sexual/NSFW content, fiction or stories, or ambiguous teen/RP meanings. Gaming-related roleplay names are reviewed rather than automatically removed.
- **User profiles:** `u_` entries are listed separately and are not subject to subreddit rules.

Other subreddit names remain in the catalog as unflagged entries; gaming alone is not an exclusion. Matching is case-insensitive with token boundaries for short terms.

| Group | Entries | Matched posts |
| --- | ---: | ---: |
| Review | 5,541 | 131,339 |
| Remove | 387 | 65,795 |
| Profiles | 35,463 | 43,264 |
| Other subreddit names | 100,557 | 2,569,520 |
| No subreddit name | — | 8 |
| **Total** | **141,948** | **2,809,926** |

## Tables

### Review

| Entries | Page |
| ---: | --- |
| 1–2,500 | [review 1](classified/review/0001.md) |
| 2,501–5,000 | [review 2](classified/review/0002.md) |
| 5,001–5,541 | [review 3](classified/review/0003.md) |

### Remove

| Entries | Page |
| ---: | --- |
| 1–387 | [remove 1](classified/remove/0001.md) |

### Profiles

| Entries | Page |
| ---: | --- |
| 1–2,500 | [profiles 1](classified/profiles/0001.md) |
| 2,501–5,000 | [profiles 2](classified/profiles/0002.md) |
| 5,001–7,500 | [profiles 3](classified/profiles/0003.md) |
| 7,501–10,000 | [profiles 4](classified/profiles/0004.md) |
| 10,001–12,500 | [profiles 5](classified/profiles/0005.md) |
| 12,501–15,000 | [profiles 6](classified/profiles/0006.md) |
| 15,001–17,500 | [profiles 7](classified/profiles/0007.md) |
| 17,501–20,000 | [profiles 8](classified/profiles/0008.md) |
| 20,001–22,500 | [profiles 9](classified/profiles/0009.md) |
| 22,501–25,000 | [profiles 10](classified/profiles/0010.md) |
| 25,001–27,500 | [profiles 11](classified/profiles/0011.md) |
| 27,501–30,000 | [profiles 12](classified/profiles/0012.md) |
| 30,001–32,500 | [profiles 13](classified/profiles/0013.md) |
| 32,501–35,000 | [profiles 14](classified/profiles/0014.md) |
| 35,001–35,463 | [profiles 15](classified/profiles/0015.md) |

### Other subreddit names

| Entries | Page |
| ---: | --- |
| 1–2,500 | [other 1](classified/keep/0001.md) |
| 2,501–5,000 | [other 2](classified/keep/0002.md) |
| 5,001–7,500 | [other 3](classified/keep/0003.md) |
| 7,501–10,000 | [other 4](classified/keep/0004.md) |
| 10,001–12,500 | [other 5](classified/keep/0005.md) |
| 12,501–15,000 | [other 6](classified/keep/0006.md) |
| 15,001–17,500 | [other 7](classified/keep/0007.md) |
| 17,501–20,000 | [other 8](classified/keep/0008.md) |
| 20,001–22,500 | [other 9](classified/keep/0009.md) |
| 22,501–25,000 | [other 10](classified/keep/0010.md) |
| 25,001–27,500 | [other 11](classified/keep/0011.md) |
| 27,501–30,000 | [other 12](classified/keep/0012.md) |
| 30,001–32,500 | [other 13](classified/keep/0013.md) |
| 32,501–35,000 | [other 14](classified/keep/0014.md) |
| 35,001–37,500 | [other 15](classified/keep/0015.md) |
| 37,501–40,000 | [other 16](classified/keep/0016.md) |
| 40,001–42,500 | [other 17](classified/keep/0017.md) |
| 42,501–45,000 | [other 18](classified/keep/0018.md) |
| 45,001–47,500 | [other 19](classified/keep/0019.md) |
| 47,501–50,000 | [other 20](classified/keep/0020.md) |
| 50,001–52,500 | [other 21](classified/keep/0021.md) |
| 52,501–55,000 | [other 22](classified/keep/0022.md) |
| 55,001–57,500 | [other 23](classified/keep/0023.md) |
| 57,501–60,000 | [other 24](classified/keep/0024.md) |
| 60,001–62,500 | [other 25](classified/keep/0025.md) |
| 62,501–65,000 | [other 26](classified/keep/0026.md) |
| 65,001–67,500 | [other 27](classified/keep/0027.md) |
| 67,501–70,000 | [other 28](classified/keep/0028.md) |
| 70,001–72,500 | [other 29](classified/keep/0029.md) |
| 72,501–75,000 | [other 30](classified/keep/0030.md) |
| 75,001–77,500 | [other 31](classified/keep/0031.md) |
| 77,501–80,000 | [other 32](classified/keep/0032.md) |
| 80,001–82,500 | [other 33](classified/keep/0033.md) |
| 82,501–85,000 | [other 34](classified/keep/0034.md) |
| 85,001–87,500 | [other 35](classified/keep/0035.md) |
| 87,501–90,000 | [other 36](classified/keep/0036.md) |
| 90,001–92,500 | [other 37](classified/keep/0037.md) |
| 92,501–95,000 | [other 38](classified/keep/0038.md) |
| 95,001–97,500 | [other 39](classified/keep/0039.md) |
| 97,501–100,000 | [other 40](classified/keep/0040.md) |
| 100,001–100,557 | [other 41](classified/keep/0041.md) |

Regenerate from the Set 3 SQLite database with:

```bash
python3 scripts/classify_subreddits.py \
  arctic_keyword_matches.sqlite \
  --output data/set3_arctic_keyword_search/subreddits
```
