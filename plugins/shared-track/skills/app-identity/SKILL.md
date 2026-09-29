---
name: app-identity
description: >-
  Decide an app's NAME for both stores, and own the project README as the source of
  truth for the name, subtitle / short description, and detected feature list. Use when
  the user wants to name or rename an app, asks "what should I call my app", wants to
  change the name under the icon or in a store listing, or wants the README's feature
  list written or refreshed ("תן שם לאפליקציה", "עדכן את ה-README"). Run it when the app
  is feature-complete, and always BEFORE app-store-metadata, play-store-metadata,
  aso-keywords and appstore-media, which all read the name and feature list from here.
  It scans the code for features and monetization, proposes ASO-aware candidates, and
  DISCUSSES them: it never picks a name on its own. Once decided it writes the display
  name into the Apple build settings and into Android's strings.xml, and owns the
  README's version label and changelog. It does NOT write the store metadata files or
  the keyword field — app-store-metadata, play-store-metadata and aso-keywords own
  those.
---

# App Name & README (the app's identity, source of truth)

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

An app's name is not one string — it shows up under the icon, in the window
title and menu bar, on the App Store listing, and in the subtitle right beneath
it. These have different rules (the on-device display name is an Xcode build
setting; the App Store name and subtitle are fastlane metadata fields with
character limits and ASO weight). When they drift apart, or when nobody wrote
down *why* this name was chosen, every later step re-litigates it.

Run this when the app is **feature-complete** — at the end of building it, and
before the store/listing steps. It decides the name *with the developer*, applies
the on-device part, **detects the app's feature list (and any Pro/premium tier)
from the finished code**, **tracks the app's version history** (asking each run
whether the version changed, and logging what's new when it did), and records all
of it in **one source of truth — the project README** — so the listing/media
skills lift from there instead of re-interviewing or inventing. In the studio flow that source of truth
is `$APP_HUB/<slug>/profile.md`; for a standalone project it is the
repo's own `README.md`, and this skill owns it.

**The README is the only listing artifact that stays in the app repo.** Everything
else — the per-locale store metadata, the screenshots, and the release notes — lives
in the **hub** (`$APP_HUB/<slug>/store/` + `media/`, owned by
`store-metadata-writer`) and is synced into `fastlane/` only at deliver time. So the
repo holds the **identity** (app name + feature list, here); the hub holds the
**listing**. Keep this README accurate and it stays the one thing a developer reads
or edits in the repo to know what the app is.

This file is the method. What running it taught — the runs behind each rule — is in
[LESSONS.md](LESSONS.md).

## Prerequisites

