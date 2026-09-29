# Content Architecture — the tree, the manifest, the policies

The structure this skill scaffolds. It applies **to a site the user asked to scaffold
this way** — it is not a convention every site is measured against.

Four kinds of text, handled differently:

| Kind | Examples | Where it lives |
|------|----------|----------------|
| **Content prose** | article bodies, page copy, FAQ answers, content headings | `src/text/<lang>/*.md` |
| **UI / chrome strings** | button labels, nav items, form labels, validation messages, aria-labels | `src/i18n/<lang>.json` |
| **Structured records** | lessons, products, team, glossary, pricing tiers | `src/data/` |
| **Fetched files** | images, video, audio, downloads | `src/media/` |

The split is deliberate: prose is long-form, edited often, authored in Markdown; UI
strings are short and keyed; records have fields and repeat. **Markup belongs in none of
them** — an `<li>` inside a translation value defeats the whole arrangement.

## Directory layout

```
locales.json
src/
├── text/
│   ├── he/
│   │   ├── index.md
│   │   ├── about.md
│   │   └── reference/shabbat.md    ← sub-paths allowed
│   └── en/
│       ├── index.md
│       └── about.md
├── data/
│   └── lessons.json
├── media/
│   ├── hero.avif
│   ├── hero-640.webp
│   ├── logo.svg
│   ├── captions/
│   │   ├── he/intro.vtt            ← captions are CONTENT: per language
│   │   └── en/intro.vtt
│   └── he/og.png                   ← per-locale ONLY for baked-in text
├── i18n/
│   ├── he.json
│   └── en.json
└── content.config.ts
public/
└── media/                          ← only files needing a stable, unhashed URL
```

- **One folder per language under `text/`**, mirroring the same file tree, so a
  translator sees exactly what is missing.
- **The default language must be complete.** Every other language may lag; the
  fallback policy decides what a visitor sees when it does.
- **Create every declared language folder even when empty.** An absent folder is
  invisible; an empty one is a gap someone can see.
- **File names are stable content IDs** (`home`, `reference/shabbat`) and they reach
  the URL. See *Slugs and renames* below.

## `locales.json` — the manifest

Without it the engine guesses, and the validator has nothing to check against.

```json
{
  "default": "he",
  "fallback": "fallback",
  "locales": {
    "he": { "name": "עברית",  "dir": "rtl", "path": "/" },
    "en": { "name": "English", "dir": "ltr", "path": "/en" },
    "fr": { "name": "Français","dir": "ltr", "path": "/fr" }
  }
}
```

- `default` — the complete language. Everything falls back to it.
- `dir` — `rtl` or `ltr`, set on `<html>` together with `lang`.
- `path` — the URL prefix. The default language may sit at the root (`/`) or under its
  own prefix (`/he`); pick one and never serve both, or the same page exists at two
  addresses.

### `fallback` — the three policies

| Policy | A page missing in this language | Use when |
|---|---|---|
| `strict` | **the build fails**, naming the file | the site must never ship partial; small, controlled language set |
| `fallback` | renders the default language, with a **visible notice** that this page is not yet translated | the common choice — the visitor gets content and knows what it is |
| `hide` | the page does not exist in that language: absent from nav and sitemap, no `hreflang` pointing at it, 404 on direct hit | a language being rolled out gradually |

**Silent fallback is not one of the options.** Serving Hebrew under `/en` with nothing
saying so makes the site look complete in a language nobody finished, and search
engines index the wrong language for that URL. If policy is `fallback`, the notice is
part of the template, not a nicety.

## Markdown content files

```markdown
---
title: הלכות שבת
description: מבוא לדיני שבת
slug: shabbat            # optional — overrides the filename in the URL
order: 1
---

## כותרת תוכן

גוף הטקסט, **Markdown** מלא: רשימות, קישורים, ציטוטים.
```

- Front-matter holds content metadata — `title`, `description`, `slug`, `order`, tags,
  source citations. `title` is required; the validator fails without it.
- The body is prose only. No button labels, no nav text — those are `i18n/`.
- For citation-heavy content, keep sources in front-matter rather than inline, so they
  can be rendered consistently and checked.

### Slugs and renames

