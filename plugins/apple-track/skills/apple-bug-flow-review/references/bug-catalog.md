# Bug Catalog — Swift / SwiftUI / UIKit / AppKit

Curated catalog of the bugs that actually bite macOS/iOS apps, organized by
category. Each entry: **what to look for**, **how to detect it**, **how to fix
it**. Platform tags: `[iOS]` `[macOS]` `[both]`. These are patterns to *check*,
not automatic findings — confirm each against the real code path.

> last-verified: 2026-06-17 · When stale or when a new OS/Swift version lands,
> reconcile via [refresh-from-web.md](refresh-from-web.md).

---

## A · Logic & correctness

### A1. Unsafe optionals & force operations `[both]`
- **Look for**: `!` force-unwrap, `try!`, `as!` downcast, implicitly-unwrapped
  optionals (`var x: Foo!`), force-access on collections (`array[i]`,
  `dict[key]!`), `URL(string:)!`, `Bundle.main.url(...)!`.
- **Detect**: scanner flags `force_unwrap`, `try_bang`, `as_bang`. Read each: is
  the value a compile-time constant (safe-ish) or runtime/user/network data
  (crash risk)?
- **Fix**: `guard let` / `if let` / `??` default / `do/catch`. For "can't
  happen" cases use `guard … else { assertionFailure(); return }` so debug
  catches it but release degrades gracefully — not `fatalError` on a path a user
  can reach.

### A2. SwiftUI state ownership `[both]`
- **Look for**: `@ObservedObject` on a property the view itself *creates* (it
  must be `@StateObject`, else the object is recreated on every re-render and its
  state is silently lost). `@State` holding a reference type. Source of truth
  duplicated into a local `@State` that drifts from the real model. Mutating
  `@State` inside `body`. Using `.id()` in a way that destroys/recreates state.
- **Detect**: grep `@ObservedObject var … = ` (assignment at declaration is the
  tell). Cross-check view lifetime.
- **Fix**: own it with `@StateObject` (pre-iOS 17) / `@State` + `@Observable`
  (iOS 17+); pass down with `@ObservedObject`/`@Bindable`/`@Binding`; keep a
  single source of truth.

### A3. Stale / derived state `[both]`
- **Look for**: a value computed once and cached but whose inputs change;
  `onAppear` that loads data once and never refreshes; two properties that must
  stay in sync but are updated independently; a `@Published` derived value
  updated by hand instead of computed.
- **Fix**: make derived values *computed*, not stored; recompute on input change;
  collapse to one source of truth.

### A4. Concurrency & data races `[both]`
- **Look for**: shared mutable state touched from multiple tasks/queues without
  isolation; UIKit/AppKit/SwiftUI updated off the main thread; `@MainActor`
  missing on a type that touches UI; `DispatchQueue.main.async` sprinkled to
  "fix" threading (a smell); `nonisolated` on something that isn't; `Task {}`
  capturing and mutating outer state; `async let` whose ordering is assumed.
- **Detect**: build with **strict concurrency** (Phase 2) and **Thread
  Sanitizer** (Phase 3) — these find real races the eye misses. Main Thread
  Checker catches off-main UIKit/AppKit calls.
- **Fix**: isolate shared state in an `actor` or to `@MainActor`; mark UI types
  `@MainActor`; make crossing types `Sendable`; don't paper over with
  `DispatchQueue.main.async` — find why it was off-main.

### A5. Completion handlers & continuations `[both]`
- **Look for**: a completion closure that can be called **twice** (e.g. called in
  both success and a fall-through) or **never** (an early `return` before
  calling it); `withCheckedContinuation` resumed twice or not at all (a crash /
  a hang); `Task` whose result is ignored where errors matter.
- **Detect**: trace every path through the function — each must call the handler
  exactly once. `withCheckedContinuation` double-resume traps at runtime.
- **Fix**: single exit, or a `defer`/flag guaranteeing one call; prefer
  `async/await` over hand-rolled callbacks.

### A6. Error handling `[both]`
- **Look for**: `try?` that discards the error and proceeds as if it worked;
  empty `catch {}`; `catch { print(error) }` with no user-facing recovery; a
  generic "Something went wrong" with no retry; force-`try` on fallible IO/JSON.
- **Detect**: scanner flags `empty_catch`, `try_optional`. Read whether the
  failure leaves the user stuck or with wrong state.
- **Fix**: handle each error meaningfully — recover, retry, or tell the user what
  to do; never silently swallow a failure that changes app state or data.

