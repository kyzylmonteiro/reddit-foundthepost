# Set 3 subreddit classification

This is a **name-based first pass** over the [full Set 3 subreddit count catalog](../README.md). Every named entry has a classification, decision, and reason. No post-count threshold was used. Post counts are shown only for context.

**Access and descriptions are unverified.** No Reddit API credentials were available, and the Set 3 post database has no subreddit descriptions. Banned, private, deleted, or otherwise inaccessible communities cannot be reliably identified here. KEEP therefore means only that no name-based exclusion rule matched; it is not final access verification. No Reddit API calls or post-content reads were made.

| Group | Entries | Matched posts |
| --- | ---: | ---: |
| Keep | 100,557 | 2,569,520 |
| Review | 5,541 | 131,339 |
| Remove | 387 | 65,795 |
| Profiles | 35,463 | 43,264 |
| No subreddit name | — | 8 |
| **Total** | **141,948** | **2,809,926** |

Among actual subreddit labels: 100,557 KEEP, 5,541 REVIEW, and 387 REMOVE. User profile entries beginning with `u_` are preserved separately.

## Tables

### Keep

| Entries | Page |
| ---: | --- |
| 1–2,500 | [keep 1](keep/0001.md) |
| 2,501–5,000 | [keep 2](keep/0002.md) |
| 5,001–7,500 | [keep 3](keep/0003.md) |
| 7,501–10,000 | [keep 4](keep/0004.md) |
| 10,001–12,500 | [keep 5](keep/0005.md) |
| 12,501–15,000 | [keep 6](keep/0006.md) |
| 15,001–17,500 | [keep 7](keep/0007.md) |
| 17,501–20,000 | [keep 8](keep/0008.md) |
| 20,001–22,500 | [keep 9](keep/0009.md) |
| 22,501–25,000 | [keep 10](keep/0010.md) |
| 25,001–27,500 | [keep 11](keep/0011.md) |
| 27,501–30,000 | [keep 12](keep/0012.md) |
| 30,001–32,500 | [keep 13](keep/0013.md) |
| 32,501–35,000 | [keep 14](keep/0014.md) |
| 35,001–37,500 | [keep 15](keep/0015.md) |
| 37,501–40,000 | [keep 16](keep/0016.md) |
| 40,001–42,500 | [keep 17](keep/0017.md) |
| 42,501–45,000 | [keep 18](keep/0018.md) |
| 45,001–47,500 | [keep 19](keep/0019.md) |
| 47,501–50,000 | [keep 20](keep/0020.md) |
| 50,001–52,500 | [keep 21](keep/0021.md) |
| 52,501–55,000 | [keep 22](keep/0022.md) |
| 55,001–57,500 | [keep 23](keep/0023.md) |
| 57,501–60,000 | [keep 24](keep/0024.md) |
| 60,001–62,500 | [keep 25](keep/0025.md) |
| 62,501–65,000 | [keep 26](keep/0026.md) |
| 65,001–67,500 | [keep 27](keep/0027.md) |
| 67,501–70,000 | [keep 28](keep/0028.md) |
| 70,001–72,500 | [keep 29](keep/0029.md) |
| 72,501–75,000 | [keep 30](keep/0030.md) |
| 75,001–77,500 | [keep 31](keep/0031.md) |
| 77,501–80,000 | [keep 32](keep/0032.md) |
| 80,001–82,500 | [keep 33](keep/0033.md) |
| 82,501–85,000 | [keep 34](keep/0034.md) |
| 85,001–87,500 | [keep 35](keep/0035.md) |
| 87,501–90,000 | [keep 36](keep/0036.md) |
| 90,001–92,500 | [keep 37](keep/0037.md) |
| 92,501–95,000 | [keep 38](keep/0038.md) |
| 95,001–97,500 | [keep 39](keep/0039.md) |
| 97,501–100,000 | [keep 40](keep/0040.md) |
| 100,001–100,557 | [keep 41](keep/0041.md) |

### Review

| Entries | Page |
| ---: | --- |
| 1–2,500 | [review 1](review/0001.md) |
| 2,501–5,000 | [review 2](review/0002.md) |
| 5,001–5,541 | [review 3](review/0003.md) |

### Remove

| Entries | Page |
| ---: | --- |
| 1–387 | [remove 1](remove/0001.md) |

### Profiles

| Entries | Page |
| ---: | --- |
| 1–2,500 | [profiles 1](profiles/0001.md) |
| 2,501–5,000 | [profiles 2](profiles/0002.md) |
| 5,001–7,500 | [profiles 3](profiles/0003.md) |
| 7,501–10,000 | [profiles 4](profiles/0004.md) |
| 10,001–12,500 | [profiles 5](profiles/0005.md) |
| 12,501–15,000 | [profiles 6](profiles/0006.md) |
| 15,001–17,500 | [profiles 7](profiles/0007.md) |
| 17,501–20,000 | [profiles 8](profiles/0008.md) |
| 20,001–22,500 | [profiles 9](profiles/0009.md) |
| 22,501–25,000 | [profiles 10](profiles/0010.md) |
| 25,001–27,500 | [profiles 11](profiles/0011.md) |
| 27,501–30,000 | [profiles 12](profiles/0012.md) |
| 30,001–32,500 | [profiles 13](profiles/0013.md) |
| 32,501–35,000 | [profiles 14](profiles/0014.md) |
| 35,001–35,463 | [profiles 15](profiles/0015.md) |

## Rules and limits

- REMOVE: explicit `roleplay`/`roleplaying` names or `RP` with roleplay context; names starting with `teenager`, an isolated `teen`/`teens` token, or an `under18` token. Gaming combinations go to REVIEW instead of automatic removal.
- REVIEW: names suggesting memes, sexual/NSFW content, fiction/stories, or ambiguous teen/RP meanings. These are flags, not removals.
- KEEP: no name-based exclusion; explicit gaming names remain eligible.
- Profiles: `u_` entries are not treated as subreddits.

Name rules use case-insensitive matching and token boundaries for short terms such as `RP` and `teen`. Some true cases will remain undetected until descriptions and access status can be checked. A 404 or 403 alone should not be labeled banned or private without confirming the response and authentication status.

Regenerate from the Set 3 SQLite database with:

```bash
python3 scripts/classify_subreddits.py \
  arctic_keyword_matches.sqlite \
  --output data/set3_arctic_keyword_search/subreddits/classified
```
