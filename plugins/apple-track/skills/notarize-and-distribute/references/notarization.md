# Developer ID notarization & DMG — reference

last-verified: 2026-06-02
sources:
- https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- `xcrun notarytool`, `codesign`, `spctl`, `stapler` man pages

## Certificate: you need "Developer ID Application"
This flow signs the app + DMG with a **Developer ID Application** certificate —
NOT Apple Development (test builds) and NOT Apple Distribution (App Store).
Gatekeeper/notarization only trust a directly-distributed app signed by a
Developer ID identity tied to your team; the other types are rejected.

Certificate types, why each exists, creation steps, limits, and roles are owned
by the **`code-signing-provisioning`** skill — defer to it for anything beyond
"do I have a Developer ID Application cert?". Quick create if you don't (and that
skill isn't around): Xcode → Settings → Accounts → Manage Certificates → **+** →
**Developer ID Application**; then re-run `list`.

## The model (why each step exists)
Gatekeeper on a user's Mac allows a downloaded app only if it is:
1. **Signed with Developer ID Application** — proves a known developer signed it.
2. **Notarized** — Apple scanned the binary for malware and known issues and
   issued a ticket.
3. **Stapled** — the ticket is attached to the artifact so it validates even
   offline. (Without stapling, Gatekeeper tries to fetch the ticket online; if
   the machine is offline or the staple is missing, the user may be blocked.)

Two extra hard requirements for notarization to even succeed:
- **Hardened Runtime** must be enabled on the app (`codesign` flag `runtime`).
- A **secure timestamp** (`codesign --timestamp`) on every signature.
- All nested code (frameworks, helpers, XPC) must also be Developer-ID signed
  with the same rules.

This is the **Developer ID** path (direct distribution). The **Mac App Store**
path is different (Apple Distribution + Mac Installer cert + sandbox +
provisioning profile, no notarization by you) — don't mix them.

## Credentials (one-time)
Notary submission needs credentials. Easiest is a keychain profile:
```bash
xcrun notarytool store-credentials "MyNotaryProfile" \
    --apple-id "you@example.com" --team-id "ABCDE12345" \
    --password "abcd-efgh-ijkl-mnop"     # app-specific password
```
- The password is an **app-specific password** (account.apple.com → Sign-In &
  Security → App-Specific Passwords), not the Apple ID password.
- CI alternative: an App Store Connect API key (.p8) →
  `--key AuthKey_XXX.p8 --key-id XXX --issuer <uuid>`.

## The chain (what the script runs)
1. `codesign -dvvv App.app` — confirm Developer ID + `runtime` flag + Timestamp.
2. **Notarize the APP** (`notarize-app`): `ditto -c -k --keepParent App.app app.zip`,
   `xcrun notarytool submit app.zip --keychain-profile MyNotaryProfile --wait`,
   then `xcrun stapler staple App.app`. Do this *before* packaging so the app
   inside the DMG is itself notarized and validates offline.
3. Build DMG **from the stapled app**: stage the app + `/Applications` symlink,
   then `hdiutil create -volname NAME -srcfolder stage -ov -format UDZO out.dmg`.
   (`build` refuses an un-stapled app unless `--allow-unstapled`.)
4. Sign the DMG: `codesign --force --sign "Developer ID Application: …"
   --timestamp out.dmg`.
5. **Notarize the DMG**: `xcrun notarytool submit out.dmg --keychain-profile
   MyNotaryProfile --wait`.
6. `xcrun stapler staple out.dmg`.
7. Verify (below) — both app and DMG.

## Verification commands (what "done" means)
- App signature: `codesign --verify --deep --strict --verbose=2 App.app`
- App Gatekeeper: `spctl -a -vvv -t exec App.app`
  → want `accepted` and `source=Notarized Developer ID`.
- DMG Gatekeeper: `spctl -a -vvv -t open --context context:primary-signature out.dmg`
  → want `accepted`.
- Staple present: `xcrun stapler validate out.dmg` (and optionally `App.app`).

## Common notarization failures (read the log!)
On `Invalid`, always pull the log: `xcrun notarytool log <submission-id>
--keychain-profile <p>`. Frequent causes:
- **"The signature does not include a secure timestamp"** → re-sign with
  `--timestamp`.
- **"The executable does not have the hardened runtime enabled"** → enable
  Hardened Runtime (build setting `ENABLE_HARDENED_RUNTIME = YES`) and re-sign
  with `--options runtime`.
- **"The binary is not signed with a valid Developer ID certificate"** → wrong
  cert (e.g. Apple Development instead of Developer ID Application), or a nested
  framework left unsigned.
- **"The signature ... is not signed"** for a nested helper/framework → sign
  inner code first, then the app (don't rely on `--deep` for distribution;
  sign nested items explicitly, then the outer app).
- **Invalid entitlements** → an entitlement not allowed for Developer ID (e.g.
  certain restricted entitlements) — remove or correct it.

## Stapling: app AND DMG (the default here)
- Stapling the **DMG** covers download → open from the DMG. But once a user drags
  the app out of the DMG, only a ticket stapled to the **app** keeps it validating
  offline — otherwise it can show "damaged".
- So the standard flow staples **both**: `notarize-app` notarizes + staples the
  app first, then `build` packages that stapled app and `notarize` staples the DMG.
  This is the default; `build` enforces it (refuses an un-stapled app unless
  `--allow-unstapled`). DMG-only stapling is the rare exception, not the norm.

## Gotchas
- Notarization is per-upload and can take from under a minute to many minutes;
  `--wait` blocks until done.
- Re-signing after building the DMG invalidates the DMG signature — sign in the
  right order (app first, then DMG).
- `spctl` assessment for installers vs apps uses different `-t` types (`exec`
  for an app, `open`/`install` context for a DMG) — using the wrong type gives
  misleading results.
- Notarizing does not re-sign; your signatures must already be correct.
