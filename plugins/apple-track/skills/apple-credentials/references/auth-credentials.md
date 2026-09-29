# Apple auth credentials — passwords, notary profiles, API keys

last-verified: 2026-06-02

These authenticate command-line tools to Apple services. They are NOT
certificates and they don't sign anything — they prove "this tool is allowed to
act for my account" without a 2FA prompt a tool can't answer.

## The three kinds, and which tool needs which

| Credential | What it is | Used by | Created by |
|------------|-----------|---------|-----------|
| **App-specific password** | A per-tool password that bypasses 2FA, scoped & revocable | `notarytool` (and legacy `altool`/fastlane Apple-ID auth) | YOU, on account.apple.com |
| **Notary keychain profile** | App-specific-password (or API key) + apple-id + team, stored in the keychain under a name | `notarytool submit --keychain-profile NAME` | `notarytool store-credentials` (the `store-creds` command here) |
| **App Store Connect API key** (`.p8`) | A private key + key-id + issuer-id; no Apple-ID/2FA at all | fastlane (deliver/pilot), `notarytool`, CI | YOU, in App Store Connect |

Rule of thumb:
- **Notarization on your Mac** → app-specific password → notary keychain profile.
- **Uploads / fastlane / CI / automation** → App Store Connect **API key**
  (no 2FA, not tied to a personal Apple ID — best for servers).

## App-specific password — how to create (you, on Apple's site)
1. https://account.apple.com → **Sign-In & Security** → **App-Specific
   Passwords** → **+** (Generate).
2. Name it (e.g. "notarytool"), copy the password it shows **once** (format
   `abcd-efgh-ijkl-mnop`). It is NOT your Apple ID password.
Then turn it into a reusable notary profile with `store-creds` (below).

## Notary keychain profile — the skill creates it for you
After the user supplies the app-specific password, this skill runs
`notarytool store-credentials` to store it:
```bash
NOTARY_PASSWORD='abcd-efgh-ijkl-mnop' \
  apple_creds.py store-creds --profile "MyNotary" \
  --apple-id "you@example.com" --team-id "ABCDE12345"
```
Pass the password via the `NOTARY_PASSWORD` env var (not in the visible command)
so it stays out of shell history. Result: a reusable profile — from then on,
`notarytool ... --keychain-profile MyNotary` works without re-entering anything.

## App Store Connect API key — how to create + use
1. App Store Connect → **Users and Access** → **Integrations** → **App Store
   Connect API** → **+** to generate a key. (Needs Admin/Account Holder.)
2. Note the **Issuer ID** (top of the page) and the **Key ID**; **download the
   `.p8` once** (you can't re-download it).
3. Place it where tools expect it, e.g.
   `~/.appstoreconnect/private_keys/AuthKey_<KEYID>.p8`. Keep it secret (it's a
   private key) — for CI, store it as an encrypted secret, not in the repo.
4. Use it:
   - notarytool: `store-creds --key AuthKey_XXX.p8 --key-id XXX --issuer <uuid>`
     (creates a notary profile backed by the API key), then
     `--keychain-profile`.
   - fastlane: configure `app_store_connect_api_key` (key id, issuer, key path)
     in the Fastfile/Appfile.

## Security
- An app-specific password and a `.p8` API key are secrets. Never commit them;
  store secrets in the keychain (for notary profiles) or encrypted CI secrets.
- Revoke an app-specific password (Apple site) or API key (App Store Connect) if
  leaked — that's why they exist separately from your main account password.
