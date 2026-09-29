---
name: content-site-structure
description: >-
  Scaffold the content architecture of a multilingual content site — the `text/<lang>/`,
  `data/` and `media/` tree, the locale manifest, the Astro rendering engine, the
  fallback policy and the completeness validator. **Use this skill when — and only
  when — the user explicitly asks for it by name, or asks for the content-site
  structure or template**
  ("תפרוס את תבנית אתר התוכן", "בנה את מבנה אתר התוכן", "scaffold the content site",
  "set up the multilingual content structure"). It is NOT a baseline and NOT a default:
  do NOT load or apply it merely because a site or page is being built, because content
  is multilingual, or because a site could be restructured this way — `page-builder`
  plans pages without it. It does NOT restructure an existing site, and it is NOT for
  catalog-driven sites whose content already lives in key/value i18n JSON.
---

# content-site-structure

Lays down the content architecture of a **multilingual content site**: prose in
Markdown per language, structured records in JSON, media in one place, an Astro engine
that renders all three, and a validator that says when a language fell behind.

It writes files. That is the whole point of it — and the reason it must never start on
its own.

## Invocation — read this before anything else

**This skill runs only when the user asked for it.** Not when a page is being built,
not when a site happens to have two languages, not because an existing site looks like
it would be better off this way.

Before the first file is written, all four must hold:

1. **The user asked for this structure**, by name or by describing it. "Build me a
   landing page" is not an ask. "Set up the content-site structure" is.
2. **The target repo is empty of a site, or the user said explicitly to scaffold into
   this one.** Check first: an existing `index.html`, `_template.html`, `package.json`
   with a framework, or a populated `src/` means a site is already here. Say what you
   found and stop.
3. **The site is not catalog-driven.** If content prose already lives in key/value i18n
   JSON (`i18n/<lang>.json` with paragraph-length values), this skill is the wrong
   shape for it. Say so and stop — converting a live site's content model is a
   migration the owner decides on, not a scaffold.
4. **Astro is acceptable, or the user named another engine.** The engine here is Astro;
   see `references/astro-engine.md`. For plain HTML or Next.js, the tree and the
   manifest still apply but the engine must be written for that stack.

If any of the four fails, **stop and say which one**. Do not scaffold "the parts that
are safe anyway".

## Prerequisites

- **Tools:** Node ≥ 18 and npm, for the Astro project. Python 3 for the validator.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** not used. Reads the site repo's own `PRODUCT.md` if it exists,
  for the audience and the language set.
- **Other tracks:** `page-builder` (web-track) decides what goes on each page and runs
  independently of this skill; `frontend-design` (design-track) styles the result;
  `web-seo` (web-track) audits the live site afterwards.

## What it produces

```
locales.json                  ← the locale manifest: languages, default, dir, fallback
src/
├── text/                     ← CONTENT prose, one folder per language
│   ├── he/
│   │   ├── index.md
│   │   └── reference/shabbat.md
│   └── en/
│       └── index.md
├── data/                     ← structured records (optional)
│   └── lessons.json
├── media/                    ← images, video, audio — locale-neutral
│   ├── hero.avif
│   ├── captions/he/intro.vtt ← captions ARE content: per language
│   └── he/og.png             ← per-locale ONLY for baked-in text
├── i18n/                     ← UI strings — buttons, nav, errors. NOT content.
│   ├── he.json
│   └── en.json
├── content.config.ts         ← Astro collections over text/ and data/
└── pages/[...]               ← routes, per locale
scripts/check_content.py      ← the validator
```

Four rules decide what goes where:

- **Prose that a reader reads** → `text/<lang>/`, Markdown.
- **A short string the interface shows** (button, nav item, error, aria-label) →
  `i18n/<lang>.json`.
- **A repeated record with fields** (lesson, product, person, term) → `data/`.
- **A file a browser fetches** (image, video, audio, download) → `media/`.

Markup belongs in none of them. A `<li>` inside a translation value is the failure this
structure exists to prevent.

## The steps

1. **Run the four invocation checks above.** Stop on any failure.
2. **Ask the four questions, then write `locales.json`.** Not one of them is
   inferable, and two of them cannot be taken back later:

   - **Which languages**, and **which is the default** — the complete one everything
     falls back to. Ask; do not infer from the language the user is writing to you in.
   - **Which are RTL** — it sets `dir`, and it changes layout decisions downstream.
   - **What a missing translation does** — `strict` fails the build, `fallback` renders
     the default language with a visible notice, `hide` removes the page from that
     language entirely. These give a visitor three different sites; the owner picks,
     not you. Silent fallback is not on the menu.
   - **Where the default language lives in the URL** — at the root (`/`) or under its
     own prefix (`/he`). **Pick one and never serve both.** This reaches every address
     the site will ever have indexed, so changing it later is a redirect map, not an
     edit.

   The last two are the expensive ones: a fallback policy chosen by accident makes a
   half-translated site look finished, and a URL shape chosen by accident is discovered
   the day someone links to the site. Do not write `locales.json` before you have all
   four answers — its shape is in `references/content-architecture.md`.
3. **Decide whether `data/` is needed at all.** Only if the site has repeated records
   with fields. A purely editorial site skips it — and unlike the four above, this one
   can be added later without breaking anything, so decide it rather than asking. See
   the same reference.
4. **Scaffold the tree**, with the default language complete and every other language
   folder present even when empty — an empty folder is a visible gap, a missing one is
   invisible.
5. **Write the Astro engine** — collections, locale routing, fallback, `lang`/`dir`.
   See `references/astro-engine.md`.
6. **Install the validator** at `scripts/check_content.py` and run it. See below.
7. **Hand off.** `page-builder` for what each page contains, `frontend-design` for how
   it looks.

## The validator

```bash
python3 scripts/check_content.py
```

Stdlib only, nothing installed. It reads `locales.json` and reports:

- **Mirror gaps** — a file in the default language with no counterpart elsewhere, and
  files in a non-default language that exist nowhere else.
- **Dead media references** — an image or video named in Markdown that is not in
  `media/`.
- **Front-matter** — missing `title`, and duplicate `slug` within one language.
- **Data completeness** — a localized field present in one language and missing in
  another.

Missing translations are **errors under `strict`, warnings under `fallback`, and
silent under `hide`** — the manifest decides, not the script. Wire it into the repo's
CI so a language that fell behind is reported by a machine and not noticed a year later.

## Principles

- **A missing translation is visible or it is a lie.** Silent fallback makes a site look
  complete in a language nobody finished. The manifest must name a policy.
- **The filename is the URL.** Renaming a content file breaks an indexed address. Use
  the `slug` front-matter field and keep a redirect when it changes.
- **Content renders at build time.** A content site that injects prose with client-side
  fetch is a content site Google reads as empty.
- **A language folder that is absent is invisible; one that is empty is a gap.** Create
  every declared language, even unpopulated.
- **`data/` ships to the client.** No secrets, no PII, on a static site.

## Boundaries

- **It does not decide what goes on a page** — `page-builder` does, and it does not
  need this skill to do it.
- **It does not design** — `frontend-design`.
- **It does not migrate an existing site** into this structure. That is the owner's
  decision and its own piece of work.
- **It does not write the site's words.** Those come from the owner and run through
  `copy-edit` (shared-track).

## References

- `references/content-architecture.md` — the tree, the locale manifest, the fallback
  policies, `data/` strategy, media and captions.
- `references/astro-engine.md` — collections, locale routing, rendering, `lang`/`dir`.
