# i18n + RTL Architecture

**Baseline requirement for every project unless the user opts out:** sites ship with multi-language support wired in from the first commit, and direction (LTR/RTL) is first-class — not bolted on later. Retrofitting i18n/RTL is far more expensive than designing for it up front.

Decide the language set and default language during project intake (the orchestrator `CLAUDE.md` asks). Then apply the rules below.

## Core principles

1. **No hardcoded UI strings.** Every visible string comes from a translation catalog keyed by message ID — even if there's only one language today. (UI/chrome strings only; long-form *content* prose is authored separately and injected — the `content-site-structure` skill covers that split for a multilingual content site.)
2. **Direction is a document/layout property, not per-element styling.** Set `dir` on `<html>` and let CSS logical properties do the rest.
3. **Design for text expansion.** Assume copy can grow 30–40% (EN→DE/FI) or shrink and grow taller (EN→HE/AR). Never size containers to a single language's string length.
4. **Locale ≠ language.** Separate language (he, en) from formatting locale (numbers, dates, currency, plurals).
5. **Translatable ≠ translated.** Ship the structure even when only one language is filled in; mark untranslated keys.

## RTL: do it with logical properties

Replace physical CSS with logical equivalents so a single stylesheet works in both directions:

| Physical (avoid) | Logical (use) |
|------------------|---------------|
| `margin-left` / `right` | `margin-inline-start` / `-end` |
| `padding-left` / `right` | `padding-inline-start` / `-end` |
| `left` / `right` | `inset-inline-start` / `-end` |
| `text-align: left` | `text-align: start` |
| `border-left` | `border-inline-start` |
| `float: left` | `float: inline-start` |

- In **Tailwind**, use logical utilities (`ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`, `text-start/end`) instead of `ml/mr/pl/pr/left/right/text-left/right`. Enable RTL via the `dir` attribute; use the `rtl:`/`ltr:` variants only for the rare cases logical properties can't express.
- **Mirror directional things:** chevrons/arrows, back/next, progress, breadcrumbs, sliders. Flip with `[dir=rtl] .icon { transform: scaleX(-1); }` or direction-aware icons.
- **Do NOT mirror:** logos, media playback controls (play stays ▶ universally is debated — follow platform norm), phone numbers, code, and LTR data.
- **Bidi text:** wrap embedded LTR runs (URLs, emails, code, latin brand names) so they don't scramble inside RTL — use `dir="auto"` on user-generated fields and Unicode isolation where needed.
- **Numerals:** keep digits LTR; choose Western vs. locale digits intentionally.

## Stack-specific implementation

The orchestrator picks the stack per project. Match the i18n library to it:

### Next.js + React (dynamic sites)
- Use **`next-intl`** (App Router-native) or `next-i18next` (Pages Router). Prefer `next-intl` for new App Router projects.
- Locale routing: `/[locale]/...` segments; configure the `[locale]` dynamic segment + middleware for locale detection/redirect.
- Set `<html lang={locale} dir={dir(locale)}>` in the root layout, where `dir` is derived from a locale→direction map (`he`, `ar`, `fa`, `ur`, `he-IL` → `rtl`).
- Use the `Intl` API (`Intl.NumberFormat`, `Intl.DateTimeFormat`, `Intl.PluralRules`) for formatting; let the i18n lib handle ICU message plurals/interpolation.
- Keep catalogs as JSON per locale (`messages/he.json`, `messages/en.json`).

### Plain HTML/CSS/JS (landing pages)
- Keep it lightweight — don't pull a framework for a static page. Options, simplest first:
  - **One file per language** (`index.he.html`, `index.en.html`) with a language switcher, for tiny sites.
  - **A small runtime i18n** using `data-i18n="key"` attributes + a JSON dictionary loaded by a ~30-line script that swaps text and sets `document.documentElement.dir`.
  - Build-time templating (e.g., 11ty/Astro) if the page count grows — escalate to a generator rather than hand-maintaining many HTML copies.
- Always set `<html lang dir>` correctly and author CSS with logical properties so the same stylesheet serves both directions.

### Astro / other SSG
- Use the framework's i18n routing (`astro:i18n`) with per-locale content collections; render `lang`/`dir` from the route locale.

## Typography for Hebrew / RTL

- Choose fonts with a **real Hebrew cut**, not a latin font faking it. Quality options: **Heebo, Assistant, Rubik, Frank Ruhl Libre** (serif/editorial), **Noto Sans/Serif Hebrew**, **Alef, IBM Plex Sans Hebrew**. Pair a display Hebrew face with a readable body face.
- Hebrew needs **more line-height** than latin for the same size; final letters and lack of ascenders/descenders change rhythm — tune `line-height` and `letter-spacing` per script.
- If the site mixes scripts, define a font stack per language (`:lang(he)` / `:lang(en)`), don't force one font on both.
- Nikud (vowel points): if content uses it (common in some RTL texts), verify the chosen font renders nikud correctly and test at real sizes — many webfonts drop or misposition it.

## Localization beyond strings

- **Dates/times/numbers/currency:** format via `Intl`, never string-concatenate.
- **Plurals/gender:** use ICU MessageFormat; Hebrew has dual forms and gendered agreement — don't fake plurals with `+ "s"`.
- **Images with text:** prefer live text over baked-in text; if baked, provide per-locale assets.
- **SEO:** emit `hreflang` alternates and a localized `<title>`/meta per locale; set canonical per locale.
- **Forms:** locale-aware validation (names, phone, postal formats), and `dir="auto"` on free-text inputs.

## Quick acceptance check

- [ ] `<html lang dir>` correct for every locale.
- [ ] No physical-side CSS that breaks under RTL; layout mirrors cleanly.
- [ ] All UI strings come from catalogs; no hardcoded text.
- [ ] Switching language updates direction, fonts, and formatting together.
- [ ] Longer/shorter translations don't clip, overflow, or break layout.
- [ ] Embedded LTR (emails, URLs, numbers) renders correctly inside RTL.
- [ ] Hebrew font renders nikud (if used) and has comfortable line-height.
- [ ] `hreflang` + localized meta present.
