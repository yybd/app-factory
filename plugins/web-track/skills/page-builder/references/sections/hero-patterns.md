# Hero Patterns

The hero answers three questions in ~5 seconds: **what is this, who is it for, what do I do next.** If a visitor can't answer all three, the hero failed regardless of how it looks.

## Required elements

- **Headline** — the promise or core value, in the reader's language. Outcome > feature > clever.
- **Subhead** — names the audience and/or qualifies the promise. One sentence.
- **Primary CTA** — one button, action verb, what happens next.
- **Visual or proof anchor** — product shot, illustration, or a trust element. Avoid generic stock.

Optional: secondary CTA (clearly subordinate), trust micro-signal (rating, "used by N"), supporting media.

## Patterns and when to use them

### 1. Centered statement
Single column, centered headline + subhead + CTA. Maximum focus, minimum distraction.
- **Use for:** landing pages, single-offer products, bold brand statements.
- **Watch:** needs strong typography to carry it (hand to `frontend-design`).

### 2. Split (text / visual)
Headline + CTA on one side, product visual on the other.
- **Use for:** product and SaaS pages where seeing the thing matters.
- **RTL note:** the text/visual sides mirror — design with logical sides, not "left/right" (see `../i18n-rtl.md`).

### 3. Hero with inline form
Headline + a short capture form directly in the hero (email, single field).
- **Use for:** lead-gen, waitlists, newsletters where the action *is* the form.
- **Watch:** keep to 1–2 fields; more belongs on a dedicated page.

### 4. Background-media hero
Full-bleed image/video behind overlaid text.
- **Use for:** emotive, brand-led, hospitality, events, mission-driven sites.
- **Watch:** contrast and text legibility (overlay scrim); performance budget for video; never autoplay sound.

### 5. Editorial / typographic hero
Oversized type as the visual itself; little or no imagery.
- **Use for:** content sites, agencies, statements where words are the brand. Strong fit for Hebrew display typography.

### 6. Interactive / product-demo hero
Live widget, animated preview, or scroll-driven reveal.
- **Use for:** tools where the "aha" is the interaction. Highest build cost — justify it.

## Selection guide

| Goal | Default pattern |
|------|-----------------|
| One offer, max conversion | Centered statement |
| Show the product | Split |
| Capture a lead now | Inline form |
| Evoke feeling / brand | Background-media or Editorial |
| Demonstrate a tool | Interactive |

## Anti-patterns

- Vague headline ("Welcome", "We do great things") that could belong to any site.
- Carousel/slider heroes — visitors rarely see slide 2+, and they hurt performance and a11y.
- Multiple competing CTAs of equal weight.
- Headline that describes the company instead of the visitor's outcome.
- Text over a busy image with no scrim — illegible, especially at small sizes.

## i18n / RTL reminders

- Hebrew/Arabic headlines run shorter character-wise but taller line-height; German/Finnish run ~35% longer. Design the hero box to flex, not to a fixed pixel width.
- Mirror the entire hero layout in RTL using logical properties; the CTA sits on the reading-start side.
- Pick a display font with a real Hebrew cut if the site is Hebrew-first (see `../i18n-rtl.md`).
