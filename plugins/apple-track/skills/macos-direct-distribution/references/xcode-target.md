# The Direct target — design & rationale

## Why a separate target, not just a build configuration

You can split *code* per build with `#if DIRECT` inside one target. But a **linked
framework is embedded per-target, not per-configuration** — Xcode has no
per-config framework linking. So if Sparkle is linked to the shared target, it
gets embedded into the App Store product too, even when its code is fully
`#if DIRECT`-guarded.

That matters because the Mac App Store rejects apps that bundle a self-update
mechanism (App Review Guideline 2.4.5). A dormant `Sparkle.framework` in the
binary is a real rejection risk. The only clean way to keep it out is a **second
target** that links Sparkle, while the App Store target does not.

The usual downside of two targets — having to add every new file to both — is
**gone** when the project uses an Xcode 16 synced source folder
(`PBXFileSystemSynchronizedRootGroup`): the new target references the *same*
synced group, so both targets automatically compile every file. There's no
per-file membership to drift.

## What the script configures on the Direct target

- **Shares the synced source folder** of the App Store target (same code, zero
  drift).
- **`SWIFT_ACTIVE_COMPILATION_CONDITIONS` += `DIRECT`** — the single switch that
  turns on direct-only code paths (Sparkle, and any direct-only payment/licensing).
- **`ENABLE_APP_SANDBOX = NO`** — direct distribution doesn't need the sandbox, and
  turning it off makes Sparkle's installer simple. (App Store target keeps it ON.)
- **`ENABLE_HARDENED_RUNTIME = YES`** — still required for notarization.
- **`INFOPLIST_FILE = DirectInfo.plist`** — holds Sparkle's `SUFeedURL` /
  `SUPublicEDKey`, merged with the generated plist (keep `GENERATE_INFOPLIST_FILE
  = YES`). The `INFOPLIST_KEY_` prefix can't carry arbitrary keys — see
  [sparkle.md](sparkle.md).
- **Links the Sparkle SPM product to this target only.**
- All other settings (bundle id, team, deployment target, PRODUCT_NAME, the other
  `INFOPLIST_KEY_*`) are **cloned** from the App Store target's matching config, so
  the two products stay identical except where intended.

A dedicated scheme (`<App> (Direct)`) is created: Debug for Run, Release for
Archive — so the direct product is one scheme-pick away in Xcode and one
`-scheme` flag in CI.

## Verifying the App Store target stayed clean

After running the script and building, confirm the App Store product embeds no
Sparkle (build it to an isolated DerivedData to avoid the two targets' identically
named products overwriting each other):

```bash
xcodebuild -scheme '<AppStoreScheme>' -configuration Release \
  -derivedDataPath /tmp/mas_check CODE_SIGNING_ALLOWED=NO build
APP=/tmp/mas_check/Build/Products/Release/<Product>.app
find "$APP" -iname '*sparkle*'        # expect: no output
ls "$APP/Contents/Frameworks" 2>/dev/null  # expect: no such directory (or no Sparkle)
```

## Two products, same name

Both targets build `<PRODUCT_NAME>.app` into `Build/Products/<Config>/`. Building
one then the other in the *same* DerivedData overwrites the product (they're never
built simultaneously, so it's harmless — but it's why the clean-check above uses a
separate `-derivedDataPath`). Archives go to separate locations, so distribution
is unaffected. If you want them installable side-by-side for testing, give the
Direct target a distinct `PRODUCT_BUNDLE_IDENTIFIER`.

## Projects without a synced source folder

Older projects list each source file explicitly (`PBXFileReference` +
`PBXSourcesBuildPhase`) instead of a synced root group. The script aborts in that
case, because sharing sources then means adding every file to the new target's
Sources/Resources build phases (and keeping them in sync). Options: migrate the
project to a synced folder (Xcode 16: drag the folder in as a "folder reference"),
or extend the script to copy the App Store target's source/resource build-phase
file refs into the new target.

## The DIRECT flag is the seam for more than Sparkle

`#if DIRECT` is also the natural place for a direct-channel **payment/licensing**
backend (e.g. a license-key system) that replaces StoreKit IAP, kept out of the
App Store build for Guideline 3.1.1. That's a separate concern from this skill, but
it rides the same flag and the same target split.
