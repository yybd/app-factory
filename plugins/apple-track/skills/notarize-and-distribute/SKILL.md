---
name: notarize-and-distribute
description: >-
  Take a built macOS app from an Xcode archive, package it into a signed DMG, notarize
  it with Apple, staple the ticket, and verify that everything — the app AND the DMG —
  is properly signed and notarized for direct (non-App-Store) distribution. Use this
  whenever the user wants to ship a Mac app outside the Mac App Store ("נוטריזציה",
  "קובץ DMG"): build/create a DMG, sign with Developer ID, notarize, staple, fix "app is
  damaged / can't be opened / unidentified developer" Gatekeeper errors, or verify
  notarization status. Covers the Developer ID flow only (for Mac App Store builds,
  that's a different signing path). It signs, notarizes and packages; setting up the
  Sparkle update channel is macos-direct-distribution's job.
---

# Notarize & Distribute (Developer ID DMG)

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

For a Mac app distributed outside the App Store, Apple's Gatekeeper will block it
unless it is signed with **Developer ID**, **notarized** by Apple, and the
notarization ticket is **stapled**. Miss any step and users see "app is damaged"
or "unidentified developer". This skill runs the whole chain — locate the app →
**notarize + staple the app** → DMG → sign → **notarize + staple the DMG** →
verify — and checks that the DMG *and* the app inside it pass Gatekeeper.

**Always notarize the app itself, not just the DMG.** The standard flow notarizes
and staples the `.app` *before* packaging it, then notarizes the DMG too. Stapling
only the DMG leaves the app inside un-notarized, so once a user drags it out of the
DMG it can fail Gatekeeper offline ("damaged"). Doing both is the default here —
`build` refuses to package an un-notarized app unless you explicitly waive it with
`--allow-unstapled`.

The work is automatable (codesign/hdiutil/notarytool/stapler are all CLI), so
this skill mostly *does* rather than guides — via
[scripts/notarize_dmg.py](scripts/notarize_dmg.py). The only manual prerequisite
is one-time credential setup.

## Prerequisites

- **Tools:** Xcode command line tools — `xcrun notarytool`, `codesign`, `stapler`,
  `hdiutil`, `spctl`. All ship with Xcode; nothing to install.
- **Credentials:** a **Developer ID Application** certificate and a notary credential
  (a keychain profile from an app-specific password, or an App Store Connect API key).
  Both are `apple-credentials`' to create — see A and B below.
- **Hub (`$APP_HUB`):** not used.
- **Other tracks:** none; `apple-credentials` and `macos-direct-distribution` are in
  this same plugin.

### Check these first, and guide the user if missing

### A) A Developer ID Application certificate
Run `list` (see step 2). If **no "Developer ID Application"** identity is found,
don't just error — get one created, then continue:
- **If the `apple-credentials` skill is available, hand off to it** — it owns
  certificates: it explains the types, why this flow needs *Developer ID
  Application* specifically, and guides creation/`.p12` export. Come back here
  once the cert exists.
- **If that skill is NOT installed, guide the user inline through Xcode** and
  continue once done:
  1. Xcode → Settings (⌘,) → **Accounts** → select the Apple ID →
     **Manage Certificates…**
  2. Click **+** → **Developer ID Application** (Xcode creates the key + cert and
     installs them in the login keychain).
  3. Re-run `list` to confirm it now appears, then proceed.
  Briefly tell the user *why*: Gatekeeper only trusts directly-distributed apps
  signed by a Developer ID identity — an Apple Development or Apple Distribution
  cert will be rejected by notarization, so it must be this specific type.

### B) A notary credential
Run `list`; if **no notary profile** is detected, hand off to the **`apple-credentials`**
skill — it owns auth credentials (app-specific passwords, notary profiles, API keys)
and creates the profile with its own `store-creds`; come back with the profile name
and pass it as `--keychain-profile`. It ships in this same plugin, so it is always
installed when this skill is. (This skill used to carry a second copy of that
command "in case the other skill is not installed" — a case that cannot occur.)

### C) Build settings
The app must be built with **Hardened Runtime ON** and signed with a secure
**timestamp** — notarization rejects apps without these.

## Workflow

### 1. Locate the app and check its signing
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/notarize-and-distribute/scripts/notarize_dmg.py locate <path-to.xcarchive | export-dir | App.app>
```
It finds the `.app` (in an `.xcarchive` it looks in `Products/Applications/`) and
reports whether it's signed with Developer ID, has Hardened Runtime, and has a
secure timestamp. Resolve any ⚠️ before continuing — an app that isn't
Developer-ID/hardened/timestamped will fail notarization. The cleanest source is
an archive exported with the **Developer ID** method (Xcode Organizer →
Distribute App → Developer ID), which produces a correctly signed `.app`.

### 2. Choose the signing identity — ask, don't auto-pick
The skill must NOT silently use whatever certificate it finds. First list what's
available, then confirm with the user which to use:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/notarize-and-distribute/scripts/notarize_dmg.py list
```
This prints the Developer ID Application identities in the keychain (and any
detectable notary profiles). When more than the empty case exists, ASK the user
which identity to use (AskUserQuestion is ideal — one option per identity), then
pass the chosen one as `--identity "Developer ID Application: …"`. If exactly one
is found, still confirm it ("Use this certificate: …?") rather than assuming.
The script enforces this: `build` without `--identity` prints the choices and
stops (exit 3) instead of auto-selecting; `--yes` is an explicit opt-in to use
the first (e.g. CI), only when the user has authorized that.

### 3. Notarize and staple the app itself (network — confirm first)
**Do this before building the DMG.** It talks to Apple, so confirm first, and
confirm WHICH notary credential to use (run `list`; ask the user — don't assume a
default). Then:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/notarize-and-distribute/scripts/notarize_dmg.py notarize-app --app <App.app or .xcarchive> \
    --keychain-profile <chosen-profile>     # or: --api-key AuthKey.p8 --api-key-id KEYID --api-issuer ISSUER
```
It re-checks the app is Developer-ID/hardened/timestamped, zips it
(`ditto -c -k --keepParent`), submits with `notarytool submit --wait`, and on
success **staples the ticket to the `.app`** so it validates offline. If the app
is already stapled it says so and does nothing (use `--force` to re-notarize). On
failure it fetches the notary **log** (common causes in
[references/notarization.md](references/notarization.md)).

### 4. Build and sign the DMG (local, safe)
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/notarize-and-distribute/scripts/notarize_dmg.py build --app <stapled App.app or .xcarchive> --out dist/ \
    --identity "Developer ID Application: …" [--versioned]
```
It re-checks app signing, **refuses (exit 4) if the app has no stapled ticket**
(run step 3 first; or pass `--allow-unstapled` to intentionally do DMG-only
notarization), builds a compressed DMG (with an `/Applications` symlink for
drag-install) via `hdiutil`, and signs the DMG with the chosen Developer ID
identity + timestamp. Use `--sign-app` only if you need it to (re)sign the app;
prefer a properly-exported archive.

### 5. Notarize and staple the DMG (network — confirm first)
Same credential as step 3. Outward-facing, so confirm before running:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/notarize-and-distribute/scripts/notarize_dmg.py notarize --dmg dist/App.dmg --keychain-profile <chosen-profile>
```
It submits with `notarytool submit --wait` and on success staples the ticket to
the DMG. On failure it fetches the notary log.

### 6. Verify everything (app + DMG)
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/notarize-and-distribute/scripts/notarize_dmg.py verify --dmg dist/App.dmg --app <App.app>
```
Confirms: code signature valid (`codesign --verify --deep --strict`), Gatekeeper
accepts both the app (`spctl -t exec`) and the DMG
(`spctl -t open`), and the notarization ticket is stapled (`stapler validate`) on
**both**. A green run here means a user can download the DMG and open the app
cleanly — and the app keeps validating after being dragged out.

## Safety
- The two `notarize*` steps (app, then DMG) are the network/outward-facing ones —
  always confirm before running each. The rest is local and reversible.
- Don't fabricate "notarized" status: only report success when `verify` actually
  passes `spctl` + `stapler` for the app AND the DMG.

## Boundaries — and what comes next
Hosting/updates (uploading the DMG to a CDN/R2, generating a Sparkle appcast for
auto-updates) is a separate concern — note it if the user mentions it, but this
skill ends at a verified, notarized, stapled DMG.

## Reference files
- [references/notarization.md](references/notarization.md) — the Developer ID +
  notarization model, credential setup, common notary-log failures and fixes,
  and the verification commands explained.
- [scripts/notarize_dmg.py](scripts/notarize_dmg.py) — locate / list / notarize-app
  / build / notarize / verify / setup.
