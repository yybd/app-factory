# Runtime Diagnostics — analyzer, sanitizers, runtime checkers

The static scan only *suspects* races, leaks, and off-main bugs. This is how you
*confirm* them, and how you surface bugs no grep can see. Read this before Phase
2–3. All commands assume you've identified the scheme and a destination from
`xcodebuild -list`.

> Pick a real scheme/destination. `<scheme>` and the simulator name below are
> placeholders — list them first:
> ```bash
> xcodebuild -list -project App.xcodeproj            # or -workspace App.xcworkspace
> xcrun simctl list devices available                # iOS destinations
> ```

## 1 · Compiler warnings (cheap, high-signal)

Warnings are real findings, not noise. Build and capture them:

```bash
xcodebuild build \
  -scheme <scheme> \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  -quiet 2>&1 | grep -E 'warning:|error:'
```

For macOS use `-destination 'platform=macOS'`. Pay attention to: deprecated-API
warnings, unused results on `@discardableResult`-less calls, unreachable code,
implicit `Sendable`/concurrency warnings, and "will never be executed".

## 2 · Strict concurrency (finds data races at compile time)

If the project isn't already on Swift 6 / complete concurrency checking, a
**temporary** build with it surfaces real shared-mutable-state races. Don't
commit the flag — it's a diagnostic lens:

```bash
xcodebuild build \
  -scheme <scheme> \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  SWIFT_STRICT_CONCURRENCY=complete \
  OTHER_SWIFT_FLAGS='-Xfrontend -warn-concurrency' \
  -quiet 2>&1 | grep -iE 'concurrency|sendable|actor|main actor|data race'
```

Each warning is a place where state crosses isolation boundaries unsafely — map
it to catalog **A4**. Note: a flood of warnings on a legacy codebase means
"migration needed", not "100 bugs" — triage to the ones touching shared mutable
state and UI.

## 3 · Clang / Swift static analyzer

Catches null-derefs, leaks, logic errors, dead stores — beyond text grep:

```bash
xcodebuild analyze \
  -scheme <scheme> \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  -quiet 2>&1 | grep -iE 'warning:|note:|analyze'
```

Triage each analyzer warning to a catalog category and confirm by reading the
site.

## 4 · Runtime sanitizers & checkers (the dynamic core)

Sanitizers instrument the running app and catch bugs *as they happen*. You can
enable them on the command line for a test run, or (for a hands-on run) in the
scheme's **Diagnostics** tab. Don't combine ASan + TSan in one run (mutually
exclusive); do two passes.

**Thread Sanitizer (TSan)** — data races, the highest-value dynamic check:

```bash
xcodebuild test \
  -scheme <scheme> \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  -enableThreadSanitizer YES \
  -only-testing:<UITestTarget>/DemoFlowSmokeTests 2>&1 | tee /tmp/tsan.log
grep -iE 'ThreadSanitizer|data race|race on' /tmp/tsan.log
```

**Address Sanitizer (ASan)** — memory corruption, use-after-free, overflow:

```bash
xcodebuild test -scheme <scheme> \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  -enableAddressSanitizer YES \
  -only-testing:<UITestTarget>/DemoFlowSmokeTests 2>&1 | tee /tmp/asan.log
```

**Undefined Behavior Sanitizer (UBSan)** — `-enableUndefinedBehaviorSanitizer YES`
(integer overflow, invalid casts, etc.).

**Main Thread Checker** — off-main UIKit/AppKit calls (catalog B4). On by default
when running from Xcode; for `xcodebuild test` it's available via the scheme.
When driving the app by hand, keep it on and watch the console for
`Main Thread Checker: UI API called on a background thread`.

**Malloc Scribble / Guard Malloc / Zombie Objects** — surface use-after-free and
released-object messaging; enable in the scheme's Diagnostics for a hands-on run.

## 5 · SwiftUI runtime issues (the purple warnings)

SwiftUI emits *runtime* warnings that never fail a build but signal real bugs:

- **"Modifying state during view update, this will cause undefined behavior."** —
  mutating `@State`/`@Published` inside `body`/a view update (catalog A2/A3).
- **"Publishing changes from within view updates is not allowed."** — a
  `@Published` set synchronously during a view update.
- **"Bound preference … tried to update multiple times per frame."**

Capture them by running the app (or the XCUITest flows) and watching the console.
In a hands-on Xcode run, "Issue Navigator → Runtime" lists them. Each maps to a
state-ownership bug — fix by moving the mutation out of the update cycle (e.g.
into `.task`/`.onChange`/an action, or `DispatchQueue.main.async` as a last
resort).

## 6 · Leaks (confirm retain cycles from catalog B1)

Two ways:

- **`deinit` log** — add a temporary `deinit { print("deinit \(Self.self)") }` to a
  suspected type, drive the flow that should free it, and confirm the log prints.
  No print = it leaked.
- **Instruments Leaks/Allocations** (deeper):
  ```bash
  xcodebuild build-for-testing -scheme <scheme> -destination '…'   # then:
  # open the app under Instruments → Leaks, or:
  xcrun xctrace record --template 'Leaks' --launch -- <path-to.app>
  ```
  Drive the journeys; a sawtooth that never drops, or flagged leaks, confirms
  B1/B2.

## 7 · Crash & console logs

While driving the app, collect the console — crashes, asserts, sanitizer hits,
Main Thread Checker, and SwiftUI runtime warnings all land there:

```bash
xcrun simctl spawn booted log stream --level debug \
  --predicate 'processImagePath CONTAINS "<AppName>"' &
```

After a crash, the `.crash`/`.ips` report is under
`~/Library/Logs/DiagnosticReports/` (device) or the simulator's container.

## Putting it together

`run_diagnostics.sh` wraps §1–§3 (build warnings, strict-concurrency
pass, analyzer) into one run and tees the output, so you can scan all the
build-time signal at once; the sanitizer/runtime passes (§4–§6) need a test
target or a hands-on run, so drive those per the Phase-3/4 plan. Always map each
machine-reported issue back to a catalog category and confirm it's real before it
becomes a finding.

## If the project won't build

If there's no buildable scheme, dependencies are missing, or the build errors out
on something the user must fix first: report that, do the static phases (1) and
the parts of (2)–(3) that don't need a green build, and **state clearly in the
report which dynamic checks were skipped**. Don't claim coverage you didn't run.
