# Responsive & Mobile (iPhone + Android)

**Baseline requirement for every project unless the user opts out:** sites are built **mobile-first** and verified on real iPhone *and* Android viewports — not just resized desktop. Mobile is the majority of traffic for most of these sites; treat the phone layout as the primary design, then enhance upward.

Combine this with `i18n-rtl.md`: responsive layouts must also mirror cleanly in RTL at every breakpoint.

## Core principles

1. **Mobile-first CSS.** Author base styles for the smallest screen, then add complexity with `min-width` media queries. Never start desktop-down.
2. **Fluid over fixed.** Prefer fluid widths, `%`, `fr`, `minmax()`, `clamp()` over fixed pixel layouts. Let content reflow; avoid horizontal scroll at any width.
3. **Content priority.** On a phone, the single most important thing (promise + primary CTA) must be visible without horizontal scroll and reachable with the thumb.
4. **Test the real range.** 320px (small phones) → 768px (tablets) → 1024px+ (desktop). No layout may break, clip, or overflow across that range.

## The non-negotiable basics

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```
- `viewport-fit=cover` is what lets you use the safe-area insets below (iPhone notch / Dynamic Island).
- Never set `maximum-scale=1` or `user-scalable=no` — it breaks pinch-zoom and fails accessibility (WCAG 1.4.4).

## Breakpoints

Use a small, content-driven set (adjust to the design, don't cargo-cult):

| Token | min-width | Target |
|-------|-----------|--------|
| (base) | 0 | phones, portrait |
| `sm` | 480px | large phones / landscape |
| `md` | 768px | tablets |
| `lg` | 1024px | small laptops |
| `xl` | 1280px+ | desktop |

- Set breakpoints where the **content** breaks, not at specific device sizes.
- In **Tailwind**, these map to default `sm/md/lg/xl` — keep using logical spacing utilities (`ps-*`, `me-*`) so RTL still mirrors.

## Touch ergonomics

- **Tap targets:** minimum **44×44px** (Apple HIG) / **48×48dp** (Android Material). Give icon buttons real padding, not just a small glyph.
- **Spacing between targets:** ≥ 8px so fingers don't hit the wrong control.
- **Thumb zones:** put primary actions in the lower-center/reach area on tall phones; avoid critical actions pinned to top corners.
- **Hover isn't available.** Anything that only appears on `:hover` must have a tap/visible equivalent. Use `@media (hover: hover)` to gate hover-only effects.
- **Sticky mobile CTA bar** is a strong pattern for long pages — but it must respect the home-indicator safe area (below).

## Safe areas (notch, Dynamic Island, home indicator, punch-holes)

Modern iPhones and many Android phones have non-rectangular display areas. Pad against them:

```css
.app-bar   { padding-top:    env(safe-area-inset-top); }
.bottom-bar{ padding-bottom: env(safe-area-inset-bottom); }
.edge      { padding-inline: max(1rem, env(safe-area-inset-left), env(safe-area-inset-right)); }
```
- Requires `viewport-fit=cover` in the viewport meta.
- Sticky/fixed bars (headers, mobile CTA bars, cookie banners) are the usual offenders — always inset the bottom bar so it clears the iPhone home indicator.

## iOS Safari gotchas (test these explicitly)

- **`100vh` is wrong on iOS.** The dynamic toolbar makes `100vh` taller than the visible area, causing content to hide behind the URL bar. Use **`100svh`/`100dvh`** (small/dynamic viewport units), with a `vh` fallback for old browsers.
- **Input zoom on focus:** iOS auto-zooms when a form field's `font-size < 16px`. Set inputs/textareas to **≥16px** to prevent the jarring zoom.
- **Tap highlight:** customize `-webkit-tap-highlight-color` rather than leaving the default grey flash.
- **Momentum scroll** inside scrollable panels: `-webkit-overflow-scrolling: touch` where needed.
- **Fixed elements + soft keyboard:** position can jump when the keyboard opens; prefer sticky over fixed for input-adjacent UI, and test with the keyboard up.
- **`prefers-reduced-motion`** is widely set on iOS — honor it for hero/scroll animations.

## Android Chrome gotchas

- **Address-bar resize:** the viewport height changes as the URL bar hides/shows; `dvh` handles this. Don't lock layout to an initial height.
- **Density range is huge** (360–412dp common widths, 1.5×–4× DPR). Verify at ~360px width and ship `srcset` for high-DPR screens.
- **`theme-color`** colors the status bar: `<meta name="theme-color" content="#...">` (supports light/dark via media).
- **Back gesture / edge swipes:** avoid horizontally-scrolling carousels glued to the screen edge that fight the system back gesture.

## Responsive media & typography

- **Images:** always `srcset` + `sizes` (or `<picture>`) so phones don't download desktop-weight images. Add `width`/`height` (or `aspect-ratio`) to prevent layout shift (CLS). Lazy-load below-the-fold (`loading="lazy"`).
- **Fluid type:** `clamp(min, preferred-vw, max)` for headings so they scale without a dozen breakpoints. Keep body ≥16px on mobile (also avoids the iOS zoom issue).
- **Line length:** target ~45–75 characters; on phones a single column with comfortable inline padding.
- **Tables:** don't let wide tables force horizontal page scroll — wrap in an overflow container or restructure to stacked cards on small screens.

## Layout patterns that reflow well

- **Stack on mobile, grid on desktop:** `display:grid` with `grid-template-columns: 1fr` at base, more columns at `md+`. Or `repeat(auto-fit, minmax(min(100%, 18rem), 1fr))` for self-wrapping card grids.
- **Off-canvas / hamburger nav** for primary nav on phones; full bar on desktop. Ensure the menu is keyboard-accessible, traps focus while open, and closes on `Esc`/backdrop tap.
- **Hero split (text|visual)** collapses to stacked (text then visual) on mobile.
- **Multi-step forms** beat long forms on phones.

## PWA / install niceties (when relevant)

- `apple-touch-icon`, maskable Android icons, `theme-color`, and a web app manifest if the site should feel app-like or be installable.

## Verification (do this, don't assume)

When building UI, run the app and check in a browser with device emulation:
- [ ] iPhone viewport (e.g. 390×844, **with** notch/safe-area + Dynamic Island) — no content under the notch or home indicator.
- [ ] Android viewport (e.g. 360×800) — no overflow; address-bar hide/show doesn't break layout.
- [ ] Small phone at **320px** — nothing clips or scrolls horizontally.
- [ ] Tablet at 768px and desktop ≥1024px.
- [ ] **RTL at each breakpoint** — layout mirrors, sticky bars and safe-area insets still correct.
- [ ] Tap targets ≥44/48px; primary CTA reachable in the thumb zone.
- [ ] Forms: inputs ≥16px (no iOS zoom); keyboard doesn't obscure the active field.
- [ ] `svh/dvh` used for any full-height section; no `100vh` jump on iOS.
- [ ] Images use `srcset`; no layout shift on load.
