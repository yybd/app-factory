---
name: frontend-design
description: >-
  Create distinctive, production-grade frontend interfaces with high design quality. Use
  this skill when the user asks to build web components, pages, artifacts, posters, or
  applications (examples include websites, landing pages, dashboards, React components,
  HTML/CSS layouts, or when styling or beautifying any web UI; "תעצב את הדף", "שפר את
  העיצוב"). Generates creative, polished code and UI design that avoids generic AI
  aesthetics. It does NOT decide a page's structure — `page-builder` does that first —
  and does NOT audit the result (`web-design-guidelines`).
license: Apache-2.0. Complete terms in LICENSE.txt; modifications in NOTICE.
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

**Carve-out — an existing `DESIGN.md` overrides this skill.** If the project has a committed `DESIGN.md` (brand spec with locked owner decisions), its rules win over every guideline below — including the font and color rules. Example: one project's spec locks a system-font stack (SF Pro, zero webfonts) and a monochrome palette; on that site those are the owner's deliberate choices, not "generic AI aesthetics", and this skill must execute *within* them. The bold-direction guidance below applies in full only when defining a new direction (no DESIGN.md yet, or the user asks to redefine it) — and whatever direction is chosen, record it back into `DESIGN.md`.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## Prerequisites

- **Tools:** none beyond Claude Code; the Motion library (`npm install motion`) only
  when a React project already has it.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** not used; the project's committed `DESIGN.md` is the one
  input it reads and writes back to.
- **Other tracks:** `page-builder` decides structure first and `web-design-guidelines`
  audits the result (both web-track).

**Content does not go into the markup you write.** Prose the reader reads, and the short
UI strings the interface shows, are authored outside the templates and injected — each
in its own place, and never mixed. Before writing markup, find where this project keeps
them (a content folder, a translation catalog, a CMS) and render from there. Typing a
paragraph or a button label straight into a component undoes it for every translator and
editor afterwards, and it is not recoverable by a later pass. If the project has no
arrangement yet, say so rather than inventing one — for a multilingual content site the
`content-site-structure` skill (web-track) scaffolds it, on request.

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics; unexpected, characterful font choices. Pair a distinctive display font with a refined body font.
- **Color & Theme**: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions. Use scroll-triggering and hover states that surprise.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density.
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, and grain overlays.

NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Remember: Claude is capable of extraordinary creative work. Don't hold back, show what can truly be created when thinking outside the box and committing fully to a distinctive vision.

## References

- `references/techniques.md` — concrete patterns for the four vectors (typography, color/theme, motion, backgrounds): example font pairings (incl. real Hebrew faces), themes, staggered-load animation, layered backgrounds, an AI-slop checklist, and a baseline-compliant (RTL + mobile-first) quick-start template. The fonts/themes there are **illustrative starting points, not defaults** — keep varying them and never use the forbidden faces (Inter, Roboto, Space Grotesk, system fonts) as your pick.

## Boundaries

- **Visual craft, not page structure.** What sections a page needs and in what order
  is `page-builder`'s, and it runs first. An accessibility and conventions audit of
  the result is `web-design-guidelines`'.
- **An existing `DESIGN.md` wins.** Where a project has committed brand decisions,
  this skill executes within them rather than proposing its own.