### A7. Edge cases & input `[both]`
- **Look for**: empty / nil / whitespace-only / very long / emoji / RTL input;
  off-by-one (`<` vs `<=`, `count` vs `count-1`); divide-by-zero / modulo-zero;
  integer overflow on user math; negative where only positive is expected;
  `Array(repeating:count:)` with a computed count that can be negative.
- **Fix**: validate at the boundary; clamp ranges; use safe-subscript helpers;
  test the empty and the huge case explicitly.

### A8. Date, time, locale, formatting `[both]`
- **Look for**: `DateFormatter` without an explicit `locale`/`timeZone` (parses
  differently per user → bugs and crashes); building/parsing dates by string
  math; assuming 24h or Gregorian; `String(format:)` with the wrong specifier;
  number/currency formatting hardcoded; comparing `Date` for "same day" with
  `==`.
- **Fix**: fixed `Locale(identifier: "en_US_POSIX")` + explicit `timeZone` for
  machine formats; `Calendar` for date math; `.formatted()` / `Measurement` /
  `NumberFormatter` with the user's locale for display.

### A9. Data integrity & loss `[both]`
- **Look for**: Core Data / SwiftData / `UserDefaults` / file writes whose
  failure is ignored (`try?` on `context.save()`); writes off the right
  queue/context; **no autosave** so unsaved edits die on background/terminate/
  crash; non-atomic file writes; `Codable` decode that crashes on a schema
  change or a missing key; model migration not handled.
- **Detect**: search every persistence call site; check the
  background/terminate path (Phase 4) for unsaved state.
- **Fix**: handle save failures; write atomically; autosave or save-on-resign;
  default-tolerant decoding (`decodeIfPresent`, custom `init(from:)`); a
  migration plan.

### A10. Logic mistakes `[both]`
- **Look for**: inverted booleans (`!isHidden` confusion), wrong operator
  (`&&`/`||`, `=`/`==` — Swift mostly blocks the latter), copy-paste blocks that
  forgot to change one identifier, non-exhaustive intent in a `switch` rescued by
  `default` that hides new cases, unreachable code, conditions that are always
  true/false.
- **Detect**: compiler warnings + analyzer catch some; read the dense
  conditionals.
- **Fix**: simplify conditionals; prefer exhaustive `switch` without `default`
  on your own enums so new cases force a decision.

---

## B · Code robustness

### B1. Retain cycles & leaks `[both]`
- **Look for**: escaping closures capturing `self` strongly (`Task {}`,
  `DispatchQueue.async`, network callbacks, `sink {}`, `Timer` blocks,
  `addObserver` blocks) where `self` also retains the closure; `delegate`
  declared `strong` instead of `weak`; parent↔child strong both ways; Combine
  `AnyCancellable` not stored (subscription dies immediately) **or** a cancellable
  stored on the object whose closure captures it strongly (cycle).
- **Detect**: scanner flags escaping closures that reference `self` without
  `[weak self]`. Confirm with the **Leaks** Instrument / a `deinit` log that
  never prints (Phase 3).
- **Fix**: `[weak self]` (+ `guard let self`) in escaping closures that outlive
  the call; `weak var delegate`; break the cycle on one side; store cancellables
  in a `Set<AnyCancellable>` owned correctly.

### B2. Observers, KVO, timers, notifications `[both]`
- **Look for**: `NotificationCenter.addObserver` / KVO / `Timer.scheduledTimer`
  never removed/invalidated; a repeating `Timer` retaining its target; observers
  added in `viewWillAppear` but removed in `deinit` (double-add on re-appear).
- **Fix**: balance add/remove on the same lifecycle pair; invalidate timers in
  `deinit`/disappear; prefer the block-based observer + token, or Combine/async
  sequences.

### B3. Lifecycle misuse `[both]`
- **Look for**: heavy work in `viewDidLoad` that should be `viewWillAppear`, or
  per-appear work done once in `viewDidLoad`; `[iOS]` assuming `viewDidLoad`
  runs once per screen visit; SwiftUI `onAppear` used as "once" (it can fire
  again); not handling `scenePhase` / app background-foreground; ignoring state
  restoration so the app forgets where the user was.
- **Fix**: match work to the right lifecycle hook; use a `hasLoaded` flag or
  `.task(id:)` for once-vs-each; handle `scenePhase`.

### B4. Main-thread / UI-thread contracts `[both]`
- **Look for**: UI mutated from a background queue/task; `URLSession` completion
  (background thread) touching UIKit/AppKit directly; image decoding / heavy work
  on the main thread (hang); layout forced in a loop.
