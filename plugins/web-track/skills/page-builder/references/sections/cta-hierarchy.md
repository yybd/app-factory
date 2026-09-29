# CTA Hierarchy

A page has **one primary action**. Everything else is subordinate. The job of CTA hierarchy is to make that one action obvious and to repeat it exactly where the reader is ready to take it.

## The rule of one

- **One primary CTA**, visually dominant, identical wording everywhere it repeats.
- **Secondary CTAs** are clearly weaker (ghost/outline button, text link) and never compete for the same eye-weight.
- If two actions feel equally important, the page hasn't decided its job. Force the ranking.

## Writing the CTA

- Start with a verb tied to the outcome: "Start free trial", "Get the guide", "Start now", "Watch the demo".
- Avoid friction words ("Submit", "Register") when an outcome word fits ("Get access").
- Set expectation: if it opens a form, say so; if it's free, say so. Reduce the "what happens if I click" doubt.
- First-person can lift conversions ("Start *my* free trial") — test per project.

## Placement (where to repeat the primary CTA)

Repeat the primary CTA at each natural **decision point** — a spot where the reader has just been given a fresh reason to act:

1. **Hero** — the first, always-visible CTA.
2. **After the core value / "how it works"** — once they understand the offer.
3. **After proof** — right when conviction peaks.
4. **Final CTA band** — restated promise + risk reverser, distractions removed.
5. **Sticky element (optional)** — persistent header button or mobile bottom bar for long pages.

Do not sprinkle CTAs randomly between these — repetition without a reason becomes noise.

## Visual weight (hand specifics to frontend-design)

- Primary: solid fill, highest-contrast accent, largest tap target.
- Secondary: outline or text; muted.
- Tertiary (nav, footer links): plain text.
- Maintain a clear weight gap between tiers so the hierarchy reads at a glance.

## Accessibility & ergonomics

- Tap target ≥ 44×44px; generous hit area on mobile.
- Real `<button>`/`<a>`, focus-visible state, descriptive accessible name (not "click here").
- Don't rely on color alone to signal the primary action.
- Sticky CTAs must not cover content or trap focus.

## Anti-patterns

- Multiple equal-weight buttons in the hero ("Sign up" + "Learn more" + "Contact" all solid).
- The same CTA stacked twice with no content between.
- A primary CTA that scrolls to another CTA instead of doing the thing.
- Burying the only CTA below the fold on a landing page.

## i18n / RTL reminders

- CTA labels expand in translation — size buttons to content, never to a fixed width that clips longer locales.
- In RTL, the primary CTA aligns to the reading-start (right) side; arrows/chevrons flip direction (see `../i18n-rtl.md`).
- Keep the verb-first pattern across languages, but localize idioms — a literal translation of "Get started" can read oddly.
