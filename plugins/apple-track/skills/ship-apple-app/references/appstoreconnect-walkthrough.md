# Developer portal & App Store Connect — navigation walkthrough

last-verified: 2026-06-02

These are the steps that can only be done on Apple's websites (not by fastlane
or local tooling). Apple changes the web UI periodically — if a label differs,
guide by intent and have the user confirm what they see. Give the user the exact
path and what to enter; you cannot click these for them.

- Developer portal: https://developer.apple.com/account/resources/
- App Store Connect: https://appstoreconnect.apple.com/

## 1. Developer portal — identifiers & signing

**Register the Bundle ID**
1. developer.apple.com → Account → Certificates, Identifiers & Profiles →
   **Identifiers** → **+**.
2. Choose **App IDs → App**. Description + explicit Bundle ID (e.g.
   `com.yourcompany.app`). Reverse-DNS, must be globally unique.
3. Under **Capabilities**, enable what the app uses (Sign in with Apple, Push
   Notifications, iCloud, App Groups, Associated Domains, …). These must match
   the app's entitlements.
4. Save. Repeat per app target (each shippable app needs its own Bundle ID).

**Signing**
- Easiest: in Xcode, target → Signing & Capabilities → **Automatically manage
  signing**, pick the team. Xcode creates certs/profiles as needed.
- Teams/CI: `fastlane match` stores and syncs distribution certs + profiles.
- macOS App Store specifics: needs **Apple Distribution** + **Mac App
  Distribution**/installer signing, **App Sandbox** enabled, and **Hardened
  Runtime** on. Verify these before archiving.

## 2. Create the app record

App Store Connect → **My Apps** → **+** → **New App**:
- **Platform(s)** — iOS and/or macOS.
- **Name** — public app name (≤30 chars; must be unique on the store).
- **Primary language**.
- **Bundle ID** — pick the one registered in step 1 (it must already exist).
- **SKU** — your internal identifier (any unique string).
- **User access** — full/limited.

(Alternatively `fastlane produce -u <apple_id> -a <bundle_id> --app_name "…"`.)

## 7. Finish and submit

Open the app → the version (e.g. "1.0 Prepare for Submission"):

**Select the build**
- After the binary finishes processing (minutes after upload), in the **Build**
  section click **+** / Select a build, and choose the uploaded build.

**Age Rating**
- App Information (or the version page) → **Age Rating → Edit** → answer the
  questionnaire honestly. This sets the rating; you can't type a rating directly.

**Pricing & Availability**
- Sidebar → **Pricing and Availability** → price tier (or Free) and territories;
  pre-orders if desired.

**App Privacy ("nutrition label")**
- Sidebar → **App Privacy → Edit/Get Started** → declare each data type
  collected, whether linked to identity, and whether used for tracking. This
  MUST match the app's actual behavior and the `PrivacyInfo.xcprivacy` manifest
  (the compliance skill checks the manifest side).

**Export Compliance (encryption)**
- Asked at submission (or set `ITSAppUsesNonExemptEncryption` in Info.plist to
  skip the prompt). Most apps using only standard HTTPS qualify for the exemption
  — but the user must answer truthfully.

**In-app purchases**
- Created under **Monetization → In-App Purchases** (or via API). A new IAP must
  be submitted **with** a version the first time. Localize each IAP's
  display name/description.

**Content rights, routing app coverage, etc.** — fill any remaining required
fields the version page flags (it shows a yellow warning per missing item).

## 8. Submit for review

- When every required item is green, click **Add for Review** → **Submit for
  Review**. Confirm with the user first — this is the irreversible "go".
- **Release option**: manual release (you press a button after approval),
  automatic, or scheduled.
- **Resolution Center**: if Apple replies or rejects, it appears here. Read the
  cited guideline number, fix, and reply in the same thread (you can attach a
  demo video / explain a demo mode here). For 2.1 "Information Needed", the fix
  is usually a demo path + clear review notes, not a code change to the feature.

## Tips
- The version page surfaces every missing required field as a warning — use it
  as the final checklist.
- "Manage" vs "Edit" links differ by section; if a label isn't found, search the
  left sidebar of the app's page.
- TestFlight (Beta) review is lighter than App Store review but uses the same
  builds — useful to validate processing/signing before the real submission.
