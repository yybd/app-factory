# Signing error decoder — symptom → cause → fix

last-verified: 2026-06-02

Each entry: the message you see, what link in the binding rule is broken, and the
fix. (Binding rule: cert ∈ profile, bundle id = App ID, entitlements ⊆ allowed,
device ∈ profile, nothing expired — see the apple-credentials skill for the model + cert types.)

### "No signing certificate 'Mac App Distribution' / 'iOS Distribution' found"
Cause: the distribution certificate isn't in the keychain (or its private key is
missing).
Fix: turn on Automatically manage signing (Xcode creates it on archive), or
create it: Xcode → Settings → Accounts → Manage Certificates → + → the right
type. If on a new Mac, import the `.p12` (cert + private key), not just the
`.cer`.

### "Provisioning profile doesn't include signing certificate '…'"
Cause: the profile was made for a different certificate than the one you're
signing with (cert ∉ profile).
Fix: regenerate the profile to include the current cert, or sign with the cert
the profile expects. With automatic signing, let Xcode regenerate it. With
match, run `fastlane match` again.

### "… doesn't match the entitlements file's value for the … entitlement"
Cause: the app requests a capability (entitlements) the App ID/profile doesn't
grant (entitlements ⊄ allowed).
Fix: enable the capability on the App ID in the portal (or via the capability in
Xcode), regenerate the profile, OR remove the entitlement if not needed. Common
with Push, App Groups, iCloud, Sign in with Apple, Keychain Sharing.

### "No profiles for 'com.you.app' were found"
Cause: no provisioning profile exists for that bundle id / platform.
Fix: automatic signing creates one on demand; or create it in the portal
(Profiles → +), or `fastlane match`. Confirm the bundle id is registered as an
App ID first.

### "Failed to register bundle identifier" / "The app ID cannot be registered"
Cause: the bundle id is taken, malformed, or you lack permission.
Fix: pick a unique reverse-DNS id; ensure your role can register identifiers
(Admin/Account Holder); check it isn't already registered under another team.

### "The executable was signed with invalid entitlements" (notarization/upload)
Cause: an entitlement not permitted for that distribution channel (e.g. a
restricted/managed entitlement on a Developer ID build, or a get-task-allow=true
debug entitlement in a distribution build).
Fix: remove the disallowed entitlement; ensure you archived a Release build (not
a debug build with `get-task-allow`).

### "Code object is not signed at all" / nested framework not signed
Cause: a bundled framework/helper/XPC wasn't signed.
Fix: sign nested code first, then the outer app. Don't rely on `--deep` for
distribution; sign each nested item explicitly with the same identity + options.

### "A valid provisioning profile for this executable was not found" (macOS)
Cause: the Mac app needs an embedded profile (e.g. uses a capability requiring
one) but none is embedded.
Fix: enable the relevant capability and let signing embed the profile, or add the
profile to the target.

### Profile/certificate **expired**
Cause: profiles expire (typically a year); certs expire too.
Fix: regenerate the profile (automatic signing or match does this); renew the
cert if expired. The diagnostic flags expiry dates.

### "Your session has expired" / 2FA loops in CLI
Cause: Apple ID auth in CLI tools needs an app-specific password or an App Store
Connect API key (2FA can't be typed by a tool).
Fix: use an App Store Connect API key (`.p8`) for fastlane/altool/notarytool, or
an app-specific password where applicable.

## General debugging moves
- `python3 scripts/diagnose_signing.py <root>` — see all settings/identities/
  profiles + cross-checks at once.
- `codesign -dvvv --entitlements - <App.app>` — what the build is actually signed
  with (authority, entitlements, timestamp, runtime flag).
- `security cms -D -i <profile>` — decode a provisioning profile.
- `security find-identity -v -p codesigning` — installed signing identities.
- Clean stale automatic profiles: `~/Library/MobileDevice/Provisioning Profiles/`
  (back up before deleting); Xcode regenerates them.
