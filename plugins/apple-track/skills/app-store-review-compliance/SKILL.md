---
name: app-store-review-compliance
description: >-
  Audit a macOS or iOS Xcode project against Apple's App Store Review Guidelines and fix
  the issues that get apps rejected, BEFORE submitting to App Store Connect. Use this
  whenever the user is preparing an app for the App Store or Mac App Store ("נדחה
  באפסטור", "בדוק תאימות"), mentions an Apple rejection or a guideline number (e.g.
  "2.1", "5.1.1", "Guideline 3.1.1"), asks why their app might get rejected, talks about
  App Review / demo accounts / demo mode / review notes, or is about to archive/upload a
  build. ALSO consult this skill at build time — before archiving or uploading — so the
  app ships compliant the first time. Covers privacy usage strings,
  PrivacyInfo.xcprivacy + Required-Reason APIs, ATT, IAP rules, Sign in with Apple,
  account deletion, sandbox/entitlements justification, and app-completeness (demo mode)
  requirements. It audits against App Review policy; it does NOT review visual design
  (apple-hig-design-review) or hunt for bugs (apple-bug-flow-review).
---

# App Store Review Compliance

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

Apple rejects apps for a fairly predictable set of reasons. This skill scans an
Xcode project, maps what it finds against the guidelines that actually cause
rejections, reports the gaps with severities, and fixes the safe ones — so a
submission passes on the first try instead of bouncing through multiple review
cycles (each costing days).

The guideline knowledge lives in [references/guidelines-curated.md](references/guidelines-curated.md)
— a curated, dated digest organized by Apple's section numbers. It is the
shared source of truth for both modes below, so the same rules that catch
problems in an audit also steer the app while it's being built.

## Prerequisites

- **Tools:** none beyond Claude Code and Xcode; `scripts/scan_project.py` is stdlib
  Python 3.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — only the conversational-language default in `DATA.md`.
- **Other tracks:** `play-store-compliance` (android-track) owns the Google Play side.

## Two ways this skill is used

