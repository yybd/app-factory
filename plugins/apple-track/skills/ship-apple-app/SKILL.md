---
name: ship-apple-app
description: >-
  Verify an Apple app is submission-ready and ship it — the FINAL App Store / Mac App
  Store step: confirm the content is already in place (signing, compliance, metadata,
  screenshots, app record), then archive, upload, complete the App Store Connect website
  steps, and submit. Use this when the user wants to release, publish, submit or upload
  an iOS or Mac build ("תעלה לאפסטור", "תשלח לבדיקה"), asks "how do I upload or submit to the App
  Store", or is at the end of the process and wants the verify → upload → submit
  checklist. This skill does NOT produce the listing copy, screenshots, compliance
  fixes, or signing — those are owned by their focused skills (app-store-metadata,
  appstore-media, app-store-review-compliance, apple-credentials,
  code-signing-provisioning). It VERIFIES their output is present and valid, then
  builds, uploads, and submits (including the website-only steps fastlane can't do).
---

# Ship an Apple App — verify & submit

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

This is the **final** step of the App Store / Mac App Store path. By the time you run
it, the content should already exist: signing set up, compliance passed, listing
metadata + screenshots produced, the app record created. **This skill does not
re-produce any of that** — it **verifies** each piece is ready, then **archives →
uploads → finishes on the App Store Connect website → submits**.

If a verification check fails, **hand off to the skill that owns that piece** to
produce it, then come back and re-verify. This skill owns only the ship itself
(build, upload, the website-only steps, submit).

## Prerequisites

- **Tools:** Xcode (`xcodebuild` archive/export, `xcrun altool`); `fastlane`
  (`gem install fastlane`) only if you archive with `gym` / `build_app`.
- **Credentials:** an App Store Connect API key, from the track's resolver
  (`shared/credentials.py`: env → `$KEYS_ROOT/credentials.json`). `altool` is the
  exception — it reads only `~/.appstoreconnect/private_keys/AuthKey_<KEY_ID>.p8`, so
  copy the resolved `.p8` there. Certificate and profiles via `apple-credentials` /
  `code-signing-provisioning`.
- **Hub (`$APP_HUB`):** optional — hub flow verifies the listing in
  `$APP_HUB/<slug>/store/apple/` and media in `$APP_HUB/<slug>/media/apple/`;
  standalone verifies the repo's own `fastlane/`.
- **Other tracks:** `store-metadata-writer` and `app-identity` (shared-track) — the
  hand-off targets when the listing or identity check fails.

## How to use
1. Detect where the user is: brand-new app or an update? App record already in App
   Store Connect? An update skips the one-time setup checks.
2. Run the **pre-flight verification** below. For anything missing or invalid, hand
   off to the owning skill, then re-verify — don't produce it here.
3. **Build → upload → finish-on-website → submit**, confirming before every
   outward-facing step.

## Pre-flight verification — confirm each is READY (don't produce here)

| Area | Verify it's ready | Owned/produced by |
|------|-------------------|-------------------|
| **App record + bundle ID** | the bundle ID is registered (portal) and the app record exists in App Store Connect | one-time portal/ASC setup |
| **App name & identity** | the on-device display name is set, and the listing **name**/**subtitle** are decided and consistent with it (the README identity block matches the build settings) | `app-identity` (decides the names early + owns the README source of truth) |
| **Signing** | Apple Distribution cert + profile present; MAS build is sandboxed + Hardened Runtime | `apple-credentials` (certs/credentials) · `code-signing-provisioning` (config/errors) |
| **Compliance** | no blockers — run the build-time checklist | `app-store-review-compliance` |
| **Listing metadata + IAP** | every locale present and within Apple's limits (run the validator); IAP localizations + reviewer screenshot present | `app-store-metadata` authors/validates it (SoT in the hub `$APP_HUB/<slug>/store/apple/`); **`app-store-deliver`** syncs it into `fastlane/` and uploads it (listing + screenshots + IAP) at send. Verify in the hub |
| **Screenshots** | exact sizes for every required device class, all locales — for the studio apps the source media lives in the hub at `$APP_HUB/<slug>/media/apple/` | `appstore-media` (capture) · `apple-app-store-screenshots` (conform) |
| **In-app localization** | UI fully localized if shipping multi-locale | `localization-i18n` |
| **Design** (optional) | no high-impact accessibility/HIG issues | `apple-hig-design-review` |

**Verify, don't re-produce.** If an item is missing or invalid, hand off to the
owning skill above, then return here.

## Build & archive  [local]
- Bump version/build number (build must be higher than any previously uploaded).
- Archive the App Store target (Xcode: Product → Archive, or `fastlane gym`/`build_app`).
- **Keep the marketing version and the ASC version record's `versionString` in
  step.** They are set in two different places and drift silently, and ASC gives no
  useful error when they disagree — the build simply never appears as selectable.
  Read the record before archiving and match it, or update the record
  (`versionString`) to the build. Seen on a real 1.0.0 submission.

  **A trailing `.0` is the exception, and it is worth knowing which.** A record
  reading `2.0` took a `2.0.0` build and reached `READY_FOR_SALE`; the next release
  did the same, `2.1` against `2.1.0`, on both platforms of the record. So a
  two-part store version over a three-part build is a normal, working combination
  and not a drift to go fixing. The evidence is bounded, though: those builds were
  attached over the API (`relationships/build`), which is what this skill does
  headless anyway — it does not prove the ASC website's build picker lists them.
  If you are guiding someone through the picker and the build is absent, an
  unmatched `.0` is the first thing to test.

### Headless archive → export → upload (no Xcode UI)
Product → Archive and the Organizer are unavailable in an agent session; this is the
whole path. Both steps below are per-platform — a universal app runs each twice.

```bash
xcodebuild -project App.xcodeproj -scheme <Scheme> -configuration Release \
  -destination 'generic/platform=macOS'   \  # or 'generic/platform=iOS'
  -archivePath build/App-mac.xcarchive archive
xcodebuild -exportArchive -archivePath build/App-mac.xcarchive \
  -exportPath build/export-mac -exportOptionsPlist build/ExportOptions-mac.plist
```

The export options that actually matter:
- `method` = `app-store-connect`.
- **`signingStyle: manual`** with an explicit `provisioningProfiles` map. Automatic
  signing fails the export with *"No profiles for '<bundle id>' were found"*, and
  `-allowProvisioningUpdates` does **not** rescue it even with
  `-authenticationKeyPath/-authenticationKeyID/-authenticationKeyIssuerID` — see
  `code-signing-provisioning` for creating the profiles first.
- `signingCertificate` = `Apple Distribution`.
- **macOS only: `installerSigningCertificate` = `3rd Party Mac Developer Installer`.**
  Without it the export fails with *"Provisioning profile … doesn't include signing
  certificate '3rd Party Mac Developer Installer'"* — the `.pkg` wrapper is signed by
  a different certificate than the app inside it, and this key is the only way to say so.

Export produces `App.ipa` (iOS) or `App.pkg` (macOS).

## Upload  [local]
- **Validate before uploading** — it catches what would otherwise come back as a
  rejection email minutes later, and costs one command:
  ```bash
  xcrun altool --validate-app -f build/export-ios/App.ipa -t ios \
    --apiKey <KEY_ID> --apiIssuer <ISSUER_ID>          # -t macos for the .pkg
  ```
  altool reads the key from `~/.appstoreconnect/private_keys/AuthKey_<KEY_ID>.p8` and
  will not take a `--file` path — copy it there from wherever the resolver reports it
  (`python3 ${CLAUDE_PLUGIN_ROOT}/shared/credentials.py`).
- Upload with the same command shape, `--upload-app`. Processing takes minutes — wait
  for the build to reach `VALID` before selecting it.
- **Attach the build to the version record.** Uploading does not select it; a version
  left with no build cannot be submitted, and the ASC website is the usual place this
  is done by hand. Headless, it is `select_build(build_id:)` on the edit version.
- Upload the verified metadata/screenshots/**IAP** by **triggering the
  `app-store-deliver` skill** (the single send-surface) — don't deliver from here
  yourself. In the **hub flow** it syncs the hub tree → `fastlane/` at send time
  (not during authoring), uploads listing + screenshots + IAP via the official ASC
  API, and authenticates with the `.p8` the track's resolver finds. Authoring the metadata
  into the hub is a separate, earlier task (`store-metadata-writer` → the metadata
  workers) — it doesn't sync or upload.
- **`app-store-deliver` verifies completeness and gates the upload.** If its
  `sync_from_hub.sh` reports missing data and exits non-zero, **stop — nothing is
  delivered.** It names the missing locale + field; hand off to `store-metadata-writer`
  to fill the hub, then re-trigger `app-store-deliver`.

## Finish on the App Store Connect website  [website — fastlane can't]
Guide the user through each, with exact navigation:
- Select the uploaded **build** for the version.
- **Age rating** questionnaire · **Pricing & availability** · **App Privacy** nutrition
  label (must match the privacy manifest / real behavior) · **Export compliance** ·
  content rights; any IAPs created & submitted with the version.
- Walkthrough: [references/appstoreconnect-walkthrough.md](references/appstoreconnect-walkthrough.md#7-finish-and-submit).

## Submit
- **Submit for Review** (never auto-submit without the user's explicit go-ahead).
- Choose manual vs automatic release.
- If rejected: read the resolution-center message, map it to a guideline (the
  `app-store-review-compliance` skill helps), fix, and reply/resubmit.

## Boundaries
- You cannot operate the App Store Connect website or the developer portal for the
  user — for every website step, give the exact menu path and what to enter, then wait
  for them to confirm.
- Uploading and submitting are outward-facing and often irreversible — always confirm
  before an upload/submit command or before telling the user to press Submit.

## Reference files
- [references/appstoreconnect-walkthrough.md](references/appstoreconnect-walkthrough.md)
  — navigation-level steps for the portal + App Store Connect website parts.

## Related skills (they produce; this skill verifies + ships)
- `app-identity` — decides the app name/subtitle early and owns the README source of truth (verify the on-device name and listing name/subtitle are set & consistent).
- `app-store-deliver` — the single send-surface this skill **triggers** to upload listing + screenshots + IAP (ASC API); it syncs from the hub and verify-gates the upload.
- `apple-credentials` · `code-signing-provisioning` — signing/credentials (verify ready).
- `app-store-review-compliance` — compliance (verify it passes).
- `app-store-metadata` — authors and validates the listing metadata files (verify
  present/valid). It does **not** upload; `app-store-deliver`, above, is the send-surface.
- `appstore-media` · `apple-app-store-screenshots` — screenshots/preview (verify present; for the studio apps the source lives in the hub at `$APP_HUB/<slug>/media/apple/`).
- `aso-keywords` — keyword optimization (applied upstream, into the metadata).
- `localization-i18n` — in-app strings (verify complete).
- `notarize-and-distribute` — the parallel path for direct (non-App-Store) Mac
  distribution (Developer ID DMG), instead of upload/submit here.
