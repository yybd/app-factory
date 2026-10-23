*English · [עברית](4-aso-analyst.he.md)*

# 4 — turning `aso-keywords` into an ASO analyst

**Type:** a plan, with the live measurements that shaped it. **Status:** steps 1–4 built
and shipped in 0.10.0 on 2026-10-23; the live trial (step 5) waits on the owner.
**Placement decided** the same day: the hub gets `apple-track`; the skill stays where it is.

**Dated.** Researched 2026-10-23 from a hub session, then tested against Apple's live
endpoints the same day. Where this disagrees with the skill as it ships, the skill is right.

---

## The goal

A skill that works the way a professional ASO analyst does: it researches App Store search
terms **with data**, writes the listing so that people searching see the app, and improves
itself from what happened after the listing shipped.

**The hard requirement:** it works fully for a developer with **no Apple Ads account**,
using what is free to everyone. Apple Ads is an optional enrichment, detected and used when
present — not a tier the method depends on. The live test below turned that requirement
into a fact as well: even with an Ads account, Apple's popularity covers head terms only,
so the free path carries the long tail for everybody.

## 0. What existed, and why it was not enough

- `plugins/apple-track/skills/aso-keywords/` did **hygiene only** — lengths, repeats,
  commas — and said outright that volume, difficulty and rank were out of scope.
- **It did not load where the listings live.** A studio hub loads `shared-track`; this
  skill is in `apple-track`. Every `<slug>/store/apple/metadata/<locale>/` is in the hub.
- The hub already had a portfolio survey and a daily stats collector, and no search data.

**The placement decision** (put to the owner before anything moves): either move
`aso-keywords` to `shared-track`, or give the hub `apple-track`. The criterion is where the
skill needs to **load** (`CLAUDE.md`). Note that `app-store-metadata`, which owns the files
this skill's output lands in, is in `apple-track` too — so the second option fixes both.

## 1. Data sources — measured, not assumed

| need | source | cost | measured 2026-10-23 |
|---|---|---|---|
| Term ideas per storefront | App Store autocomplete, `MZSearchHints.woa/wa/hints?clientApplication=Software` with `X-Apple-Store-Front` (US `143441-1,29`, IL `143491-2,29`). ≤10 terms, plist, no score — **the order is the signal** | free, unofficial | works, Hebrew included. **iOS store only**: `clientApplication=MacAppStore` returns non-app terms, and the Mac web store's suggestion API needs a token. For a Mac app the iOS autocomplete is a labelled proxy |
| Real search order (rank) | `apps.apple.com/{cc}/{iphone,mac}/search?term=…` → `<script id="serialized-server-data">`, the first shelf's lockups in order: `adamId`, `title`, `subtitle`, `rating`, `ratingCount` | free, fragile | works for **iPhone and Mac**, US and IL. 12 items, one of them can be an editorial card — skip it. The rating counts mean difficulty needs no second call |
| Rank beyond 12 | iTunes Search API, `entity=software` / `macSoftware`, `limit=200` | free, ~20 req/min | order close to the store's, not identical — recorded as an approximation |
| Popularity, head terms | **Apple Ads Platform API v1**, `POST /v1/insights/apps/search-term-popularity/query` | free with an Ads account | **works with no campaign**: US PRODUCTIVITY_UTILITIES, week 2026-10-11..17 → 500 terms, `searchPopularity1to100` 55–90 (not stuck at 5, as reported elsewhere); IL → 209 terms, 51 of them Hebrew (גוגל 78, רכבת ישראל 74, וויז 73). **Head terms only — the floor is ≈54.** `searchTerm CONTAINS` for niche terms (markdown, clock, תזכורת, סידור) returns nothing. Without a genre filter it returns every genre. Fifteen genres accepted |
| Popularity of chosen phrases | `POST /v1/suggestions/phrases/query`, `queryType: SEARCH` | — | **returns empty**, even for chatgpt and vpn; rejects `countriesOrRegions`. Unusable for now |
| Keyword suggestions for an app | `POST /v1/suggestions/keywords/query`, phrases `SUGGESTION` | — | "App not found or access denied" for the owner's app: the Ads account is not linked to the developer account's apps. Linking is the owner's to investigate; the skill does not depend on it |
| Search feedback per app | App Store Connect **Analytics Reports API** — "App Store Discovery and Engagement" (impressions, page views by source type = App Store search, per territory). `POST /v1/analyticsReportRequests` `ONGOING`, first request by an Admin key. **No per-term data anywhere in ASC** | free | not yet requested — data accumulates only from the request onward |
| Search feedback per term | Apple Ads search-terms report | needs a running campaign | optional |
| Paid, if the free stack falls short | Astro ($9/mo, Apple-sourced popularity + rank history, local MCP), Sonar ($29/mo), Appfigures (IL popularity confirmed) | paid | not needed for steps 1–4 |

Not worth it at this budget: AppTweak (API ≈$166 a month), Sensor Tower / data.ai, KeywordTool.io,
MobileAction's API.

