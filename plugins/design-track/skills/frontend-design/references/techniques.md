# Distinctive Frontend Techniques (four-vector toolkit)

Concrete patterns for executing the aesthetic philosophy in `../SKILL.md`. Four vectors: **typography, color/theme, motion, backgrounds.**

> **Read this first — how to use the examples below.**
> Every font name, theme, and snippet here is an **illustrative starting point, never a default.** The parent skill's core rule is *avoid distributional convergence* — so:
> - **Do NOT ship the same fonts/themes across projects.** Rotate. If the last site was dark cyberpunk, the next should not be.
> - **Never use the fonts the parent skill forbids** as your pick: Inter, Roboto, Arial, system fonts — **and Space Grotesk** (the skill explicitly calls it out as an over-converged choice). They appear *only* in "avoid" lists here.
> - **Obey the project baselines** (these override any snippet): CSS **logical properties** so RTL and LTR both hold, **mobile-first** with `100svh/dvh` (never `100vh`) and `viewport-fit=cover`, real fonts for the site's own scripts. The detail is in the **`page-builder`** skill's
>   `i18n-rtl.md` and `responsive-mobile.md` — that skill is in another plugin
>   (`web-track`), so ask for it by name rather than by path: no variable can address
>   another plugin's root, and `web-track` may not be installed at all.

## Core principles

- **Avoid distributional convergence**: reject the safe defaults; make bold, cohesive decisions.
- **Think in systems**: drive everything from CSS variables / design tokens, coordinated across all four vectors — not isolated tweaks.

---

## 1. Typography — use extremes

### Weight strategy
- Go to extremes: **100–200 (thin) vs 800–900 (black)**, not safe 400 vs 600.
- Build hierarchy through **weight contrast**, not size alone.
- Pairings: headers 900 / body 200; or headers 100 (elegant) / body 500.

### Font pairing (rotate — these are examples, not a menu to default to)

Pick distinctive faces and vary them per project. Some non-generic directions (all on Google Fonts):

```css
/* Editorial serif display + clean body */
--font-display: 'Fraunces', serif;          /* or Playfair Display, Libre Caslon Display */
--font-body:    'Newsreader', serif;          /* or Source Sans 3 */

/* Expressive grotesque display + neutral body (NOT Inter/Space Grotesk) */
--font-display: 'Clash Display', sans-serif;  /* or Unbounded, Sora, Archivo */
--font-body:    'Hanken Grotesk', sans-serif; /* or Schibsted Grotesk, General Sans */

/* Condensed + wide contrast */
--font-display: 'Anton', sans-serif;          /* or Oswald */
--font-body:    'DM Sans', sans-serif;

/* Variable-font extremes (one family, full weight range) */
--font-main:    'Recursive', sans-serif;      /* use weights 300–1000 */
--font-mono:    'JetBrains Mono', monospace;  /* or IBM Plex Mono, Space Mono */
```

### Non-Latin / RTL typography (required when the site's script is not Latin)

Latin display faces above have **no Hebrew or Arabic glyphs** — for those scripts choose a real cut of that script, and set fonts per script. Hebrew, as the worked example:

```css
/* Hebrew pairings (Google Fonts) */
/* Editorial:  Frank Ruhl Libre (display) + Heebo / Assistant (body) */
/* Modern:     Rubik / Suez One (display) + Assistant / Noto Sans Hebrew (body) */
/* Character:  Secular One, Karantina, Bellefair, Suez One (display accents) */

:root { --font-display-he: 'Frank Ruhl Libre', serif; --font-body-he: 'Assistant', sans-serif; }

:lang(he), [dir="rtl"] { font-family: var(--font-body-he); }
:lang(he) h1, [dir="rtl"] h1 { font-family: var(--font-display-he); }
```
- Hebrew needs **more line-height** than Latin at the same size; tune per script.
- If the content uses **nikud**, verify the chosen face renders it correctly at real sizes.

### Implementation pattern

```css
:root {
  --weight-thin: 100; --weight-light: 200; --weight-bold: 800; --weight-black: 900;
}
h1, h2, h3 {
  font-family: var(--font-display);
  font-weight: var(--weight-black);
  letter-spacing: -0.03em;   /* tight tracking for heavy weights */
  text-align: start;         /* logical, not "left" */
}
body, p {
  font-family: var(--font-body);
  font-weight: var(--weight-light);
  letter-spacing: 0.01em;
}
```

---

## 2. Color & theme — commit to cohesion

- **Draw from a cultural reference**: a film, art movement, IDE theme, landscape.
- Drive with CSS variables; dominant color + sharp accents beat timid, even palettes.
- **Avoid**: safe blue/purple gradients, low-contrast pastels.
- **Always meet WCAG AA contrast** (4.5:1 body, 3:1 large) — bold ≠ illegible.