- **Tools:** `scripts/read_app_identity.sh` (bash; `grep` and macOS's `/usr/libexec/PlistBuddy`, optional `xcodebuild` for the resolved value) and `scripts/check_name.py` (Python 3, standard library; reads the public iTunes Search API over the network) — nothing to install; `copy-edit`'s `measure_copy.py` (Python 3) for Step 6b.
- **Credentials:** none — `check_name.py` uses the public iTunes Search API, no account.
- **Hub (`$APP_HUB`):** optional — `DATA.md` is read for the conversational language; in the studio flow `app-profile` lifts this README into `<slug>/profile.md`, and standalone the README is the only source of truth. Nothing is written to the hub.
- **Other tracks:** `aso-keywords`, `app-store-metadata`, `appstore-media` and `ship-apple-app` (apple-track); `play-store-metadata` (android-track). `app-profile`, `store-metadata-writer` and `copy-edit` are this track's.

## Where this sits in the flow

```
app-identity  ─▶  aso-keywords      (optimize the chosen name/subtitle for search)
   │      ─▶  app-store-metadata (write name.txt / subtitle.txt / description)
   └──────▶  appstore-media     (lift the ranked feature list → screen story)
```

Run it once the app's features exist (end of development) and **before** the three
listing/media skills — the name and the detected feature list it settles are their
inputs. Don't author the name fresh inside those skills — take it from the README
this skill maintains.

## The naming surfaces (what gets set, and who applies it)

| Surface | What it is | Where it lives | Applied by |
|--------|-----------|----------------|-----------|
| **On-device display name** | the name under the icon, in the window title / menu bar / About box | Xcode build settings (`PRODUCT_NAME`, `INFOPLIST_KEY_CFBundleDisplayName` / `CFBundleName`) or a hand-maintained Info.plist; per-locale via `InfoPlist.strings` | **this skill** → see [references/build-settings.md](references/build-settings.md) |
| **App Store name** | the title on the listing (≤30 chars), search-indexed | `fastlane/metadata/<locale>/name.txt` | `app-store-metadata` (files) — decided here |
| **Subtitle** | the one-liner under the name (≤30 chars), search-indexed | `fastlane/metadata/<locale>/subtitle.txt` | `app-store-metadata` (files) — decided here |
| **Source of truth** | the chosen names + ranked feature list, with rationale | the project `README.md` | **this skill** → see [references/readme-source-of-truth.md](references/readme-source-of-truth.md) |

The display name and the App Store name **do not have to match** — and renaming
the *display* is far less disruptive than renaming the Xcode target or the
bundle id (which you almost never want to touch). See the reference for the
"rename the display only vs. rename the target" decision.

### The same app on Google Play

The naming **decision is one decision** — an app called two different things in two
stores is a mistake, not a localization — so it is made once, here, and recorded once
in the README. What differs is only where it gets written and the shape of the fields:

| Surface | Where it lives | Applied by |
|---|---|---|
| **On-device name (Android)** | `android/app/src/main/res/values/strings.xml` → `app_name` (the launcher label) and `title_activity_main`; per-locale via `values-<lang>/strings.xml`. In a Capacitor project `appName` in `capacitor.config.json` seeds these, and `npx cap sync` **rewrites `strings.xml` from it** — so change the config, not only the resource | **this skill** |
| **Play listing title** | `<slug>/store/play/metadata/<locale>/title.txt` — **≤ 30 chars** | `play-store-metadata` (files) — decided here |
| **Short description** | `<locale>/short_description.txt` — **≤ 80 chars** | `play-store-metadata` (files) — decided here |

**Play has no subtitle.** The 80-character *short description* does that job, and it
is both longer and fully search-indexed, so it is not a copy-paste of the Apple
subtitle — it is the same promise, written to its own length. Decide both here, at
the same time, from the same understanding of the app, and let the two metadata
skills write them.

The Android **applicationId** (`com.example.myapp`) is the counterpart of the bundle
id: permanent once published, and never renamed to follow a display name.

## Workflow

### 1. Scan — detect the app's features and read the current names
Before proposing anything, learn what the app actually does, **build its feature
list**, and find what it's called today:
- **Detect the features from the finished code** — walk the menus/commands,
  settings/preferences, the feature-bearing views and models, and entitlements;
  each surfaced capability is a feature. Reuse the app's own wording (menu titles,
  button labels) rather than inventing. This detected list is what you'll rank and
  write into the README, so be thorough — it's the app's feature inventory.
- **Detect monetization** — check StoreKit products / a `.storekit` config and any
  `Pro`/`Premium` gating in the code. If there's a paid tier, capture the product
  id and what it unlocks; it becomes the `Pro` line in the identity block.
- Read any existing README and marketing copy for the app's real job, its hero
  feature, and its honest differentiators.