**What follows:** popularity is a **proxy from autocomplete** for every term, and Apple's
1–100 figure **replaces** the proxy where Apple has one. The source of every number is
stored next to it. A term with neither is said to have neither.

## 2. Facts the method encodes

Apple-confirmed unless marked.

- Indexed: app name, subtitle, keywords field, primary **and secondary** category,
  developer name. Ranking = text relevance + user behaviour (downloads, ratings).
- The description is not a ranking lever on iOS; promotional text **does not** affect
  ranking (Apple, explicit).
- Keywords field: comma-separated; no repeats of name/subtitle/category/developer words;
  plural = duplicate (practitioners: singular and plural SERPs overlap only ~44%, so test
  both where it matters); no "app"/"game"; no competitor or trademark names (Guideline
  2.3.7). The limit is **100 characters**, Hebrew included: Apple's reference says bytes,
  but App Store Connect accepted and App Review approved a Hebrew field of 84 characters
  (155 bytes) — verified 2026-10-23, after this plan was first written.
- Word combinations form across name + subtitle + keywords **within one locale**, never
  across locales (practitioner consensus).
- Cross-localization (practitioners): **US** indexes en-US + ar, zh-Hans, zh-Hant, fr, ko,
  pt-BR, ru, es-MX, vi. **Israel** = he + en-GB. **UK** = en-GB (+ en-AU). **Germany** =
  de + en-GB. So Israel has two keyword fields, and en-GB is shared with the UK and Germany.
- Custom Product Pages can carry keywords and appear in organic results for them.
- Screenshot-caption indexing is **disputed**; captions carry a core term anyway, because
  it helps conversion at no risk.
- After a metadata change, ranks settle in about **4 weeks** (practitioners). Name,
  subtitle and keywords change only with a version.

## 3. The method

1. **Brief** — the app's profile, current metadata per locale, prices. Jobs-to-be-done in
   the user's words, per language.
2. **Universe** — 150–400 candidates per storefront: seeds from the profile → autocomplete
   expansion (each seed, then prefixes) → competitor mining (titles and subtitles of the
   top SERP apps) → Apple Ads head terms when present → 2–3 word phrases. Hebrew is
   researched in Hebrew, not translated.
3. **Score** each candidate, saved so later runs compare:
   - **Relevance 1–10**, judged by the agent against the profile, with a one-line reason.
     **Below 6 is discarded** — a gate, not a weight.
   - **Popularity 1–10** — Apple's figure when Apple has one, otherwise the autocomplete
     proxy (shorter prefix and higher position ⇒ more popular).
   - **Difficulty 1–10** — from the real SERP: the top results' rating counts, how many
     carry the exact term in their name.
   - **Chance** — our ratings and current rank against the top results.
   - Priority = relevance × popularity / difficulty, banded **stretch** (1–2),
     **core** (15–25), **long tail** (10–15). A small app leads with relevant long tail.
4. **Allocate** — a deterministic script per storefront and its indexed locales: what the
   name and subtitle already cover, the keyword field packed with the remaining distinct
   words up to the limit, no duplicates across the storefront's locales, combinations
   checked.
5. **Write the visible copy** — name and subtitle read well (they are conversion too);
   promotional text, first sentence, captions. Then `copy-edit`. The files are handed to
   the skills that own them; the owner approves every field.
6. **Record** the change as an experiment before the version ships.

## 4. The feedback loop

**Per app, in the hub** (`<slug>/aso/`): `keywords.json` (the scored universe and the
owner's rejections), `experiments.jsonl` (one line per shipped change, review due +28
days), `ranks/YYYY-MM-DD.json` (rank snapshots, plus search impressions when the
Analytics report exists). A weekly snapshot runs as a source in the hub's stats collector.
The review gives each target term a verdict: keep · replace (not in the top 100 after one
cycle) · conversion problem (ranks, does not convert — screenshots, not keywords). One
change per field per cycle, so a result can be attributed.

**Per method, in the skill:** `LESSONS.md` (dated: expected, happened) and
`calibration.json` (weights and proxy thresholds, adjusted from reviews across the
portfolio). An outcome about one app is data; an outcome that would change how every app
is scored is a lesson.

## 5. Build order

0. ~~Verify live~~ — done 2026-10-23 (above), bytes-vs-characters included; except the
   Analytics request.
1. Placement decision + autocomplete, SERP, scoring, allocation scripts — a full research
   → proposal run with no paid data and no Ads account.
2. SKILL.md rewritten to the method; the guide updated; LESSONS.md, calibration.json.
3. Apple Ads popularity (optional enrichment) and the Analytics client.
4. Rank snapshot, review, the hub stats source, eval cases.
5. CI, version bump, deploy, a new session in the hub → **live trial** on one app.

**Scripts are stdlib only.** Signing (ES256, for Apple Ads and App Store Connect) goes
through the `openssl` binary, as the live probe did — no pip dependency.
