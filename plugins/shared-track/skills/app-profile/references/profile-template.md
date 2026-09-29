# {{SLUG}} — Product Profile

> **The heading is the SLUG, not the app's name.** The name, the App Store title and the
> subtitle live in exactly one place — the app repo's `README.md` identity block, owned
> by `app-identity` — and this file must not carry a second copy. It goes stale the day
> the app is renamed, silently, while everything derived from it keeps the old name.
> `SKILL.md` states that rule and this template used to break it in its own first line.
> Where a sentence below needs the name, read it from the README at the time of writing.
>
> **Source of truth for this app.** Every piece of copy written about it — catalog card, app page, product site, App Store listing, ad campaigns — derives from this file. When the app's story changes, edit here first, then regenerate downstream.
>
> **Tone (do not violate):** factual, direct, specific. State the feature, then the concrete benefit. No hype words (*powerful, seamless, effortless, revolutionary, cutting-edge, supercharge, intuitive*), no exclamation marks, no superlatives, no invented claims. An engineer describing the product accurately. See `PRODUCT.md`.

- **Slug:** {{SLUG}}
- **Last updated:** {{DATE}}
- **Project:** {{PROJECT_PATH}}

## What it is
<!-- One or two factual sentences: core function + platform. -->
{{WHAT_IT_IS}}

## Positioning
<!-- One line: who it's for and the job it does. The single thing to remember. -->
{{POSITIONING}}

## Platforms & distribution
- **Platforms:** {{PLATFORMS}}        <!-- macOS · iOS · Android · Web -->
- **Distribution:** {{DISTRIBUTION}}  <!-- App Store / direct (Developer ID DMG) / web -->
- **Pricing:** {{PRICING}}            <!-- free / paid once / IAP / "Pro" tier and what it unlocks -->
- **OS minimums:** {{OS_MIN}}

## Links (studio defaults from `DATA.md`, `{app-slug}` substituted)
- **Marketing URL:** {{MARKETING_URL}}
- **Support URL:** {{SUPPORT_URL}}
- **Privacy URL:** {{PRIVACY_URL}}

## Key features
<!-- Each line: a real capability traceable to a screen/menu/setting, then what it gives the user.
     Ranked, most important first. No filler entries. -->
- **{{FEATURE}}** — {{what it does, concretely}}.

## Advantages / differentiators
<!-- What this does better or differently than the obvious alternative, stated plainly.
     e.g. "Native menu-bar app, not an Electron wrapper." / "Runs entirely on-device — no account, no server." -->
- **{{ADVANTAGE}}** — {{the concrete edge}}.

## Market context & what to leverage
<!-- From web research (Step 3). FACTS get a cited source link; RECOMMENDATIONS are labelled. Never blur the two. -->
**Comparable apps (cited):**
- {{COMPETITOR}} — {{positioning / price}}. [source]({{URL}})

**What the category competes on:**
- {{AXIS}} — {{where this app sits on it}}.

**Unique value vs the alternatives:**
- {{UNIQUE_THING}} — tied to {{feature}}; the named alternatives {{don't / do worse}}.

**Recommendation — lead with (analyst's call, not an app fact):**
- {{ANGLE_TO_LEVERAGE}}.

**Downplay (table stakes):**
- {{COMMODITY_FEATURE}}.

## Target users
<!-- Who specifically benefits, and what they were doing before. -->
- {{AUDIENCE}}

## Proof points (truthful only)
<!-- Real, citable facts: supported formats, station counts, OS coverage, engine used. Never invented. -->
- {{PROOF}}

## Tech & privacy notes
- **Stack:** {{STACK}}                 <!-- native Swift/SwiftUI, React Native, Tauri, bundled engine… -->
- **Privacy posture:** {{PRIVACY}}     <!-- on-device / iCloud / what leaves the device — link the policy once created: /privacy-policy/{{SLUG}}/ -->

## Derived copy (house voice — lift these downstream)
<!-- Pre-written, reusable strings. add-app-to-site and store-metadata-writer lift these verbatim so every surface — site and stores — matches. -->
- **One-liner (≤10 words):** {{ONELINER}}
- **Catalog-card sentence (the `app.<slug>.desc`):** {{CARD_SENTENCE}}
- **Short description (≤160 chars, meta/OG):** {{SHORT_DESC}}
<!-- NO app name, store title or subtitle here. They live in ONE place: the app
     repo's README identity block, written by `app-identity`. A copy in this file
     is a second source that silently goes stale the day the app is renamed —
     and that has happened: after one rename the store and the website carried
     the new name while this file, the thing everything is supposed to derive
     from, still carried the old one, and nothing noticed. Downstream skills read
     the README for these three strings. -->
- **Google Play short description (≤80 chars):** {{PLAY_SHORT_DESC}}
- **Hero tagline (for an app page / product site):** {{TAGLINE}}

## Media
<!-- Apple App Store-format assets in media/apple/. (Non-Apple formats — Play/web/social — go in sibling media/<platform>/ folders, added later.) add-app-to-site optimizes copies into the web locations. -->
- `media/apple/{{file}}` — {{caption}}

## Open questions / TODO
<!-- Anything unverified or missing. Better an honest gap than a guess. -->
- {{TODO}}
