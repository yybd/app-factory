# Pre-Delivery Checklist (structural)

Run this before handing a page off as "done". This is the **structure/conversion** gate from the page-builder skill. It does **not** replace the `web-design-guidelines` audit (accessibility/performance/UX rules) — run that too.

## Goal & structure
- [ ] The page has exactly **one** primary conversion goal, and it's obvious in the hero.
- [ ] Section order follows a sensible archetype (`../page-archetypes.md`); no padding sections.
- [ ] Every section earns the scroll — gives a reason to continue. Cut any that don't.
- [ ] Value is front-loaded; the reader isn't made to scroll past fluff to learn what this is.

## Hero
- [ ] Communicates what / who / next action within ~5 seconds.
- [ ] Headline is about the visitor's outcome, not a vague greeting.
- [ ] One dominant primary CTA; any secondary CTA is clearly subordinate.

## Trust
- [ ] Proof sits next to the claims it supports, not dumped in one band.
- [ ] A light trust signal appears right after the hero promise.
- [ ] All testimonials/stats/logos are **real** and attributed — nothing fabricated.
- [ ] Relevant proof appears just before each CTA.

## CTAs
- [ ] Primary CTA repeats at decision points (post-value, post-proof, final band).
- [ ] CTA copy is verb-first and sets expectation of what happens next.
- [ ] No competing equal-weight CTAs; visual hierarchy is clear.
- [ ] CTAs are real `<button>`/`<a>`, keyboard-focusable, ≥44px targets.

## Content completeness
- [ ] No lorem ipsum or placeholder copy left in.
- [ ] Every content TODO (missing testimonial, real photo, real number) is flagged to the user, not invented.
- [ ] FAQ/objection section covers the real top 3–5 hesitations.

## Content architecture
*Checks the principle, not one particular tree. A site already has an arrangement for
this — respect it. Scaffolding one is `content-site-structure`'s, on request only.*
- [ ] Content prose is authored outside the templates and injected — none typed into the markup.
- [ ] UI/button/nav strings live with the other UI strings, not mixed into the content.
- [ ] No markup inside a translation value — a `<li>` in a catalog entry is a defect.
- [ ] Every language the site claims is actually served; a missing translation behaves by a rule someone chose, and is visible to the reader rather than silent.
- [ ] `lang` and `dir` are set correctly per language.
- [ ] SEO-critical pages render content at build time (or are pre-rendered) — not client-only injection.
- [ ] Structured records, if any, keep language-neutral facts in one place; no secrets/PII in anything a static site ships.
- [ ] Images and video live in one media location (AVIF/WebP first, SVG icons); per-locale copies only for baked-in-text assets.
- [ ] Every video and audio file has a caption or transcript in each language served.

## Error & state pages (see `../page-archetypes.md` → System & state pages)
- [ ] Custom, on-brand, localized **404** that keeps header/footer/language switcher and links a way forward; server returns a real 404 status.
- [ ] Error/500 page is reassuring and non-technical; returns a real 500 status.
- [ ] Empty states (no-results / first-use / load-error) say why and offer a next action — not a dead end.
- [ ] Loading states use layout-matching skeletons where possible (no CLS), reduced-motion-safe; submit disabled in-flight.

## i18n / RTL (see `../i18n-rtl.md`)
- [ ] `<html lang dir>` correct for each locale.
- [ ] No hardcoded UI strings — all from catalogs.
- [ ] Layout uses logical CSS properties and mirrors cleanly in RTL.
- [ ] Longer/shorter translations don't clip or overflow.
- [ ] Embedded LTR (emails/URLs/numbers) renders correctly within RTL.
- [ ] Hebrew typography: real Hebrew font, comfortable line-height, nikud renders if used.
- [ ] Language switcher present and functional; switching updates direction + fonts + formatting.

## Responsive & mobile (see `../responsive-mobile.md`)
- [ ] Built mobile-first; works at **320px** through wide desktop with no horizontal scroll.
- [ ] Verified on an **iPhone** viewport (safe areas respected — nothing under the notch/Dynamic Island or home indicator).
- [ ] Verified on an **Android** viewport (~360px); address-bar hide/show doesn't break layout.
- [ ] Viewport meta includes `width=device-width` + `viewport-fit=cover`; pinch-zoom NOT disabled.
- [ ] Full-height sections use `svh/dvh`, not `100vh` (no iOS URL-bar jump).
- [ ] Tap targets ≥ 44px (iOS) / 48px (Android) with ≥8px spacing; primary CTA in thumb reach.
- [ ] Form inputs ≥ 16px font-size (no iOS auto-zoom); keyboard doesn't obscure active field.
- [ ] RTL verified at each breakpoint — layout mirrors and safe-area insets stay correct.
- [ ] Images use `srcset`/`sizes`; sized to avoid layout shift (CLS); below-fold lazy-loaded.

## SEO & share metadata (see `../seo-metadata.md`)
- [ ] Unique `<title>` + meta description per indexable page; one absolute `canonical` per locale.
- [ ] `hreflang` alternates (incl. `x-default`) on every localized page, reciprocal.
- [ ] Open Graph + Twitter tags present; **share preview tested (incl. WhatsApp)** with a real 1200×630 image.
- [ ] JSON-LD matches a real on-page entity (Article/FAQ/Breadcrumb/Organization) — no fabricated author/rating.
- [ ] `sitemap.xml` (with locale alternates) + `robots.txt` present and in sync; utility pages `noindex`.

## Forms & conversion (if the goal is a submission — see `../forms-conversion.md`)
- [ ] Submission destination is real and confirmed with the user; server/handler-side validation exists (not client-only).
- [ ] Every field has a real `<label>`; errors via `aria-describedby` + `role="alert"`; focus moves to first error.
- [ ] Correct `type`/`inputmode`/`autocomplete`; inputs ≥16px; phone/email `dir="ltr"`, free text `dir="auto"`.
- [ ] All four states implemented: idle / submitting (no double-submit) / success ("what's next") / error (input preserved).
- [ ] Spam defense (honeypot/time-trap min); CAPTCHA only if needed and accessible.
- [ ] Privacy policy linked; explicit opt-in for marketing/broadcast; HTTPS; data minimized; no PII in static `data/`/logs.
- [ ] Consent banner present only if non-essential cookies/scripts used; conversion event fires on success (if analytics).

## Performance & fonts (see `../performance.md`)
- [ ] Fonts self-hosted + subset to used ranges; **nikud range included if content uses nikud**, and verified.
- [ ] `font-display: swap`; critical hero font `preload`ed; `woff2` only; families/weights limited; fallback metrics tuned.
- [ ] LCP element identified and fast; content rendered at build time (not client-only).
- [ ] CWV sane on a mid-range phone (LCP ≤2.5s, CLS ≤0.1, INP ≤200ms) — checked, not assumed.

## Basics
- [ ] Favicon set, apple-touch-icon, web manifest (+512 maskable) and light/dark `theme-color` present (see `../seo-metadata.md`).

## Handoff
- [ ] Ran the `web-design-guidelines` skill for the a11y/perf/UX audit.
- [ ] Listed remaining content TODOs and any known limitations for the user.
- [ ] **Published.** Committing is not delivering: the page is live at its real URL, confirmed by fetching it, not assumed from a green build. Follow the project's publishing step (in this repo: `npm run ship` — see `CLAUDE.md` → *Workflow phases* → *Publish*). Report the live URL only after that check passes.
