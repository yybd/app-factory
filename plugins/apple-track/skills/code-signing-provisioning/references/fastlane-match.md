# Shared signing with fastlane match

last-verified: 2026-06-02
source: https://docs.fastlane.tools/actions/match/

## What it solves
Certificates + their private keys and provisioning profiles normally live on one
Mac's keychain. Sharing them across a team or CI by hand (exporting `.p12`s,
emailing profiles) is error-prone. **match** stores them encrypted in a private
git repo (or S3/Google Cloud) and syncs them to any machine — so everyone signs
with the same identity, reproducibly.

When to recommend it: a team, CI/CD, or more than one build machine. For a solo
developer on one Mac, Xcode automatic signing is usually simpler — don't add
match unless there's a real multi-machine need.

## Setup (guide; ask before running — it touches the keychain + a remote repo)
1. A private git repo to hold the encrypted certs/profiles.
2. `fastlane match init` → writes a `Matchfile` (set the repo URL).
3. Generate/fetch per type:
   ```bash
   fastlane match development      # Apple Development + dev profiles
   fastlane match appstore         # Apple Distribution + App Store profiles
   fastlane match developer_id     # Developer ID Application + profiles (direct dist)
   ```
   The first run on the first machine creates them; later runs on other machines
   just decrypt and install.
4. A passphrase encrypts the repo (store it in CI secrets, not in the repo).
5. In the Fastfile, call `match(type: "appstore", readonly: is_ci)` before
   building; set targets to manual signing using the match-provisioned profiles.

## Notes
- `readonly: true` on CI so it never tries to create/revoke — it only fetches.
- Authenticate to Apple with an **App Store Connect API key** for CI (no 2FA
  prompts).
- `match nuke` revokes and deletes — destructive; never run casually (it can
  invalidate other people's/active builds).
- match is the clean way to do **manual** signing reproducibly; it doesn't
  replace understanding the certificate types — it just distributes them.