```css
/* Theme: Cyberpunk */
:root { --bg-primary:#0a0e27; --bg-secondary:#1a1f3a; --accent-1:#ff2e97; --accent-2:#00d9ff; --accent-3:#ffd700; --text-primary:#e4f1ff; --text-secondary:#8b9dc3; }

/* Theme: Brutalist (raw concrete) */
:root { --bg-primary:#f5f5f0; --bg-secondary:#fff; --accent-1:#ff0000; --accent-2:#000; --text-primary:#1a1a1a; --border:3px solid #000; }

/* Theme: Vaporwave */
:root { --bg-primary:#1a0033; --bg-secondary:#2d1b4e; --accent-1:#ff71ce; --accent-2:#01cdfe; --accent-3:#b967ff; --accent-4:#05ffa1; --text-primary:#fffb96; }

/* Theme: Nordic */
:root { --bg-primary:#2e3440; --bg-secondary:#3b4252; --accent-1:#88c0d0; --accent-2:#bf616a; --accent-3:#a3be8c; --text-primary:#eceff4; --text-secondary:#d8dee9; }
```

These four are **examples to spark a direction**, not the only options — invent one true to the brief (see `DESIGN.md`).

```css
body       { background: var(--bg-primary); color: var(--text-primary); }
.card      { background: var(--bg-secondary); border: 1px solid var(--accent-1); }
.cta-button{ background: var(--accent-1); color: var(--bg-primary); }
.highlight { color: var(--accent-2); }
```

---

## 3. Motion — orchestrated page load

- Prioritize **page-load choreography** (staggered reveals) over scattered micro-interactions.
- One well-timed entrance sequence creates more delight than many random hovers.
- **Always honor `prefers-reduced-motion`.**

```css
.fade-in { opacity: 0; animation: fadeInUp 0.8s cubic-bezier(0.16,1,0.3,1) forwards; }
.stagger-1{animation-delay:.1s} .stagger-2{animation-delay:.2s} .stagger-3{animation-delay:.3s}
.stagger-4{animation-delay:.4s} .stagger-5{animation-delay:.5s}

@keyframes fadeInUp { from { opacity:0; transform: translateY(30px);} to { opacity:1; transform: translateY(0);} }
@keyframes scaleIn  { from { opacity:0; transform: scale(.9);}      to { opacity:1; transform: scale(1);} }

@media (prefers-reduced-motion: reduce) {
  .fade-in { animation: none; opacity: 1; }
}
```

**RTL note:** vertical/scale entrances (`translateY`, `scale`) are direction-safe. For *horizontal* slides, flip the direction in RTL so motion reads naturally:

```css
@keyframes slideInStart { from { opacity:0; transform: translateX(-40px);} to { opacity:1; transform: translateX(0);} }
[dir="rtl"] .slide-in    { animation-name: slideInStartRTL; }
@keyframes slideInStartRTL { from { opacity:0; transform: translateX(40px);} to { opacity:1; transform: translateX(0);} }
```

### React (Motion / Framer Motion)

```jsx
const container = { hidden:{opacity:0}, show:{opacity:1, transition:{staggerChildren:0.1}} };
const item      = { hidden:{opacity:0, y:20}, show:{opacity:1, y:0} };

<motion.div variants={container} initial="hidden" animate="show">
  <motion.h1 variants={item}>Title</motion.h1>
  <motion.p  variants={item}>Subtitle</motion.p>
  <motion.button variants={item}>CTA</motion.button>
</motion.div>
```

---

## 4. Backgrounds — atmospheric depth

- Layer gradients/patterns instead of flat fills; build depth with overlays; add subtle noise/grain.

```css
/* Radial, multi-stop */
.gradient-bg-1 { background: radial-gradient(circle at 20% 50%, rgba(255,46,151,.3) 0%, rgba(0,217,255,.2) 50%, rgba(10,14,39,1) 100%); }

/* Mesh (layered radials) */
.gradient-bg-mesh {
  background:
    radial-gradient(at 0% 0%,   rgba(255,113,206,.4) 0, transparent 50%),
    radial-gradient(at 100% 0%, rgba(1,205,254,.4)  0, transparent 50%),
    radial-gradient(at 100% 100%,rgba(185,103,255,.4)0, transparent 50%),
    radial-gradient(at 0% 100%, rgba(5,255,161,.4)  0, transparent 50%),
    #1a0033;
}

/* Noise overlay */
.textured-bg { position: relative; background: var(--bg-primary); }
.textured-bg::before {
  content:''; position:absolute; inset:0; opacity:.05; mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* Grid pattern */
.grid-bg {
  background-image:
    linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px);
  background-size: 50px 50px;
}
```

---

## Workflow: building a distinctive interface

1. **Choose an aesthetic reference** — name it ("Nordic minimalism", "90s brutalism", "retro-futurism"). Vary it from your last project.
2. **Set design tokens** (typography, color, motion, spacing) as CSS variables.
3. **Apply all four vectors** together in the hero, then carry the system through.
4. **Run the AI-slop checklist** below.

```css
:root {
  /* Typography — pick distinctive faces; NOT Inter/Roboto/Space Grotesk */
  --font-display: /* chosen display */;  --font-body: /* chosen body */;
  --weight-thin:100; --weight-black:900;
  /* Color — from the chosen theme */
  --bg-primary: ; --bg-secondary: ; --accent-1: ; --accent-2: ; --text-primary: ;
  /* Motion */
  --ease-out: cubic-bezier(0.16,1,0.3,1); --duration-base:0.6s;
  /* Spacing */
  --space-sm:1rem; --space-md:2rem; --space-lg:4rem; --space-xl:8rem;
}
```

