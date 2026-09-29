---
name: app-profile
description: >-
  Build an app's product profile — the one document every piece of copy about it is
  later derived from: store listings, site pages, campaigns. Use when onboarding a new
  app, before writing any copy for it, or when the user asks to "analyze my app", "write
  up what my app does", "build the marketing profile", "document the app's advantages"
  ("נתח את האפליקציה", "בנה פרופיל"). It reads the app's source like a product analyst,
  interviews the owner for what code cannot reveal, researches the real competitors, and
  proposes a feature and advantage list for the owner to edit before anything is
  written. Writes `profile.md`, an owner-facing translation beside it, and prepares the
  media folder. It does NOT capture media (appstore-media does), does NOT write store
  listing text (store-metadata-writer does), and never writes the app's name or subtitle
  — those live in the app's README, owned by app-identity.
---

# App Profile — the source of truth for an app's copy

> **Conversational language:** talk to the owner — interview questions, summaries, the hand-off — in the `conversational language` set in the hub `DATA.md` (`$APP_HUB/DATA.md`). This is the language of the **owner mirror** (Step 7) too. The English `profile.md` stays the source of truth regardless.

This skill produces **one artifact**: `<slug>/profile.md` in the **studio hub**
(`$APP_HUB`) — a structured, factual dossier of what an app is, what it
does, and why it's worth using, plus the folder of its Apple App Store-format screenshots and media.
Every later piece of copy (catalog card, app page, product site, App Store + Google
Play listing, campaign, ad) is **derived from this file** rather than re-invented.
Write it once, well; reuse it everywhere.

This skill runs from **anywhere** — most often from the app's own repo, where the
source it reads is. It writes only into the hub.

You operate here as a **product analyst, not a hype writer.** The job is to surface
what is genuinely true and useful about the app and state it plainly. A reader
should finish the profile knowing exactly what the app does and why they'd pick it —
with zero marketing inflation.

## Prerequisites

- **Tools:** none beyond Claude Code (web search/fetch for Step 3; no scripts).
- **Credentials:** none.
- **Hub (`$APP_HUB`):** required — reads `DATA.md` and `PRODUCT.md`, writes
  `<slug>/profile.md`, `profile.<lang>.md` and `media/apple/`; stops if unset.
- **Other tracks:** `appstore-media` and `aso-keywords` (apple-track) take the media
  folder and the discovery terms; the site repo's `add-app-to-site` reads the profile.

## The tone — non-negotiable

Match the hub's `PRODUCT.md` (the **master product voice**) exactly — it's the
default tone for all copy. The profile and everything derived from it is:

- **Factual and direct.** State the feature, then the concrete benefit. "Generates every required AppIcon size from one 1024px image" — not "effortlessly supercharges your icon workflow".
- **Specific over vague.** Name the real mechanism (openrsync, on-device, menu-bar, SSH, CloudKit). Specifics are credible; adjectives are not.
- **No hype vocabulary.** Banned: *powerful, seamless, effortless, revolutionary, cutting-edge, game-changing, supercharge, unleash, blazing-fast, magical, intuitive* (show it instead of claiming it), exclamation marks, and breathless superlatives.
- **No empty intensifiers.** Cut *deep, smart, clean, fast, simple* when the concrete mechanism is already named — "deep AI integration" → name the agents/tool-use; "smart backup" → "incremental backup"; "clean monochrome interface" → "monochrome interface". The intensifier adds emphasis, not information.
- **Headings name the content, not the action.** Any title in the Derived copy (tagline) or that downstream pages inherit must describe what's there, never exhort. Banned heading clichés: *See it in action, A closer look, Get started, Why choose…, The power of…, Discover…*. A demos section is titled by what the demos cover; a screenshots section by what's pictured.
- **No invention.** Every claim traces to the code, the app's own metadata/README, an explicit answer from the owner, or **cited web research** (link the source). Keep researched market facts (cited) separate from your own recommendations (labelled as recommendations) — never present a recommendation as an app fact. An advantage you can't ground is a question for the owner, not a guess.
- **Quiet confidence.** An engineer describing their own product accurately — never an enterprise consultancy or an AI SaaS landing page.

If a sentence would feel at home on a generic SaaS hero, rewrite it.

---

## Step 1 — Inputs

**Two different directories are in play — do not confuse them:**

- **The app's source project** (e.g. `$DEV_ROOT/xcode/<AppName>`) — you only **read** from here. It is somewhere else on disk.
- **The hub** (`$APP_HUB`) — you **write** the profile here, at its **root**, in `<slug>/`. **Always resolve it as `$APP_HUB`**, never with `git rev-parse --show-toplevel`: this skill ships in `shared-track`, which is enabled in app repos too, so from an app repo `--show-toplevel` returns *that* repo and the profile lands in the wrong one — a file in the right shape, in the wrong place, that nothing downstream reads. If `$APP_HUB` is unset, stop and say so. **Never** write into the app's source project. Create the `<slug>/` folder if it doesn't exist yet.