**Audit mode** — the user wants a full compliance pass on an existing project
("is this ready for the App Store?", "why did Apple reject this?", "review my
app before I submit"). Run the whole workflow below.

**Build-time mode** — the user is creating or changing app code and you want to
avoid baking in a rejection. You don't need the full audit; instead, before
archiving/uploading (or while adding a sensitive feature — camera, login,
purchases, tracking), read [references/guidelines-curated.md](references/guidelines-curated.md)
and apply the relevant rules to what you're writing. The "Build-time checklist"
section near the end is the short version.

## Audit workflow

### 1. Understand the project

Identify, before judging anything:
- **Platform(s)** — iOS, macOS, or both. Many rules are platform-specific; the
  curated reference tags each item `[iOS]`, `[macOS]`, or `[both]`.
- **Distribution** — App Store vs Mac App Store (MAS). MAS adds sandbox and
  entitlement-justification requirements that direct-distribution builds skip.
- **Targets** — there may be several app targets (one project can ship several
  apps, each with its own bundle id). Audit each shippable target.

Locate the `.xcodeproj`/`.xcworkspace`, the `Info.plist`(s), `.entitlements`
files, any `PrivacyInfo.xcprivacy`, StoreKit config, and the source tree.

### 2. Gather deterministic signals

Run the scanner — it does the mechanical detection (which usage strings exist,
which sensitive APIs/entitlements are used, whether StoreKit/login/account code
is present) so you don't do it by hand and miss something:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/app-store-review-compliance/scripts/scan_project.py <project-root>
```

It prints JSON: detected platform, targets, plist keys present, API usages that
imply a required usage string or privacy-manifest reason, sensitive
entitlements, and feature flags (StoreKit, auth, account creation, external
purchase URLs). Treat it as evidence to interpret — not a verdict. It can miss
things and it can over-flag; confirm each signal against the actual code before
reporting it.

### 3. Map signals to guidelines

Read [references/guidelines-curated.md](references/guidelines-curated.md) and,
for each relevant rule, decide whether this project complies. Combine the
scanner output with your own reading of the code — e.g. the scanner can tell you
`AVCaptureDevice` is referenced and `NSCameraUsageDescription` is absent
(a finding), but only reading the code tells you whether a login screen has no
demo path (a 2.1 finding the scanner only hints at).

### 4. (Hybrid) Refresh against the live guidelines

The curated reference has a `last-verified` date. If it's stale (say >60 days),
or the user asks to be sure it's current, or the app is in a fast-moving area
(privacy, AI, crypto), follow [references/refresh-from-web.md](references/refresh-from-web.md)
to fetch the live guidelines and reconcile. Report any drift you find and offer
to update the curated reference — don't silently trust a possibly-stale digest
on a high-stakes submission.

### 5. Report

Produce the report using the exact template below. Lead with blockers; an
engineer should be able to act on each finding without rereading the guidelines.

### 6. Fix

Apply **safe** fixes directly, then list them. **Ask first** for anything that
changes product behavior, adds dependencies, or touches signing/entitlements.
See "What's safe to auto-fix" below.

## Severity tiers

Order every report by these. The point of the tiers is to separate "this *will*
be rejected" from "an unlucky reviewer *might* complain", so the user spends
effort where it matters.

- **🔴 Blocker** — Apple will almost certainly reject. Hard technical violations:
  a sensitive API used with no usage string (guaranteed crash-on-permission or
  rejection), missing required privacy manifest, external payment links for
  digital goods, app non-functional without a separately-installed app and no
  demo path.
- **🟠 Likely rejection** — commonly enforced and frequently cited; fix before
  submitting. E.g. account creation with no in-app deletion, social login with
  no Sign in with Apple, unjustified sensitive entitlement.
- **🟡 Risk** — depends on reviewer/context; worth addressing or pre-empting in
  review notes. E.g. thin/minimum-functionality concerns, permissions requested
  but seemingly unused.
- **⚪ Info** — good practice / forward-looking, not a rejection basis today.

## Report structure

ALWAYS use this template:

```
# App Store Review Compliance Report — <app/target name>
Platform: <iOS / macOS / both>   Distribution: <App Store / Mac App Store>
Guidelines reference: curated digest (last-verified <date>)<, refreshed against live guidelines on <date> if done>

## Summary
<N blockers, N likely, N risks. One-sentence verdict: ready / not ready to submit, and the single most important thing to fix.>

## 🔴 Blockers
### [<guideline #>] <short title>
- Where: `path/to/file.swift:line` (or "project-wide" / Info.plist key)
- Problem: <what violates the guideline, concretely>
- Guideline: <one-line paraphrase of the rule + the number>
- Fix: <the specific change>
- Auto-fixable: yes (applied) / yes (needs approval) / no (manual)

## 🟠 Likely rejection
<same shape>

## 🟡 Risks
<same shape>

## ⚪ Info
<same shape>

## Fixes applied
<bullet list of what you changed, with file paths>

## Needs your decision
<changes you did NOT make because they affect behavior/signing/deps — each with the recommended action>
```

If there are zero findings in a tier, write "None" under it rather than dropping
the heading — the reader should see you checked.

## Boundaries

- **It audits against App Review policy, and nothing else.** Visual design is
  `apple-hig-design-review`'s; real defects are `apple-bug-flow-review`'s; Google
  Play's rules are `play-store-compliance`'s and barely overlap.
- **It does not submit.** Passing here is a precondition for `ship-apple-app`.
- A fix that changes what the app does is proposed, never applied silently — a
  permission or a privacy string is a product decision.

## What's safe to auto-fix

Apply without asking (they're additive, reversible, and don't change runtime
behavior or product decisions):
- Adding a **missing `NS*UsageDescription`** string to Info.plist with a clear,
  honest purpose string (flag it so the user can refine the wording).
- Scaffolding a **`PrivacyInfo.xcprivacy`** with the Required-Reason API entries
  implied by the code (fill reasons you can infer; mark the rest `TODO:`) — but
  only treat its absence as a *blocker* on iOS/iPadOS/tvOS/watchOS/visionOS; on
  **macOS** the Required-Reason manifest is not required (see the reference),
  so offer it as optional good practice, not a finding.
- Drafting/updating **App Review notes** and demo-mode instructions (as text /
  fastlane `review_information/notes.txt`), like documenting how a reviewer
  reaches a demo path.
- Adding a **Restore Purchases** affordance stub where StoreKit purchases exist
  but no restore is found — but flag it, since wiring matters.

Ask first (these are product or trust decisions, or hard to reverse):
- Removing a permission, entitlement, or capability.
- Adding **Sign in with Apple** (UI + capability + Apple Developer config).
- Adding an **account-deletion** flow (needs backend + UX).
- Changing **payment** flows or removing external links.
- Anything touching **signing, sandbox, or Hardened Runtime** settings.
- Building an in-app **demo mode** (it's code that ships to real users — design
  it with them; see the worked pattern in the reference). This is the *App Review*
  demo path — letting a reviewer use the app past a login/paywall. Don't confuse
  it with the *marketing-capture* demo mode in the `appstore-media` skill, which
  seeds attractive data for screenshots (one launch argument can serve both, but
  the goals differ).

## Build-time checklist

Before archiving or uploading, or when adding a feature, verify the high-signal
items (full detail in the reference):
- Every permission you trigger has an honest `NS*UsageDescription`.
- [iOS family] If you read any Required-Reason API (UserDefaults, file
  timestamps, disk space, system boot time, active keyboards),
  `PrivacyInfo.xcprivacy` declares a valid reason — and each bundled
  commonly-used SDK ships its own manifest. (Not required on macOS.)
- [iPad] If a target supports iPad (`TARGETED_DEVICE_FAMILY` includes `2`) and
  doesn't set `UIRequiresFullScreen = YES`, the **base**
  `UISupportedInterfaceOrientations` lists all four orientations (incl.
  `PortraitUpsideDown`), or upload fails iPad-multitasking validation. The
  `INFOPLIST_KEY_…~ipad` build setting is silently ignored — don't rely on it
  (see 2.4.1 in the reference).
- Digital goods go through StoreKit only; no external "buy here" links; a
  Restore path exists.
- Any third-party/social login is accompanied by Sign in with Apple.
- If users can create an account, they can delete it in-app.
- [macOS/MAS] App is sandboxed; every sensitive entitlement has a written
  justification ready for review notes; Hardened Runtime on.
- The app does something useful on a clean review machine — if it depends on
  another app, a login, or hardware the reviewer lacks, ship a demo path AND
  document it in review notes.

## Reference files
- [references/guidelines-curated.md](references/guidelines-curated.md) — the
  curated, dated digest of rejection-prone guidelines, by section number. Read
  this in both modes.
- [references/refresh-from-web.md](references/refresh-from-web.md) — how to
  reconcile the digest against the live guidelines URL (hybrid freshness).
- [scripts/scan_project.py](scripts/scan_project.py) — deterministic project
  scanner; emits JSON evidence.
