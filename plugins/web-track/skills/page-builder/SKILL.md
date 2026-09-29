---
name: page-builder
description: >-
  Plan the structure, section order, and conversion architecture of a web page or site
  before any visual design happens. Use when the user asks to "build a landing page",
  "what sections should this page have", "structure a homepage", "plan a marketing
  site", "lay out a product page", or when starting any new page and the information
  architecture is not yet decided ("תבנה דף נחיתה", "מה צריך להיות בדף"). Produces a
  section-by-section blueprint, hero pattern, trust-signal placement, and CTA hierarchy
  — category-aware and i18n/RTL-aware. Pairs with the frontend-design skill (which
  handles aesthetics) and web-design-guidelines (which audits the result). It decides
  structure and content architecture; it does NOT do the visual design (frontend-design)
  or the accessibility audit (web-design-guidelines).
---

# Page Builder

This skill decides **what goes on the page and in what order** — the skeleton — before the `frontend-design` skill decides how it looks. Structure first, aesthetics second, audit last.

Do not jump to writing markup. First produce a blueprint the user can react to, then build.

**Before starting, read `PRODUCT.md`** (audience, voice, the single goal, and which proof the audience needs) — it is the contract this skill builds against. (`DESIGN.md` is read later, when handing off to `frontend-design`.)

## Prerequisites

- **Tools:** none beyond Claude Code.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** not used; reads the site repo's own `PRODUCT.md` (and
  `DESIGN.md` at hand-off).
- **Other tracks:** `frontend-design` (design-track) takes the blueprint;
  `copy-edit` (shared-track) edits the claims the page carries;
  `content-site-structure` (web-track) scaffolds a multilingual content tree — on
  request only, and this skill never needs it to plan a page.

## When this skill runs

- A new page or site is being created and the section structure is not yet agreed.
- The user describes a goal ("get signups", "explain the rules", "sell the course") but not a layout.
- An existing page converts poorly or feels unstructured and needs re-architecting.

If the page structure is already fixed and the request is purely visual, skip to `frontend-design`.

## The blueprint process

1. **Identify the page archetype.** Landing page, homepage, product/marketing page, content/article page, docs, contact, pricing. Each has a proven section order — see `references/page-archetypes.md`. Do not invent a structure when a known archetype fits.
2. **Define the single conversion goal.** Every page has exactly one primary action (one job). Secondary actions exist but never compete visually with the primary. If a stakeholder lists three "primary" goals, push back and rank them.
3. **Choose the hero pattern.** The hero must communicate *what this is, who it's for, and the one action* within ~5 seconds. Pick a pattern from `references/sections/hero-patterns.md` that matches the archetype and goal.
4. **Place trust signals.** Decide which proof elements (social proof, authority, numbers, guarantees) the audience needs and *where* in the scroll they reduce the most doubt. See `references/sections/trust-signals.md`.
5. **Set the CTA hierarchy.** One primary CTA, repeated at natural decision points; clearly subordinate secondary CTAs. See `references/sections/cta-hierarchy.md`.
6. **Layer in i18n + RTL from the start.** Section structure, text length, and directionality are decided now, not retrofitted. See `references/i18n-rtl.md`. This is a baseline requirement, not an add-on.
7. **Design mobile-first.** Decide how each section reflows on a phone before the desktop layout — the phone is the primary design, not an afterthought. Verify on real iPhone and Android viewports. See `references/responsive-mobile.md`. This is a baseline requirement, not an add-on.
8. **Keep content and strings out of the markup.** Prose the reader reads, and short UI strings the interface shows, are both authored outside the templates and injected — never typed into the markup, and never mixed with each other. Decide the content slots now. *How* they are stored is the project's own decision: for a multilingual content site there is a scaffold for it in the `content-site-structure` skill, which runs only when asked for; an existing site's arrangement wins over any convention.
9. **Plan SEO & share metadata.** Per-page title/description, canonical, `hreflang`, Open Graph/Twitter cards (the WhatsApp/Facebook share preview), JSON-LD, sitemap/robots, and the favicon/manifest set. Decide these now so they ride the same content and locale map. See `references/seo-metadata.md`. Baseline, not an add-on.
10. **If the goal is a form, plan its mechanics.** When the primary action is a sign-up/lead/contact submission: decide the submission destination, validation, spam defense, the four states (idle/submitting/success/error), and the privacy obligations that PII triggers (consent, privacy policy, minimization). See `references/forms-conversion.md`.
11. **Set the performance & font budget.** Concrete Core Web Vitals targets and — for Hebrew-first sites especially — the font-loading strategy (self-host, subset incl. nikud, `font-display`, preload). See `references/performance.md`. Baseline, not an add-on.
12. **Run the pre-delivery checklist** before handing off. See `references/checklists/pre-delivery.md`.

## Output format

Deliver the blueprint as an ordered list of sections, each with: purpose (one line), key content, and the action/proof it carries. Example shape:

```
1. Hero — [pattern]. Promise + primary CTA. Subhead names the audience.
2. Trust strip — logos / stats. Reduces "is this legit" doubt immediately after the promise.
3. Problem → solution — frames the pain, then the offer.
4. ...
N. Footer — secondary nav, legal, language switcher.
```

Confirm the blueprint with the user (or proceed if they asked you to just build), then move to `frontend-design` for the visual layer.

## Principles

- **One page, one job.** Clarity of a single goal beats a buffet of options.
- **Earn the scroll.** Each section must give a reason to reach the next. Front-load value.
- **Proof near claims.** Place trust signals adjacent to the claim they support, not all dumped in one band.
- **Decision points get CTAs.** Repeat the primary CTA wherever the reader has just been given a reason to act.
- **Structure is language-agnostic, copy is not.** Design sections to survive 30–40% text expansion and full RTL mirroring.
- **Phone-first, not phone-also.** Most traffic is mobile. Every section must work at 320px and within iPhone/Android safe areas before the desktop layout is considered done.
- **Content lives outside the code.** Prose, UI strings, records and media are each authored in their own place and injected. Editors and translators never touch markup — and markup never appears inside a translation value.
- **Design the non-happy-path too.** A 404, error, empty, and loading state are part of the site, not an afterthought — on-brand, localized, never a dead end. See `references/page-archetypes.md` → System & state pages.

## References

Load these as needed — do not inline their full content unless relevant:

- `references/page-archetypes.md` — section blueprints per page type
- `references/sections/hero-patterns.md` — hero variants and selection
- `references/sections/trust-signals.md` — proof types and placement
- `references/sections/cta-hierarchy.md` — primary/secondary CTA strategy
- `references/i18n-rtl.md` — multi-language + RTL-first architecture
- `references/responsive-mobile.md` — mobile-first, responsive, iPhone + Android specifics
- `references/seo-metadata.md` — titles/meta, hreflang, Open Graph/share cards, JSON-LD, sitemap/robots, favicon/manifest
- `references/forms-conversion.md` — form submission, validation, spam defense, success/error states, privacy/PII
- `references/performance.md` — Core Web Vitals budgets + Hebrew-first font-loading strategy
- `references/checklists/pre-delivery.md` — final structural QA

## Boundaries

- **Structure before aesthetics.** What the page contains and in what order is
  decided here; how it looks is `frontend-design`'s, and the compliance audit of the
  result is `web-design-guidelines`'.
- **It does not write the product's claims.** Those come from the app's profile or
  the owner, and run through `copy-edit`.
- **It does not scaffold a content tree.** Where prose, records and media are stored
  for a multilingual content site is `content-site-structure`'s, and that skill runs
  only when the user asks for it by name — never as a side effect of planning a page.
