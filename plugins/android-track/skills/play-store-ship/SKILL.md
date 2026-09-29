---
name: play-store-ship
description: >-
  Verify an Android app is release-ready and ship it to Google Play — the FINAL Play
  step: confirm the content is in place (signing key, versionCode, listing, changelog),
  then build the signed AAB, upload it, assign it to a track, and publish. Use this when
  the user wants to release/publish/upload an Android build, ship a new versionCode,
  push an app to production / internal / alpha / beta, roll out a staged release, or
  asks "how do I upload the AAB" / "תעלה לפרודקשן". This skill does NOT author the
  listing copy, graphics, or changelogs — those are owned by play-store-metadata
  (authoring into the hub) and delivered by play-store-deliver (the listing
  send-surface). It VERIFIES their output exists, then builds, uploads, and publishes
  the BINARY, which no other skill does. Authenticates with the Google Play
  service-account JSON the track's credential resolver finds. The Apple counterpart
  is ship-apple-app.
---

# Ship an Android App — verify, build, upload, publish

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

The Android counterpart of `ship-apple-app`, and the **only** skill that sends a
**binary** to Google Play. `play-store-deliver` is the send-surface for the
**listing** (text, graphics, in-app products) and explicitly does not build or
upload an APK/AAB — that gap is what this skill fills.

```
authoring (→ hub):   play-store-metadata / store-metadata-writer
                              │
listing SEND:        play-store-deliver      (supply: text, graphics, IAP)
binary SEND:         play-store-ship         (this skill: AAB → track → publish)
```

## Prerequisites

- **Tools:** a JDK matching the project's toolchain (Gradle, `jarsigner`), the repo's
  `./gradlew`, `openssl` and `unzip` for the script; Capacitor apps: `npm`, `npx cap`.
- **Credentials:** the upload keystore (`credentials.py --keystore <app>`) and a Play
  service-account JSON with release rights, both resolved by `shared/credentials.py`.
- **Hub (`$APP_HUB`):** optional — release notes are verified and sent from
  `<hub>/<slug>/store/play/changelogs/<vc>`; `--notes-dir` takes any `<locale>.txt` dir.
- **Other tracks:** `copy-edit` (shared-track) in parity mode over the changelog.

## Pre-flight verification — confirm each is READY (don't produce here)

| Area | Verify | Owned by |
|---|---|---|
| **Signing key** | `keystore.properties` reachable (usually `$KEYS_ROOT/android/<app>-keystore/`), and the AAB it produces is signed | one-time keystore setup |
| **versionCode** | strictly higher than every code already uploaded — **read it from `build.gradle`, not from notes** | this skill |
| **Changelog** | a folder of `<locale>.txt` for this versionCode — `<hub>/<slug>/store/play/changelogs/<versionCode>/` with a hub, `<app-repo>/fastlane/metadata/android/changelogs/<versionCode>/` without one | `play-store-metadata` |
| **Listing** | title / short / full description present per locale, if the listing itself is changing | `play-store-metadata` → `play-store-deliver` |
| **Play Console access** | the track accepts writes (see *the production gate*) | Play Console |

**Verify, don't re-produce.** If something is missing, hand off to the owning skill
and come back.

## versionCode discipline

The single most common way this goes wrong is trusting a note about the current
version instead of reading the file. **Read it:**

```bash
grep -nE "versionCode|versionName" <android-root>/app/build.gradle{,.kts}
```

- Play rejects any upload whose `versionCode` is not **higher than every code ever
  uploaded** — including codes used by releases on *other* tracks, and codes that
  were uploaded and then superseded.
- A bug-fix release should move `versionName` too. Two production releases that
  report the same version leave nobody able to tell which one they have.
- **An edit that is never committed consumes nothing.** Uploading an AAB into an
  edit and then deleting that edit leaves the versionCode free to upload again —
  verified 2026-09-07 on a live app, where vc6 was uploaded, the edit
  deleted, the AAB rebuilt with a new `versionName`, and vc6 uploaded again
  cleanly. This is what makes `--dry-run` below safe.

## Build the signed AAB  [local]

**Find the Android root first.** In a native project it is the repo, or `android/`. In
a hybrid one it is wherever the generated Android project sits — `android/` under the
web project. Everything below runs from there, and `./gradlew` is in it.

Copy the signing credentials in and build. The keystore is **never committed**, and
`build.gradle` leaves the release config unsigned when the file is absent rather than
failing — so an unsigned AAB is a real possible outcome, and the signature is checked
below rather than assumed.

```bash
cp "$(python3 ${CLAUDE_PLUGIN_ROOT}/shared/credentials.py --keystore <app>)" \
   <android-root>/keystore.properties
cd <android-root>
./gradlew bundleRelease
```

Output lands at `app/build/outputs/bundle/release/app-release.aab`.

**If Gradle cannot find a JDK, or dies with `invalid source release: NN`**, the toolchain
is older than the project asks for. `/usr/libexec/java_home -v <NN>` names one on macOS;
otherwise set `JAVA_HOME` to any JDK of that version. Android Studio bundles one at
`<Android Studio>/Contents/jbr/Contents/Home`, which is the reliable fallback when the
system default is a different major version.

### If this is a hybrid app (Capacitor, Cordova, a web shell)

**Sync the web assets before building**, or you will ship the previous build's HTML and
JavaScript under a new versionCode — the most silent failure in this whole path, because
the AAB is valid, the upload succeeds, and the app is simply the old one.

```bash
npm run build && npx cap sync android      # or whatever this project calls it
```

Run it from the web project, then build from the Android root as above.

### Verify the artifact before it leaves the machine
```bash
unzip -p app-release.aab base/manifest/AndroidManifest.xml | strings | grep -o "[0-9]\+\.[0-9]\+\.[0-9]\+"
jarsigner -verify -verbose:summary app-release.aab | tail -3      # must not say "unsigned"
```

