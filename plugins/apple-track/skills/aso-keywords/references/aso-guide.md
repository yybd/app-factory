# App Store search — what is indexed, what ranks, and where the data comes from

last-verified: 2026-10-23
source: developer.apple.com/app-store/search · App Store Connect Help (keywords, localization) ·
Apple Ads Platform API v1 (tested live 2026-10-23) · practitioner studies where marked

Each claim is marked **[Apple]** when Apple states it, **[practice]** when it is the
consensus of practitioners, **[measured]** when this skill measured it, and **[disputed]**
when the evidence disagrees.

## What is indexed

- **[Apple]** App name (30 characters), subtitle (30), keywords field (100 — see the ⚠),
  primary **and secondary** category, developer name. In-app purchase names can appear
  in search too.
- **[Apple]** Ranking uses text relevance **and user behaviour** — downloads, ratings.
  A term the app ranks for and does not satisfy hurts: it is tapped and not installed.
- **[Apple]** The promotional text **does not** affect search. The description is not a
  ranking lever on iOS ("don't add unnecessary keywords to your description").
- **[practice]** Weight: name > subtitle > keywords field.
- **[disputed]** Screenshot captions: Appfigures reports indexing; a 64-phrase test by
  ConsultMyApp found none. Rule: put a core term in a caption anyway — it helps
  conversion at no cost.
- **[Apple, WWDC25]** App Store Tags are generated from the metadata and can only be
  removed; their ranking effect is not stated.
- **[Apple]** Custom Product Pages can be assigned keywords and then appear in organic
  results for them.

## The keywords field

- **[Apple]** Comma-separated. A space after a comma is a wasted unit.
- **[Apple]** Don't repeat words the name, subtitle, category or developer name already
  have; don't use "app" or the category name; no competitor or trademarked names
  (Guideline 2.3.7 — a rejection risk).
- **[practice]** Singular and plural count as one word for matching — don't spend units on
  both. (AppTweak 2025 found singular/plural results overlap only ~44%; when a term
  matters, test the other form in a later cycle rather than packing both.)
- **[practice]** Single words beat phrases in the field: the store combines words across
  name + subtitle + keywords **within one locale**, never across locales.
- ⚠ **[Apple]** The reference says **100 bytes**. UTF-8 Hebrew is 2 bytes a letter, so a
  Hebrew field may hold only 50 letters. **Unverified** whether App Store Connect counts
  bytes or characters; the scripts count bytes until LESSONS.md records the answer.
- **[practice]** Name, subtitle and keywords change only with a new version. Ranks settle
  about **four weeks** after a change — review then, not before.

## Localization multiplies the fields

**[practice]** Each storefront indexes several listing locales (Apple's localization
table lists the display languages per storefront; practitioners report all of them are
indexed):

| storefront | indexed locales |
|---|---|
| United States | en-US, es-MX, zh-Hans, zh-Hant, fr-FR, ko, pt-BR, ru, vi, ar-SA |
| Israel | he, en-GB |
| United Kingdom | en-GB, en-AU |
| Germany | de-DE, en-GB |
| France | fr-FR, en-GB |
| Canada | en-CA, fr-CA |
| Australia | en-AU, en-GB |

So the US has ten keyword fields, Israel two — and en-GB is shared by Israel, the UK and
Germany, which constrains it: what is packed there serves all three. A phrase still needs
all its words in one of them.

## The data sources

| source | what it gives | cost | measured 2026-10-23 |
|---|---|---|---|
| App Store autocomplete (`MZSearchHints`, iOS) | ≤10 suggestions in order — **the order is the signal** | free | works in every storefront tried, Hebrew included. The Mac store's autocomplete needs a token; a Mac app uses iOS's, labelled |
| The store's search page (`apps.apple.com/{cc}/{iphone,mac}/search`) | the top ~12 in order, with subtitle and rating count | free, not an API | works for iPhone and Mac. Counts are abbreviated (`2.8K`); an editorial card can sit among the apps |
| iTunes Search API | up to 200 results, order close to the store's | free, ~20 a minute | used for our rank past 12, marked as an approximation |
| iTunes lookup | rating count and average per storefront; id from bundle id | free | works |
| Apple Ads Platform API v1 — search-term popularity insights | real `searchPopularity1to100`, weekly, per country and genre (or all genres) | free with an Ads account, **no campaign needed** | US: 500 terms in one genre, 55–90; IL: 1,070 terms over all genres, 209 in one, Hebrew included. **Head terms only (floor ≈54)**; niche terms absent |
| Apple Ads — phrase suggestions (`queryType: SEARCH`) | popularity for chosen phrases | — | returned empty, even for head terms; rejects a country filter. Not used |
| Apple Ads — keyword suggestions for an app | Apple's suggested terms | — | "App not found or access denied" unless the Ads account is linked to the developer account's apps. Not relied on |
| App Store Connect Analytics Reports — Discovery and Engagement | impressions and page views by source type (App Store search), per territory | free; first request by an Admin key | read works with the studio's sales-reports key; **no per-term data exists in ASC** |
| Apple Ads search-terms report | impressions, taps, installs per real search term | needs a running campaign | optional |

**Paid, if the free stack is not enough** (not needed for the method): Astro ($9 a month;
Apple-sourced popularity and daily rank history, local MCP), Sonar ($29 a month, or
credit packs), Appfigures (Israel popularity confirmed; API 1,000 requests a day). Not
worth it at a small studio's budget: AppTweak's API, Sensor Tower, data.ai,
KeywordTool.io, MobileAction's API.

## The study file — `<aso>/keywords.json`

```json
{
  "schema": 1,
  "app": {"bundle_id": "…", "adam_id": "…", "platform": "iphone|mac", "ratings": {"us": [count, avg]}},
  "rejected": {"term": "the owner's reason"},
  "storefronts": {
    "us": {
      "apple_read": "Apple Ads week 2026-10-11",        // only when apple_ads.py ran
      "candidates": {
        "markdown editor": {
          "sources": ["autocomplete", "competitor", "apple-ads"],
          "relevance": 8, "reason": "what the app is",  // written by the agent
          "trademark": false,
          "hints": {"obs": [["mark", 2]]},              // hints.py
          "apple": {"pop": 62, "week": "…"},            // apple_ads.py
          "serp": {"top": [[id, title, ratings]], "median_ratings": 0, "title_matches": 0,
                   "our_rank": 41, "rank_source": "itunes-search"},
          "popularity": 6.6, "popularity_source": "autocomplete-proxy",
          "difficulty": 4.3, "chance": 2.1, "priority": 12.3, "band": "core",
          "review": {"verdict": "keep", "date": "…", "rank": [41, 9]}  // review.py --apply
        }
      }
    }
  }
}
```

Beside it: `experiments.jsonl` (one line per recorded change, and one per review) and
`ranks/YYYY-MM-DD.json` (snapshots).
