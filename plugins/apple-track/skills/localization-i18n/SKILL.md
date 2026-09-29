---
name: localization-i18n
description: >-
  Audit and manage IN-APP localization for a macOS or iOS Xcode project — the
  user-facing strings inside the app (Localizable.strings / .xcstrings String Catalogs),
  NOT the App Store listing text. Use this whenever the user wants to localize or
  translate the app's UI ("תתרגם את האפליקציה", "תוסיף שפה"), add or check a language,
  find hardcoded (un-localized) strings in Swift, check that all locales have all keys
  (no missing / empty / untranslated strings), find unused or undefined string keys,
  migrate to String Catalogs, or handle RTL (e.g. Hebrew) and pluralization. For App
  Store listing metadata (name/description/keywords per language), that's the separate
  app-store-metadata skill.
---

# Localization & i18n (in-app strings)

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

This is about the strings **inside the app** that users read — buttons, labels,
messages — across languages. The goal: every user-facing string is localizable,
every locale is complete, and nothing is hardcoded or left untranslated. (App
Store *listing* text is a different concern — `app-store-metadata`.)

## Prerequisites

- **Tools:** none beyond Claude Code and Xcode; `scripts/scan_localization.py` is
  stdlib Python 3.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — only the conversational-language default in `DATA.md`.
- **Other tracks:** `copy-edit` (shared-track) for the pass over added or translated
  strings; `capacitor-localization` (capacitor-track) owns the web layer of a
  Capacitor app.

## Workflow

### 1. Audit the current state
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/localization-i18n/scripts/scan_localization.py <project-root>
```
It reports, across `Localizable.strings` and `.xcstrings` catalogs:
- **Per-locale completeness** vs the base language: keys **missing**, **extra**,
  **empty**, or **untranslated** (value identical to the base — a strong hint
  it was never translated).
- **Code vs catalog**: keys **referenced in Swift but not defined** (a runtime
  fallback to the raw key — looks broken), and keys **defined but never used**
  (dead).
- **Hardcoded UI string candidates**: SwiftUI literals (`Text("…")`,
  `Button("…")`, `.navigationTitle("…")`, …) not wrapped for localization.

Treat the hardcoded list as *candidates* — some literals are intentional (brand
names, format strings, symbols). Confirm against the code before changing.

### 2. Decide the scope with the user
- Which locales are in scope (match what the app ships / the user wants).
- The **base/development language** (usually English) — it must be 100% complete;
  other locales fall back to it.
- Classic `.strings` vs **String Catalog** (`.xcstrings`). New work should prefer
  String Catalogs (Xcode 15+); see the reference for migration. Don't migrate an
  existing setup without asking — it changes the project.

### 3. Fix, in priority order
1. **Missing-in-catalog keys** (used in code, undefined) — 🔴 these show the raw
   key to users. Add them to the base, then translate.
2. **Hardcoded UI strings** — wrap in `NSLocalizedString`/`String(localized:)`
   (or move into the String Catalog) and add keys to every locale.
3. **Missing / empty keys per locale** — fill so each locale matches the base.
4. **Untranslated (same-as-base)** — translate; or confirm it's intentionally
   identical (e.g. a proper noun) so it's not re-flagged.
5. **Unused keys** — remove if truly dead (confirm they're not referenced
   dynamically by string-built keys before deleting).

### 4. Translate carefully
When you add/translate strings, keep keys identical across locales and translate
the *value*. Preserve format specifiers (`%@`, `%d`, `%1$@`) and their order;
keep placeholders intact. For anything you translate, tell the user it's a draft
to review — translation quality is their call, and tone matters in UI copy.

### 4b. Edit the strings you wrote (`copy-edit`)
In-app strings are customer-facing copy — an alert, an onboarding paragraph or a
help screen is read more carefully than a store listing, and the same rules apply.
Run the `copy-edit` skill over the strings you added or translated:

Hand it `<path-to>/Localizable.xcstrings` — `copy-edit` lives in another plugin
(shared-track), so invoke the skill and let it locate its own script.

It reads a String Catalog directly: it measures every language in the file (per
language, with characters rather than words for Japanese and Chinese) and compares
each language against the source language string by string — reporting any value
still identical to the English, and any translation that gained or lost a claim.
That comparison is the only check on a language nobody on the team reads.

Fix what it finds in the catalog, not in the built app.

## RTL and pluralization (flag when relevant)
- **RTL languages (Hebrew, Arabic):** the app should use leading/trailing (not
  left/right) and natural text alignment so layout mirrors automatically. If you
  see hardcoded `.left`/`.right` or left/right constraints, flag them. Test the
  UI in an RTL locale.
- **Plurals:** don't hand-build "1 item"/"N items" with if-statements — use a
  `.stringsdict` (classic) or the String Catalog's plural variations, which
  handle each language's plural rules. Flag manual pluralization.

Details and examples in [references/localization-guide.md](references/localization-guide.md).

## Boundaries

- **The app's own UI strings, not the store listing.** The App Store description,
  keywords and release notes per language are `store-metadata-writer`'s and
  `app-store-metadata`'s.
- **The native Apple layer.** Strings living in JavaScript or HTML inside a Capacitor
  app are `capacitor-localization`'s.
- **It does not translate.** It finds what is missing, untranslated, unused or
  hardcoded; the wording is the owner's and runs through `copy-edit`.

## What's safe vs ask-first
Safe: auditing, finding hardcoded strings, adding missing keys, drafting
translations (flagged as drafts), filling empty values. Ask first: migrating to
String Catalogs (project change), deleting "unused" keys (may be referenced
dynamically), and finalizing translation wording (the user's call).

## Reference files
- [references/localization-guide.md](references/localization-guide.md) —
  `.strings` vs `.xcstrings`, `NSLocalizedString`/`String(localized:)`, base
  language & fallback, `.stringsdict`/plural variations, RTL, and migration.
- [scripts/scan_localization.py](scripts/scan_localization.py) — the audit
  (completeness, code-vs-catalog, hardcoded candidates).
