# SEO, Metadata & Site Chrome

**Baseline for every project unless the user opts out.** A page that converts but can't be found, or that shares as a blank box in WhatsApp/Facebook, is unfinished. Wire discoverability and share-cards in from the start — they depend on the same `text/<lang>/` content and i18n locale map you already set up.

Combine with `i18n-rtl.md` — every tag below is per-locale, and titles/descriptions are better carried by the content's own front-matter than typed into the template.

## 1. Per-page metadata (every page, every locale)

```html
<title>Daily Practice Digest · Site Name</title>            <!-- ≤ ~60 chars, page-specific -->
<meta name="description" content="…">                  <!-- ≤ ~155 chars, unique per page -->
<link rel="canonical" href="https://example.com/he/">  <!-- absolute, per-locale -->
<meta name="robots" content="index,follow">             <!-- noindex thin/utility pages -->
<html lang="<the page's language>" dir="<ltr or rtl>">                              <!-- from the locale map -->
```

- **Title & description come from content**, not the markup — pull from front-matter (`title`, `description`) in `text/<lang>/*.md` where it makes sense.
- One **canonical** per page, **absolute URL**, per-locale. Avoid duplicate-content penalties.
- `noindex` utility pages (thank-you, internal search results).

## 2. `hreflang` (multi-language — see `i18n-rtl.md`)

Tell search engines about every localized version of a page, including a default:

```html
<link rel="alternate" hreflang="he" href="https://example.com/he/reference">
<link rel="alternate" hreflang="en" href="https://example.com/en/reference">
<link rel="alternate" hreflang="x-default" href="https://example.com/he/reference">
```

- Every page lists **all** its locale alternates **plus** `x-default`. Links must be reciprocal.
- Use real language (and region if needed) codes that match `<html lang>`.

## 3. Open Graph & Twitter cards (the WhatsApp/Facebook share box)

Critical for sites distributed by sharing (WhatsApp groups, etc.) — without these the link previews as a bare URL.

```html
<meta property="og:type"        content="website">          <!-- "article" for content pages -->
<meta property="og:title"       content="Daily Practice Digest">
<meta property="og:description" content="…">
<meta property="og:url"         content="https://example.com/he/">
<meta property="og:image"       content="https://example.com/og/he.png"> <!-- 1200×630, <300KB, absolute -->
<meta property="og:image:alt"   content="Description of the image">
<meta property="og:locale"      content="he_IL">
<meta property="og:locale:alternate" content="en_US">
<meta property="og:site_name"   content="Site Name">
<meta name="twitter:card"       content="summary_large_image">
```

- **OG image: 1200×630px, absolute URL, < 300KB.** Per-locale if it contains text (prefer live text over baked-in — see `i18n-rtl.md`).
- WhatsApp reads OG tags; test the real preview before delivery.

## 4. Structured data (JSON-LD / Schema.org)

Machine-readable context → rich results. Match the type to the page; one `<script type="application/ld+json">` per entity. For **citation-heavy reference content** this is especially valuable:

- **`Article`** — content/article pages (author, datePublished, headline, inLanguage). Pair with the authority information in `PRODUCT.md` — never fabricate an author.
- **`FAQPage`** — any real FAQ/objection section (mirrors questions actually on the page).
- **`BreadcrumbList`** — docs/nested reference content for breadcrumb rich results.
- **`Organization`** / **`WebSite`** — sitewide identity (logo, name, sameAs social links) + `SearchAction` if there's site search.

```html
<script type="application/ld+json">
{ "@context":"https://schema.org", "@type":"Article",
  "headline":"…", "inLanguage":"<lang>", "datePublished":"2026-05-28",
  "author":{"@type":"Person","name":"…"} }
</script>
```

> **Integrity rule (see `PRODUCT.md` §7):** structured data must reflect *real* on-page facts and real authorship. Never invent `aggregateRating`, review counts, or authors to win a rich snippet.

## 5. Crawl files

- **`sitemap.xml`** — list every indexable URL, include per-locale `xhtml:link` alternates mirroring your `hreflang`. Generate at build time so it stays in sync.
- **`robots.txt`** — allow crawling, point to the sitemap (`Sitemap: https://example.com/sitemap.xml`); disallow utility/duplicate paths.

## 6. Site chrome / icons & manifest (consolidated)

The full asset set (formerly scattered across mobile/perf notes):

```html
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">   <!-- 180×180 -->
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#…" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#…" media="(prefers-color-scheme: dark)">
```

- **Manifest** (`name`, `short_name`, `theme_color`, `background_color`, icons incl. a **512×512 maskable** for Android) — required for installable/app-like sites; harmless to include otherwise.
- `theme-color` colors the mobile status/URL bar (see `responsive-mobile.md`); provide light + dark.
- Icons & OG images count toward the performance budget — compress them (`performance.md`).

## Per-stack notes

- **Next.js:** use the Metadata API (`generateMetadata` per route, `alternates.languages` for hreflang, `opengraph-image`/`icon`/`sitemap.ts`/`robots.ts` file conventions). Renders into `<head>` server-side — SEO-safe.
- **Astro:** set head tags per page/layout; generate sitemap with `@astrojs/sitemap`; build OG images with `astro-og-canvas` or similar.
- **Plain HTML/CSS/JS:** put the tags directly in each page's `<head>`. If using one-file-per-language, each file carries its own correct `lang`/`canonical`/`hreflang`/OG.

## Acceptance check

- [ ] Every indexable page has a unique `<title>` and `description`.
- [ ] One absolute `canonical` per page, per locale.
- [ ] `hreflang` alternates (incl. `x-default`) on every localized page, reciprocal.
- [ ] OG + Twitter tags present; **share preview tested** (incl. WhatsApp) with a real 1200×630 image.
- [ ] JSON-LD matches a real on-page entity; no fabricated authors/ratings.
- [ ] `sitemap.xml` (with locale alternates) + `robots.txt` present and in sync.
- [ ] Favicon set, apple-touch-icon, manifest (+512 maskable), light/dark `theme-color`.
- [ ] Utility pages (`thank-you`, search) are `noindex`.
