---
name: apple-credentials
description: >-
  The single owner of Apple developer credentials and certificates — checking what you
  have, explaining the types and why each is needed, creating the ones that can be
  created, and setting up auth credentials. Use this whenever the user needs a signing
  certificate ("תעודת חתימה", "אישורים של אפל") (Apple Development / Apple Distribution
  / Developer ID / installer), asks which certificate they need or why, has no
  certificates and needs to create one, wants to export a certificate as .p12 (e.g. for
  GitHub Actions / CI / another Mac), needs an app-specific password or a notary
  credential profile (notarytool store-credentials), or needs an App Store Connect API
  key. Other Apple skills (code-signing-provisioning, notarize-and-distribute,
  app-store-metadata, ship-apple-app) draw from this one for anything
  certificate/credential related. It creates and locates credentials; diagnosing a build
  that will not sign is code-signing-provisioning's job.
---

# Apple Credentials & Certificates

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

This is the home for everything "identity material" in Apple development: the
**certificates** that sign your apps, and the **credentials** that authenticate
command-line tools to Apple. The goal is that the user understands *which* one
they need and *why*, has the right ones present, and can create what's missing.

Teach as you go — explain why a given certificate/credential is required, not
just the command. Other skills defer here, so be the authoritative, clear source.

## Prerequisites

- **Tools:** Xcode command line tools (`xcrun notarytool`, `codesign`) and macOS
  `security` for `scripts/apple_creds.py`; `fastlane match` (`gem install fastlane`)
  only as one of the ways certificates get minted.
- **Credentials:** an Apple Developer account — this skill is where the notarytool
  keychain profile, app-specific password and App Store Connect API key (`.p8`) are
  created and stored; nothing is resolved from elsewhere.
- **Hub (`$APP_HUB`):** optional — only the conversational-language default in `DATA.md`.
- **`$KEYS_ROOT/APPLE.md`:** optional — the owner's map of team, certificates and
  keys; read first when present, kept current by this skill (see below).
- **Other tracks:** none.

## Two families (don't confuse them)
1. **Certificates** — cryptographic signing identities in your keychain (Apple
   Development, Apple Distribution, Developer ID Application, installer certs).
   They *sign* apps/installers.
2. **Auth credentials** — secrets that let CLI tools talk to Apple services
   without typing a 2FA code: an **app-specific password**, a **notary keychain
   profile** (built from one), and an **App Store Connect API key** (`.p8`).
   They *authenticate*, they don't sign.

## Workflow

