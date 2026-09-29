---
name: android-credentials
description: >-
  The single owner of Android signing and Google Play credentials — the upload keystore,
  Play App Signing, the SHA-1/SHA-256 fingerprints other services ask for, and the Play
  Developer API service account. Use this whenever an Android app needs a signing key
  created or located, a build comes out unsigned, an install fails with a signature
  mismatch, Play rejects an upload as "signed with the wrong key", a service needs the
  app's certificate fingerprint (Firebase, Maps, Google Sign-In), the Play API returns
  401/403, or the user asks which key is which and what happens if one is lost. Other
  Android skills (play-store-ship, play-store-deliver) draw from this one for anything
  key-or credential-related. The Apple counterparts are apple-credentials and
  code-signing-provisioning ("חתימה לאנדרואיד", "מפתח חתימה"). It stores and locates
  keys; it does NOT build or upload — play-store-ship does that.
---

# Android Credentials & Signing

> **Conversational language:** talk to the user — questions, summaries, reports — in the `conversational language` set in the hub `DATA.md` (`$APP_HUB/DATA.md`); fall back to the language the user writes in if it is unset. This sets the *conversation* language only.

Android signing is far smaller than Apple's — no provisioning profiles, no
per-device entitlements, no portal. One keystore signs the build; Google does the
rest. Almost every confusion comes from **there being two keys, not one.**

## Prerequisites

- **Tools:** a JDK matching the project's toolchain (`keytool`, `jarsigner`) and
  `apksigner` from the Android SDK build-tools; nothing to `pip`/`gem` install.
- **Credentials:** owned here — the upload keystore under `$KEYS_ROOT/android/` and the
  Play service-account JSON, both recorded by path in `$KEYS_ROOT/credentials.json`.
- **Hub (`$APP_HUB`):** optional — `DATA.md` records identifiers and paths and sets the
  conversational language; the secrets themselves never live there.
- **Other tracks:** none.

## The two keys

| | **Upload key** | **App signing key** |
|---|---|---|
| Who holds it | you (`$KEYS_ROOT/android/<app>-keystore/`) | **Google**, under Play App Signing |
| What it does | proves *you* uploaded the AAB | signs the APKs that reach devices |
| If lost | recoverable — ask Google to reset it | fatal if you are **not** enrolled in Play App Signing |

With Play App Signing on (the default for new apps, and mandatory for AABs),
Google **re-signs** every APK it serves. Three consequences that explain most
mysteries:

- **A locally built release APK is not the store APK.** It carries the upload key,
  the store's carries the app signing key, so it can neither update nor be updated
  by the installed store copy. Installing one over the other requires an uninstall,
  which **erases the app's local data**.
- **A debug build matches neither.** Same story, plus the debug key is per-machine.
- **The fingerprint other services want is usually the *app signing* one.** Firebase,
  Google Maps, Google Sign-In and App Links validate what is on the device.

## Where things live

Credentials never enter a repo. Identifiers and paths are recorded in
`$KEYS_ROOT/credentials.json` (a studio hub's `DATA.md` is read too, for an
installation that predates it); the secrets themselves sit in `$KEYS_ROOT/`, which is
deliberately not a git repository.

```
$KEYS_ROOT/android/<app>-keystore/keystore.properties   # storeFile/…/keyAlias
$KEYS_ROOT/android/api-fastlane-supply/*.json           # Play API service account
```

`build.gradle` reads the properties file **only if it is present**, and the guard
around it leaves every field of the release signing config null when it is not.
What that produces depends on the task:

- **`bundleRelease` fails outright**, at `:app:signReleaseBundle`, with a bare
  `java.lang.NullPointerException (no error message)` that never mentions signing
  or the keystore. It is the likeliest cause of that NPE by a distance — look for
  the missing properties file before anything else.
- Tasks that do not run the signer can still hand back an **unsigned** artifact,
  so verify the signature rather than assuming a build that succeeded is signed.

Copy the file in before a release build, verify the signature after, and delete it
from the project directory when done.

```gradle
def keystorePropertiesFile = rootProject.file("keystore.properties")
```

Keep `*.jks`, `*.keystore` and `keystore.properties` in `.gitignore`. Losing the
keystore is unrecoverable without Play App Signing; leaking it is worse.

## Create an upload keystore
```bash
keytool -genkeypair -v -keystore upload.jks -alias upload \
        -keyalg RSA -keysize 2048 -validity 10000
```
Validity must outlast the app — Play requires a key valid past 2033. Then write
`keystore.properties` beside it (`storeFile`, `storePassword`, `keyAlias`,
`keyPassword`) and record only its **path**, under `googleplay.keystores` in
`$KEYS_ROOT/credentials.json`.

## Read the fingerprints
```bash
keytool -list -v -keystore upload.jks -alias upload | grep -A1 "SHA1\|SHA-256"   # upload key
apksigner verify --print-certs app-release.apk                                   # what a built APK carries
jarsigner -verify -verbose:summary app-release.aab | tail -3                     # signed at all?
```
The **app signing** fingerprint is not on your machine at all — read it in the Play
Console under *Release → Setup → App signing*. When a Google service rejects the
app in production while debug works, this mismatch is nearly always why.

## The Play Developer API service account
For everything the Console can be scripted out of (`play-store-ship`,
`play-store-deliver`, review replies):

1. Google Cloud → create a service account → download its JSON key.
2. Play Console → *Users and permissions* → invite that service account's email →
   grant per-app rights (release, or reply-to-reviews).
3. Record the **path** under `googleplay.service_account` in
   `$KEYS_ROOT/credentials.json`; never the key itself.

Auth is a self-signed RS256 JWT exchanged for a token, scope
`https://www.googleapis.com/auth/androidpublisher`;
`${CLAUDE_PLUGIN_ROOT}/skills/play-store-ship/scripts/publish_aab.py`
has a working `token()` to copy.

Reading the API says nothing about permissions being complete: a fresh personal
account can be **gated out of production** while `alpha` still accepts writes —
that is an account-status gate, not a credentials fault. See `play-store-ship`.

## Build environment
`bundleRelease` needs a JDK of the version the project declares (`languageVersion` /
`sourceCompatibility` / `jvmTarget`). A system default that is older fails with
`invalid source release: NN`, which reads like a compiler bug and is a toolchain
mismatch. `/usr/libexec/java_home -v NN` finds one on macOS; Android Studio bundles one
at `<Android Studio>/Contents/jbr/Contents/Home` when nothing else is installed.

## CI
Base64 the keystore into a secret, decode it at build time, and write
`keystore.properties` from separate secrets. Never check either into the repo, and
never echo them into build logs.

## Boundaries
- Creating the Google Cloud service account and granting it in the Play Console are
  **website steps** — give the exact navigation, let the user do them.
- Never print a password, key file, or service-account JSON into the transcript.

## Related skills
- `play-store-ship` — builds and uploads the binary using these keys.
- `play-store-deliver` — the listing send-surface, same service account.
- `apple-credentials` · `code-signing-provisioning` — the Apple counterparts.
