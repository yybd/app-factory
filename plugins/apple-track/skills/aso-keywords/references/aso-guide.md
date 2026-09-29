# App Store Optimization — keywords guide

last-verified: 2026-06-03
source: Apple App Store Connect Help (app information, keywords) + ASO practice

## How App Store search indexing works
The store builds your searchable index from, roughly in weight order:
1. **App name** (30 chars) — highest weight.
2. **Subtitle** (30 chars) — high weight.
3. **Keywords field** (100 chars, hidden from users) — the rest.
(Plus your developer name and in-app purchase names play a minor role.)

Crucially, these are indexed **together** as one bag of terms. So:
- A word in the name/subtitle does NOT need to be in the keywords field —
  repeating it there is wasted space.
- The store matches word **stems / combinations**, so you don't need both
  "note" and "notes", and you don't need multi-word phrases the store can
  assemble from individual terms (having "task" and "manager" can match "task
  manager").

## Rules for each field
**Name (30):** brand + the single strongest keyword. e.g. "Bear — Markdown
Notes". Don't keyword-stuff the name (Apple rejects spammy names, 2.3.7).

**Subtitle (30):** a benefit + secondary keywords; complements the name, doesn't
repeat it. Shown to users, so it must read well.

**Keywords field (100):**
- Comma-separated, **NO spaces after commas** ("a,b,c" — every space is a wasted
  character out of 100).
- **Don't repeat** words already in the name/subtitle.
- **No duplicates**, and don't include both singular and plural of the same word.
- Don't include your **own brand name** (you already rank for it) or
  **competitor/trademarked** names (rejection risk).
- Single words generally beat phrases — the store recombines them.
- Use the full ~100 chars; an empty/short field wastes a ranking surface.

## Localization = more keywords (high-leverage)
Each App Store **locale** has its own name/subtitle/keywords → its own index.
- Translating the listing isn't just for readability; it multiplies your indexed
  terms market by market.
- Even **English (U.S.)** vs **English (U.K.)** vs **English (Australia)** are
  separate fields — you can put *different* keywords in each to cover more terms
  for English-speaking users (a common advanced ASO move).
- Some locales also serve other countries by fallback — research which locale
  covers which storefronts before duplicating effort.

## Common mistakes (the audit flags these)
- Spaces after commas in the keyword field (wasted chars).
- Repeating name/subtitle words in keywords (redundant).
- Singular + plural of the same word; duplicate terms.
- Leaving the keyword field half-empty.
- Stuffing the **name** with keywords (spammy → rejection).
- Using competitor trademarks (rejection).
- Generic terms only ("app", "tool") with nothing specific to how users search.

## What needs paid tools (out of scope here)
Actual **search volume**, **keyword difficulty**, and **competitor rank
tracking** require third-party ASO platforms (AppTweak, Sensor Tower, App Radar,
…). This skill does on-page hygiene and structure; for volume-driven keyword
selection, point the user to those tools and treat any volume claim as unverified
without them.
