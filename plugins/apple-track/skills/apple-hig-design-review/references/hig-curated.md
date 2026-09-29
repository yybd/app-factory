# Curated Human Interface Guidelines — review topics

last-verified: 2026-06-02
source: https://developer.apple.com/design/human-interface-guidelines/

A working digest of the HIG topics that matter most in a practical design
review, with what to look for in code/UI and why it matters. Platform tags:
`[iOS]`, `[macOS]`, `[both]`. These are defaults and heuristics — design has
context, so weigh them against what the app is and who uses it. Reconcile with
the live HIG via [refresh-from-web.md](refresh-from-web.md) when it may be stale.

## Table of contents
- [Accessibility](#accessibility) — usually the highest-impact area
- [Typography & Dynamic Type](#typography--dynamic-type)
- [Color, Dark Mode & contrast](#color-dark-mode--contrast)
- [Layout, spacing & adaptivity](#layout-spacing--adaptivity)
- [Navigation & information architecture](#navigation--information-architecture)
- [Controls & targets](#controls--targets)
- [Feedback & state](#feedback--state)
- [Iconography & imagery](#iconography--imagery)
- [Motion](#motion)
- [Platform conventions: iOS vs macOS](#platform-conventions-ios-vs-macos)

---

## Accessibility `[both]` — weight highest
Why: it's where code-level fixes have the clearest, largest impact, and where
Apple's expectations are firmest. Excludes real users when missing.
Look for:
- **Labels on non-text controls.** Icon-only buttons / tappable images need an
  accessible label. SwiftUI: `.accessibilityLabel("…")`; UIKit/AppKit:
  `accessibilityLabel`. A button whose content is only `Image(systemName:)`
  with no label reads as "button" to VoiceOver — unusable.
- **Traits & grouping.** Use `.accessibilityElement(children:)`, correct traits
  (button/header/selected). Decorative images hidden with
  `.accessibilityHidden(true)`.
- **Dynamic Type** (see typography) — text must scale.
- **Contrast** (see color) — meet WCAG-ish ratios; respect Increase Contrast.
- **Reduced Motion** — honor `accessibilityReduceMotion` /
  `UIAccessibility.isReduceMotionEnabled` for large animations.
- **VoiceOver order & focus** — logical reading order; move focus on context
  change. **Hit targets** — see controls.
Recommendation default: add labels/traits (mechanical, safe to apply); test one
pass with VoiceOver / Accessibility Inspector.

## Typography & Dynamic Type `[both]`
Why: hardcoded point sizes ignore the user's preferred text size and break
accessibility; semantic text styles adapt automatically and stay consistent.
Look for:
- SwiftUI: prefer `.font(.body/.headline/.title/…)` over
  `.font(.system(size: 13))`. Fixed sizes don't scale with Dynamic Type.
- UIKit: prefer `UIFont.preferredFont(forTextStyle:)` +
  `adjustsFontForContentSizeCategory = true` over
  `UIFont.systemFont(ofSize:)`.
- Custom fonts: scale them with `UIFontMetrics` / `@ScaledMetric`.
- Hierarchy: limited, consistent set of styles; don't invent many ad-hoc sizes.
Recommendation: swap fixed sizes for text styles (mostly mechanical). For a
dense pro/utility UI where fixed sizing is deliberate, note the tradeoff rather
than insisting.

## Color, Dark Mode & contrast `[both]`
Why: hardcoded RGB colors often look wrong in Dark Mode and can fail contrast;
semantic/system colors adapt to appearance, contrast and accessibility settings.
Look for:
- Prefer **semantic colors**: SwiftUI `Color.primary/.secondary`, system colors,
  asset-catalog colors with light/dark variants; UIKit `UIColor.label`,
  `.systemBackground`, etc. Flag literal `Color(red:…)`, `UIColor(red:…)`,
  raw `.white`/`.black` used for text/background.
- **Dark Mode**: is there any handling? Asset colors with appearances, or
  `@Environment(\.colorScheme)`. Pure hardcoded palette = likely broken in dark.
- **Don't encode meaning in color alone** (add icon/label) — colorblind users.
- **Contrast**: body text should clearly exceed background; check the lightest
  text on its background.
Recommendation: move to semantic/asset colors (mechanical where 1:1); verify in
both appearances.

## Layout, spacing & adaptivity `[both]`
Why: fixed sizes and absent safe-area handling cause clipping, overlap, and
content trapped under notches/toolbars; Apple UIs adapt to size, orientation,
text size, and (on Mac) window resizing.
Look for:
- **Safe areas**: respect them; don't push content under the Dynamic Island,
  home indicator, or title bar. Flag broad `.ignoresSafeArea()`.
- **Fixed frames**: many `.frame(width:height:)` with hard numbers hurt
  adaptivity; prefer flexible layouts, `minWidth`/`maxWidth`, spacers, Grid.
- **iOS adaptivity**: size classes; works on smallest target device and iPad if
  universal. **macOS**: window is resizable; sensible min size; content reflows.
- **Consistent spacing**: a small spacing scale (e.g. 4/8/12/16), aligned edges,
  standard margins — not arbitrary paddings everywhere.

## Navigation & information architecture `[both]`
Why: a predictable, platform-idiomatic structure lets users build a mental model
and never feel lost.
Look for:
- **iOS**: pick the right pattern — tab bar for peer sections, navigation stack
  for hierarchy, sheets/popovers for self-contained subtasks, not a maze of
  modals. Back behavior standard. Don't hide primary navigation.
- **macOS**: window/sidebar/toolbar model; menu-bar commands for actions;
  multiple windows where it fits. Don't force an iOS phone layout onto Mac.
- **Depth**: keep hierarchy shallow; common actions reachable quickly.
- **Titles**: clear screen titles; the user always knows where they are.

## Controls & targets `[both]`
Why: standard controls are familiar, accessible, and free; custom ones must earn
their keep and re-implement state/accessibility correctly.
Look for:
- Prefer system controls (`Button`, `Toggle`, `Picker`, `Stepper`, `Slider`)
  over hand-built equivalents unless there's a real reason.
- **Touch targets [iOS]**: ~44×44pt minimum. Flag tiny tap areas (small icon
  buttons with no padding/`contentShape`).
- **Click targets / pointer [macOS]**: adequate size; hover/cursor affordances
  where helpful; tooltips (`.help`) on icon-only controls.
- **State**: disabled/loading/selected states are visible and accessible.

## Feedback & state `[both]`
Why: real apps spend time empty, loading, or in error; designing only the
"happy full" state makes the app feel broken in the other states.
Look for:
- **Empty states**: a helpful message + next action, not a blank screen.
- **Loading**: progress indication for anything non-instant; avoid frozen UI.
- **Errors**: clear, human, actionable messages (not raw codes); recovery path.
- **Confirmation/undo** for destructive actions; success feedback.

## Iconography & imagery `[both]`
Why: SF Symbols give consistent, scalable, accessible icons that match the
system and Dynamic Type / weights for free.
Look for:
- Prefer **SF Symbols** (`Image(systemName:)`) with appropriate weight/scale and
  rendering mode; consistent visual weight across the icon set.
- App icon follows current template (no transparency/legacy shapes); provided at
  required sizes.
- Images have accessibility labels or are marked decorative.

## Motion `[both]`
Why: motion should clarify (where things come from / go), not distract; and must
respect Reduce Motion.
Look for: purposeful, short transitions tied to navigation/state; honor
`reduceMotion` for large/parallax/auto-playing animation; nothing that blocks
interaction.

## Platform conventions: iOS vs macOS `[both]`
Why: the biggest "this doesn't feel native" smell is an app that ports one
platform's idioms wholesale to the other.
Look for:
- **macOS**: menu-bar menus for commands; keyboard shortcuts; toolbar; resizable
  windows; pointer/hover; right-click context menus; Preferences/Settings
  window; respects "close vs quit". Menu-bar-only (`LSUIElement`) apps should
  still expose actions discoverably.
- **iOS**: touch-first spacing and targets; standard gestures; bottom-reachable
  primary actions; sheets/`presentationDetents` for subtasks.
- **Shared SwiftUI codebase**: good for reuse, but check each platform gets its
  idioms (e.g. `.commands`, `.toolbar` placement, `NavigationSplitView` on
  larger screens) rather than a lowest-common-denominator layout.
