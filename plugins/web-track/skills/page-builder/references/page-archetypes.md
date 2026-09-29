# Page Archetypes

Proven section orders per page type. Use these as a starting skeleton, then cut or merge sections to fit the actual content — never pad a page to hit a section count.

Each archetype lists sections top-to-bottom. `[primary CTA]` marks where the main action should repeat.

---

## Landing page (single goal, paid-traffic or campaign)

Tightest possible path to one action. No global nav distractions.

1. **Hero** — promise + `[primary CTA]`. Subhead names the audience and the outcome.
2. **Trust strip** — logos, ratings, or a single strong stat. Kills the "is this real" doubt instantly.
3. **Problem / agitation** — name the pain in the reader's words.
4. **Solution** — how the offer resolves the pain. Benefit-led, not feature-led.
5. **How it works** — 3 steps max. Reduces perceived effort.
6. **Proof** — testimonials, case results, before/after. `[primary CTA]` after proof.
7. **Objection handling / FAQ** — the 3–5 reasons people hesitate.
8. **Final CTA band** — restate the promise, `[primary CTA]`, remove the nav, add a risk-reverser (guarantee, free trial).
9. **Minimal footer** — legal, contact, language switcher. No competing links.

## Homepage (multi-audience, navigational hub)

Routes different visitors to the right place; does not try to convert everyone in one scroll.

1. **Hero** — what the org *is* in one sentence + `[primary CTA]` for the main audience.
2. **Audience split** — cards/links sending each segment to its own page.
3. **Value pillars** — 3–4 core benefits or offerings.
4. **Social proof** — logos, numbers, featured testimonial.
5. **Highlighted content/products** — most important 3–6 items.
6. **About / mission teaser** — link to full story.
7. **Secondary CTA** — newsletter, contact, or community.
8. **Full footer** — complete nav, legal, language switcher, social.

## Product / marketing page (considered purchase)

1. **Hero** — product name, core value, `[primary CTA]`, product visual.
2. **Trust strip.**
3. **Benefits** — outcomes for the user, each tied to a feature.
4. **Feature deep-dives** — alternating visual/text rows.
5. **Comparison / "why us"** — vs. alternatives or status quo.
6. **Proof** — testimonials, case studies, metrics. `[primary CTA]`.
7. **Pricing teaser or link.**
8. **FAQ.**
9. **Final CTA band** + risk-reverser.
10. **Full footer.**

## Content / article page (read + subscribe/convert)

1. **Title + meta** — H1, author, date, reading time.
2. **Lead / standfirst** — the payoff up front.
3. **Body** — well-structured headings, generous measure, pull-quotes.
4. **Inline CTA** — contextual, mid-article (subscribe / related offer).
5. **Author / source box** — authority signal.
6. **Related content.**
7. **End CTA** — subscribe or next step.
8. **Footer.**

For citation-heavy reference content: add source citations, a clear hierarchy of ruling vs. discussion, and print/share affordances.

## Docs / reference site

1. **Persistent sidebar nav** (collapsible on mobile).
2. **In-page TOC** for long pages.
3. **Search** — prominent, keyboard-accessible.
4. **Content** with copy-able code/quote blocks.
5. **Prev/next** navigation.
6. **Footer** with version + language switcher.

## Contact / lead page

1. **Hero** — one line on what happens after they reach out.
2. **Form** — minimum viable fields; every extra field costs conversions.
3. **Alternative channels** — phone, email, address, map, hours.
4. **Trust** — response-time promise, privacy note.
5. **Footer.**

## Pricing page

1. **Hero** — value framing, not just numbers.
2. **Plan cards** — highlight the recommended plan; 3 tiers is the sweet spot.
3. **Feature comparison table.**
4. **FAQ** — billing, cancellation, refunds (objection handling).
5. **Trust** — guarantee, security, testimonials.
6. **Final CTA.**
7. **Footer.**

## System & state pages (don't skip these)

Every site needs the non-happy-path screens. They're easy to forget and they're where trust is won or lost. Keep them **on-brand, localized (i18n/RTL), and helpful** — never a dead end.

### 404 (not found)
1. **Clear, human message** — "This page does not exist", not a raw stack trace. On-brand, not jarring.
2. **A way forward** — link to home, primary sections, and (if the site has it) search. Offer the primary CTA where it fits.
3. **Keep chrome** — header, footer, and **language switcher** stay, so the user isn't stranded.
4. **Correct HTTP status** — the server must return a real **404** (not 200), so it isn't indexed as a valid page. Configure per stack (Next.js `not-found`, Astro `404.astro`, host rewrite for plain HTML).

### 500 / error page
- Reassuring, non-technical copy; a retry/home link; never leak internals. Return a real **500** status.

### Empty states (first-use / no-results / no-data)
When a list, search, or feed has nothing to show, design the empty view deliberately:
- **Say why it's empty** and **what to do next** (a primary action), not just "no results".
- Distinguish **first-use** ("you haven't added anything yet" → add CTA) from **no-results** ("nothing matched 'X'" → clear/adjust the query) from **error** ("couldn't load" → retry).

### Loading states
- Use **skeletons** that match the final layout (reserve the space → avoids CLS, see `performance.md`) rather than a bare spinner where possible.
- Show loading only after a short delay so fast loads don't flash; keep spinners/skeletons **`prefers-reduced-motion`-safe** (`frontend-design`).
- Disable submit buttons while in-flight (see `forms-conversion.md`).

### Offline (only if it's a PWA)
- A minimal offline fallback page if the site is installable/service-worker-backed (`responsive-mobile.md`).

---

## Choosing between archetypes

- Paid campaign / one offer → **Landing page**.
- "I don't know where to send people" → **Homepage**.
- One thing to sell, considered decision → **Product page**.
- Education/SEO/authority → **Content page**.
- Many docs → **Docs site**.

When the brief blends two (e.g., "homepage that also sells the flagship product"), lead with the homepage skeleton and embed a strong product block — do not try to be both fully.
