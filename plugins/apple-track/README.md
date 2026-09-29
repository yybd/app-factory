# apple-track

Everything Apple: the App Store and the Mac App Store, plus direct macOS
distribution outside them. Enable it in a repo that builds an Apple app.

<!-- generated:track -->
*Generated from the skills themselves by `factory/render_track_readmes.py` —
edit a skill, not this table.*

## The 16 skills

| Skill | What it is for | scripts | refs |
|---|---|---|---|
| `app-icon-generator` | Generate a complete Xcode app-icon set from a single source image (or create a starter icon if the user has none), sized to Apple's current icon sp… | 2 | 1 |
| `app-store-deliver` | Send an App Store listing to App Store Connect: sync the text and media into the app repo, verify against what is already live, then upload metadat… | 8 | 1 |
| `app-store-metadata` | Create, organize, translate, and validate App Store / Mac App Store listing metadata for an Xcode project — localized text (name, subtitle, descrip… | 2 | 3 |
| `app-store-review-compliance` | Audit a macOS or iOS Xcode project against Apple's App Store Review Guidelines and fix the issues that get apps rejected, BEFORE submitting to App… | 1 | 2 |
| `app-store-reviews-responder` | Monitor App Store / Mac App Store customer reviews and draft developer responses to them. | 1 | 1 |
| `apple-app-store-screenshots` | Conform an image that already exists to one of Apple's exact App Store screenshot sizes — resize, pad or crop, flatten alpha, write a validated PNG. | 1 | 1 |
| `apple-bug-flow-review` | Find real bugs in an Apple app and audit its user journeys end to end — static scan, build-time diagnostics, runtime sanitizers, then a flow-by-flo… | 2 | 4 |
| `apple-credentials` | The single owner of Apple developer credentials and certificates — checking what you have, explaining the types and why each is needed, creating th… | 1 | 2 |
| `apple-hig-design-review` | Review a macOS or iOS app's UI against Apple's Human Interface Guidelines (HIG) and produce prioritized, actionable design/UX/accessibility recomme… | 1 | 2 |
| `appstore-media` | Produce App Store screenshots and App Preview videos for iOS and macOS, from a scripted XCUITest demo flow that can be re-run every release. | 7 | 5 |
| `aso-keywords` | App Store Optimization (ASO) for APPLE discoverability — research and optimize the search-indexed fields of an App Store listing: the app name, sub… | 1 | 1 |
| `code-signing-provisioning` | Understand, diagnose, and fix Apple code signing and provisioning for macOS and iOS Xcode projects — certificates, identifiers, provisioning profil… | 1 | 2 |
| `localization-i18n` | Audit and manage IN-APP localization for a macOS or iOS Xcode project — the user-facing strings inside the app (Localizable.strings / .xcstrings St… | 1 | 1 |
| `macos-direct-distribution` | Set up direct (outside the Mac App Store) distribution for a macOS Xcode app: a dedicated "Direct" target — sandbox off, hardened runtime on, a DIR… | 3 | 3 |
| `notarize-and-distribute` | Take a built macOS app from an Xcode archive, package it into a signed DMG, notarize it with Apple, staple the ticket, and verify that everything —… | 1 | 1 |
| `ship-apple-app` | Verify an Apple app is submission-ready and ship it — the FINAL App Store / Mac App Store step: confirm the content is already in place (signing, c… |  | 1 |

**What it costs.** 12,920 characters of description ≈ 3,230 tokens, in every session
that enables this track. A skill's body is read only when the skill fires; its description
is in context always.

**What it needs on the machine**, from the scripts that call it: `fastlane`, `xcodebuild`, `xcrun`, `ffmpeg`, `ImageMagick`, `ruby`, `Pillow`, `sips`, `swift`.
<!-- /generated:track -->
