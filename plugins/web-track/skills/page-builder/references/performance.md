# Performance & Font Loading

**Baseline for every project unless the user opts out.** Performance is a conversion and SEO factor, not a finishing touch — and for **Hebrew-first sites it starts with fonts**, which are the single heaviest, most render-blocking asset on a typical page (Hebrew webfonts are large, and **nikud variants larger still**).

Pairs with `responsive-mobile.md` (images, `srcset`, CLS) and is gated by the `web-design-guidelines` audit. This reference adds concrete budgets and the font strategy those don't spell out.

## 1. Core Web Vitals — concrete targets

Aim for the "good" threshold on a **mid-range phone over 4G**, not a desktop on fiber:

| Metric | Target ("good") | What blows it |
|--------|-----------------|---------------|
| **LCP** (Largest Contentful Paint) | ≤ 2.5s | Render-blocking fonts/CSS, heavy hero image, slow server |
| **CLS** (Cumulative Layout Shift) | ≤ 0.1 | Unsized images, late-swapping fonts (FOUT jump), injected banners |
| **INP** (Interaction to Next Paint) | ≤ 200ms | Heavy JS on the main thread |

- The LCP element is usually the **hero heading or hero image** — make *that* fast first.
- Client-only content injection delays LCP and hurts indexing — prefer build-time rendering.

## 2. Font loading strategy (the Hebrew-first priority)

Order of preference:

1. **Self-host + subset** the chosen Hebrew face(s) instead of hot-linking the full Google Fonts family. Subset to the scripts/ranges you actually use (Hebrew block + Latin if mixed). **If the content uses nikud, the subset MUST include the niqqud range (U+0591–05C7)** — and verify it renders (`i18n-rtl.md`).
2. **`font-display: swap`** so text is visible immediately with a fallback, then swaps in. Prevents invisible text (FOIT) blocking LCP.
3. **`preload` the one or two critical fonts** (the display face used in the hero) so the swap happens early:
   ```html
   <link rel="preload" href="/fonts/frank-ruhl-libre-900.woff2" as="font" type="font/woff2" crossorigin>
   ```
4. **`woff2` only** (universally supported, best compression).
5. **Match the fallback metrics** to reduce the swap jump (CLS): set a fallback stack and tune with `size-adjust` / `ascent-override` on an `@font-face` fallback, or use the framework's automatic adjustment.
6. **Limit families & weights.** Two families (display + body) and the specific weights you use — not the whole 100–900 range. Each weight is bytes.

```css
@font-face {
  font-family: 'Frank Ruhl Libre';
  src: url('/fonts/frank-ruhl-libre-900.woff2') format('woff2');
  font-weight: 900; font-display: swap;
  unicode-range: U+0590-05FF, U+0591-05C7, U+20AA; /* Hebrew + nikud + ₪ */
}
```

- **Next.js:** `next/font` self-hosts, subsets, and auto-adjusts fallback metrics — use it (`next/font/google` or `next/font/local`).
- **Astro / plain HTML:** self-host the `woff2`, subset (e.g. `glyphhanger`/`subfont`), preload the critical face.

## 3. Images & media (cross-ref `responsive-mobile.md`)

- **Modern formats:** AVIF or WebP with a fallback; never ship desktop-weight JPEGs to phones.
- **`srcset` + `sizes`** (or `<picture>`); **always set `width`/`height` or `aspect-ratio`** (prevents CLS).
- **Lazy-load below the fold** (`loading="lazy"`); **eager-load the LCP/hero image** and consider `fetchpriority="high"` on it.
- Compress OG images, favicons, and icons too (`seo-metadata.md`).

## 4. CSS / JS / delivery

- **Critical CSS first; defer the rest.** Avoid large render-blocking stylesheets; inline critical above-the-fold CSS for landing pages.
- **Ship little JS.** Plain landing pages should need almost none; defer/`type=module`; avoid heavy libraries for effects CSS can do (the **`frontend-design`** skill's
  `techniques.md`; it is in the `design-track` plugin, so ask for it by name).
- **`preconnect`** to required third-party origins (font/provider) you can't self-host.
- **Cache headers / immutable hashed assets** at build time.
- **Compression** (Brotli/gzip) on text assets — usually the host's job; confirm it's on.

## 5. Respect the user & the device

- **`prefers-reduced-motion`** — already required by `frontend-design`; also a perf win.
- **`prefers-color-scheme`** — don't ship both themes' heavy assets if one suffices.
- Don't autoplay heavy video on mobile data.

## Acceptance check

- [ ] Fonts self-hosted + subset to used ranges; nikud range included **if** content uses nikud, and verified.
- [ ] `font-display: swap`; critical (hero) font `preload`ed; `woff2` only; families/weights limited.
- [ ] Fallback metrics tuned (or framework auto-adjust) — no large font-swap layout jump.
- [ ] LCP element identified and fast (eager hero image / early text); build-time rendered content.
- [ ] Images: AVIF/WebP, `srcset`+`sizes`, sized to prevent CLS, below-fold lazy-loaded.
- [ ] Minimal render-blocking CSS/JS; third-party origins `preconnect`ed; compression on.
- [ ] CWV sane on a mid-range phone profile (LCP ≤2.5s, CLS ≤0.1, INP ≤200ms) — checked, not assumed.
