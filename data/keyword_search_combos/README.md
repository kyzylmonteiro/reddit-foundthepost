# Keyword Search Combos

Search-phrase sets for identity-discovery collection, organized by threat model.
These are search-design inputs, not collected Reddit data.

## TL;DR — What Each CSV Is And How It Is Used

| CSV | Rows | Voice | Used for |
| --- | ---: | --- | --- |
| `general.csv` | 69 | 1st person | set2 `first_person` run |
| `institutional_threats.csv` | 1,248 | 1st person | set2 `first_person` run |
| `organizational_threats.csv` | 2,112 | 1st person | set2 `first_person` run |
| `ambiguous_others.csv` | 233 | 1st person | set2 `first_person` run |
| `interpersonal.csv` | 4,224 | 1st person | set2 `first_person` run |
| `all_first_person_searches.csv` | 7,886 | 1st person | reference only — flat list, no provenance columns |
| `third_person_observer.csv` | 21,564 | 3rd person | set2 `third_person_observer` run |
| `third_person_finder.csv` | 3,894 | finder | set2 `third_person_finder` run |

The five category CSVs drive the first-person run rather than
`all_first_person_searches.csv`, because only they carry the
`Category` / `Target Term` / `Template` columns that flow into the output tables.
Same 7,886 phrases either way.

**Total searched: 33,344 unique phrases across three sets. No phrase appears in
more than one set.**

## Where They Came From

- The 6 first-person CSVs are sheets of
  `keyword_search_combos_first_person_by_threat_model.xlsx`, converted by
  `scripts/xlsx_to_csv.py`. See `conversion_manifest.json`.
- The 2 third-person CSVs are generated from those sheets by
  `scripts/build_third_person_queries.py`. See
  `third_person_generation_manifest.json`.

```bash
python3 scripts/xlsx_to_csv.py \
  data/keyword_search_combos/keyword_search_combos_first_person_by_threat_model.xlsx \
  --out-dir data/keyword_search_combos \
  --manifest data/keyword_search_combos/conversion_manifest.json

python3 scripts/build_third_person_queries.py \
  --keyword-dir data/keyword_search_combos \
  --manifest data/keyword_search_combos/third_person_generation_manifest.json
```

## The Three Voices

**First person** — the person who got found, telling it.
`My boss found my post`, `The court found out I posted`

**Third person observer** — the same event narrated about somebody else. Built by
swapping first-person pronouns for `her` / `his` / `their`. The 698 workbook
phrases with no first-person marker (`Found the post`, `Is a lurker`) are skipped
because the swap would change nothing.
`Her boss found her post`, `Their coworker found out about their posts`

**Third person finder** — the discovering party telling it instead. Built from
each target term's possessive form, learned from the workbook's own
`found my [obj]` rows. Institutional targets are excluded because "I found the
court's account" is not a thing anybody posts.
`I found my boss's Reddit`, `I found out my sister posts on Reddit`

## Columns

`Search Phrase` is in every file. Category sheets add construction provenance:

- `Category`: threat-model grouping (`Work-based`, `Family`, …).
- `Target Term`: the discovering party named (`boss`, `partner`, `court`). Blank
  in `ambiguous_others.csv` where no one is named.
- `Template`: the generating pattern. `[obj]` = Reddit object (post, account,
  comment, thread), `[det]` = determiner, `[where]` = location. Templates marked
  `(suggested)` are one-offs, not generated combinations.
- `Pronoun` (observer only): `her`, `his`, or `their`.
- `Source Phrase` (observer only): the first-person phrase it was derived from.
- `Object` (finder only): the Reddit object slot filled.

`institutional_threats.csv` and `ambiguous_others.csv` have no `Category` column;
their sheet name is the category.

## Structure

| Sheet | Rows | Categories | Target terms |
| --- | ---: | ---: | ---: |
| General | 69 | 1 | — |
| Institutional Threats | 1,248 | — | 13 |
| Organizational Threats | 2,112 | 2 | 22 |
| Ambiguous Others | 233 | — | 4 |
| Interpersonal | 4,224 | 4 | 44 |
| **All first person** | **7,886** | | |

41 distinct templates. Most productive: `came across [det] [obj]` and
`stumbled across [det] [obj]` (1,230 each), then `saw my [obj]`,
`exposed my [obj]`, `knows about my [obj]`, `found my [obj]`,
`found out about my [obj]`.

## Verified

- `all_first_person_searches.csv` is exactly the multiset union of the five
  category sheets.
- All 7,886 first-person phrases are unique; no blanks.
- Zero overlap between first person, observer, and finder sets.