**Delete `keystore.properties` from the project directory when the build is done.**

## Upload and publish  [Play Developer API]

Use the script — it implements the whole edit lifecycle and avoids the traps below:

```bash
# read-only: what is on each track right now
python3 ${CLAUDE_PLUGIN_ROOT}/skills/play-store-ship/scripts/publish_aab.py --package <pkg> --status

# rehearsal: uploads and stages the track, then DELETES the edit — changes nothing
python3 ${CLAUDE_PLUGIN_ROOT}/skills/play-store-ship/scripts/publish_aab.py \
  --package <pkg> --aab <path> --track production --name 1.2.3 \
  --notes-dir $APP_HUB/<slug>/store/play/changelogs/<vc> --dry-run

# the real thing (drop --dry-run; add --rollout 0.2 for a staged release,
# or --draft on an app that has never been published — see the draft-app gate)
```

The flow it runs is: **create edit → upload the bundle → PUT the track → commit**,
then re-reads the tracks to prove what landed.

### Traps this path has

- **The upload endpoint is a different host path.** Bundles go to
  `https://androidpublisher.googleapis.com/**upload**/androidpublisher/v3/…/bundles?uploadType=media`.
  Posting the AAB to the ordinary `/androidpublisher/v3/…` path returns
  `Invalid JSON payload received. Unexpected token. PK…` — the API trying to parse
  the zip as JSON.
- **`:commit` must not go through curl.** The URL
  `…/edits/<id>:commit` returns a **404 HTML page** through curl in zsh — the colon
  does not survive — while the identical request through Python's `urllib` succeeds.
  Every other call in the flow works either way. The script uses `urllib` throughout.
- **`status: "completed"` means 100% rollout, not "approved".** It describes the
  release's rollout, not Google's review.
- A **staged rollout** is `status: "inProgress"` with `userFraction`; the script's
  `--rollout` sets both.

### The production gate (new accounts)
A personal developer account can be limited to closed testing until production
access is granted. The signature from the API: `alpha` accepts writes while **both
`beta` and `production` reject every write with `FAILED_PRECONDITION`**, even a PUT
with `releases: []`. That is the gate, not a credentials or metadata problem —
`--status` will show it. It lifted, on one measured app, about five days after
applying.

### The draft-app gate (an app never published)
A different wall, and it comes earlier. Until an app has been published once — while
the Console's app-content forms (Data safety, content rating, target audience, …) are
not all complete — Play calls it a **draft app**, and the upload and the track PUT
succeed but **the commit** fails:

```
HTTP 400 … Only releases with status draft may be created on draft app.
```

Pass **`--draft`** (mutually exclusive with `--rollout`): the release is created with
`status: "draft"`, the commit goes through, and nothing reaches any tester until it is
rolled out from the Console once the forms are done. Measured 2026-09-26 on the first
upload of a new app — it landed on `alpha` as a draft. The versionCode **is** spent by
that commit, like any committed edit.

## Listing and changelog

The **binary** carries its release notes in the track's `releaseNotes` (that is what
`--notes-dir` sends). The **listing** — title, descriptions, graphics — is a
different surface: trigger `play-store-deliver`, and never run `supply` casually,
because it overwrites the image sets it is given and can wipe screenshots uploaded
by hand.

**Run the copy gate on the changelog before shipping it.** Completeness is not
correctness, and a translation nobody here reads is exactly where a claim goes
missing:

Run the **`copy-edit`** skill in parity mode — `--parity-only --fail-on-parity` — over
the changelog folder for this versionCode (`--notes-dir` above names it). It is in another plugin
(shared-track): pass it the flags and the paths, and let it find its own script.

## After publishing

- Re-read the tracks and show the user what actually landed (the script does this).
- **Every production release is reviewed by Google before it reaches devices**, and
  **the API exposes no review-status field at all.** Don't infer approval from the
  API. The observable signals are the Console dashboard (`In review` → `Available on
  Google Play`) and the public listing page, whose served version number is the
  honest answer to "is it out yet":
  ```bash
  curl -s "https://play.google.com/store/apps/details?id=<pkg>&hl=en" | grep -o '"[0-9]\+\.[0-9]\+\.[0-9]\+"'
  ```
- Record the release (versionCode, version name, track, date) wherever the project
  keeps its release history.

## Testing a build on a physical device

- A **debug** build cannot replace a Play-installed one — different signing key. The
  store copy must be uninstalled first, which **erases the app's local data**
  (`localStorage`, preferences). Say so before doing it, and remember the user cannot
  update that debug build from Play afterwards: it must be uninstalled again.
- **Never drive the user's phone with `adb shell input tap`.** The taps land on
  whatever holds focus, not on the app you launched — this has put taps into a
  user's private chat. Verify focus first with
  `adb shell dumpsys window | grep mCurrentFocus`, and prefer driving the WebView
  over devtools (see `android-webview-toblob-is-slow` in memory for the CDP recipe)
  or simply asking the user to tap.

## Boundaries
- **Publishing is outward-facing and hard to undo. Confirm before committing an
  edit**, and treat `--dry-run` as the default first run.
- Never lower a versionCode, and never work around the review — there is nothing to
  work around; it is a wait.
- The Data safety form, content rating, pricing, and the production-access
  application are **Console-only**: give the exact navigation and let the user do it.

## Related skills
- `play-store-deliver` — the listing/graphics/IAP send-surface (`supply`); trigger it
  for anything that is not the binary.
- `play-store-metadata` — authors the listing text and the changelogs into the hub.
- `copy-edit` — the parity gate this skill runs over the changelog.
- `ship-apple-app` — the Apple counterpart of this skill.
