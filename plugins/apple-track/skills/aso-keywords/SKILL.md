---
name: aso-keywords
description: >-
  App Store Optimization (ASO) for APPLE discoverability — research and optimize the
  search-indexed fields of an App Store listing: the app name, subtitle, and the
  100-character keywords field, per locale. Use this whenever the user wants to improve
  their app's search ranking / discoverability, choose or refine keywords, audit the
  keywords field, decide what to put in the name vs subtitle vs keywords, or expand to
  more locales for more keyword coverage ("מילות מפתח", "דירוג בחיפוש"). It audits the
  existing fields for ASO mistakes and suggests improvements. It optimizes the CONTENT
  for ranking; the app-store-metadata skill owns the files and validates limits. APPLE
  ONLY: Google Play has no keywords field, so Play discoverability is written into the
  visible title / short description / full description and belongs to
  play-store-metadata — do not use this skill for a Play listing. It owns the keyword
  strategy and the 100-character field; app-store-metadata owns the files it lands in.
---

# ASO Keywords & Discoverability

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

Most App Store traffic is search. The App Store indexes three fields together —
**app name**, **subtitle**, and the **100-character keywords field** — and ranks
on them. This skill helps the user use those fields well: no waste, no
redundancy, the right terms, multiplied across locales.

It's the strategy/optimization layer; `app-store-metadata` owns the actual files
and validates Apple's character limits. This skill reads those fields, audits
them for ASO, and proposes better content; metadata applies the changes.

> **In the studio flow**, the name and subtitle come from the app's
> profile (`$APP_HUB/<slug>/profile.md`) via `store-metadata-writer`,
> and the keyword *intent* is the app's own vocabulary already in the profile —
> lift and optimize from there rather than inventing a separate brand voice. This
> skill owns the **keyword strategy and the 100-char field**; `app-store-metadata`
> owns the files. Standalone (no profile), the app's `README.md` (written by the
> `app-identity` skill) holds the chosen **name** and **subtitle** to optimize and the
> feature vocabulary to mine for terms — start there, then gather any missing terms
> with the user as below.

> **Google Play is out of scope, and not because nobody got to it.** Apple hides a
> 100-character keywords field, and the whole craft here is fitting terms into it
> without wasting them on what the name and subtitle already index. **Play has no
> such field.** Its ranking reads the visible title, short description and full
> description — so on Play the keywords *are* the customer-facing copy, which
> `play-store-metadata` already owns, writes and validates. Optimising it here too
> would put two skills in charge of one paragraph. For Play, go there.

## Prerequisites

- **Tools:** none beyond Claude Code; `scripts/analyze_keywords.py` is stdlib Python 3
  and reads the `fastlane/metadata/<locale>/` files (fastlane itself is not run).
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — studio flow lifts name, subtitle and vocabulary
  from `$APP_HUB/<slug>/profile.md`; standalone uses the repo's `README.md`.
- **Other tracks:** `store-metadata-writer` and `app-identity` (shared-track) for the
  source copy; `play-store-metadata` (android-track) owns the Google Play side.

## What this can and can't do
- ✅ **On-page ASO hygiene & structure** (fully here): field length usage,
  wasted characters, redundancy across name/subtitle/keywords, duplicate/plural
  waste, per-locale coverage, and concrete keyword suggestions from the app's
  purpose.
- ❌ **Search volume / difficulty / competitor rankings**: that needs paid data
  (AppTweak, Sensor Tower, etc.) — out of scope. Say so honestly; don't invent
  volume numbers. You can use web search for autocomplete-style ideas, but treat
  them as hypotheses.

## Workflow

### 1. Audit the current fields
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/aso-keywords/scripts/analyze_keywords.py <project-root>
```
Per app + locale it reports name/subtitle/keywords length usage and flags the
classic mistakes: **words repeated** across name/subtitle/keywords (redundant —
they're indexed together, so repeating wastes space), **spaces after commas**
(wasted chars), **duplicate/again-pluralized** terms, an **under-used** or
**over-limit** keyword field, and an **empty** keyword field.

### 2. Understand the app and its users
Good keywords come from how users would search for *this* app, not generic terms.
Ask (or infer): what the app does, the category, the words a non-technical user
would type, and any strong differentiators. *(In the studio flow these are
already in the profile — lift them instead of asking cold.)* Avoid the app's brand name in
keywords (it already ranks for that) and avoid competitor trademarks (rejection
risk).

### 3. Optimize, following the rules in the guide
Apply [references/aso-guide.md](references/aso-guide.md):
- Put the **strongest term** in the name/subtitle (highest weight).
- Fill the keywords field with **distinct** terms (no repeats of name/subtitle),
  comma-separated, **no spaces**, singular OR plural (not both — the store
  matches stems), no plurals/duplicates, fit 100 chars.
- **Localize per store** — each locale is a fresh set of indexed terms; even
  "English (UK)" vs "English (US)" gives you a second keyword field.

### 4. Propose changes; let metadata apply them
Draft improved name/subtitle/keywords per locale and show the user. Once
approved, hand the actual file edits + limit-validation to the
`app-store-metadata` skill (it owns `keywords.txt` etc.). Keyword/marketing
wording is the user's call — present options, don't unilaterally rewrite their
brand voice.

## Boundaries

- **It owns the strategy and the 100-character field, not the files.**
  `app-store-metadata` writes what this skill decides.
- **Google Play is out of scope** and not by omission: Play has no keywords field, so
  there the keywords *are* the visible copy, which `play-store-metadata` already owns.
- **It does not rename the app.** The name and subtitle are `app-identity`'s; this
  skill optimises within them and says so when they are the thing holding ranking
  back.

## Reference files
- [references/aso-guide.md](references/aso-guide.md) — how App Store search
  indexing works, the rules for name/subtitle/keywords, localization strategy,
  and common mistakes.
- [scripts/analyze_keywords.py](scripts/analyze_keywords.py) — per-locale ASO
  hygiene audit of the indexed fields.
