# Apple signing certificates — the whole model, in plain terms

last-verified: 2026-06-02
source: developer.apple.com (Certificates, Identifiers & Profiles; signing docs)

Understanding first, commands second. Once the four parts and the certificate
types click, every signing error becomes readable.

## The four parts and how they bind
1. **Certificate** — proves *who* is signing. A public/private key pair: the
   private key lives in your keychain; Apple signs the matching certificate to
   vouch it's you. Signing stamps "this build came from this identity."
2. **Identifier (App ID)** — names *which app* (bundle id) and which
   **capabilities** it may use (Push, iCloud, Sign in with Apple…). In the portal.
3. **Entitlements** — capabilities the binary actually requests; must be a
   **subset** of what the App ID/profile allow.
4. **Provisioning profile** — the glue binding a **certificate** + an **App ID**
   + (dev/ad-hoc) **devices**; embedded in the app.

**Binding rule:** build succeeds when `cert ∈ profile` AND `bundle id = App ID`
AND `entitlements ⊆ allowed` AND (dev/ad-hoc) `device ∈ profile` AND nothing
expired. Every signing error is one broken link.

## The certificate types — what each is for and WHY
Apple separates certificates by purpose on purpose: each asserts a different
kind of trust, so they're deliberately not interchangeable.

| Certificate | Asserts… | Use it for | Why separate |
|-------------|----------|------------|--------------|
| **Apple Development** | "a team developer is testing" | Run/debug on registered devices | Limited trust — devices only, not shippable |
| **Apple Distribution** | "this team ships via the App Store" | App Store / **Mac App Store** app signing | Store vets/re-signs; not for direct running |
| **Mac Installer Distribution** ("3rd Party Mac Developer Installer") | "this team built this MAS installer" | The **`.pkg`** uploaded to the Mac App Store | MAS uploads a signed installer — different artifact |
| **Developer ID Application** | "a known developer ships this directly" | **Direct** Mac distribution (DMG/zip) + notarization | Gatekeeper trusts direct downloads only from Developer ID |
| **Developer ID Installer** | "a known developer built this direct installer" | A **`.pkg`** for direct distribution | Installer variant of the above |

Why you can't mix them: Gatekeeper/the store check *which* authority signed.
Development = "test build for my devices"; Apple Distribution = "goes through the
store's trust"; only **Developer ID** = "a known developer distributes this
directly." Wrong cert = the #1 signing/notarization rejection.

## Platform matrix (which certs each goal needs)
| Goal | App signed with | Package/extra | Notarized? |
|------|-----------------|---------------|------------|
| iOS / macOS development | Apple Development | — | no |
| iOS App Store | Apple Distribution | App Store profile | no (store) |
| **Mac App Store** | Apple Distribution | **Mac Installer Distribution** for the `.pkg` | no (store) |
| **Direct Mac (DMG)** | **Developer ID Application** | — | **yes** |
| Direct Mac (`.pkg`) | Developer ID Application | **Developer ID Installer** | yes |

## Automatic vs manual signing
- **Automatically manage signing** (Xcode): for **development & App Store**,
  Xcode creates/renews the certs (Apple Development, Apple Distribution, Mac
  Installer Distribution) and profiles on demand. Solo devs rarely create these
  by hand.
- **Developer ID is the exception**: NOT auto-created by archive/upload. Create
  it once (Xcode → Manage Certificates → + → Developer ID Application, or the
  portal). Small per-account limit — reuse/export rather than mint duplicates.

## Creating certificates — roles & limits
- **Xcode** → Settings → Accounts → Manage Certificates → **+** → type. Easiest;
  Xcode makes the key pair and installs it.
- **Portal** → Certificates, Identifiers & Profiles → Certificates → + → type →
  upload a CSR (Keychain Access → Certificate Assistant → Request a Certificate
  from a CA) → download → double-click to install.
- **Roles**: creating *distribution*/Developer ID certs needs **Account
  Holder/Admin**. Individual accounts: that's you.
- **Limits**: distribution & Developer ID certs are capped per account. At the
  cap, reuse the existing cert (export `.p12`) rather than revoke/recreate —
  revoking can break other builds/profiles referencing it.
- **The private key matters**: a certificate is useless without its private key.
  A new Mac needs the `.p12` (cert + key) or `fastlane match`, not just the
  `.cer`.

## Exporting a certificate as .p12 (for CI / another Mac)
A `.p12` (PKCS#12) file bundles the **certificate + its private key**, encrypted
with a password — the portable form needed to sign on a machine that didn't
create the cert (GitHub Actions, another Mac, a build server).

**Via Keychain Access (GUI):**
1. Open **Keychain Access** → **login** keychain → **My Certificates**.
2. Find the cert (e.g. "Developer ID Application: …"); expand the disclosure
   triangle to confirm a **private key** is nested under it (no key = you can't
   export a usable `.p12`).
3. Right-click the certificate → **Export "…"** → format **Personal Information
   Exchange (.p12)** → choose a location → set a **strong export password**
   (you'll need it on the other machine).

**Via CLI:**
```bash
security export -k login.keychain-db -t identities -f pkcs12 \
    -P 'EXPORT_PASSWORD' -o DeveloperID.p12
# (exports identities; for a specific one, do it from Keychain Access)
```

**Using it in GitHub Actions (typical):**
1. base64-encode the file: `base64 -i DeveloperID.p12 | pbcopy`.
2. Store the base64 string and the export password as **encrypted repo secrets**
   (e.g. `CERT_P12_BASE64`, `CERT_P12_PASSWORD`). Never commit the `.p12`.
3. In the workflow: decode it, create a temporary keychain, `security import`
   the `.p12` with the password, set it as the default keychain, then build/sign.
   (`fastlane match` automates this whole dance if you prefer.)

Security: the `.p12` contains your private key — treat it like a password. Only
in encrypted secrets/secure storage, never in the repo.
