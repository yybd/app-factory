---
name: apple-bug-flow-review
description: >-
  Find real bugs in an Apple app and audit its user journeys end to end — static scan,
  build-time diagnostics, runtime sanitizers, then a flow-by-flow walk looking for dead
  ends, lost state and silent failures. Use when the user asks for a bug hunt, a QA
  pass, a code health check, a crash investigation, or a review before submitting ("בדוק
  באגים", "תעשה QA"), and after a large change when nothing obvious is broken. It
  reports with severity and evidence, and fixes only what the user approves. It does NOT
  review visual design (apple-hig-design-review), App Review policy compliance
  (app-store-review-compliance), or the web layer of a Capacitor app
  (capacitor-bug-flow-review).
---

# Apple Bug & User-Flow Review (iOS + macOS)

This skill answers one question: **"Is the app actually correct, and does every
user journey work?"** — before the user ships it. It hunts for *defects*: logic
bugs, fragile code, and places where the user flow breaks (crashes, dead-ends,
data loss, broken states). It is the QA pass, not the design pass and not the
compliance pass.

Be a sharp QA engineer, not a style linter. A finding is only worth reporting if
it can actually hurt a user — a crash, wrong result, lost data, a flow the user
can't complete, a leak that degrades the app over time. For each finding, give a
**concrete repro** (or the exact code path) and a **fix**, and rank by user
impact. Call out what's already solid — a credible review isn't all red.

**Language**: Write all conversation, findings, and the report in the
**`conversational language`** set in the hub `DATA.md`
(`$APP_HUB/DATA.md`) — fall back to the language the
user writes in if it's unset (e.g. a standalone project with no hub). Write all
code, identifiers, test names, and shell commands in **English**.

The bug knowledge lives in [references/bug-catalog.md](references/bug-catalog.md)
(what to look for, how to detect it, how to fix it). The flow-audit method and
state matrix live in [references/flow-audit.md](references/flow-audit.md). How to
collect runtime signals (analyzer, sanitizers, SwiftUI runtime warnings,
Instruments) lives in
[references/runtime-diagnostics.md](references/runtime-diagnostics.md). Read each
when you reach the phase that needs it — not all up front.

## Prerequisites

- **Tools:** Xcode (`xcodebuild`, `xcrun simctl`) for `scripts/run_diagnostics.sh`;
  `scripts/scan_bugs.py` is stdlib Python 3.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — only the conversational-language default in
  `DATA.md`; a standalone project falls back to the language the user writes in.
- **Other tracks:** `security-review` (Claude Code's built-in skill, not a track) for
  vulnerabilities.

## Boundaries
**In scope** — three pillars:

- **A · Logic / correctness bugs** — unsafe optionals (`!`, `try!`, `as!`, IUO),
  state-management mistakes (`@StateObject` vs `@ObservedObject`, stale/derived
  state, duplicate source of truth), concurrency & data races (`@MainActor`
  violations, off-main UI, `Sendable`, completion handlers called twice/never),
  memory (retain cycles, `deinit` never called), swallowed errors, edge cases
  (empty/nil/huge input, off-by-one, divide-by-zero, date/timezone/locale,
  emoji/RTL), data integrity & **data loss** (persistence failures, crash on
  terminate, `Codable` failures).
- **B · Code robustness** — leaked observers/KVO/timers/Combine cancellables,
  lifecycle misuse, main-thread-only APIs called off-main, deprecated APIs,
  networking without timeout/retry/offline handling, debug leftovers
  (`print`/`NSLog`/test data/dead code), `TODO`/`FIXME`/`HACK`, compiler
  warnings.
- **C · User-flow / functional QA** — for each journey: does it complete? Are
  the four states handled (loading / empty / error / success) plus **offline**
  and **permission-denied**? Dead-end navigation, broken back/dismiss, lost
  place after backgrounding, deep links, **unsaved-data loss**, destructive
  actions without confirm/undo, interruptions (call, low-memory, rotation,
  window resize / multi-window / Stage Manager), main-thread hangs.

**Out of scope (defer to the owner skill):**

- Apple **Review-Guideline** compliance (privacy strings, IAP rules, demo mode,
  entitlements) → `app-store-review-compliance`.
- **Design / aesthetics** and deep accessibility polish (typography, spacing,
  Dark Mode look, VoiceOver labels) → `apple-hig-design-review`. Here, only flag
  UX that *blocks a flow* (e.g. a control the user literally can't reach/tap).
- **Translation** completeness / RTL correctness → `localization-i18n`. Here,
  only flag i18n that *breaks a journey*.
- **Security** vulnerabilities (injection, secrets, insecure storage/transport)
  → the `security-review` skill. Flag the obvious, defer the audit.

If a finding clearly belongs to another skill, name the bug and point to that
skill rather than doing its job.

## Workflow

```
Phase 0  Discover   → platform, framework, schemes, and the map of user journeys
Phase 1  Static     → scan_bugs.py → confirm candidates by reading code
Phase 2  Build-time → xcodebuild analyze + strict-concurrency + warnings
Phase 3  Runtime    → build & run with sanitizers + Main Thread Checker + SwiftUI runtime warnings   (full mode)
Phase 4  Flow audit → walk each journey vs the state matrix; XCUITest smoke flows  (full mode)
Phase 5  Report     → severity-ranked findings + repro + fixes
Phase 6  Fix/tests  → offer to apply safe fixes and write regression tests
```

This skill is configured for **full depth**: it runs the static scan, the
analyzer, and the dynamic phases (3–4). If the project can't be built (no
buildable scheme, missing dependencies, build errors the user must fix first),
say so plainly and fall back to static + analyzer, listing what dynamic checks
were skipped — never silently drop coverage.

### Phase 0 — Discover the app and its journeys

1. Locate the `.xcodeproj`/`.xcworkspace`, list schemes (`xcodebuild -list`),
   and determine platform(s) (iOS, macOS, or both) and UI framework (SwiftUI,
   UIKit, AppKit, or mixed).
2. Build the **journey map** — the concrete user flows you will audit in Phase
   4: onboarding/first-run, the 2–5 core tasks, settings, and any destructive or
   data-entry flows. Derive them from the code (entry points, navigation, tab
   bars, menus); confirm with the user, since flow correctness is contextual.
3. **Reuse existing capture infrastructure.** If the project already has a demo
   mode / seeded data / `accessibilityIdentifier`s (often added by the
   `appstore-media` skill), reuse them for the Phase-4 smoke flows instead of
   re-inventing. Note what's missing.

Don't proceed past Phase 4 without an agreed journey list — the flow audit is
built on it.

### Phase 1 — Static scan

Run the heuristic scanner:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/apple-bug-flow-review/scripts/scan_bugs.py <project-root>
```

It prints JSON: counts and example sites for risky patterns (force-unwraps,
`try!`/`as!`, `self` captured strongly in escaping closures, UI mutated off the
main actor, empty `catch`, debug leftovers, `TODO`/`FIXME`, fixed-size
assumptions, etc.). **These are heuristics, not findings.** Open each candidate,
read the surrounding code, and decide whether it's a real bug. A `try!` on a
compile-time-constant regex is fine; a `try!` on user/network input is a crash.
Confirm before you report.

### Phase 2 — Build-time signals

Read [references/runtime-diagnostics.md](references/runtime-diagnostics.md) for
the exact invocations. Run the Clang/Swift static analyzer and collect compiler
warnings; if the project isn't already on Swift strict concurrency, a temporary
build with it surfaces real data-race risks. Triage the analyzer/warning output —
it catches null-derefs, leaks, and logic bugs the grep scanner can't.

### Phase 3 — Runtime signals (dynamic)

Build and run on a simulator (or locally for macOS) with the diagnostic tooling
from [references/runtime-diagnostics.md](references/runtime-diagnostics.md):
Address/Thread/UB sanitizers, **Main Thread Checker**, **Malloc Scribble**, and
SwiftUI **runtime issue** breakpoints (the "Modifying state during view update"
/ "Publishing changes from within view updates" purple warnings). Exercise the
journeys and capture the console. Runtime is where races, leaks, and
off-main-thread bugs actually surface — the static phases only suspect them.

`${CLAUDE_PLUGIN_ROOT}/skills/apple-bug-flow-review/scripts/run_diagnostics.sh`
wraps the common `xcodebuild` invocations and
collects warnings + runtime issues into one place; read the reference before
using it so you know what each flag does.

### Phase 4 — Flow audit

Read [references/flow-audit.md](references/flow-audit.md). Walk every journey
from Phase 0 against the **state matrix** (loading / empty / error / success /
offline / permission-denied) and the interruption checklist for the platform.
Two complementary ways to do it:

- **Scripted smoke flows** — adapt
  [assets/FlowSmokeTests.template.swift](assets/FlowSmokeTests.template.swift)
  into an XCUITest that drives each journey and asserts the user reaches the end
  without a crash or dead-end. Reuse the app's accessibility identifiers. This is
  repeatable and becomes the regression suite.
- **Hands-on driving** — for states a script can't easily force (deny a
  permission, kill the network, background mid-edit), drive the running app
  (simulator, or Claude Code's built-in `run` skill) and observe.

Record, for each journey, what worked and exactly where it broke.

### Phase 5 — The report (template below)

### Phase 6 — Offer fixes and regression tests

Some findings are safe, local fixes (add `[weak self]`, replace `try!` with a
handled `do/catch`, hop to `@MainActor` before a UI update, remove a debug
`print`). Offer to apply those. Anything that changes behavior, flow, or
architecture is the user's call — propose it, show the diff, let them decide. For
every confirmed bug, offer to write a regression test (XCTest for logic,
XCUITest for flows) so it can't silently come back. Never push fixes the user
didn't approve.

## Severity

Rank by user impact, not by ease of fix:

- **🔴 Critical** — crashes, **data loss / corruption**, a core journey that
  can't be completed, a data race that produces wrong results, an obvious
  security hole (then defer to `security-review`).
- **🟠 High** — a flow breaks in a common state (error/offline/permission-denied
  unhandled → blank or stuck screen), a retain cycle/leak that grows over a
  session, a main-thread hang the user will hit, a wrong result on a realistic
  input.
- **🟡 Medium** — an unhandled edge case on less-common input, a poor/destructive
  error experience (silent failure, no recovery), a missing confirm/undo on a
  reversible-but-painful action.
- **🟢 Low** — robustness/polish: debug leftovers, dead code, `TODO`/`FIXME`,
  minor defensive gaps with no current trigger.
- **✅ Strengths** — what's already solid (good error handling, no force-unwraps,
  states covered). Always include.

## Report structure

ALWAYS use this template (write it in the `conversational language` from the hub `DATA.md`):

```
# Bug & Flow Review — <app name>
Platform: <iOS / macOS / both>   framework: <SwiftUI / UIKit / AppKit / mixed>
Depth performed: static + analyzer + runtime + flow   (or whatever was actually done)
Inspected from: <code / analyzer / running app / XCUITest>

## Summary
<2–3 sentences: the overall impression, the single worst bug, and what is already strong.>

## ✅ Strengths
<bullets — concrete things that work correctly>

## 🔴 Critical
### <short title> — <category: logic / code / flow>
- Where: `path/file.swift:line` or <screen / journey name>
- What happens: <the description>
- Reproduction: <exact steps, or the code path that leads to it>
- Why it matters: <what the user loses / when it bites>
- Fix: <a specific change>
- Kind: safe fix (offered to apply) / behaviour change (your decision)

## 🟠 High
<same structure>

## 🟡 Medium
<same structure>

## 🟢 Low / robustness
<same structure>

## Flow matrix
<table: journey × state (loading/empty/error/success/offline/permission) → ✅ / ⚠️ / ❌ / n/a>

## Fixes that can be applied now
<the safe, local fixes; offer to apply them and add regression tests>
```

Write "none found" under a heading rather than dropping it, so the user sees the
area was checked. If a phase was skipped (e.g. the build failed), say so under
"Depth performed" and list what wasn't covered.

## Reference files

- [references/bug-catalog.md](references/bug-catalog.md) — curated catalog of
  Swift/SwiftUI/UIKit/AppKit/concurrency/memory/persistence bug patterns: what to
  look for, how to detect, how to fix, with platform tags.
- [references/flow-audit.md](references/flow-audit.md) — the user-journey audit
  method, the state matrix, and the iOS/macOS interruption checklists.
- [references/runtime-diagnostics.md](references/runtime-diagnostics.md) —
  analyzer, sanitizers, Main Thread Checker, SwiftUI runtime warnings, and
  Instruments: exact `xcodebuild` invocations and how to read the output.
- [references/refresh-from-web.md](references/refresh-from-web.md) — reconcile
  the catalog against current Apple docs / Swift Evolution when it goes stale.
- [scripts/scan_bugs.py](scripts/scan_bugs.py) — heuristic static bug-signal
  scanner; emits JSON. Stdlib only.
- [scripts/run_diagnostics.sh](scripts/run_diagnostics.sh) — wraps the
  analyzer/sanitizer `xcodebuild` invocations and collects the output.
- [assets/FlowSmokeTests.template.swift](assets/FlowSmokeTests.template.swift) —
  XCUITest skeleton for smoke-testing each user journey.