**The filename reaches the URL, so renaming a file breaks an indexed address.** Set
`slug` in front-matter and let the route read it, so the file can be reorganised
without moving the URL. When a slug genuinely must change, add the old one to a
redirects map in the same commit — a 404 on a page that ranked is the most expensive
kind of tidying.

## `data/` — only if the site has records

Add it only for **structured, repeated records**: a lesson list, a product catalog, a
glossary, pricing tiers. A purely editorial site skips `data/` entirely.

**Two strategies — pick one per project:**

*Localized fields in one file* (recommended for small sets — a price is never
duplicated):

```json
{ "id": "l1", "date": "2026-03-01", "media": "media/l1.mp4",
  "title": { "he": "שיעור ראשון", "en": "First lesson" } }
```

*Per-language files* (for large localized datasets): mirror `text/` —
`data/he/lessons.json`, `data/en/lessons.json`.

- Keep language-neutral facts — ids, dates, prices, file paths — in exactly one place.
- The validator reports a localized field present in one language and absent in another.
- **`data/` ships to the client on a static site.** No secrets, no real user PII. Public
  catalog data only.

### Records that become pages

A record may carry its own page (a lesson, a product) with its prose in
`text/<lang>/<collection>/<id>.md`. When it does, the record holds the facts and the
Markdown holds the words — never the same sentence in both. Routing for these is
declared in the engine; see `astro-engine.md`.

## `media/`

All images, video, audio and downloads live under `src/media/` — not beside the markup,
not inside `text/` or `data/`.

- **Locale-neutral by default.** A photograph is the same photograph in every language;
  duplicating it per language is pure weight. Create `media/<lang>/` **only** for
  assets with text baked into the pixels — realistically, OG share images.
- **Captions and transcripts are content, and they are per language:**
  `media/captions/<lang>/<name>.vtt`. Every video and every audio file needs a track in
  each language the site claims to serve; the validator warns when one is missing. This
  is an accessibility requirement, not a nicety — audio without a transcript is content
  that some visitors simply do not receive.
- **Modern formats first** — AVIF/WebP for photographs with a fallback, SVG for logos
  and line art. Provide several widths (`hero-640.webp`, `hero-1280.webp`) so phones do
  not download desktop images.
- **Always set `width`/`height` or `aspect-ratio`** — prevents layout shift.
- **`alt` text is content.** It comes from the content or the i18n catalog, never
  hardcoded in the template; decorative images get `alt=""`.
- **`src/media/` vs `public/media/`:** put files in `src/media/` so the build optimizes
  and fingerprints them. Use `public/media/` only for files that need a stable,
  unhashed URL — favicons, an OG image referenced by absolute URL elsewhere, a PDF
  linked from outside the site.
- **Never inline large media as base64.** It defeats caching.

## Why the split pays off

- Translators and editors touch `text/<lang>/` and `i18n/<lang>.json` — never code.
- Adding a language is one folder, one catalog, one manifest entry.
- Missing translations degrade by a policy that was chosen, not by accident.
- The markup stays structure: no prose, no strings, no records inside it.

## Acceptance check

- [ ] `locales.json` exists and names `default`, `dir` per locale, and a `fallback` policy.
- [ ] All four were answered by the owner, not chosen by the scaffold: the languages, the default, the fallback policy, and the URL shape.
- [ ] The default language is served at exactly one address — the root or its own prefix, never both.
- [ ] No content prose in the markup — it is in `text/<lang>/*.md`.
- [ ] No UI/button/nav strings in `text/` — those are in `i18n/<lang>.json`.
- [ ] No markup inside any translation value.
- [ ] Every declared language has a folder; the default language is complete.
- [ ] Missing translations behave per the declared policy — and `fallback` shows a visible notice.
- [ ] Every `.md` has `title` in front-matter; slugs are unique within a language.
- [ ] Content renders at build time, and `lang`/`dir` are set per locale.
- [ ] `data/` exists only if the site has records; no secrets or PII in it.
- [ ] Media lives in `media/`, locale-neutral except baked-in-text assets; sized to prevent CLS; `alt` from content.
- [ ] Every video and audio file has a caption/transcript track per language.
- [ ] `python3 scripts/check_content.py` passes.