### 1. Check what already exists
**If `$KEYS_ROOT/APPLE.md` exists, read it first.** It is the owner's map of the
Apple account: the team ID (and which ID is *not* a team), every certificate with
its SHA-1 and expiry, which App Store Connect API key under
`$KEYS_ROOT/appstoreconnect/<name>/` serves what, the provisioning profiles, and
the signing traps already met. It holds no secrets — only IDs, dates and
locations. Then run the check:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/apple-credentials/scripts/apple_creds.py check
```
It lists signing certificates grouped by type with SHA-1 and expiry, detects App
Store Connect API keys (the track's resolver, the standard folders, and
`$KEYS_ROOT/appstoreconnect/*/`), notes notary-profile setup, and summarizes
what's present vs missing for each goal (development / App Store / Developer ID).

**Reconcile the two and report every disagreement** — the file is a record, and
the world moves without it: a certificate the file lists that the keychain no
longer has, or whose expiry differs (renewed, or lapsed); one expiring within
60 days; an API key whose folder or `.p8` moved; a key or certificate on disk
that the file does not mention. Say which side looks right, and offer to
correct the file.

### 2. Identify what's needed for the goal
Map the user's goal to the right certificate using
[references/certificate-types.md](references/certificate-types.md) (the full
plain-language explanation of every type and *why* it exists):
- Run/debug on devices → **Apple Development**
- App Store / Mac App Store → **Apple Distribution** (+ **Mac Installer
  Distribution** for the MAS `.pkg`)
- Direct Mac distribution (DMG/notarized) → **Developer ID Application** (+
  **Developer ID Installer** for a `.pkg`)
And the right auth credential using
[references/auth-credentials.md](references/auth-credentials.md):
- Notarization (`notarytool`) → app-specific password → **notary keychain
  profile**, or an API key
- App Store uploads / fastlane / CI → **App Store Connect API key** (preferred)
  or app-specific password

### 3. Create / set up what's missing
- **A certificate is missing** → guide creation. Easiest: Xcode → Settings →
  Accounts → Manage Certificates → **+** → the type. Portal route + roles/limits
  are in [references/certificate-types.md](references/certificate-types.md).
  (Certificates aren't minted by a script here — Xcode/`fastlane match` do that
  properly, managing the private key; this skill guides and verifies.)
- **Export a certificate as `.p12`** (for GitHub Actions / CI / a second Mac) →
  follow [references/certificate-types.md](references/certificate-types.md#exporting-a-certificate-as-p12-for-ci--another-mac).
  This bundles the cert **and its private key** so another machine can sign.
- **A notary credential** → the skill creates the profile FOR the user after
  they supply an app-specific password (or an API key):
  ```bash
  NOTARY_PASSWORD='abcd-efgh-ijkl-mnop' \
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/apple-credentials/scripts/apple_creds.py \
    store-creds --profile "MyNotary" \
    --apple-id "you@example.com" --team-id "ABCDE12345"
  # or, from an API key:
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/apple-credentials/scripts/apple_creds.py \
    store-creds --profile "MyNotary" \
    --key /path/AuthKey_XXX.p8 --key-id XXXXXXXXXX --issuer <uuid>
  ```
  Then tell the user they now have a reusable profile (`--keychain-profile
  MyNotary`) and won't re-enter the password.
- **An app-specific password or API key** → these are created by the USER on
  Apple's sites (only they can); run `setup` to print the exact steps, then use
  the result with `store-creds` or place the `.p8` per
  [references/auth-credentials.md](references/auth-credentials.md).

### 4. Profiles, capabilities and key backup — the studio's policy
The rules are in [references/profiles-and-backup.md](references/profiles-and-backup.md);
this installation's specifics (which apps have a manual profile, the backup's date,
which key exports iOS builds) are in `$KEYS_ROOT/APPLE.md`. In short:
- **Manual profile only for a Tauri Mac App Store build** (embedded before signing).
  Everything else is automatic — including the **iOS App Store export** (Capacitor and
  Tauri): `ExportOptions.plist` with `method` `app-store-connect`, `signingStyle`
  `automatic`, `teamID`, and `xcodebuild -exportArchive -allowProvisioningUpdates` with
  an ASC API key (`-authenticationKeyPath/-authenticationKeyID/-authenticationKeyIssuerID`).
  No manual iOS store profiles.
- **A manual Mac App Store profile** lives in `~/Library/MobileDevice/Provisioning Profiles`
  (never in `$KEYS_ROOT` — it is not a secret), one per app, a new one named
  `<App> macOS AppStore`; the build script finds it **by name** (`MAS_PROFILE`
  overrides). When the app gains a capability, regenerate it immediately and record it.
- **Capabilities:** Capacitor → in Xcode (`ios/App` is tracked). Tauri → in the
  project's patch script, writing `project.yml` `entitlements.properties` **and**
  `SystemCapabilities` — never in Xcode (`gen/apple` is regenerated). After every build,
  `codesign -d --entitlements -` on the app and each extension; `Provisioning Profile:
  "…: *"` in the build log means the capabilities were stripped silently.
- **Key backup:** after every certificate creation or renewal, back up that
  certificate's private key to `$KEYS_ROOT/apple-certificates/<type>-<YYYY-MM-DD>.p12`
  — one file per certificate, one password for all in `p12-password.txt` beside them
  (`chmod 600`) — verify the key matches the certificate, and keep the old file until
  its certificate expires. `.p8` keys and the Sparkle key have **no other
  copy**. `check` reports, per certificate in the keychain, the backup file that holds its
  SHA-1 (or flags that none does), and
  whether `$KEYS_ROOT` has a copy off this disk — warn when it does not.
- **Don't** choose the personal ID in the development certificate's name as the team;
  don't use `fastlane match` for one developer on one Mac.

## Keep `$KEYS_ROOT/APPLE.md` current

**Whenever this skill creates or renews a certificate, an API key, a notary
profile, a manual provisioning profile, a key backup or an App ID capability, update `$KEYS_ROOT/APPLE.md` in the same turn**
— the name, team, SHA-1, expiry, Key ID, folder, profile name, and the date of
the change. **Never a secret:** no password, no `.p8`/`.p12` content, no private
key — IDs, dates and locations only. A record that is not updated at the moment
of change is wrong from that moment on, and nothing else will notice.

If the file does not exist and `$KEYS_ROOT` is set, **offer** to create it from
the check's output (team ID, certificates with SHA-1 and expiry, each API key's
folder, Key ID and purpose — ask the user what each key is for, the folder name is
only a hint). `$KEYS_ROOT` is outside every repo; the file never moves into one.
If `$KEYS_ROOT` is not set, do not invent a location — say so and go on.

## What's safe vs ask-first
Safe: `check`, reading `APPLE.md`, explaining, guiding creation, drafting
commands, updating `APPLE.md` after a change this skill made. Ask first:
creating `APPLE.md`, exporting private keys to the backup `.p12` files,
running `store-creds` (writes to the keychain), exporting a `.p12` (handles the
private key), and anything touching the Apple account.

## How other skills use this
`code-signing-provisioning` (signing model, profiles, errors), and
`notarize-and-distribute` / `app-store-metadata` / `ship-apple-app` defer here
for certificates and credentials, and point at `$KEYS_ROOT/APPLE.md` as the first
place to look for which key or certificate to use. If this skill isn't installed, those skills
fall back to inline Xcode/`notarytool` guidance — but when it's present, it's the
single source of truth.

## Boundaries

- **It creates and locates; it does not diagnose a failing build.** "No signing
  certificate", a profile that does not match the entitlements, a build that will not
  archive — those are `code-signing-provisioning`'s, which reads the error and works
  backwards.
- **It never prints a secret**, never copies one into a repo, and never commits one.
  The files stay where they are and are referred to by path.

## Reference files
- [references/certificate-types.md](references/certificate-types.md) — every
  certificate type, why it exists, platform matrix, creation, roles/limits, and
  **`.p12` export for CI**.
- [references/auth-credentials.md](references/auth-credentials.md) —
  app-specific passwords, notary keychain profiles, and App Store Connect API
  keys: what each is, which tool needs which, and how to set them up.
- [references/profiles-and-backup.md](references/profiles-and-backup.md) — which
  builds get a manual profile, iOS automatic export, where capabilities are declared
  (Capacitor vs Tauri) and how to verify them, the key backup and restore, the don'ts.
- [scripts/apple_creds.py](scripts/apple_creds.py) — `check`, `store-creds`,
  `setup`.
