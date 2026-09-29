---
name: play-store-compliance
description: >-
  Audit an Android app against Google Play's policies and the Console declarations that
  gate a release, and fix what would get it rejected or removed — BEFORE uploading. Use
  this whenever an app is being prepared for Google Play, the user mentions a Play
  rejection, policy warning, or app-suspension email, asks why a release was blocked or
  why an update will not roll out, or is about to ship an AAB ("נדחה בפליי", "בדוק
  מדיניות"). Covers the target-API-level deadline, the Data safety form, permissions and
  the sensitive/restricted ones, content rating (IARC), ads and account-deletion
  declarations, families policy, and the store-listing rules that get an app taken down.
  The Apple counterpart is app-store-review-compliance. It finds and explains policy
  blockers; it does NOT write listing text or upload a build.
---

# Google Play Compliance

> **Conversational language:** talk to the user — questions, summaries, reports — in the `conversational language` set in the hub `DATA.md` (`$APP_HUB/DATA.md`); fall back to the language the user writes in if it is unset. This sets the *conversation* language only.

Play does not reject like Apple does. Most of what stops a release is either a
**declaration missing in the Console** or a **technical requirement in the AAB** —
both checkable before uploading, which is the point of running this first.

**Check the live requirement, don't trust this file's numbers.** Play's thresholds
move on an annual schedule; where a specific level or date matters, confirm it
against the current policy page and say what you confirmed.

## Prerequisites

- **Tools:** `aapt2` (Android SDK build-tools) and `jarsigner` (JDK) for the AAB/APK
  checks; the rest is `grep` over the repo.
- **Credentials:** none — the Console declarations are filled by the user on the website.
- **Hub (`$APP_HUB`):** optional — only the conversational language comes from `DATA.md`.
- **Other tracks:** none.

## Blocks the upload — check these in the AAB first

| Requirement | How to check | Why it bites |
|---|---|---|
| **Target API level** | `grep targetSdkVersion` / `variables.gradle` | Play refuses new releases below the current floor, which rises every year (deadline around 31 August). An app that shipped fine last year cannot ship an update this year without bumping. |
| **AAB, not APK** | you are producing `bundleRelease` | APKs are not accepted for new apps. |
| **64-bit** | native libs only; pure-Capacitor apps are unaffected | 32-bit-only is refused. |
| **versionCode** | strictly higher than every code ever uploaded | see `play-store-ship`. |
| **Signing** | `jarsigner -verify` | an unsigned AAB is a silent outcome of a missing `keystore.properties`; see `android-credentials`. |

## Blocks the release — Console declarations

These live only in the Console. An incomplete one holds the release in a state that
looks like a review delay but is a form waiting to be filled.

- **Data safety** — what the app collects, shares, and whether it is encrypted and
  deletable. It must match the app's real behaviour and its privacy policy. An app
  that genuinely collects nothing still has to say so.
- **Content rating** — the IARC questionnaire; without it the app is listed as
  unrated and restricted.
- **Privacy policy URL** — required whenever the app requests sensitive permissions
  or handles personal data; increasingly required regardless.
- **Ads declaration**, **News / Financial / Health** categories where they apply, and
  the **Families** policy if the listing targets children.
- **Account deletion** — an app with in-app accounts must offer deletion **and** a
  web URL to request it, declared in the Console.

## Permissions — the usual cause of a policy warning

Audit what the app actually declares:
```bash
grep -rn "uses-permission" android/app/src/main/AndroidManifest.xml
aapt2 dump permissions app-release.apk        # what really shipped
```
Every permission must be used and justified by a user-facing feature. The costly
ones are the **restricted** permissions — all-files access, SMS/call log, exact
alarms, background location, accessibility services, package queries — which need a
declaration form and a written justification, and are the most common reason for a
takedown of an otherwise ordinary app. A Capacitor app inherits permissions from its
plugins: remove a plugin, re-check the merged manifest.

## Store listing — what gets an app removed
- No keyword stuffing, competitor names, or "#1"-type claims in title or description.
- No fake urgency, prices in the graphics, or reviews/ratings solicited in the copy.
- Screenshots and the feature graphic must show the app itself, not concept art.
- Title ≤ 30 characters; the limits are enforced at upload (`play-store-metadata`).

## The one-time account gates
A new personal developer account is **capped at closed testing** until production
access is approved, and Google may require a period of testing with a minimum number
of testers first. From the API the signature is `alpha` accepting writes while both
`beta` and `production` return `FAILED_PRECONDITION`. It is not a metadata or
credentials fault; it is an account state, and only the Console clears it.

## How to run this
1. Read the manifest, the gradle target/compile levels, and the merged permissions.
2. Report findings **ranked by whether they block the upload, block the release, or
   risk a later takedown** — with the file and line for anything in the repo.
3. Fix what lives in the repo (permissions, target level, manifest).
4. For the Console-only forms, give the exact navigation and what to answer, and let
   the user complete them — you cannot fill them for the user.

## Boundaries

- **It finds and explains; it does not rewrite.** A policy blocker in the listing
  text goes to `play-store-metadata`; one in the manifest or the build goes to the
  app's own code with an explanation of what Google requires and why.
- **It does not upload.** Passing this check is a precondition for `play-store-ship`,
  not a substitute for it.
- Apple's equivalent review rules are `app-store-review-compliance`'s; they overlap
  in spirit and almost nowhere in detail.

## Related skills
- `play-store-ship` — the release itself; run this before it.
- `play-store-metadata` — the listing text and its limits.
- `android-credentials` — signing and the service account.
- `app-store-review-compliance` — the Apple counterpart.
