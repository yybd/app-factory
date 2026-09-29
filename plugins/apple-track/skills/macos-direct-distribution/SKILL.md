---
name: macos-direct-distribution
description: >-
  Set up direct (outside the Mac App Store) distribution for a macOS Xcode app: a
  dedicated "Direct" target — sandbox off, hardened runtime on, a DIRECT flag,
  direct-only frameworks linked to it alone — wired to Sparkle auto-updates with EdDSA
  signing keys, a SUFeedURL, a "Check for Updates" menu item and an appcast signing
  script. Use whenever the user wants automatic updates for a Mac app sold outside
  the App Store ("הפצה ישירה", "עדכונים אוטומטיים"), add Sparkle, create a second
  non-MAS target alongside an App Store build, set up an appcast, or ask how to keep
  Sparkle out of the App Store build. Pairs with `notarize-and-distribute`, which builds
  the signed DMG this skill's appcast points at.
---

# Direct distribution + auto-updates for a macOS app

Give a macOS app a second distribution channel — a notarized DMG downloaded from
your own site — that lives **alongside** the App Store build from one codebase,
and updates itself via Sparkle. This skill creates the build target and the
update mechanism; the **notarize-and-distribute** skill builds the signed DMG.

The hard part is keeping the two channels cleanly separated. The key constraint:
**a linked framework is embedded per-target, not per-configuration**, so keeping
Sparkle out of the App Store build (required by Guideline 2.4.5) means the direct
build needs its own *target*, not just a build config. See
[references/xcode-target.md](references/xcode-target.md) for the full rationale.

## Prerequisites

