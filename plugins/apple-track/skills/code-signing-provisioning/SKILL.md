---
name: code-signing-provisioning
description: >-
  Understand, diagnose, and fix Apple code signing and provisioning for macOS and iOS
  Xcode projects — certificates, identifiers, provisioning profiles, entitlements,
  automatic vs manual signing, and fastlane match. Use whenever the user hits a signing
  or provisioning error ("שגיאת חתימה", "פרופיל הקצאה") ("no signing certificate",
  "provisioning profile doesn't include signing certificate", "doesn't match the
  entitlements", "no profiles found", "failed to register bundle identifier"), asks
  why a build will not sign, is setting up signing for a new app / machine / CI, or
  needs to diagnose a project's signing configuration. It explains the signing
  model, diagnoses the current setup (build settings, provisioning profiles,
  identities), and decodes errors. For certificate types, creating certificates, .p12
  export, and auth credentials (app-specific passwords / API keys), it defers to the
  `apple-credentials` skill. It diagnoses and repairs signing; creating certificates is
  apple-credentials' job.
---

# Code Signing & Provisioning

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

Signing is the most confusing part of Apple development because several
certificates look alike but do different jobs, and the error messages are
cryptic. This skill has two goals: **make the user understand the model** (so
they're not cargo-culting), and **diagnose + fix** the concrete setup.

Teach as you go. When you explain a fix, also explain *why* the right
certificate/profile is required — the user has said they want to understand the
whole process, not just paste commands.

## Prerequisites

- **Tools:** Xcode (`xcodebuild`, `codesign`) and macOS `security` for
  `scripts/diagnose_signing.py`; `fastlane` (`gem install fastlane`) for `match`
  (teams/CI) and the Spaceship snippet that creates distribution profiles.
- **Credentials:** an App Store Connect API key for the headless profile creation
  (Spaceship); certificates, keys and passwords themselves come from `apple-credentials`.
- **Hub (`$APP_HUB`):** optional — only the conversational-language default in `DATA.md`.
- **Other tracks:** none.

## Start here: understand, then diagnose

### 1. Ground the user in the model (briefly, in their terms)
Before touching errors, make sure the user knows the four moving parts and how
they bind together — certificate, identifier (App ID), entitlements,
provisioning profile — and which **certificate type** matches their goal. The
full, plain-language explanation (the "why each one exists" table and the
platform matrix) is owned by the **`apple-credentials`** skill
(its `certificate-types.md`) — defer there for certificate types/creation. If
that skill isn't installed, give the summary inline yourself.

The one-line version of the binding: a **provisioning profile** ties together a
**certificate** (who signs), an **App ID** (which app + capabilities), and (for
development/ad-hoc) **devices** — and the app's **entitlements** must be a subset
of what the profile/App ID allow. Mismatch anywhere → a signing error.

### 2. Diagnose the current setup
Run the diagnostic to see everything at once instead of guessing:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/code-signing-provisioning/scripts/diagnose_signing.py <project-root>
```
It reports: the target's signing build settings (automatic vs manual, team,
identity, profile specifier), the signing identities in the keychain (grouped by
type), installed provisioning profiles decoded (name, team, App ID, dev vs
distribution, **expiry**, certificates), and cross-checks (team consistency,
expired profiles, entitlements vs profile). Read it before concluding anything.

### 3. Map the goal to the right certificate
Pick the type for the goal (full table in the `apple-credentials` skill):
- Run/debug on your devices → **Apple Development**
- App Store / Mac App Store → **Apple Distribution** (+ **Mac Installer
  Distribution** for the MAS `.pkg`)
- Direct Mac distribution (DMG/notarized) → **Developer ID Application** (+
  **Developer ID Installer** if shipping a `.pkg`)

### 4. Fix or create what's missing
- If it's an **error**, decode it with
  [references/error-decoder.md](references/error-decoder.md) (symptom → cause →
  fix) and apply the fix.
- If a **certificate is missing**, guide creation (see "Creating a certificate"
  below). Don't try to mint certs silently — creation is tied to the user's
  Apple account and keychain.
- For **teams/CI/multiple machines**, prefer `fastlane match` (shared, version-
  controlled certs/profiles) — see
  [references/fastlane-match.md](references/fastlane-match.md).

## Creating a certificate
Certificate creation (and `.p12` export, limits, roles) is owned by the
**`apple-credentials`** skill — **hand off to it**. If it isn't installed, guide
inline and continue:
1. Xcode → Settings (⌘,) → **Accounts** → select the Apple ID → **Manage
   Certificates…** → **+** → the type needed (Apple Development / Apple
   Distribution / Developer ID Application / Developer ID Installer). Xcode makes
   the key + cert and installs them. (With Automatically manage signing, App
   Store/development certs are created on demand at archive/run.)
2. Portal route when Xcode can't: developer.apple.com → Certificates → + → type
   → upload a CSR → download → double-click to install.
After creation, re-run the diagnostic to confirm the identity appears, then
continue with the original task.

## Creating an App Store provisioning profile (headless)
Distribution profiles are **not** created on demand the way development ones are.
An account can hold a valid Apple Distribution certificate and a registered bundle
id and still have **zero** profiles — a first App Store export then fails with:

```
error: exportArchive No profiles for 'com.example.App' were found
```

`-allowProvisioningUpdates` does not fix this, **not even** with
`-authenticationKeyPath` / `-authenticationKeyID` / `-authenticationKeyIssuerID`
pointing at a working ASC key: the flag renews and creates *development* profiles,
and stays silent on distribution ones. Xcode's UI would create them; there is no
`xcodebuild` equivalent.

Create them directly (once per app, per platform) and write them where Xcode looks —
`~/Library/MobileDevice/Provisioning Profiles/`, `.mobileprovision` for iOS and
`.provisionprofile` for macOS, named by the profile's UUID:

```ruby
Spaceship::ConnectAPI::Profile.create(
  name: 'App iOS App Store',        # MAC_APP_STORE for the Mac one
  profile_type: 'IOS_APP_STORE',
  bundle_id_id: <bundle id resource id>,   # BundleId.all → .id, NOT the identifier string
  certificate_ids: [<distribution cert id>]  # Certificate.all → type DISTRIBUTION
)
```

Then export with **manual** signing, naming the profile per bundle id — see
`ship-apple-app` for the export-options shape. A universal app (one bundle id,
macOS + iOS) needs **both** profiles; they share the bundle id and the certificate.

Seen on a real account: it had a valid Apple Distribution cert
and a UNIVERSAL bundle id, and no profiles at all.

## What's safe vs ask-first
Safe: reading build settings, decoding profiles, diagnosing, explaining,
generating a `Matchfile`/lane. Ask first: running `fastlane match` (touches the
keychain + a private git repo + the Apple account), changing a target's signing
style or team, revoking certificates, or deleting profiles.

## Boundaries

- **It repairs; it does not create from nothing.** A missing certificate, a notary
  profile, a fresh key — `apple-credentials` makes those.
- **It does not upload or submit.** Signing correctly is a precondition for
  `ship-apple-app`.
- It changes project settings only with the user's agreement: a wrong signing setting
  committed to a shared project breaks every other machine.

## Reference files
- Certificate types, creation, `.p12` export, limits/roles → owned by the
  **`apple-credentials`** skill (its `certificate-types.md`). Defer there.
- [references/error-decoder.md](references/error-decoder.md) — common signing
  errors → cause → fix.
- [references/fastlane-match.md](references/fastlane-match.md) — shared signing
  for teams/CI.
- [scripts/diagnose_signing.py](scripts/diagnose_signing.py) — one-shot signing
  diagnostic.