- Run `${CLAUDE_PLUGIN_ROOT}/skills/app-identity/scripts/read_app_identity.sh [PROJECT_DIR]`
  to print the **current** on-device name, bundle id, target name,
  Info.plist / localized display names,
  the README identity block, and the **current version** (`MARKETING_VERSION` +
  the README's version label). This is read-only and gives you the
  "current → proposed" baseline so a rename is a deliberate diff, not a guess.
- **Note the version baseline** — keep the reported `MARKETING_VERSION` handy as
  the suggested answer for the "did the version change?" question in Step 5. Don't
  assume a bump means new features (or vice versa); the developer confirms.

### 1b. Critique — audit the name the app already has

Before proposing anything, put the current name through the same test a candidate would
face (why: see [LESSONS.md](LESSONS.md#the-name-is-usually-already-wrong-when-this-skill-arrives)):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/app-identity/scripts/check_name.py \
  --name "Quicknote: Templates Keyboard" \
  --subtitle "Fills from the message you got" \
  --category "text expander,snippet manager,paste keyboard" \
  --claims "fills from the message,placeholder,encrypt"
```

It reports, from the live store: character counts, any word repeated between the name and
the subtitle, whether the name's tail or any adjacent word pair in it already sits on
another listing, and — the one that matters most — **how many apps in the category already
claim each thing the subtitle sells**.

Read the output against the division of labour below. The four questions:

1. **Is the term the buyer types in the name?** If the highest-volume category word is only
   in the subtitle or the keyword field, it is ranking at a fraction of its weight.
2. **Does the tail collide?** A tail that duplicates a live listing is a 4.3 exposure.
3. **Is the subtitle's claim verified, or assumed?** A claim `> 4` competitors also make is
   table stakes; selling on it wastes the field and invites the comparison.
4. **Does anything repeat between the two fields?**

Report what you find and say plainly whether the name should change. **A name that is
merely unexciting is not a reason to rename** — the cost lands on every downstream surface
(store text, captions, README, profile, site), so say so and let the developer weigh it.

### 2. Propose — ASO-aware candidates, with reasons

**Split the work between the name and the subtitle before writing either.** They are
indexed together but they are not doing the same job, and a name that tries to do both
usually does neither:

| Field | Job | What goes in it |
|---|---|---|
| **App Store name** | **Being found** | The brand, plus the term the buyer actually types. It carries the highest ranking weight of any field — a keyword in the name outranks the same keyword in the subtitle or the keyword field. It does **not** have to differentiate. |
| **Subtitle** | **Being chosen** | The one verified thing no competitor offers, in words the name does not already use. |

A name that names the category is doing its job. **The failure is a name that describes a
feature the category already has** (why: see
[LESSONS.md](LESSONS.md#a-name-that-describes-a-feature-the-category-already-has)).
Measure before assuming a feature differentiates: pull the category from the iTunes Search
API and count how many descriptions already claim it.

**Never repeat a word between the name and the subtitle.** Apple indexes name + subtitle +
keyword field as one pool, so a repeated word buys nothing and costs a slot.

**Check every candidate against the store, not against taste.** For each proposed tail,
search the category and look for the phrase and for each adjacent word pair in existing app
names. A tail that duplicates a live listing is a 4.3 risk, not a coincidence (why: see
[LESSONS.md](LESSONS.md#a-tail-that-duplicates-a-live-listing)). Report the
collisions with the candidate; do not present a name you have not checked.

Offer a small set of candidates (typically 3–5) for the **app name**, and for
the **App Store name + subtitle** (these are usually richer than the on-device
name — e.g. display `Quicknote`, App Store `Quicknote: Templatesized Shots`,
subtitle `App Store screenshot maker`). For each, say *why* — what it conveys,
who it's for.

Run them past ASO before presenting: brief, plural/duplicate waste, the 30-char
limits on name and subtitle, and whether the high-value search terms live in the
name vs. the subtitle. **Draw on the `aso-keywords` skill for this** — it owns
the keyword strategy and the search-indexed-fields rules; don't reinvent that
analysis here, lift it. If `aso-keywords` isn't available, do a light local
pass (length, redundancy, the obvious search terms) and say so.

### 3. Discuss — the developer decides, not you
**Never pick the name unilaterally.** Naming is a product and brand decision the
developer owns; your job is to give them good options and sharpen their
thinking, then let them choose. Ask the questions that actually change the
answer:
- Who is the audience, and what's the one thing they should grasp from the name?
- Is there an existing brand / wordmark / domain to stay consistent with?
- Trademark or App Store name-collision concerns? (Flag the risk; you can't
  clear a trademark — say so.)
- Should the App Store name carry a keyword tail (`Name: keyword phrase`) or stay
  clean? Should the display name match the App Store name or be shorter?

Iterate on candidates with them until they pick. If they're undecided, narrow —
don't decide for them.

### 4. Apply — the on-device display name
Once the developer has chosen the **display name**, set it in the Xcode project
following [references/build-settings.md](references/build-settings.md): prefer
`PRODUCT_NAME` / `INFOPLIST_KEY_CFBundleDisplayName` over renaming the target or
bundle id, apply it to every relevant target (app + extensions/widgets/watch
app), add per-locale `InfoPlist.strings` only if the name should differ by
language, then verify the built `.app` shows the new name. Confirm before
editing the project file.

### 5. Version — ask whether this is a new version
**Not every run is a version bump.** Before writing the README, ASK the developer
explicitly: *did the app's version change, and to what?* Use the `MARKETING_VERSION`
baseline from Step 1 as the suggested answer, but let them confirm or override. Only the
developer's answer decides (why: see
[LESSONS.md](LESSONS.md#a-version-bump-is-not-a-feature-change-and-features-are-not-a-bump)).

- **No** → don't touch the version history. Update the identity block and reconcile
  the feature list as usual; the current-version label above the feature list stays
  as-is.
- **Yes (e.g. "version 2")** → this is a version event. Do two things in the README
  (Step 6 writes them):
  1. Set the **current-version label above the feature list** to the new version.
  2. Add a **precise changelog entry** for that version under `## Version history` —
     what was **added**, **changed**, or **removed** *for users*, in the app's own
     wording. Derive the delta by diffing the freshly-detected feature list against
     the previous version's documented features, and confirm the change list with
     the developer (they know what actually shipped). Keep each line concrete and
     truthful — it's user-facing release documentation, not a git log.

Document each version against the feature list it describes, so every recorded
version stays an accurate snapshot of what the app did at that version. Never
rewrite or delete past version entries — append the new one on top.

### 6. Record — write the source-of-truth README
This is the README finalization step — do it when the app is feature-complete so
the detected feature list matches the shipped software. Write into the project
`README.md` per [references/readme-source-of-truth.md](references/readme-source-of-truth.md):

1. The **identity block** — exactly these fields, in this order (the `Pro` line
   only when the app has a paid/Pro IAP tier; drop it for a fully-free app):

   ```markdown
   - **App name:** <on-device display name>
   - **App Store name:** <listing title, ≤30 chars>
   - **Subtitle:** <one-liner, ≤30 chars>
   - **Platform:** <e.g. macOS 14.6+>
   - **Bundle id:** `<com.acme.app>`
   - **Built with:** <stack, one line>
   - **Pro:** <one-time / subscription> (`<product id>`) — <what it unlocks>
   ```

2. The **current-version label directly above the feature list** (e.g.
   `**Version 2**`) — the version the listed features describe.

3. The **detected, ranked feature list** (hero first; each feature one honest
   line, in the app's own wording).

4. The **`## Version history`** changelog — but only per Step 5: add a new entry
   (what was added/changed/removed for users) **only when the developer confirmed a
   version change**; otherwise leave the history and the version label untouched.
   Newest version on top; never rewrite past entries.

This is the artifact the downstream skills read. Keep it truthful — it becomes
listing copy, so no invented claims. If a README already exists, update the
identity block in place and reconcile the feature list (and append a version entry
only when the version actually changed) rather than clobbering the developer's
prose.

### 6b. Edit the copy-bearing lines (`copy-edit`)
Run the `copy-edit` skill over the lines that are *copy* — the subtitle, the one-liner,
the feature list, any positioning paragraph (why: see
[LESSONS.md](LESSONS.md#a-clumsy-readme-line-is-copied-onto-every-surface)):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/copy-edit/scripts/measure_copy.py <path-to>/README.md
```

Leave the records alone — bundle id, platform, version, build settings, paths. They
are facts, not prose.

### 7. Hand off — point the listing/media skills at the README
Everything downstream reads the README from here: see **Where this sits in the flow**
above for who takes what. The one thing to say out loud: that is the next step, and
**none of those skills re-authors the name** — the newest version-history entry is also
the raw material for the release notes.

## The core principle
You **propose and apply**; the developer **decides**. A name nobody chose on
purpose is worse than no rename at all — so the value here is the conversation
and the written-down rationale, not a clever auto-generated string. Scan, offer
real options with ASO and audience reasoning, and let the human land it.

## Boundaries
- You can't clear a trademark or guarantee an App Store name is free — surface
  the risk and tell the developer to verify in App Store Connect / a trademark
  search before committing.
- Renaming the Xcode **target**, **scheme**, or **bundle id** is invasive and
  rarely necessary just to change what users see — default to changing the
  display name only, and only touch the target/bundle id if the developer
  explicitly wants it (see the reference for the cost).
- Editing the project file is a code change — confirm before applying, and have
  the developer do a clean build to confirm the new name resolves.

## Reference files
- [references/build-settings.md](references/build-settings.md) — exactly where
  the on-device name lives and how to change it safely (build settings vs.
  Info.plist vs. target rename; per-target; per-locale; verification).
- [references/readme-source-of-truth.md](references/readme-source-of-truth.md) —
  the README structure this skill owns (identity block + current-version label +
  ranked feature list + per-version changelog) and how each downstream skill
  consumes it.

## Related skills
- `aso-keywords` — owns keyword strategy and the 100-character field; **this skill
  draws on it** when vetting candidates, then records the result.
- `ship-apple-app` — verifies late that the on-device name and the listing name agree;
  this skill produces both, early.
- `app-profile` — with a hub, the profile plays this source-of-truth role; without one
  the repo's README is the equivalent, and this skill owns it.