- **Tools:** Xcode 16, and the `xcodeproj` Ruby gem (`gem install xcodeproj`, or via
  the project's `bundle`) — the scripts use it to edit the project safely. Sparkle
  itself is added as a package dependency, not installed.
- **Credentials:** a Developer ID Application certificate, plus the Sparkle EdDSA key
  pair this skill generates and stores in the keychain. Notarization credentials belong
  to `notarize-and-distribute`.
- **Hub (`$APP_HUB`):** not used — everything is in the app's own repo.
- **Other tracks:** none; `notarize-and-distribute` and `apple-credentials` ship in this
  same plugin.

And before starting:

- A macOS Xcode project that builds for the App Store, using an Xcode 16 **synced
  source folder** (`PBXFileSystemSynchronizedRootGroup`). Projects with explicit
  per-file membership need a different path — see
  [references/xcode-target.md](references/xcode-target.md).
- The `xcodeproj` Ruby gem (`gem install xcodeproj`, or via the project's
  `bundle`). The scripts use it to edit the project safely.
- For shipping: a Developer ID Application cert + a notary credential. Creating
  the signed, notarized DMG is the **notarize-and-distribute** skill's job.
- Decide the **hosting URL** up front (where the DMG + appcast will live), and
  talk to the user about the **sandbox**: the Direct target ships non-sandboxed
  (simplest for Sparkle, and direct distribution doesn't require it).

## Workflow

Work in order. Steps 2–4 have a deliberate ordering wrinkle around the Sparkle key
(you need the package resolved before you can generate the key, then you re-run the
target script to embed the key) — follow it and it's smooth.

### 1. Find the app target and confirm the plan

Identify the App Store application target and confirm with the user: the new target
name (default `<App> Direct`), the **appcast URL** (`SUFeedURL`), and that the
direct build will be **non-sandboxed**. Inspect:

```bash
xcodebuild -list                      # targets + schemes
ruby -e 'require "xcodeproj"; p=Xcodeproj::Project.open(Dir.glob("*.xcodeproj").first); \
  p.targets.each{|t| puts "#{t.name}  #{t.respond_to?(:product_type) ? t.product_type : ""}"}'
```

### 2. Create the Direct target (placeholder key)

Run [scripts/add_direct_target.rb](scripts/add_direct_target.rb) from the project
directory. On this first pass the Sparkle public key is a placeholder — you'll
patch it in step 3. It also adds the Sparkle SPM dependency.

```bash
SUFEED_URL='https://downloads.example.com/myapp/releases/appcast.xml' \
  ruby ${CLAUDE_PLUGIN_ROOT}/skills/macos-direct-distribution/scripts/add_direct_target.rb
```

Config is via environment variables (all optional except where noted) — see the
header of the script: `PROJECT`, `APP_TARGET`, `DIRECT_TARGET`, `SCHEME`,
`SUFEED_URL`, `SPARKLE_PUBKEY`, `SPARKLE_MIN`, `LINK_SPARKLE`. The script is
idempotent. It clones the App Store target's settings, then sets sandbox off,
hardened runtime on, the `DIRECT` flag, the Sparkle Info.plist keys, links Sparkle
to the new target only, and creates a `<App> (Direct)` scheme.

### 3. Generate the Sparkle signing key, then embed it

Resolve the package so Sparkle's tools exist, generate (or read) the EdDSA key,
then **re-run the target script** with the real public key to patch the Info.plist:

```bash
xcodebuild -scheme '<App> (Direct)' -resolvePackageDependencies
GK=$(find ~/Library/Developer/Xcode/DerivedData -path "*artifacts/sparkle/Sparkle/bin/generate_keys" | head -1)
"$GK" --account '<App>'              # prints SUPublicEDKey; private key → login Keychain

SUFEED_URL='…/appcast.xml' SPARKLE_PUBKEY='<the base64 key>' \
  ruby ${CLAUDE_PLUGIN_ROOT}/skills/macos-direct-distribution/scripts/add_direct_target.rb
```

**Tell the user to back up the private key** (`generate_keys -x backup --account
'<App>'`) — losing it strands every direct user on their current version. Key
details: [references/sparkle.md](references/sparkle.md).

### 4. Add the Sparkle Swift code

Copy [assets/SparkleUpdater.swift](assets/SparkleUpdater.swift) into the app's
source folder (it's fully `#if DIRECT`-guarded, so the App Store target ignores
it). Then wire the updater + "Check for Updates…" menu into the app's `@main App`
struct following [assets/AppEntry-snippet.swift](assets/AppEntry-snippet.swift) —
add the `#if DIRECT` property and `.commands { … }` to the *existing* App struct;
don't replace it.

### 5. Build & verify BOTH targets

This is the proof the split is correct. Build the App Store target to an isolated
DerivedData and confirm it embeds **no** Sparkle; build the Direct target and
confirm it **does**.

```bash
# App Store target — must stay Sparkle-free + sandboxed
xcodebuild -scheme '<AppStoreScheme>' -configuration Release \
  -derivedDataPath /tmp/mas_check CODE_SIGNING_ALLOWED=NO build
find /tmp/mas_check/Build/Products/Release/*.app -iname '*sparkle*'   # expect: nothing

# Direct target — must build with Sparkle embedded
xcodebuild -scheme '<App> (Direct)' -configuration Release \
  CODE_SIGNING_ALLOWED=NO build
```

Both must succeed. If the App Store build references Sparkle, the target split is
wrong — re-check that Sparkle is linked only to the Direct target.

### 6. Ship a release (DMG + appcast)

1. **Bump `CFBundleVersion`** (Sparkle compares it to decide "newer") + the
   marketing version. Archive the `<App> (Direct)` scheme, export **Developer ID**,
   then build + **notarize + staple** the DMG — this is the
   **notarize-and-distribute** skill. Leave the notarized DMG in `dist/`.
2. Stage + sign + upload with [scripts/stage_release.sh](scripts/stage_release.sh).
   It reads the app name + version from the DMG, builds the stable-latest +
   versioned-archive layout (see [references/sparkle.md](references/sparkle.md)),
   signs the appcast, and prints/runs an S3-compatible upload:
   ```bash
   DOWNLOAD_URL_PREFIX='https://downloads.example.com/myapp/releases/' \
   PREFIX='myapp/releases' BUCKET='<bucket>' ENDPOINT='https://<id>.r2.cloudflarestorage.com' \
   SPARKLE_KEYCHAIN_ACCOUNT='<App>' DO_UPLOAD=1 \
     bash ${CLAUDE_PLUGIN_ROOT}/skills/macos-direct-distribution/scripts/stage_release.sh
   ```
   The website download link (`…/<App>.dmg`) never changes; existing users get the
   update prompt automatically.

   **If the app has ever been renamed, publish the old name too.** The staged
   layout is built from the DMG, so the stable-latest object is named after the
   app's CURRENT `productName` — and the object under the previous name is not
   part of the layout, which means nothing here refreshes it. It does not 404 and
   it does not error: it keeps serving, frozen at whatever release was current
   when the rename happened. One app was found a full version behind that way,
   under a caller's own line claiming both names carried the same bits. Sparkle
   pulls such a copy forward on its next check, so it self-heals for anyone who
   opens the app — but a fresh download has no reason to be a version old, and a
   page or a bookmark that predates the rename still points there. Copy the same
   staged DMG to `<PREFIX>/<old-name>.dmg` in the same run, from the caller, and
   keep doing it for as long as the old URL is reachable. Note that the PATH
   prefix must not be renamed at all — Sparkle reads the feed URL out of the
   Info.plist shipped with each install, so changing it orphans every existing
   copy.

### 7. Document it

Add a "Distribution builds" section to the project's README (or hub docs) covering
both channels and the release flow. Use the template in
[references/readme-template.md](references/readme-template.md) — fill in the app's
names, URLs, and target names. Keeping this current is what lets the next release
(or the next person) run step 6 without rediscovering everything.

## Scripts & assets

- [scripts/add_direct_target.rb](scripts/add_direct_target.rb) — creates the Direct
  target + scheme, links Sparkle, sets sandbox/flags/Info.plist. Idempotent.
- [scripts/stage_release.sh](scripts/stage_release.sh) — stages the stable-latest +
  versioned-archive layout, signs the appcast, prints/runs the S3-compatible upload.
- [scripts/make_appcast.sh](scripts/make_appcast.sh) — signs the release DMG(s) and
  writes `appcast.xml` (called by `stage_release.sh`).
- [assets/SparkleUpdater.swift](assets/SparkleUpdater.swift) — the updater + menu
  command (`#if DIRECT`).
- [assets/AppEntry-snippet.swift](assets/AppEntry-snippet.swift) — how to wire it
  into the `@main App`.

## References

- [references/xcode-target.md](references/xcode-target.md) — why a target (not a
  config), what the script sets, verifying the App Store build stays clean, and
  the non-synced-folder fallback.
- [references/sparkle.md](references/sparkle.md) — EdDSA keys, Info.plist, the
  appcast, `sign_update` vs `generate_appcast`, hosting, sandbox & signing notes.

## Boundaries
This skill creates the **target** and the **update mechanism** and documents them.
It does **not** build/sign/notarize the DMG (that's **notarize-and-distribute**) and
does not prescribe a payment system — though the `DIRECT` flag it adds is also the
right seam for a direct-channel licensing backend kept out of the App Store build.