- **Detect**: **Main Thread Checker** (Phase 3) flags off-main UIKit/AppKit;
  watch for beachball `[macOS]` / unresponsive UI `[iOS]`.
- **Fix**: hop to `@MainActor`/`DispatchQueue.main` for UI; move heavy work off
  main; never block main on IO/network.

### B5. Networking `[both]`
- **Look for**: requests with no timeout, no cancellation, no retry; no offline
  handling (`NSURLErrorNotConnectedToInternet` ignored); response status not
  checked before decoding; `JSONDecoder` crash on unexpected shape; main-thread
  blocking on a synchronous request; missing cancellation when the screen
  disappears mid-request.
- **Fix**: set timeouts; check status codes; tolerant decoding; handle the
  offline and the slow case in the UI (Phase 4 states); cancel on disappear.

### B6. Deprecated / misused APIs `[both]`
- **Look for**: deprecated APIs (compiler warns), wrong threading contract on an
  API, `UIApplication.shared` in extensions/SwiftUI where unavailable, file APIs
  ignoring the sandbox/security scope `[macOS]`.
- **Detect**: compiler warnings (Phase 2).
- **Fix**: migrate to the current API; respect documented threading/availability.

### B7. Debug & dead code `[both]`
- **Look for**: `print` / `NSLog` / `debugPrint` left in; hardcoded test data,
  test endpoints, or credentials; large commented-out blocks; unreachable code;
  `TODO` / `FIXME` / `HACK` / `XXX` markers that mark a known-unfinished path.
- **Detect**: scanner flags `debug_print`, `todo_marker`, `hardcoded_test`.
- **Fix**: remove or gate behind `#if DEBUG`; resolve or ticket the markers;
  delete dead code.

---

## C · User-flow correctness (code-side signals)

Flow bugs are mostly found by *walking the app* (see
[flow-audit.md](flow-audit.md)), but these code smells predict them:

### C1. Missing states `[both]`
- **Look for**: a view that renders data with no branch for **loading**,
  **empty**, or **error**; a `ForEach` over a possibly-empty array with no empty
  state; an `AsyncImage`/network view with no failure placeholder.
- **Fix**: every data-driven screen handles the four states explicitly.

### C2. Navigation integrity `[both]`
- **Look for**: a pushed/presented screen with no reachable way back/dismiss; a
  programmatic navigation path that can desync from the UI (`NavigationStack`
  path bound to state that's mutated elsewhere); deep-link handling that assumes
  the target exists; a modal presented over a modal with no dismissal chain.
- **Fix**: guarantee a back/close affordance; keep the nav path as single source
  of truth; validate deep-link targets and fall back gracefully.

### C3. Permission flows `[both]`
- **Look for**: camera/photos/location/mic/notifications/contacts requested with
  **only the granted path** handled — the *denied* and *restricted* branches lead
  to a blank or stuck screen; no deep-link to Settings to re-enable.
- **Fix**: handle every authorization status; degrade gracefully on denial; offer
  "Open Settings".

### C4. Destructive actions & data loss `[both]`
- **Look for**: delete/overwrite/reset with no confirmation and no undo; a form
  that loses input on accidental dismiss/background; "discard changes?" missing.
- **Fix**: confirm destructive actions; offer undo; preserve in-progress input
  across dismiss/background.

### C5. Platform interruptions
- `[iOS]` rotation (layout breaks / state lost), Dynamic Type enlarging text past
  the layout, multitasking/split-view on iPad, keyboard covering the focused
  field, low-memory purging state, incoming call/Face ID interruption.
- `[macOS]` window resize to very small/large, **multiple windows** of the same
  document (do edits sync?), full-screen, menu-bar commands and keyboard
  shortcuts that must mirror in-window actions, becoming background app,
  Stage Manager / external display.
- **Fix**: test these explicitly in Phase 4; they're the most-missed flow bugs.

---

## How to use this catalog

1. In Phase 1, let the scanner point you at candidate sites for A1, A4(partial),
   A6, B1, B2, B7.
2. In Phase 2–3, let the analyzer + sanitizers + Main Thread Checker confirm A4,
   B1, B4 — the ones static text can only suspect.
3. In Phase 4, walk the journeys for C1–C5 — code smells flag them, but only
   running the flow proves them.
4. Report only what you confirmed, with a repro or the exact code path, and rank
   by the severity rubric in `SKILL.md`.
