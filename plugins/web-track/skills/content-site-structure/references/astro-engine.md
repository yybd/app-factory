# The Astro engine

Astro renders at build time, so the prose ships inside the HTML — which is the whole
reason a content site is not a client-side fetch. Requires Astro 5 (the Content Layer
API: `glob`/`file` loaders and `render()`).

**One source of truth for locales: `locales.json`.** Do **not** also enable Astro's
built-in `i18n` routing in `astro.config.mjs`. Two routing authorities produce two URLs
for one page, and the manifest is the one the validator reads.

## `src/content.config.ts` — the collections

```ts
import { defineCollection, z } from 'astro:content';
import { glob, file } from 'astro/loaders';

// Every .md under src/text/<lang>/… — entry ids come out as "he/index", "en/about",
// "he/reference/shabbat": the first segment is the locale.
const text = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/text' }),
  schema: z.object({
    title: z.string(),                    // required — the validator agrees
    description: z.string().optional(),
    slug: z.string().optional(),          // overrides the filename in the URL
    order: z.number().optional(),
  }),
});

// Only if the site has records. Localized fields stay objects keyed by locale.
const lessons = defineCollection({
  loader: file('./src/data/lessons.json'),
  schema: z.object({
    id: z.string(),
    date: z.string(),
    media: z.string().optional(),
    title: z.record(z.string()),          // { he: "…", en: "…" }
  }),
});

export const collections = { text, lessons };
```

The schema is the second line of defence. `check_content.py` catches what a build does
not (mirror gaps, dead media, duplicate slugs); the schema catches a malformed entry at
build time.

## Routing — one catch-all, driven by the manifest

`src/text/<lang>/index.md` is the locale's root page. Everything else routes by its
path under the language folder, or by its `slug`.

```astro
---
// src/pages/[...route].astro
import { getCollection, render } from 'astro:content';
import locales from '../../locales.json';
import Layout from '../layouts/Layout.astro';

export async function getStaticPaths() {
  const all = await getCollection('text');
  const byId = new Map(all.map((e) => [e.id, e]));
  const def = locales.default;
  const defaults = all.filter((e) => e.id.startsWith(`${def}/`));
  const paths = [];

  for (const [code, cfg] of Object.entries(locales.locales)) {
    const prefix = cfg.path.replace(/^\/|\/$/g, '');        // "" for "/", "en" for "/en"

    // The default language defines the page set; other languages fill it in.
    for (const base of defaults) {
      const page = base.id.slice(def.length + 1);           // "index", "reference/shabbat"
      const translated = byId.get(`${code}/${page}`);

      if (!translated) {
        if (locales.fallback === 'hide') continue;
        if (locales.fallback === 'strict') {
          throw new Error(`[content] missing translation: ${code}/${page}`);
        }
      }
      const entry = translated ?? base;
      const slug = entry.data.slug ?? page;
      const segments = slug === 'index' ? [] : slug.split('/');
      const route = [prefix, ...segments].filter(Boolean).join('/');

      paths.push({
        params: { route: route || undefined },              // undefined ⇒ the site root
        props: { entry, code, page, translated: Boolean(translated) },
      });
    }
  }
  return paths;
}

const { entry, code, page, translated } = Astro.props;
const { Content } = await render(entry);
---

<Layout code={code} page={page} title={entry.data.title} description={entry.data.description}>
  {!translated && <p class="untranslated" data-lang={locales.default}>
    <!-- the visible notice the `fallback` policy requires -->
  </p>}
  <Content />
</Layout>
```

**Why the default language defines the page set:** a page that exists only in a
non-default language is unreachable from the site's own structure and invisible to the
fallback. The validator reports it as an orphan rather than the engine inventing a
route for it.

## The layout — `lang`, `dir`, hreflang, UI strings

```astro
---
// src/layouts/Layout.astro
import locales from '../../locales.json';
const { code, page, title, description } = Astro.props;
const cfg = locales.locales[code];
const ui = (await import(`../i18n/${code}.json`)).default;

const href = (c) => {
  const p = locales.locales[c].path.replace(/^\/|\/$/g, '');
  const segs = page === 'index' ? [] : page.split('/');
  return '/' + [p, ...segs].filter(Boolean).join('/');
};
---
<html lang={code} dir={cfg.dir}>
  <head>
    <title>{title}</title>
    {description && <meta name="description" content={description} />}
    {Object.keys(locales.locales).map((c) => (
      <link rel="alternate" hreflang={c} href={new URL(href(c), Astro.site)} />
    ))}
    <link rel="alternate" hreflang="x-default" href={new URL(href(locales.default), Astro.site)} />
  </head>
  <body>
    <nav aria-label={ui['nav.label']}>
      {Object.entries(locales.locales).map(([c, l]) => (
        <a href={href(c)} hreflang={c} lang={c}>{l.name}</a>
      ))}
    </nav>
    <main><slot /></main>
  </body>
</html>
```

- `lang` and `dir` come from the manifest, never hardcoded.
- Under the `hide` policy, emit `hreflang` **only** for locales where the page exists —
  a reciprocal link to a 404 is worse than no link.
- UI strings come from `i18n/<code>.json`. Nothing in that file is a sentence of prose,
  and nothing in it is markup.

## Records that carry pages

When a `data/` record has its own page, the record holds the facts and
`text/<lang>/<collection>/<id>.md` holds the words. A second `getStaticPaths` over the
data collection joins them by id, applying the same fallback policy. Never write the
same sentence in both places — if the prose is in the record, the translator has to
edit JSON.

## Media

```astro
---
import { Image } from 'astro:assets';
import hero from '../media/hero.jpg';
---
<Image src={hero} alt={ui['hero.alt']} widths={[640, 1280]} formats={['avif', 'webp']} />
```

`src/media/` is optimized and fingerprinted by the build. `public/media/` is served
verbatim — use it only where a stable URL matters. For `<video>`, point `<track>` at
`media/captions/<lang>/<name>.vtt` and pick the track by the current locale.

## Build-time checks worth wiring in

```json
{ "scripts": {
    "check:content": "python3 scripts/check_content.py",
    "build": "npm run check:content && astro build"
} }
```

Under the `strict` policy the build already fails on a missing translation. Under
`fallback` it does not — which is exactly when the validator is the only thing that
will tell you a language stopped being maintained.
