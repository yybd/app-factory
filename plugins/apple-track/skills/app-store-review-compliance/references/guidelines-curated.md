# Curated App Store Review Guidelines — rejection-prone items

last-verified: 2026-06-02
source: https://developer.apple.com/app-store/review/guidelines/

This is a working digest of the guidelines that *actually* cause rejections,
not the full document. Each item gives: the rule (paraphrased) + number, how to
detect it in an Xcode project, the default severity, and the fix. Platform tags:
`[iOS]`, `[macOS]`, `[both]`. Severities are defaults — adjust to context.

When the live guidelines may have changed, reconcile via
[refresh-from-web.md](refresh-from-web.md) and bump `last-verified`.

## Table of contents
- [1. Safety](#1-safety)
- [2. Performance](#2-performance)
- [3. Business](#3-business)
- [4. Design](#4-design)
- [5. Legal](#5-legal)
- [Platform-specific: macOS / Mac App Store](#platform-specific-macos--mac-app-store)
- [Privacy manifest & Required-Reason APIs](#privacy-manifest--required-reason-apis)
- [Worked pattern: demo mode for 2.1](#worked-pattern-demo-mode-for-21)

---

## 1. Safety

### 1.5 Developer/support contact `[both]` 🟡
Rule: a working support URL/contact must be available.
Detect: missing/placeholder `support_url` in metadata, dead link.
Fix: provide a real reachable URL.

### 1.x User-generated content `[both]` 🟠
Rule (1.2 / UGC): apps with user content need a filtering mechanism, a way to
report offensive content, the ability to block abusive users, and a published
way to contact you. Required if the app has comments, chat, posts, uploads.
Detect: networking + content-submission UI, no report/block UI.
Fix: add report-content + block-user + EULA/contact. Don't auto-build; flag.

---

## 2. Performance

### 2.1 App completeness `[both]` 🔴 — the #1 cause of "Information Needed"
Rule: the app must be complete and fully testable by the reviewer. The reviewer
gets a clean machine and will NOT install other software, create external
accounts, or supply hardware. If your app needs any of those to show its
features, you must provide a **demo account** or **built-in demo mode** that
exercises the full functionality without them. Apple's wording: the demo "must
enable a complete review without requiring App Review to install another app."
Detect (signals, confirm by reading code):
- A login/onboarding gate with no demo credentials in review notes.
- Code that targets another app's presence (e.g. `bundleIdentifier ==
  "com.microsoft.Word"`, `runningApplications`, Apple Events to a third-party
  app) — if that app isn't on the review machine, the UI is empty.
- Hardware dependence (BLE peripheral, specific camera) with no simulated path.
Fix:
- Provide demo credentials in App Review notes, OR
- Build a demo mode that populates representative data and keeps the UI
  interactive (see [Worked pattern](#worked-pattern-demo-mode-for-21)), AND
- Document exactly how the reviewer reaches it in review notes (a hidden demo
  toggle the reviewer can't find is the same as no demo). Optionally attach a
  demonstration video — but a video supplements, never replaces, the demo path.
Severity 🔴 because it blocks the review entirely.

### 2.3 Accurate metadata `[both]` 🟡
Rule: screenshots/description must reflect actual functionality; no hidden,
dormant, or undocumented features; don't mention other platforms.
Detect: features in description not present in build; placeholder screenshots.
Fix: align metadata with the build (out of this skill's code scope — flag it).

### 2.3.10 Irrelevant platform references `[both]` 🟡
Rule: don't reference Android/other platforms or include their names in
metadata. Detect: "Android", competitor names in description. Fix: remove.

### 2.4.1 iPad multitasking — all four orientations `[iOS]` 🔴 (upload-time validation)
Rule: an iPad app that does NOT opt out of multitasking (no
`UIRequiresFullScreen = YES`) must declare all **four** interface orientations —
`UIInterfaceOrientationPortrait`, `UIInterfaceOrientationPortraitUpsideDown`,
`UIInterfaceOrientationLandscapeLeft`, `UIInterfaceOrientationLandscapeRight`.
Enforced at **binary upload**, not human review: the build is rejected with
*"Invalid bundle. The '…' orientations were provided for the
UISupportedInterfaceOrientations Info.plist key … but you need to include all of
the '…four…' orientations to support iPad multitasking."* Applies to any target
whose `TARGETED_DEVICE_FAMILY` includes iPad (`2`), e.g. universal `"1,2"`.
Detect: scanner `ipad_multitasking_orientations.likely_finding`
(targets_ipad && !requires_full_screen && base orientations missing
PortraitUpsideDown).
THE TRAP (why a correct-*looking* project still fails): the `~ipad` device
suffix on `INFOPLIST_KEY_*` build settings is **silently ignored** by
`GENERATE_INFOPLIST_FILE`. `INFOPLIST_KEY_UISupportedInterfaceOrientations~ipad`
does not appear in `xcodebuild -showBuildSettings` and never reaches the
generated Info.plist — so a project can set the iPad split to all four, look
right, and still ship the base three. Verify against the **base** key, not the
`~ipad` one. (A real `Info.plist` *file* with a `UISupportedInterfaceOrientations~ipad`
array DOES work — the trap is specific to the build-setting form.)
Fix (safe): put all four orientations on the BASE
`INFOPLIST_KEY_UISupportedInterfaceOrientations`, in **every** config
(Debug + Release). iPhone then also lists upside-down, which is harmless —
Face ID iPhones never rotate upside-down regardless; only the Touch-ID SE honors
it, and any rotation-capable layout handles it.
Alternative (ask first): `INFOPLIST_KEY_UIRequiresFullScreen = YES` opts the app
out of multitasking and drops the four-orientation requirement — but it disables
Split View / Slide Over, a worse iPad experience. Don't pick it just to silence
the validator.

### 2.5.1 Public APIs only `[both]` 🟠
Rule: use only public APIs; don't call private/SPI, don't load executable code,
don't change primary purpose via update.
Detect: `dlopen`/`dlsym`, `performSelector` on private selectors, `valueForKey`
on private ivars, runtime swizzling of system internals, downloaded JS that
changes behavior. Fix: remove/replace; flag for manual review.

### 2.5.2 No downloading executable code `[both]` 🟠
Rule: don't download code that changes features. (JS in a WebView for content
is fine.) Detect: remote bundle/dylib download + load. Fix: flag.

---

## 3. Business

### 3.1.1 In-App Purchase for digital goods `[both]` 🔴
Rule: unlock features/content/subscriptions **only** through StoreKit IAP. Do
NOT link to or steer users toward external purchase mechanisms for digital
goods. (Physical goods/services use other payment and must NOT use IAP.)
Detect:
- StoreKit present (`import StoreKit`, `Product.purchase`) — good for digital.
- External purchase signals: `SKStoreProductViewController` aside, links like
  `openURL(... /buy, /upgrade, /pricing, stripe, paypal, checkout ...)` near
  paywall copy. A "manage subscription on our website" link is a classic reject.
Fix: route digital unlocks through IAP; remove external buy links/steering.
Flag — don't rip out payment code automatically.

### 3.1.1 Restore purchases `[both]` 🟠
Rule: users must be able to restore previously bought non-consumables/
non-renewing items. Detect: StoreKit purchase code but no `Transaction`
restore / `AppStore.sync()` / "Restore Purchases" button. Fix: add a Restore
affordance (stub is safe to add; wiring needs care — flag).

### 3.1.2 Subscriptions `[both]` 🟠
Rule: subscription apps must show terms, price, period, and link to privacy/
terms before purchase; provide functional content. Detect: `*.subscription`
products without a disclosure screen. Fix: add the standard disclosure block.

### 3.1.3(b) "Reader" / multiplatform `[both]` ⚪
Context-dependent exceptions to 3.1.1 (reader apps, etc.). Usually not relevant;
note only if the app is clearly a reader/enterprise case.

---

## 4. Design

### 4.0 / 4.2 Minimum functionality `[both]` 🟡→🟠
Rule: the app must be more than a repackaged website, a thin wrapper, or a
single trivial feature; it should offer lasting value and native experience.
Detect: app is essentially one `WKWebView` pointed at a site; almost no native
UI; "marketing app". Fix: add genuine native functionality, or reposition.
Flag — this is a product judgment.

### 4.8 Login Services (Sign in with Apple) `[both]` 🟠
Rule: if the app uses a third-party or social login service (Google, Facebook,
etc.) as a *primary* sign-in, it must also offer an equivalent privacy-friendly
option — in practice, **Sign in with Apple** — that limits data collection to
name+email, supports private email relay, and doesn't track without consent.
(Exceptions: your own account system only, education/enterprise, or a login
that's purely the provider's own app.)
Detect: `GIDSignIn`, `FBSDKLoginKit`, `LoginManager`, OAuth to google/facebook,
and NO `ASAuthorizationAppleIDProvider` / `SignInWithAppleButton`.
Fix: add Sign in with Apple (capability + Apple Developer config + UI). Ask —
it's real work and a config change.

### 4.5.x Apple services use `[both]` ⚪
Don't misuse Apple Push, Game Center, Maps attribution, etc. Note only if used.

---

## 5. Legal

### 5.1.1(i) Privacy — usage strings `[both]` 🔴
Rule: you must request permission and explain *why* before accessing protected
data/resources. On iOS a missing purpose string **crashes** on access; either
way it's a rejection. Detect: API usage with no matching `Info.plist` key.
Common pairs (see full table in scanner output):
- Camera → `NSCameraUsageDescription`
- Microphone → `NSMicrophoneUsageDescription`
- Photos → `NSPhotoLibraryUsageDescription` / `...AddUsageDescription`
- Location → `NSLocationWhenInUseUsageDescription` / `...AlwaysAndWhenInUse...`
- Contacts → `NSContactsUsageDescription`
- Calendars → `NSCalendarsUsageDescription` (+ Full/Write variants on newer OS)
- Reminders → `NSRemindersUsageDescription`
- Bluetooth → `NSBluetoothAlwaysUsageDescription`
- Local network → `NSLocalNetworkUsageDescription`
- Speech → `NSSpeechRecognitionUsageDescription`
- Motion → `NSMotionUsageDescription`
- FaceID → `NSFaceIDUsageDescription`
- Apple Music/Media → `NSAppleMusicUsageDescription`
- [macOS] Apple Events automation → `NSAppleEventsUsageDescription`
Fix (safe): add the missing key with an honest purpose string; flag for wording.

### 5.1.1(v) Account deletion `[both]` 🟠
Rule: if the app supports **account creation**, it must let users **initiate
account deletion from within the app** (not just deactivate, not "email us").
Detect: signup/registration code (`createUser`, `/register`, `/signup`,
Firebase `createUser`, your own auth) with no in-app delete-account path.
Fix: add an in-app "Delete Account" flow. Ask — needs backend + UX.

### 5.1.1 ATT — tracking `[both]` 🔴 if tracking present
Rule: to track users across apps/sites owned by other companies, or to access
the IDFA, you must use the App Tracking Transparency prompt and respect the
choice. Detect: `ATTrackingManager`, `advertisingIdentifier`, third-party ad/
analytics SDKs (AppsFlyer, Adjust, Facebook) AND missing
`NSUserTrackingUsageDescription`. Fix (safe to add the string): add
`NSUserTrackingUsageDescription` and ensure the ATT prompt precedes tracking;
flag the call-ordering.

### 5.1.1 / 5.1.2 Privacy policy + data use `[both]` 🟠
Rule: a privacy policy URL is required; data collection must match the App
Privacy ("nutrition label") declarations and the privacy manifest. Detect:
missing privacy URL; SDKs that collect data not declared. Fix: provide URL;
align declarations (mostly metadata — flag).

### 5.1.2 Permission minimization `[both]` 🟡
Rule: only request access you actually use; data gathered for one purpose can't
be repurposed without consent. Detect: a usage string / entitlement present but
no corresponding API use (the inverse of 5.1.1) — looks like over-asking.
Fix: remove the unused permission/entitlement. Ask before removing.

---

## Platform-specific: macOS / Mac App Store

### App Sandbox `[macOS/MAS]` 🔴 for MAS
Rule: Mac App Store apps must enable App Sandbox
(`com.apple.security.app-sandbox = true`). Detect: MAS target `.entitlements`
without app-sandbox, or with it false. Fix: enable; add only the specific
sandbox entitlements the app needs.

### Sensitive / temporary-exception entitlements `[macOS/MAS]` 🟠
Rule: entitlements that widen sandbox access must be necessary and justified to
review. `com.apple.security.temporary-exception.*` especially invites scrutiny.
Detect entitlements such as:
- `com.apple.security.temporary-exception.apple-events` (scope it to the exact
  bundle IDs you send events to — not a broad list)
- `com.apple.security.automation.apple-events`
- `com.apple.security.cs.disable-library-validation`
- `com.apple.security.cs.allow-unsigned-executable-memory`
- broad file access (`...files.user-selected.read-write` is normal; broad
  `...files.all` is suspicious)
Fix: keep only what's needed; narrow scopes; prepare a one-paragraph
justification per sensitive entitlement for the review notes (safe to draft).

### Hardened Runtime `[macOS]` 🟠
Rule: notarized/MAS apps need Hardened Runtime
(`ENABLE_HARDENED_RUNTIME = YES`). Detect: build setting off. Fix: enable;
add only the specific runtime exceptions required (and justify them).

### LSUIElement / background agents `[macOS]` ⚪
Menu-bar/agent apps (`LSUIElement = true`, no Dock icon) are fine, but the
reviewer may not realize the app launched. Note it in review notes and make the
menu-bar entry discoverable. (Relevant to 2.1 — see the worked pattern.)

---

## Privacy manifest & Required-Reason APIs

### PrivacyInfo.xcprivacy — Required-Reason APIs 🔴 iOS family / ⚪ macOS
**PLATFORM APPLICABILITY — check this first, it changes the severity:**
The Required-Reason API manifest declaration is enforced (ITMS-91053, rejection
since 2024-05-01) only on **iOS, iPadOS, tvOS, watchOS, and visionOS**. Apple
does **NOT** require the Required-Reason API declaration for **macOS** apps. So:
- `[iOS/iPadOS/tvOS/watchOS/visionOS]` → 🔴 a missing/incomplete manifest when
  Required-Reason APIs are used is a (often automated) rejection.
- `[macOS]` → ⚪ not required. A correct manifest is harmless and good practice
  (future-proofs an iOS port, feeds the Xcode privacy report), but do NOT report
  its absence as a blocker for a macOS-only app. (The App Store Connect "App
  Privacy" nutrition label, however, IS required on macOS too — that's a
  separate, website-side declaration, not this file.)

Rule (on the platforms above): the app — and each bundled **third-party SDK on
Apple's "commonly used" list** — must include a `PrivacyInfo.xcprivacy`
declaring collected data types, tracking, tracking domains, and Required-Reason
API usage with an approved reason code. The app's own manifest does NOT cover
SDKs; every such SDK needs its own manifest inside its bundle (and a valid
signature). Missing SDK manifests are a very common ITMS-91053 cause.

Required-Reason API categories — Apple defines **exactly these five** (there are
no others; "more coverage" means more detection patterns + reason codes per
category, not new categories). Detect usage in code and map to a reason:
- **File timestamp** → `NSPrivacyAccessedAPICategoryFileTimestamp`. APIs:
  `creationDate`, `modificationDate`, `.fileModificationDate`,
  `NSFileModificationDate`, `contentModificationDateKey`,
  `URLResourceKey.contentModificationDateKey`, `stat`/`fstat`/`lstat`,
  `getattrlist`, `NSFileManager.attributesOfItem`. Reasons: `C617.1` (display to
  user / same app), `3B52.1` (access by another process the user initiated),
  `0A2A.1` (3rd-party SDK on behalf of app), `DDA9.1` (file timestamp APIs).
- **System boot time** → `...CategorySystemBootTime`. APIs: `systemUptime`,
  `mach_absolute_time`, `clock_gettime(CLOCK_UPTIME...)`, `NSProcessInfo`
  uptime. Reasons: `35F9.1` (measure elapsed time), `8FFB.1` (calc absolute
  timestamps for in-app events).
- **Disk space** → `...CategoryDiskSpace`. APIs: `volumeAvailableCapacity*`,
  `systemFreeSize`, `systemSize`, `NSFileSystemFreeSize`,
  `statfs`/`statvfs`/`fstatfs`. Reasons: `E174.1` (write/delete to avoid
  failures), `85F4.1` (display to user), `7D9E.1` (3rd-party SDK on behalf of
  app), `B728.1` (health/fitness data).
- **Active keyboards** → `...CategoryActiveKeyboards`. APIs: `activeInputModes`,
  `UITextInputMode.activeInputModes`. Reasons: `3EC4.1` (custom-keyboard app
  using it for its own keyboards), `54BD.1` (present correct UI for active
  keyboards).
- **User defaults** → `...CategoryUserDefaults`. APIs: `UserDefaults`,
  `NSUserDefaults`. Reasons: `CA92.1` (read/write info accessible only to the
  app itself), `1C8F.1` (app-group container shared by your apps), `C56D.1`
  (3rd-party SDK reading its own defaults), `AC6B.1` (`UserDefaults` to access
  managed-app config / MDM).
Fix (safe to scaffold, on iOS-family targets): create `PrivacyInfo.xcprivacy`
(a plist) with `NSPrivacyAccessedAPITypes` entries for each detected category +
the inferred reason; mark uncertain reasons `TODO:` for the user to confirm. Set
`NSPrivacyTracking`, `NSPrivacyTrackingDomains`, `NSPrivacyCollectedDataTypes`
to match actual behavior (don't guess data collection — ask). For a flagged SDK
without a manifest, the fix is upgrading to a version that ships one or
contacting the vendor — you cannot author another vendor's manifest for them.

A minimal manifest skeleton lives at
[../assets/PrivacyInfo.template.xcprivacy](../assets/PrivacyInfo.template.xcprivacy).

---

## Worked pattern: demo mode for 2.1

When an app is useless on a clean review machine (needs another app, a login, or
hardware), a good demo mode makes it reviewable. What "good" means here — Apple
must be able to verify *all features*, so the demo has to look and behave like a
working app, not a static screen.

Principles, learned from real rejections:
1. **Discoverable.** A demo toggle the reviewer can't find = no demo. If it's
   hidden (e.g. behind an Option-click in a menu-bar app), you MUST spell out
   the exact steps in review notes, or make it visible. Undiscoverable demo
   modes get the same rejection a second time.
2. **Interactive, not a frozen screenshot.** Populate representative sample data
   AND keep controls responsive. If tapping an item normally switches to a real
   document you can't show, at least reflect the tap (select/highlight) so the
   reviewer sees the UI responds — a dead no-op reads as "broken app", not
   "no backing app".
3. **Don't fight the user.** Watch for background timers/pollers that overwrite
   demo state (e.g. a refresh loop that re-hides the bar after the reviewer
   shows it). Set demo state once; don't let polling stomp it.
4. **Show paid tiers.** If there's a freemium gate, seed enough demo data to
   cross the free limit so the "locked"/upgrade state is visible, and make the
   upgrade (IAP) reachable so the reviewer can test it (sandbox).
5. **Set expectations in notes.** Tell the reviewer which path to use (real
   dependency if they have it, demo otherwise), that the two are mutually
   exclusive if so, and what each control does. Attaching a short demonstration
   video helps — as a supplement, not a substitute.

Because demo mode is code that ships to real users, design it WITH the user —
don't auto-generate it. Offer the pattern and implement once agreed.
