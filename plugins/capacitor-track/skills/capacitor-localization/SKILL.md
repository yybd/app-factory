---
name: capacitor-localization
description: >-
  Audit and manage the in-app localization of a Capacitor / web-shell app, whose UI
  strings live in JavaScript and HTML rather than in .strings, .xcstrings or
  strings.xml. Use whenever such an app needs a language checked, added or fixed, when a
  screen shows the wrong language or an empty label, when asked to find untranslated or
  hardcoded UI text, or when handling RTL in a bilingual app ("שפה לא נכונה", "תרגום
  באפליקציה"). It finds the failure this architecture hides: a lookup that falls back
  instead of failing, so a missing translation ships silently as the wrong language. For
  an Xcode project whose strings really are in String Catalogs, use localization-i18n
  instead — that skill has nothing to work on here. It covers the web layer's strings;
  native Apple localization is localization-i18n's job.
---

# Capacitor Localization — strings that live in JS and HTML

> **Conversational language:** talk to the user — questions, summaries, reports — in the `conversational language` set in the hub `DATA.md` (`$APP_HUB/DATA.md`); fall back to the language the user writes in if it is unset. This sets the *conversation* language only.

## Prerequisites

- **Tools:** none beyond Claude Code — `scan_web_strings.py` is stdlib Python 3.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — only the conversational language from `DATA.md`;
  falls back to the language the user writes in.
- **Other tracks:** `copy-edit` and `app-identity` (shared-track);
  `localization-i18n` (apple-track) for `.xcstrings` and Info.plist keys.

## Why this exists as its own skill

A Capacitor app has native shells, and it is tempting to look for strings in them.
They are not there. In one measured app: `strings.xml` holds **four lines** of plumbing
(app name, activity title, package, url scheme), there are **no** `.strings` or
`.xcstrings` files at all, and every user-facing word is in JavaScript object
literals and paired HTML spans. `localization-i18n` — built on String Catalogs and
Swift scanning — would report a clean bill of health on an app with no
localization at all.

The native surface that *does* exist (the launcher label, `CFBundleDisplayName`,
the Play title) is owned by **`app-identity`**, not here.

## The failure this architecture hides

The usual lookup is a fallback:

```js
function t(key) {
  const e = typeof key === 'string' ? T[key] : key;
  return e ? (e[S.lang] || e[DEFAULT]) : '';    // ← a missing language is NOT an error
}
```

A key with no entry for the current language does not throw, does not warn, does
not render empty. It renders **the default language, to a reader of another one**,
forever. Nothing in the build, the tests or the store review will catch it. That is
the first thing to scan for.

## Scan

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/capacitor-localization/scripts/scan_web_strings.py app
```

It discovers the app's languages from its own translation tables; `--langs a,b`
overrides. The examples below use `he` and `en`; the pattern is the same for any pair.

It reports four kinds, ranked:

| finding | what it means |
|---|---|
| **missing `<lang>`** | a `{ he: …, en: … }` pair lacking a language — ships the fallback silently |
| **`lbl-<primary>` with no `lbl-<secondary>` sibling** | see below — the label *disappears*, it does not fall back |
| **identical across languages** | same text in both; sometimes deliberate (a proper name), often untranslated |
| **hardcoded** | a literal in the primary script outside any language pair — heuristic, judge each |

`--no-hardcoded` skips the heuristic pass when you only want the hard findings.
Exit code is non-zero when anything is found, so it works as a gate.

## The two HTML patterns, and why only one direction is a bug

Both are deliberate; telling them apart is the whole job:

```html
<!-- SWAP: one replaces the other -->
<span class="lbl-he">כרטיס ברכה</span><span class="lbl-en">Greeting Card</span>

<!-- STACKED: an English subtitle shown under Hebrew, in both languages -->
<div class="brand">שם המוצר<span class="lbl-en">Product Name</span></div>
```

The CSS is what decides (the primary language here is `he`, the secondary `en`):

```css
body.lang-en .lbl-he            { display: none; }    /* hides EVERY primary label */
body.lang-en .lbl-he ~ .lbl-en  { display: inline; }  /* only a SIBLING replaces it */
```

So a primary label whose sibling is missing **vanishes in the secondary language** —
an empty label, not a fallback. A bare secondary label, by contrast, is the stacked
pattern and is correct. Flagging it would bury the real finding in noise, so the scanner checks
**siblinghood, not proximity** — the next element's own `lbl-en` sits a few dozen
characters away and would otherwise mask a genuinely broken pair.

## Adding a language

1. Extend every pair in the JS tables; the scanner tells you which ones you missed.
2. Extend the HTML swap pairs, or move to a `data-i18n` key if a third language
   makes the span-pair pattern unwieldy — two languages are its comfortable limit.
3. Check the **direction**: `document.documentElement.lang` and `dir` must follow
   the choice, and per-field `dir` where the content language differs from the UI
   (a Hebrew card composed in an English UI, and the reverse).
4. Fonts: a language whose script has no vendored face falls back to a system font
   and looks foreign to the design. Check what is in `vendor/fonts/`.
5. Run `copy-edit` over the new locale — completeness is not correctness.

## Boundaries

- **The strings that live in JavaScript and HTML.** Native Apple localization —
  `.xcstrings`, `Localizable.strings`, Info.plist keys — is `localization-i18n`'s, and
  Android's `strings.xml` is not covered by either.
- **It does not translate.** It finds what is missing, untranslated or hardcoded, and
  reports it; the wording is the owner's and goes through `copy-edit`.

## Related skills
- `app-identity` — owns the native display name and the store names.
- `copy-edit` — the parity and craft pass over the text itself.
- `capacitor-bug-flow-review` — the QA counterpart for the same web layer.
- `localization-i18n` — the Xcode/String-Catalog skill this one replaces for
  Capacitor apps.