---

## AI-slop checklist

❌ Avoid:
- Inter, Roboto, **Space Grotesk**, or system fonts as the primary face
- Weights 400/500/600 only (too safe)
- Purple/blue gradient backgrounds
- No page-load choreography
- Flat white/gray backgrounds; low-contrast pastels
- The same theme/fonts as your previous project (convergence)

✅ Aim for:
- A distinctive, project-specific font pairing (with a real **Hebrew** cut when Hebrew-first)
- Extreme weight contrast (100–200 vs 800–900)
- A cohesive theme with a clear cultural reference
- An orchestrated entrance sequence (reduced-motion safe)
- Layered/textured backgrounds
- A bold, memorable identity — different every time

---

## Quick-start template (RTL + mobile-first + baseline-compliant)

A correct starting shell — Hebrew/RTL, `100svh`, `viewport-fit=cover`, logical properties, reduced-motion. Swap the *example* fonts/theme for your own (these obey the rules above but should still be varied per project).

```html
<!DOCTYPE html>
<html lang="<lang>" dir="<ltr or rtl>">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#0a0e27">
  <!-- Real Hebrew faces + a Latin pairing for mixed content -->
  <link href="https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@300;900&family=Assistant:wght@200;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --font-display: 'Frank Ruhl Libre', serif;
      --font-body:    'Assistant', sans-serif;
      --weight-light: 200; --weight-bold: 600; --weight-black: 900;
      --bg-primary:#0a0e27; --accent-1:#ff2e97; --text-primary:#e4f1ff;
      --ease: cubic-bezier(0.16,1,0.3,1);
    }
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
      font-family: var(--font-body); font-weight: var(--weight-light);
      background: var(--bg-primary); color: var(--text-primary);
      min-height: 100svh;                     /* not 100vh — avoids iOS URL-bar jump */
      display:flex; align-items:center; justify-content:center;
      padding-inline: max(1.5rem, env(safe-area-inset-inline)); /* logical + safe area */
      text-align: start;
    }
    body::before { content:''; position:fixed; inset:0; z-index:-1;
      background: radial-gradient(circle at 20% 50%, rgba(255,46,151,.2) 0%, rgba(0,217,255,.1) 50%, transparent 100%); }
    h1 { font-family: var(--font-display); font-weight: var(--weight-black);
         font-size: clamp(2rem, 8vw, 5rem); letter-spacing:-0.02em; margin-block-end:1rem; }
    p  { font-size: clamp(1rem, 3vw, 1.25rem); margin-block-end:2rem; opacity:.9; }
    .cta { background: var(--accent-1); color: var(--bg-primary);
           font-family: var(--font-display); font-weight: var(--weight-bold);
           padding: 1rem 2rem; border:none; border-radius:.5rem; font-size:1.125rem;
           min-height:48px; cursor:pointer; transition: transform .2s var(--ease); }
    .cta:hover { transform: translateY(-2px); }
    .fade-in { opacity:0; animation: fadeInUp .8s var(--ease) forwards; }
    .stagger-1{animation-delay:.1s} .stagger-2{animation-delay:.2s} .stagger-3{animation-delay:.3s}
    @keyframes fadeInUp { from{opacity:0; transform:translateY(30px);} to{opacity:1; transform:translateY(0);} }
    @media (prefers-reduced-motion: reduce) { .fade-in{ animation:none; opacity:1; } }
  </style>
</head>
<body>
  <main>
    <h1 class="fade-in stagger-1">עיצוב ייחודי</h1>
    <p  class="fade-in stagger-2">טיפוגרפיה נועזת, צבע מגובש, מושן מתוזמן.</p>
    <button class="cta fade-in stagger-3">בואו נתחיל</button>
  </main>
</body>
</html>
```

## Examples by use case (typography / color / motion / background)

- **Landing page** — display 900 / body 200 · bold themed palette · staggered hero reveal · mesh gradient + noise.
- **Dashboard** — mono for data, 800 headers · dark + 2–3 status accents · slide-in panels, fade-in cards · subtle grid + dark gradient.
- **Marketing site** — serif display + sans body · high-contrast or vibrant · scroll-triggered reveals · bold gradients + geometric overlays.
- **Portfolio** — variable font 300–900 · minimal + one bold accent · cards stagger on load · radial gradient + grain.

## Implementation tips

1. **Always load the chosen fonts** (Google Fonts / self-hosted) — never assume system fonts; for Hebrew, load a face with a real Hebrew cut.
2. **Drive everything from CSS custom properties** so theming stays systematic.
3. **Reduced-motion**: always provide the `prefers-reduced-motion` fallback.
4. **Light/dark variants** from the same token system.
5. **Document the aesthetic reference** in `DESIGN.md` so it stays consistent and isn't reused verbatim next project.
