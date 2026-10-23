---
name: aso-keywords
description: >-
  App Store Optimization for APPLE search, done the way an ASO analyst does it: research
  real search terms per storefront with data (App Store autocomplete, the store's own
  results, rating counts; Apple Ads popularity when a key is present), score them for
  relevance, popularity and difficulty, pack the name, subtitle and 100-character keywords
  field per locale, record the change as an experiment, and review the ranks four weeks
  later. Use when the user wants better App Store search ranking or discoverability,
  keyword research, to audit or rewrite the keywords field, to choose between name,
  subtitle and keywords, to track ranks, or to review a past keyword change ("מילות
  מפתח", "דירוג בחיפוש", "ASO", "למה לא מוצאים את האפליקציה"). Works fully with no Apple
  Ads account. It owns the keyword strategy and the 100-character field; app-store-metadata
  owns the files. Not for Google Play, which has no keywords field — play-store-metadata
  writes Play's visible copy.
---

# ASO Keywords — the analyst

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

Most App Store installs start with a search. The store indexes the **name**, the
**subtitle** and the hidden **keywords field** of each locale (plus the category and the
developer name) and ranks on text relevance and on how users behave. This skill does what
a professional does with that: finds the terms people actually type, judges which of
them fit the app, measures how hard each is to win, packs the fields so no byte is
wasted, and — four weeks after the version ships — checks what happened and learns.

**It never invents a number.** Every popularity, difficulty and rank in a study carries
its source next to it, and a term with no signal is said to have none.

## Prerequisites

- **Tools:** Python 3 (stdlib only) and the `openssl` binary (macOS has it) — the scripts
  under `scripts/` need nothing installed.
- **Network:** Apple's public endpoints — the App Store autocomplete, the store's own
  search page, the iTunes Search and lookup APIs. No account.
- **Credentials:** **none required.** Two optional enrichments, each detected:
  - an **Apple Ads API key** at `$KEYS_ROOT/appleads/api_key.json` (client id, team id,
    key id, `private_key` file beside it) → Apple's own popularity for head terms;
  - an **App Store Connect key** that can read analytics (the apple-track resolver, or
    `--key-json`) → the app's search impressions and page views, for reviews.
- **Hub (`$APP_HUB`):** optional. With one, a study lives in `$APP_HUB/<slug>/aso/` and
  the listing in `$APP_HUB/<slug>/store/apple/metadata/`; without one, in the app repo's
  `aso/` and `fastlane/metadata/`.
- **Other tracks:** `app-profile` and `app-identity` (shared-track) for what the app is;
  `store-metadata-writer` and `copy-edit` (shared-track) for the visible copy;
  `play-store-metadata` (android-track) for Google Play.

## What the numbers are, and where each comes from

| number | with no Apple Ads account | with an Apple Ads key |
|---|---|---|
| **relevance** 1–10 | **you judge it**, against the profile, one-line reason each | same |
| **popularity** 1–10 | the **autocomplete proxy**: how short a prefix makes the store suggest the term, and how high (`hints.py measure`) | Apple's `searchPopularity1to100` ÷ 10 for the **head terms Apple lists** (floor ≈54, measured 2026-10-23); every other term keeps the proxy, **capped under that floor** — Apple's list is the proof it is smaller |
| **difficulty** 1–10 | the store's own results: median rating count of the top ten, and how many carry the term in their name (`serp.py`) | same |
| **chance** 1–10 | our rating count against theirs, and our current rank | same |
| **rank** | the store's search page (top ~12), then the iTunes Search API to 200 (marked `itunes-search` — close, not identical) | same |
| **feedback** | rank snapshots per term; App Store **search** impressions and page views per app from the Analytics Reports API, with a key that can read it | same, and an Ads search-terms report if a campaign ever runs |

**Mac apps:** the Mac App Store's autocomplete is not reachable without a token, so a Mac
app's popularity proxy is **iOS autocomplete** — what iPhone users type — and is labelled
so. Its ranks and difficulty come from the Mac store's own results (`--platform mac`).

**Apple Ads is an enrichment, not a tier.** Even with a key it covers head terms only;
a small app's long tail is scored by the proxy for everyone. When it was used, say so in
the report: *"popularity: Apple Ads for 6 terms (week of …), autocomplete for the rest."*

## Workflow

`S` below is the study file, `<aso>/keywords.json`; `D` is
`${CLAUDE_PLUGIN_ROOT}/skills/aso-keywords/scripts`; `M` is the metadata root.

### 0. Audit what is there (two minutes, always)

```bash
python3 $D/allocate.py --check --metadata M --cc us
```

Lengths (the keyword field in **characters** — see below), spaces around commas, words
repeated across name/subtitle/keywords, singular+plural pairs, stop and category words.
The older `analyze_keywords.py <repo>` still runs the same audit over a whole fastlane
tree.

### 1. Brief

Read the profile (`$APP_HUB/<slug>/profile.md`, or the repo `README.md`), the current
metadata per locale and the category. Write down the **jobs** the app does in the
words a user would type, **per language** — Hebrew in Hebrew, not translated. No profile
→ `app-profile` first. Decide the storefronts (the app's main markets) and the platform
(`iphone` or `mac`).

### 2. Universe — 150–400 candidates per storefront

```bash
python3 $D/hints.py S expand --cc us --seed "markdown editor" --seed "writing app" --alphabet
python3 $D/serp.py --cc us --platform mac --term "markdown editor"      # read competitors
python3 $D/apple_ads.py popularity S --cc us --add-matching             # only if a key exists
```

Seeds come from the brief. `--alphabet` adds "seed a … seed z" (א … ת for Hebrew) — the
long tail. Read the top results' **titles and subtitles** for words you missed, and add
them as candidates by hand (`"sources": ["competitor"]`). Suggestions that are another
app's name are flagged `looks_like_app_name`.

### 3. Judge relevance — the gate

For every candidate write `relevance` (1–10) and a one-line `reason` into the study.
**Below 6 is discarded** however popular. Mark competitor brands and trademarks
`"trademark": true` (Guideline 2.3.7). The owner's "never X" goes into `rejected` with
the reason. This is the step a script cannot do, and the one that matters most: a
popular term the app does not satisfy ranks, gets tapped, and is not downloaded — which
teaches the store the app is a poor answer.

### 4. Measure and score

```bash
python3 $D/hints.py S measure --cc us           # popularity proxy for the relevant terms
python3 $D/serp.py S --cc us --platform mac --bundle-id com.example.app
python3 $D/score.py S --cc us
```

Priority = relevance × popularity ÷ difficulty, banded **stretch** (1–2 popular terms
our chance is low on), **core** (≈20), **long tail** (≈15, relevant and rare — where a
small app wins first). The weights are in `calibration.json`.

### 5. Allocate the fields

```bash
python3 $D/allocate.py S --cc il --metadata M --set he:subtitle="…" --exclude "<developer>"
```

You write the **name and subtitle** — they are read by people and are conversion too:
brand + the strongest core term in the name (readable, not stuffed), the next core terms
as a benefit in the subtitle. The script packs each keyword field the storefront indexes
with the words the scored terms still need, then reports what fitted, what did not, and
which strong terms no name/subtitle carries. Iterate with `--set` until the subtitle
reads well and the important terms are covered.

Rules it enforces, and you keep when writing:
- a word the locale's name or subtitle has is never repeated in its keyword field;
- a **phrase** ranks only when **all** its words are in **one locale** — combinations do
  not cross locales;
- one form per stem (note/notes, תזכורת/תזכורות);
- no stop words, "app", category or developer words — Apple indexes those already;
- **each storefront indexes several locales** (US: en-US + es-MX, zh-Hans … ; Israel: he +
  en-GB; UK and Germany share en-GB). A locale the listing lacks is another free keyword
  field — the script lists them.

**The limit is 100 characters, in Hebrew too.** Apple's reference says "bytes", but App
Store Connect counts characters: a Hebrew field of 84 characters (155 bytes) was accepted,
approved and is live (verified 2026-10-23, LESSONS.md). A Hebrew field packed to 50
letters wastes half of it.

### 6. Write the visible copy, hand it over

Promotional text (does not affect ranking; changeable any time), the description's first
sentence, screenshot captions carrying a core term. Run `copy-edit`. Then hand the files
to `store-metadata-writer` / `app-store-metadata` — **this skill writes no metadata
file**, and the owner approves every field before it is written.

### 7. Record the experiment — before the version ships

```bash
python3 $D/track.py <aso> --force                       # the baseline
python3 $D/review.py record <aso> --cc il --locale he --field keywords --version 1.3 \
        --before "<old>" --after "<new>" --targets "a,b,c" --hypothesis "…"
```

**One change per field per cycle**, or no result can be attributed.

### 8. Track and review

`track.py <aso>` takes a weekly rank snapshot (the hub's stats collector can run it).
`review.py due <aso>` lists experiments past their 28 days; `review.py review <aso>
--apply` gives each target term a verdict — **keep** (top 10, or up into the top 30),
**watch**, **replace** (not in the top 100 after a cycle), or a **conversion** note
(seen more in search, page not visited more: screenshots or a custom product page, not
keywords) — and writes them into the study, where the next `score.py` reads them.

**Feedback has two levels.** An outcome about one app is **data** — it stays in that
app's study and experiments. An outcome that would change how every app is scored (the
proxy over-rates two-letter Hebrew prefixes; a band size is wrong) is a **lesson** —
a dated line in [LESSONS.md](LESSONS.md), and if it moves a number, a change to
`calibration.json` with the same date. The owner's corrections ("that word is wrong for
us") go into the app's `rejected`; if it generalises, a LESSONS line too.

### Analytics: one owner step

The search-impressions half of the feedback exists only after the app's analytics report
is requested, and accumulates from that day on:

```bash
python3 $D/asc_analytics.py status  --app-id <id> [--key-json …]
python3 $D/asc_analytics.py request --app-id <id> [--key-json …]   # ask the owner first
```

`request` is a write to the owner's App Store Connect account (the first one needs an
Admin key). Ask before running it; until then the reviews run on ranks alone and say so.

## Boundaries

- **It owns the keyword strategy and the 100-character field, not the files.**
  `app-store-metadata` writes what this skill decides; `store-metadata-writer` writes the
  listing copy from the profile.
- **It does not rename the app.** The name is `app-identity`'s; this skill optimises
  within it and says when the name is what holds ranking back.
- **Google Play is out of scope** and not by omission: Play has no keywords field, so its
  ranking reads the visible copy, which `play-store-metadata` owns.
- **It does not buy data.** If the free stack falls short for a market, say which paid
  source would fill it (the guide lists them) and let the owner decide.
- **It changes nothing on an account without asking** — the one write it can make is the
  analytics request, and that waits for the owner.

## Reference files

- [references/aso-guide.md](references/aso-guide.md) — how App Store search indexes and
  ranks, which rules are Apple's and which are practitioners', cross-localization, and
  the data sources with what each was measured to give.
- [LESSONS.md](LESSONS.md) — what running the method taught; dated.
- [calibration.json](calibration.json) — every weight and threshold the scripts use.
- [scripts/hints.py](scripts/hints.py) · [scripts/serp.py](scripts/serp.py) ·
  [scripts/apple_ads.py](scripts/apple_ads.py) · [scripts/score.py](scripts/score.py) ·
  [scripts/allocate.py](scripts/allocate.py) · [scripts/track.py](scripts/track.py) ·
  [scripts/review.py](scripts/review.py) · [scripts/asc_analytics.py](scripts/asc_analytics.py)
  — each prints its usage with `--help`.
- [scripts/analyze_keywords.py](scripts/analyze_keywords.py) — the original hygiene audit
  over a whole fastlane tree.
