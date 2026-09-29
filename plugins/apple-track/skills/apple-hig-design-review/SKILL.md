---
name: apple-hig-design-review
description: >-
  Review a macOS or iOS app's UI against Apple's Human Interface Guidelines (HIG) and
  produce prioritized, actionable design/UX/accessibility recommendations. Use this
  whenever the user wants a design review ("ביקורת עיצוב", "נראה כמו אפליקציית אפל"),
  asks if their UI "feels native" or follows Apple's conventions, mentions the Human
  Interface Guidelines or HIG, wants to improve accessibility (VoiceOver, Dynamic Type,
  contrast), check Dark Mode / layout / typography / spacing / navigation patterns, or
  polish an app before shipping. This is advisory design guidance — it complements (does
  NOT replace) App Store Review Guidelines compliance, which is a separate concern
  handled by the app-store-review-compliance skill.
---

# Apple HIG Design Review

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

Apple's Human Interface Guidelines describe what makes an app feel native, clear
and accessible on Apple platforms. Unlike the App Store *Review* Guidelines,
HIG conformance is rarely binary and rarely a rejection basis on its own — it's
a spectrum of quality. So this skill produces a **prioritized design review**
(what would most improve the experience), not a pass/fail verdict.

Be a thoughtful design reviewer, not a linter. Many HIG "rules" are defaults
with legitimate exceptions; a deliberate, well-executed choice that departs from
convention can be better than rote conformance. Explain the *why* behind each
recommendation (what the user gains) so the user can judge, and call out what's
already done well — a review that's all criticism is less useful and less
trusted.

The design knowledge lives in [references/hig-curated.md](references/hig-curated.md),
organized by topic with platform tags. Read it before reviewing.

## Prerequisites

- **Tools:** none beyond Claude Code; `scripts/scan_design.py` is stdlib Python 3.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — only the conversational-language default in `DATA.md`.
- **Other tracks:** none.

## Boundaries
In scope: layout & spacing, navigation & information architecture, typography &
Dynamic Type, color & Dark Mode & contrast, controls & touch/click targets,
accessibility (VoiceOver, labels, traits, reduced motion), platform conventions
(iOS vs macOS idioms), feedback & state (loading/empty/error), iconography, and
adaptivity (size classes, window resizing, safe areas).

Out of scope (handled elsewhere): App Store *Review* Guidelines compliance
(privacy strings, IAP rules, demo mode, entitlements) → use the
`app-store-review-compliance` skill. App Store metadata/screenshots.

## Workflow

### 1. Understand the app and its surfaces
Identify platform(s) (iOS/macOS/both), the UI framework (SwiftUI, UIKit,
AppKit, or mixed), and the main screens/flows. Ask the user what the app is for
and who uses it if it isn't obvious — good design review is contextual, and a
pro tool, a kids' game, and a glanceable utility have different "right answers".

If a running app or screenshots are available, look at them — design is visual
and the code only tells part of the story. If not, review from the code.

### 2. Gather detectable signals
Run the scanner for the mechanical heuristics (framework, accessibility
modifier coverage, hardcoded font sizes vs text styles, hardcoded colors vs
semantic colors, Dark Mode signals, fixed frames):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/apple-hig-design-review/scripts/scan_design.py <project-root>
```

It prints JSON. These are *heuristics*, not findings — e.g. a low ratio of
accessibility labels to interactive elements is a prompt to look, not proof of a
problem. Confirm by reading the code and (ideally) seeing the UI.

### 3. Review against the HIG topics
Read [references/hig-curated.md](references/hig-curated.md) and go topic by
topic. For each, judge how the app does and what would improve it most. Weight
accessibility highly — it's the area where code-level fixes have the clearest,
highest impact and where Apple's expectations are firmest (and it shades into
Review Guideline territory if egregious).

### 4. (Hybrid) Refresh against the live HIG when it matters
The curated reference has a `last-verified` date. If it's stale, the user wants
certainty, or the platform recently changed (new OS design language — e.g. a
new material/skin, new layout metrics), reconcile via
[references/refresh-from-web.md](references/refresh-from-web.md) and note any
drift.

### 5. Produce the prioritized review (template below)
### 6. Offer to apply the safe, mechanical fixes
Some recommendations are safe, local code changes (adding an
`.accessibilityLabel`, swapping a hardcoded font size for a text style, using a
semantic color). Offer to apply those. Anything that changes layout, flow, or
visual identity is a design decision — propose it, show the option, let the user
choose. Never silently restyle an app.

## Prioritization

Rank every recommendation by user impact, not by how easy it is to fix:
- **High** — meaningfully hurts usability or excludes users. Almost always
  accessibility (unlabeled controls, no Dynamic Type, fails contrast), broken
  adaptivity (clipped on small screens / not resizable on Mac), or a confusing
  navigation model.
- **Medium** — noticeably off-convention or inconsistent; erodes the "native"
  feel. Non-semantic colors that break Dark Mode, fixed type that ignores user
  text size, nonstandard controls where standard ones exist.
- **Low** — polish. Spacing/alignment nits, icon weight, minor copy.
- **Strengths** — what's already good. Always include this.

## Report structure

ALWAYS use this template:

```
# HIG Design Review — <app name>
Platform: <iOS / macOS / both>   UI framework: <SwiftUI / UIKit / AppKit / mixed>
HIG reference: curated digest (last-verified <date>)<, refreshed <date> if done>
Reviewed from: <code / screenshots / running app>

## Summary
<2-3 sentences: overall impression, the single highest-impact improvement, and what's done well.>

## ✅ Strengths
<bullets — concrete things the app does right>

## 🔴 High impact
### <topic> — <short title>
- Where: `path/file.swift:line` or <screen/flow name>
- Observation: <what you see>
- Why it matters: <what the user loses / who is excluded>
- Recommendation: <specific change>
- Effort: mechanical fix (offer to apply) / design change (needs your call)

## 🟠 Medium impact
<same shape>

## 🟡 Low impact / polish
<same shape>

## Mechanical fixes I can apply now
<list the safe local code changes; offer to do them>
```

Write "None found" under a heading rather than dropping it, so the user sees the
area was considered.

## Reference files
- [references/hig-curated.md](references/hig-curated.md) — curated HIG digest by
  topic, with platform tags and what-to-look-for.
- [references/refresh-from-web.md](references/refresh-from-web.md) — reconcile
  against the live HIG site.
- [scripts/scan_design.py](scripts/scan_design.py) — heuristic design-signal
  scanner; emits JSON.
