# Provisioning-profile policy and key backup

last-verified: 2026-11-08

The studio's rules for which builds get a manual profile, where capabilities are
declared, and how the private keys behind the signing certificates are kept safe.
Stated generically here; **this installation's specifics** — which apps have a manual
profile and what each is called, the backup file's date, which ASC key exports iOS
builds — **are in `$KEYS_ROOT/APPLE.md`** (its profile-policy and backup sections).
Read that first; when it disagrees with the machine, say so.

## 1. Profiles: manual only where unavoidable

**The rule:** a manual provisioning profile only where there is no alternative — a
**Tauri Mac App Store build**, where the profile has to be embedded in the bundle before
signing. Everything else is automatic.

| Build | Profile |
|---|---|
| iOS — development / device (Capacitor and Tauri) | Automatic signing. Xcode creates it. |
| iOS — App Store (Capacitor and Tauri) | Automatic, at export time (below). **No manual iOS store profiles.** |
| Mac App Store (Tauri) | Manual, one per app (below). |
| Mac direct distribution (DMG) | None — Developer ID + notarization. |

### iOS App Store export — automatic

`ExportOptions.plist`:

```xml
<key>method</key>        <string>app-store-connect</string>
<key>signingStyle</key>  <string>automatic</string>
<key>teamID</key>        <string>ABCDE12345</string>
```

```bash
xcodebuild -exportArchive -archivePath App.xcarchive \
  -exportOptionsPlist ExportOptions.plist -exportPath build/ \
  -allowProvisioningUpdates \
  -authenticationKeyPath "$ASC_KEY_PATH" \
  -authenticationKeyID "$ASC_KEY_ID" \
  -authenticationKeyIssuerID "$ASC_ISSUER_ID"
```

The three `-authentication…` flags are not optional when it runs headless: a
non-interactive `xcodebuild` sees no Xcode account, and `-allowProvisioningUpdates`
without a key fails with *No Accounts*. Which key to pass is in `APPLE.md`.

### Mac App Store (Tauri) — manual, found by name

- **Where:** `~/Library/MobileDevice/Provisioning Profiles` — the system's own folder.
  **Never in `$KEYS_ROOT`**: a profile is not a secret and can be downloaded again from
  the developer portal; `$KEYS_ROOT` is for what cannot be recreated.
- **One per app.** A new one is named **`<App> macOS AppStore`** (existing ones keep
  their names; `APPLE.md` lists them).
- **The build script finds it by name, not by path** — it scans the folder, decodes each
  profile (`security cms -D -i`), and takes the one whose `Name` matches; an environment
  variable (`MAS_PROFILE`) overrides with an explicit path. A path written into a script
  breaks the day the profile is regenerated, because the file name is a UUID.
- **When the app gains a capability, regenerate its profile immediately** and record it
  in `APPLE.md`. An old profile does not fail the build — it signs without the new
  entitlement, and the feature fails at runtime or in review.
- **When Apple Distribution is renewed,** automatic profiles renew themselves; manual
  Mac App Store profiles must be regenerated.

## 2. Capabilities (App Groups, Face ID, …): declared where they survive

- **Capacitor:** in Xcode → Signing & Capabilities. `ios/App` is tracked in git, so the
  change stays.
- **Tauri:** in the project's **patch script**, which writes into `project.yml` both
  **`entitlements.properties`** and **`SystemCapabilities`**. **Never in Xcode** —
  `gen/apple` is regenerated and the change is lost, and XcodeGen rewrites the
  entitlements file from `properties` (an empty file when there are none).
- **After every build, verify** on the app **and on every app extension**:
  ```bash
  codesign -d --entitlements - path/to/App.app
  codesign -d --entitlements - path/to/App.app/PlugIns/*.appex   # or Contents/PlugIns on macOS
  ```
  A line `Provisioning Profile: "…: *"` in the build log means the wildcard profile was
  chosen, and **the capabilities were stripped silently** — the build succeeds.

## 3. Backing up the private keys

**Back up only what cannot be recreated in the same state** — private keys. Profiles and
public certificates can be downloaded again.

