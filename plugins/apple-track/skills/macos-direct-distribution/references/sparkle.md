# Sparkle auto-updates — details

Sparkle is the de-facto framework for updating macOS apps distributed outside the
Mac App Store. The app periodically fetches an **appcast** (an RSS/XML feed you
host), compares the newest version listed there against the running version, and
— if newer — shows an update window. On install it downloads the new DMG/zip,
verifies its **EdDSA signature** against the public key baked into the app, then
swaps the app and relaunches.

## EdDSA signing keys

Sparkle signs every update with an ed25519 key pair. The **private key lives in
your login Keychain**; the **public key** goes in the app's Info.plist as
`SUPublicEDKey`.

Generate (or read the existing) key with Sparkle's `generate_keys` tool, which is
fetched with the package. Find it under DerivedData after resolving:

```bash
GK=$(find ~/Library/Developer/Xcode/DerivedData -path "*artifacts/sparkle/Sparkle/bin/generate_keys" | head -1)
"$GK" --account "<AppName>"        # namespaced key (recommended if you ship >1 app)
```

It prints the `SUPublicEDKey` to embed. **Back up the private key** — losing it
means you can't sign future updates and users are stranded:

```bash
"$GK" -x sparkle_private_key.txt --account "<AppName>"   # export to a base64 text file
```

The exported file is plain base64 text and IS the secret — store it in a password
manager (Apple's **Passwords** app is a good choice: iCloud Keychain is
end-to-end encrypted; paste the key into a new entry's password field). It's a
`genp` Keychain item, so it won't show in the Passwords app on its own — add it
manually. Never put it in the repo. Once it's in your vault, delete the on-disk
copy; the working key stays in the login Keychain.

### Restore on a new Mac (from a password manager)

```bash
# generate_keys ships with the package — resolve it first if needed:
xcodebuild -scheme '<App> (Direct)' -resolvePackageDependencies
GK=$(find ~/Library/Developer/Xcode/DerivedData -path "*artifacts/sparkle/Sparkle/bin/generate_keys" | head -1)

# Copy the key from your password manager, then:
pbpaste > /tmp/sparkle_key.txt
"$GK" -f /tmp/sparkle_key.txt --account "<AppName>"   # import into the Keychain
"$GK" -p --account "<AppName>"                        # verify: prints the SUPublicEDKey
rm /tmp/sparkle_key.txt && pbcopy < /dev/null         # clean up file + clipboard
```

If the Mac already holds a Sparkle key for this account, remove the existing
"Private key for signing Sparkle updates" item in Keychain Access before `-f`.

`--account` namespaces the key so multiple apps can each have their own. Omit it
to use one shared key for all your apps (Sparkle explicitly supports that too).

## Info.plist keys (set on the Direct target)

- `SUFeedURL` — absolute URL of the appcast (e.g. `https://…/releases/appcast.xml`,
  or a stable `…/releases/latest` path that serves it).
- `SUPublicEDKey` — the base64 public key from `generate_keys`.

⚠️ These go in a **real `Info.plist` file** (`DirectInfo.plist`), set via
`INFOPLIST_FILE` while keeping `GENERATE_INFOPLIST_FILE = YES` — Xcode merges your
custom keys with the generated standard keys. Do **not** use `INFOPLIST_KEY_SUFeedURL`
/ `INFOPLIST_KEY_SUPublicEDKey`: the `INFOPLIST_KEY_` prefix only injects Apple's
**known** keys and silently drops arbitrary ones, so Sparkle ends up unconfigured
and the build looks fine. `add_direct_target.rb` writes `DirectInfo.plist` and wires
`INFOPLIST_FILE` for you. Verify after building:
`plutil -p App.app/Contents/Info.plist | grep SU`.

Background checks: the script writes `SUScheduledCheckInterval` (seconds;
default **172800 = 48h**, override with `SU_CHECK_INTERVAL`). It deliberately
**omits** `SUEnableAutomaticChecks`, so Sparkle shows the first-launch consent
prompt ("Check for updates automatically?") and respects the user's choice. To
auto-enable checks without asking, add `SUEnableAutomaticChecks = true` to
`DirectInfo.plist` yourself.

## The appcast

`make_appcast.sh` signs each DMG in a release directory with `sign_update`
and emits `appcast.xml` with absolute download URLs. Each `<item>` needs at least:
`sparkle:shortVersionString`, `sparkle:version` (the CFBundleVersion — Sparkle
compares THIS to decide "newer"), and an `<enclosure>` carrying the url, length,
type, and `sparkle:edSignature`.

### sign_update vs generate_appcast

Sparkle ships both. `generate_appcast` is the "official" tool (handles deltas and
version history) but it needs **interactive Keychain approval** the first time and
will silently produce an *unsigned* appcast if denied — which is easy to miss in a
script or CI. `sign_update` is deterministic and returns the signature string
directly, so the script builds the XML around it. If you prefer `generate_appcast`,
run it once from a real Terminal and click "Always Allow" on the Keychain prompt.

## Hosting layout — stable latest + versioned archive

Upload the DMG **and** the appcast, and make sure the appcast is reachable at the
**exact** `SUFeedURL` the app was built with. A clean, low-maintenance layout that
also gives the website a download link that never changes:

```
<releases>/
├── <App>.dmg                 latest — STABLE website URL + appcast enclosure
├── latest                    the appcast XML (serve appcast.xml's content here)
└── <version>/<App>-<ver>.dmg permanent versioned archive (old + current)
```

- **Website download** → `…/<App>.dmg` (constant filename → constant URL). The
  version isn't in the filename — it lives in the bundle and in the appcast's
  `<sparkle:version>`.
- **Sparkle** reads the appcast at `…/latest`; its `<enclosure>` also points at the
  constant `…/<App>.dmg`. Sparkle compares `<sparkle:version>` (= CFBundleVersion)
  to decide "newer", so **bump CFBundleVersion every release**.
- **Old versions** stay downloadable at `…/<version>/<App>-<ver>.dmg`.

If `SUFeedURL` ends in `…/latest` (no extension), serve the appcast content at that
key — name the object `latest`, with `Content-Type: application/xml`.

`stage_release.sh` builds this layout from a notarized DMG (reads the app
name + version from the bundle), signs the appcast, and prints/runs the upload for
any S3-compatible host (Cloudflare R2, AWS S3, B2 …) via `aws s3` or `rclone`.

## Sandbox note

Sparkle in a **sandboxed** app needs extra plumbing (Installer/Downloader XPC
services + network entitlements). Because direct distribution doesn't require the
sandbox, the simplest path — and what the target script does — is to ship the
Direct target **non-sandboxed** (App Sandbox off, Hardened Runtime on). If you
must keep the sandbox, see Sparkle's "Sandboxing" guide.

## Signing & notarization

Sparkle.framework embeds nested code (Updater.app, Downloader.xpc, Installer.xpc).
A Developer ID **export** (Xcode Organizer or `-exportArchive` with method
`developer-id`) re-signs all of it; notarization then validates it. Verify before
shipping:

```bash
codesign -dvv "App.app/Contents/Frameworks/Sparkle.framework" | grep "Developer ID"
find "App.app/Contents/Frameworks/Sparkle.framework" \( -name "*.xpc" -o -name "*.app" \) \
  -exec codesign --verify --strict {} \;
```

The DMG packaging + notarization itself is the **notarize-and-distribute** skill —
this skill stops at "the update mechanism is wired and an appcast can be produced."
