# Refreshing the bug catalog against current Apple / Swift guidance

The [bug-catalog.md](bug-catalog.md) is fast and works offline, but the platform
moves: Swift concurrency tightens, SwiftUI adds/changes state primitives, new OS
versions deprecate APIs and add new lifecycle/diagnostic behavior. This is the
"hybrid" half — when accuracy matters, reconcile the catalog against current
sources and report any drift.

## When to refresh
- The catalog's `last-verified` date is more than ~90 days old.
- The user explicitly wants certainty ("is this current with Swift 6 / the latest
  SDK?").
- A new major version landed (new Swift, new Xcode, new iOS/macOS) that changed:
  - **Concurrency** — strict-concurrency defaults, `Sendable`/actor rules,
    `@MainActor` inference (catalog A4/A5).
  - **SwiftUI state** — `@Observable`/`@Bindable` vs `ObservableObject`, new
    navigation APIs, lifecycle (catalog A2/A3, B3).
  - **Deprecations** — APIs the project uses that became deprecated (catalog B6).
  - **Diagnostics** — new sanitizer/runtime-checker behavior
    ([runtime-diagnostics.md](runtime-diagnostics.md)).

## How to refresh
1. For a specific concern, fetch the authoritative doc:
   ```
   WebFetch https://developer.apple.com/documentation/swift/...   (or the relevant API page)
   WebFetch https://www.swift.org/migration/                       (concurrency migration)
   ```
   Prompt it for what changed and any version note.
2. For evolving language rules, check **Swift Evolution** (search "Swift Evolution
   SE-#### <topic>") and the Swift migration guide.
3. If WebFetch returns little (JS-heavy pages), fall back to WebSearch:
   "<API> deprecated iOS 19", "Swift 6 <topic> migration", "SwiftUI @Observable
   vs @StateObject".

## What to do with drift
- **Report it** in the review output: note which guidance changed and how it
  affects this app (e.g. "this `ObservableObject` pattern is now `@Observable`;
  the old `@StateObject` caveat changes").
- **Offer to update** [bug-catalog.md](bug-catalog.md) in place: adjust the
  affected entries (keep the *look-for / detect / fix / platform-tag* shape),
  and bump `last-verified` to today. Keep it curated — only the bugs that
  actually bite, not the whole language reference.
- If nothing changed materially, bump `last-verified` and say so.

## Note on diagnostics tooling
`xcodebuild` flags and sanitizer names occasionally change across Xcode versions.
When the runtime phases fail with "unknown flag", confirm the current flag with
`xcodebuild -help` / `man xcodebuild` and update
[runtime-diagnostics.md](runtime-diagnostics.md).