Ask the user (use `AskUserQuestion` if not given):

- **App project path** — e.g. `$DEV_ROOT/xcode/<AppName>` (the read-only source). Confirm the folder exists.
- **Display name** — the user-facing store name. The app's `README.md` identity block (written by the `app-identity` skill) is the **authoritative source** for the chosen **App name**, **App Store name**, and **Subtitle** — lift them from there; fall back to `CFBundleDisplayName` / the App Store listing only when there's no README. Confirm if ambiguous.
- **Slug** — the `<slug>/` folder name in the hub. Use the same slug the app uses elsewhere (matches the site's `privacy-policy/<slug>/` and `apps/<slug>/` convention).

**Read the app's `README.md` first.** This skill runs **after** `app-identity`, which
(in the app repo) settles the names and writes the README as the repo's source of
truth — its **identity block** (App name · App Store name · Subtitle · Bundle id ·
Platform) and its **ranked feature list**. Read that README the same way you read
the code: lift the decided names and the feature ranking from it as your starting
inventory, then *enrich and verify* against the source (Step 2) and the market
(Step 3). The profile supersedes it as the hub source of truth, but it is built
*from* it — don't re-derive the name or re-rank features the developer already
ranked. If there's no README, `app-identity` hasn't run; proceed from the code.

**Read the studio defaults — `DATA.md`.** Before reading the app, read `DATA.md` at the **hub root** for studio-wide defaults and any app data the owner dropped there. Today it sets the default **marketing / support / privacy URLs**, with `{app-slug}` substituted for this app's slug — e.g. for slug `app-screenshot-builder` the privacy URL becomes `https://<your-site>/privacy-policy/app-screenshot-builder`. These defaults are the **canonical** values for those fields: use them to fill the profile, and when the app's own `fastlane/metadata` disagrees (a stale or placeholder URL — e.g. a different app's slug, an old domain), **prefer the `DATA.md` default and flag the mismatch under Open questions** so the owner fixes the app's metadata. If `DATA.md` is missing, proceed without it.

If `<hub>/<slug>/profile.md` already exists, read it and offer to **update** it rather than overwrite — the owner may have hand-edited it. (If you update it, also regenerate the owner translation `profile.<lang>.md` — Step 7.)

## Step 2 — Read the project like a product analyst

Inventory what the app actually *does* and what's notable about it. Record findings with file references. Look at:

| Source | What to extract |
|--------|-----------------|
| `*.strings` / `*.xcstrings` / localized catalogs | The real, user-facing feature vocabulary — menu titles, button labels, setting names, empty-state copy. This is the app's own language; reuse it. |
| SwiftUI `View`s / storyboards / screens | The actual surfaces and capabilities — what windows/screens/panels exist, what each does. |
| Menu definitions, `Settings`/preferences, `Commands` | Feature breadth — every menu item and preference is a capability. |
| `Info.plist`, entitlements, `*.entitlements` | Platforms, OS minimums, what the app is allowed to do (sandbox, network, iCloud, widgets, extensions). |
| `StoreKit` / products config | Monetization — free, paid up-front, IAP, subscription, "Pro" tier and what it unlocks. |
| `README.md` (authored by `app-identity`) | The **authored source of truth** for this repo: the identity block (App name / App Store name / Subtitle) and the **ranked feature list**. Lift the names and the ranking directly; treat the features as the developer-vetted inventory, then verify each against the code. |
| `fastlane/metadata` / existing App Store text | The owner's prior listing copy and keywords — a useful cross-check, but the README (above) is the primary source; verify both against the code. |
| Bundled engines / notable dependencies | Differentiators worth naming (e.g. `openrsync`, a parsing engine, an on-device model). |
| App icon / `Assets.xcassets` | The marketing icon (for later media). |

From this, draft — **grounded, not yet polished**:

1. **What it is** — one or two factual sentences: core function + platform.
2. **Feature inventory** — the concrete capabilities, each traceable to a screen/menu/setting.
3. **Differentiators** — what's unusual or done better than the obvious alternative (native vs Electron, on-device vs cloud, no-account, no-terminal, one-tool-does-the-whole-job).
4. **Target user** — who specifically benefits.
5. **Monetization & platforms** — pricing model, platforms, distribution.

## Step 3 — Market research & competitive positioning (web)

Now switch hats: you are an **app-market analyst** who understands how apps in this category sell. The code told you *what the app does*; the market tells you *which of those things to lead with*. Use web search / fetch to ground this — do **not** rely on memory or assumptions about competitors.

Research, for this app's category and platform:

- **Comparable apps** — the obvious alternatives a buyer would weigh this against. Name them, note what they charge, and how they position themselves.
- **What the category competes on** — the axes buyers actually decide by (price, privacy, native vs web/Electron, speed, breadth, output quality, no-account, automation/CLI).
- **Gaps & complaints** — recurring user complaints about the alternatives (App Store/Play reviews, forums, Reddit) that this app happens to answer.
- **Discovery language** — the words real users use for this problem (this later feeds ASO; hand the raw terms to `aso-keywords`, don't optimise them here).

From that, decide and record:

1. **Unique value** — what this app provides that the named alternatives don't, or do worse — each tied to a real feature from Step 2.
2. **What to leverage** — the 1–3 angles the copy should lead with, given where the market is weak and this app is strong.
3. **What to downplay** — table-stakes features that won't differentiate.

Rules:

- **Cite every external claim** (link the source). A competitor's price, a complaint, a market trend — all need a source.
- **Facts vs recommendations.** "Competitor X is $29/yr [link]" is a fact; "lead with the free + offline angle" is your recommendation — label which is which, never blur them.
- **Never invent** competitors, prices, or quotes. If web access is unavailable, say so plainly and mark this section **TODO (no web access)** rather than guessing.
- Feed the conclusions into the profile's **Advantages**, **Positioning**, and the dedicated **Market context & what to leverage** section (Step 6) — and raise anything surprising (a strong competitor, an unmet need) with the owner in Step 4.

## Step 4 — Interview the owner for what code can't reveal

Code shows *what* the app does; the owner knows *why it matters* and *who it's for*. Ask only what the scan left open, in one or two focused `AskUserQuestion` rounds. Good questions:

- **The single biggest advantage** — "If a user remembers one thing, what should it be?"
- **Who it's for and the alternative it replaces** — what were they doing before this app?
- **The standout feature to lead with** — and any feature the scan missed.
- **Positioning vs alternatives** — what it deliberately does *not* try to be.
- **Pricing / availability** — if `StoreKit` was ambiguous.
- **Proof points** — any real, citable facts (number of stations, supported formats, OS versions) — never invented.

Keep questions concrete and few. Don't ask what you already found in the code.

## Step 5 — Propose the advantages, let the owner edit

Present a tight, ranked list: **what you believe the app's key features and advantages are**, each one line, factual. Explicitly invite the owner to **add, cut, reorder, or correct** — they are the authority on their product. Iterate until they're satisfied. This is the heart of the skill: the profile reflects the owner's real product, refined with your analysis, not your guesses.

## Step 6 — Write `<slug>/profile.md` (in the hub)

Copy `references/profile-template.md` and fill every section from Steps 2–5. Rules:

- Lead the file with the "source of truth / tone" banner from the template — verbatim — so anyone editing it later inherits the rules.
- Fill the URL fields (marketing / support / privacy) from the **`DATA.md` defaults** (Step 1), with `{app-slug}` substituted. Note any app-metadata mismatch under Open questions.
- Fill the **"Market context & what to leverage"** section from Step 3: cited competitor/market facts first, then your labelled recommendations on what to lead with. Keep facts and recommendations visually separate.
- The **"Derived copy"** section is the payoff: pre-write the reusable strings (one-liner, ≤160-char short description, the catalog-card sentence, the hero tagline, the Play short description) in house voice, **shaped by the "what to leverage" angles** from Step 3.
- **Never write the app name, the App Store title or the subtitle into the profile.** Those three live in exactly one place — the app repo's `README.md` identity block, owned by `app-identity` — and downstream skills read them from there. Writing them here creates a second source that goes stale the moment the app is renamed, and nothing catches it: the store and the site carry the new name while the profile, the file everything derives from, still carries the old one. If you need the name while writing, read the README; do not copy it in. These are exactly what `add-app-to-site` and `store-metadata-writer` lift — get them right here so downstream copy is consistent everywhere.
- Mark anything still unknown under **Open questions** rather than filling it with a guess.
- Validate the character-limited derived strings against their limits before moving on.

## Step 6b — Edit the copy-bearing sections (`copy-edit`)

Before translating, run **`copy-edit`** over "What it is", "Positioning", "Name &
brand story", "Key features" and "Advantages". Every downstream skill lifts its
words from those sections, so a clumsy sentence here is copied into the store
listing, the site and the campaigns.

Leave the status, media-inventory and open-item lines alone — they are records,
not copy, and tightening them costs precision for no reader.

Translating *after* this matters: an edited English sentence is much easier to
write as Hebrew than a convoluted one, which tends to be carried across
literally.

## Step 7 — Owner translation (`profile.<lang>.md`, the conversational language)

The owner reads in the **`conversational language`** from the hub `DATA.md`
. Once the English `profile.md` is finalised, write a full
translation into that language at `<slug>/profile.<lang>.md` (e.g. `profile.he.md`)
so the owner can review the profile in their language. **If the conversational
language *is* English** (the source language), skip this step — `profile.md` already
serves; there's no second file.

- **One profile, NOT one-per-language.** No matter how many locales the app ships, there is a **single** `profile.md` (English base). The per-language *store strings* are produced **downstream, in the metadata** — `store-metadata-writer` drives `app-store-metadata` / `play-store-metadata` to translate the Derived copy into each `<locale>/`, with per-locale character limits and ASO (`aso-keywords`; keyword vocabulary differs by language). Don't fork the profile per language. (Edge case: if a market needs genuinely *different positioning* — not a translation — capture that as a market note inside the one profile.)
- **English `profile.md` stays the single source of truth.** `profile.<lang>.md` is the **only** translated profile file, and it is a **derived, read-only mirror** for the owner — every downstream skill (`add-app-to-site`, `store-metadata-writer`, campaigns/ads) reads the **English** file, never the translated one. Regenerate the translation after **any** edit to the English profile so the two never drift.
- Start the translated file with a one-line banner **in the conversational language** stating it is a translation of `profile.md` for reading only, and that the English file is the source of truth. Keep the same section order as the English file so they can be read side by side.
- Translate the **prose** (What it is, Positioning, features, advantages, market context, target users, proof points, tech/privacy, open questions).
- **Do not translate the literal store/web strings** whose value is the shipping English text — the **Derived copy** block (one-liner, short description, titles, subtitle, keywords, taglines) and the **URLs** stay in English. Add a short gloss (in the conversational language) in parentheses after each so the owner understands what the field is for.

## Step 8 — App media (`media/apple/`)

The app's media lives in `<slug>/media/apple/` (Apple App Store-format) — but **this skill does not create it.** `appstore-media` does, **later**, once the app is buildable: it captures the screenshots + App Preview and writes them **straight here**. At profile time there are usually no screenshots yet, so:
- record the expected media in the profile's **Media** section as **TODO**;
- optionally drop in the **1024px marketing icon** / logo now — that's the one asset available early (from the Xcode assets).

Later, `appstore-media` fills the screenshots/video (run it in the app repo with its output pointed here). `add-app-to-site` then reads from here and optimizes copies into the web locations (`media/apps/<slug>/`, `sites/<name>/media/`) — it does not move the originals. List each asset with a one-line caption in the **Media** section.

**Apple only, for now.** This folder holds Apple-conforming media exclusively. Non-Apple-format media (Google Play 1024×500 feature graphic, web, social) belongs in sibling folders — `<slug>/media/play/`, `media/web/`, `media/social/` — added when you produce them (a dedicated skill may come later). Don't create those folders or non-Apple assets here yet.

## Step 9 — Hand off

The profile is now the source of truth. Tell the user:

- where it lives (`<hub>/<slug>/profile.md`) and that it's the file to edit when the app's story changes — and that `profile.<lang>.md` is the read-only mirror they review in the conversational language, regenerated from the English whenever it changes;
- a short summary of the **market research** — the named competitors and the angles you chose to leverage — so the owner can sanity-check your positioning;
- that `add-app-to-site` will read the English profile to write the privacy page, catalog card, app page, or product site — no copy gets re-invented downstream;
- that `store-metadata-writer` will read it to produce the App Store + Google Play listing metadata (cross-store, consistent copy), handing the file mechanics to the global per-store skills;
- that campaigns and ads (under `<slug>/campaigns/` and `<slug>/ads/`) derive from it too;
- any open questions or missing media still outstanding.

Commit the profile, its owner translation, and media together in the **hub** repo: `docs: add product profile for {{APP_NAME}}`.

> Ordering: `app-identity` runs first **in the app repo** to settle the name and write
> the README; this skill is the first **hub** step and lifts that README into the
> profile. Both `add-app-to-site` (web presence) and `store-metadata-writer` (store
> metadata) call for the profile: if none exists when someone runs either, run this
> one first (and if there's no README yet, run `app-identity` before it).

## Boundaries

- **It does not capture media** — `appstore-media` does, later, into the folder this
  skill prepares.
- **It does not write store listings** (`store-metadata-writer`) or the website.
- **It never writes the app's name, title or subtitle.** Those live in the app
  repo's README, owned by `app-identity`, and a second copy here would go stale the
  day the app is renamed.