| What | Where it lives | Its backup |
|---|---|---|
| Private keys of the signing identities | the login keychain | `$KEYS_ROOT/signing/apple/` — **one `.p12` per certificate**, named `<type>-<YYYY-MM-DD>.p12` (`apple-development-…`, `apple-distribution-…`, `developer-id-application-…`, `3rd-party-mac-developer-installer-…`): one certificate and its private key each. One password for all, in `p12-password.txt` beside them (`chmod 600`, folder `700`) |
| App Store Connect API keys (`.p8`) | `$KEYS_ROOT/store-api/appstoreconnect/<name>/private_keys/` | **none** — Apple lets you download a `.p8` once. This copy is the only one. |
| Sparkle EdDSA key, other signing keys | under `$KEYS_ROOT` | **none** — the file is the original. A lost Sparkle key means existing users never get another update. |

One file per certificate, so that renewing one certificate replaces one file and a
restore can take only the identity it needs.

### Re-export after every certificate creation or renewal

A new dated `.p12` **for that certificate**; **keep its old file until the old
certificate expires** (it is the only copy of the old key). `security export` writes
every identity into one file, so export to a temporary folder and split:

```bash
D="$KEYS_ROOT/signing/apple"; umask 077; T="$D/.tmp"; mkdir -p "$T"
security export -k ~/Library/Keychains/login.keychain-db -t identities -f pkcs12 \
  -P "$(cat "$D/p12-password.txt")" -o "$T/all.p12"
openssl pkcs12 -legacy -in "$T/all.p12" -passin "file:$D/p12-password.txt" -nodes -out "$T/all.pem"
# in all.pem each certificate and each key carries a localKeyID: pair them by it into
# <type>.pem (certificate + key), then for each:
openssl pkcs12 -export -legacy -in "$T/<type>.pem" -name "<certificate CN>" \
  -passout "file:$D/p12-password.txt" -out "$D/<type>-$(date +%Y-%m-%d).p12"
rm -rf "$T"     # all.pem holds unencrypted private keys — delete it
```

**Verify each file:** one certificate, one key, and the key matches the certificate
(compare their public keys):

```bash
P="file:$D/p12-password.txt"; f="$D/<file>.p12"
openssl pkcs12 -legacy -in "$f" -passin "$P" -nokeys | grep -c "BEGIN CERTIFICATE"   # 1
openssl pkcs12 -legacy -in "$f" -passin "$P" -nokeys | openssl x509 -noout -pubkey | shasum
openssl pkcs12 -legacy -in "$f" -passin "$P" -nocerts -nodes | openssl pkey -pubout | shasum   # identical
```

`-legacy` because macOS imports only the older PKCS#12 encryption. macOS asks for the
login password once per private key. If `p12-password.txt` does not exist yet, generate
one (`openssl rand -base64 24`), write it with `umask 077`, and never print it.

**This is ask-first** — it handles private keys. Then update `APPLE.md` (the files'
date and what was verified — never the password).

### Restore on a new Mac

Double-click the `.p12` and enter the password from the file, or:

```bash
security import "$KEYS_ROOT/signing/apple/<type>-<date>.p12" \
  -k ~/Library/Keychains/login.keychain-db \
  -P "$(cat "$KEYS_ROOT/signing/apple/p12-password.txt")" -T /usr/bin/codesign
```

### An off-machine copy

Everything above sits on one disk. **Warn when `$KEYS_ROOT` has no copy off this
machine** — `tmutil isexcluded "$KEYS_ROOT"` says whether Time Machine includes it, and
`tmutil destinationinfo` shows where Time Machine writes; a destination on the same disk
as the system is not a backup. If the disk dies, certificates can be reissued, `.p8`
keys revoked and recreated — but the Sparkle key is gone for good. Suggest an encrypted
external disk or another encrypted off-machine copy; do not set one up unasked.

## 4. Don'ts

- **Never choose the personal ID in the development certificate's name as the team.**
  `Apple Development: Name (XXXXXXXXXX)` carries the *person's* ID; the team is the
  `OU` of the certificate (and what `APPLE.md` names). Choosing the personal ID fails
  with *No Accounts*.
- **No `fastlane match` for a single developer on one Mac.** It exists to share
  certificates across a team or CI; for one person it adds a repo of encrypted
  certificates and a password to lose, and solves nothing.
- **No capability added in Xcode to a Tauri project** (section 2).
- **No profiles in `$KEYS_ROOT`** (section 1).
