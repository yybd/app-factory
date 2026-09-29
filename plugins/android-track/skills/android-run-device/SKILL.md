---
name: android-run-device
description: >-
  Build a debug APK and run it on a connected Android phone or emulator — the
  development loop, not a store release. Use whenever the user asks to run, test,
  install or try the app on Android ("תריץ על המכשיר", "תתקין באנדרואיד"), when a Gradle
  build fails with "Cannot find a Java installation ... languageVersion=21" or "invalid
  source release: 21", when `adb` is missing or picks the wrong device, when an
  installed APK still shows old UI after a code change, or when a device-only behaviour
  (background audio, media notifications, battery, permissions) needs checking on real
  hardware. For the signed release build that goes to Google Play, use play-store-ship
  instead; this skill never touches the keystore. Debug builds only: it does NOT touch
  the release keystore or upload anything.
---

# Run an Android app on a connected device

The Android counterpart of building to an iPhone. Everything here is the **debug**
loop: unsigned-by-debug-key, installed over USB, launched immediately. Nothing in
it touches release signing — that is `play-store-ship`, and the two must not be
confused, because a debug APK and a release AAB are signed by different keys and
cannot replace each other on a device.

## Prerequisites

- **Tools:** a JDK of the version the project declares (Android Studio's JBR as fallback),
  Android SDK platform-tools (`adb`), the repo's `./gradlew`; Capacitor: `npm`, `npx cap`.
- **Credentials:** none — debug builds use the per-machine debug key.
- **Hub (`$APP_HUB`):** not used.
- **Other tracks:** `capacitor-bug-flow-review` (capacitor-track) for a bug that shows
  up on the device.

## First: does the repo already have a script?

Look for `run-android.sh` (usually beside the project's iOS run script, in whatever directory
holds the Capacitor project). If it exists, **run it** rather than re-deriving the
steps — it already encodes the app's package name, launcher activity, and build
command, and re-deriving them by hand is how those drift apart.

If it does not exist, do the steps below, and then **offer to write the script**.
The knowledge belongs in the skill; the artifact belongs in the repo, so a person
can run it without opening a session at all. The template is at the end.

## The two things that actually go wrong

Both of these have cost real time, and neither announces itself as what it is.

### 1. Gradle needs the JDK the project asks for, and the system default is not it

The symptom depends on how the project declares its Java version, so it arrives in two
different disguises — with `NN` being whatever the project wants:

```
Cannot find a Java installation on your machine (…) matching:
  {languageVersion=NN, vendor=any vendor, …}
```

```
invalid source release: NN
```

**The first reads like a missing installation and is not one.** It means no *matching*
JDK, which is a different problem with a different fix.

Read the version the project actually asks for — `languageVersion`,
`sourceCompatibility` or `jvmTarget` in `app/build.gradle` or `build.gradle.kts` — then
point Gradle at a JDK of that version for the one command:

```bash
JAVA_HOME="$(/usr/libexec/java_home -v NN)" ./gradlew assembleDebug     # macOS, any vendor
```

If none is installed, Android Studio bundles one at
`<Android Studio>/Contents/jbr/Contents/Home`, which is the reliable fallback on a Mac
that has it. On Linux or a CI runner, install the JDK and set `JAVA_HOME`.

`play-store-ship` carries the same fact for the release build. It is stated in both
places on purpose: someone hitting it while installing a debug build will not think
to open the store-shipping skill.

### 2. `adb devices` returns emulators too, and an emulator can lie

Prefer a **physical device** whenever one is attached, and say so when falling back
to an emulator.

This is not tidiness. On one project, an emulator reported
`Stopping service due to app idle` for a foreground media service, and three
separate fixes were written to chase it — `RENDERER_PRIORITY`, MediaController
binding, `onUpdateNotification(true)`. None of them was the problem. The behaviour
never occurred on a real OnePlus 7 Pro with default battery settings. **Anything
about background execution, doze, battery, notifications or audio focus is only
trustworthy on hardware.**

```bash
adb devices | awk '$2=="device"{print $1}'      # emulator-NNNN are emulators
adb -s <serial> install -r <apk>                # -s is not optional with two attached
```

`adb` may not be on `PATH`; the SDK copy is at
`~/Library/Android/sdk/platform-tools/adb`.

## The loop

For a **Capacitor** app, the web build and the sync come first, and skipping either
is the quietest failure in this path — Gradle happily builds an APK around whatever
`android/app/src/main/assets/public` last held, so the install succeeds and the app
shows the previous UI. That looks like "my change did nothing", not like a missing
build step.

```bash
npm run build                # web bundle (and whatever else the app bakes in)
npx cap sync android         # copies www/ and native config into android/
cd android && JAVA_HOME="..." ./gradlew assembleDebug
adb -s <serial> install -r app/build/outputs/apk/debug/app-debug.apk
adb -s <serial> shell am start -n <package>/<activity>
```

For a **native** Android app, drop the first two lines.

**Read the package and activity from the manifest rather than assuming them** —
`android:name=".MainActivity"` under the `LAUNCHER` intent-filter in
`android/app/src/main/AndroidManifest.xml`, and the package from `namespace` or
`applicationId` in `app/build.gradle`. `am start` fails with
`Activity class ... does not exist` when either is guessed wrong, and that error
looks like a broken install.

`adb shell monkey -p <package> -c android.intent.category.LAUNCHER 1` also launches
an app and needs no activity name, but it injects a random event and prints network
statistics; prefer `am start` and keep `monkey` for when the activity is genuinely
unknown.

## When it still fails

| What you see | What it is |
|---|---|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | A build signed by a different key is installed (often a release build). `adb uninstall <package>` first — this erases the app's data. |
| `INSTALL_FAILED_INSUFFICIENT_STORAGE` | Usually an emulator. Also check the APK size: a stale `outDir` that is not cleaned between builds accumulates dead bundles inside it. |
| `device unauthorized` | The USB-debugging prompt on the phone was not accepted. Unlock the screen and look for it. |
| App installs, UI is old | The web build or `cap sync` was skipped. See **The loop**. |
| `no devices/emulators found` | Cable, or USB debugging off, or `adb kill-server && adb start-server`. |

## The script to leave behind

Write it beside the iOS one, in the directory a session actually stands in for this
app (for a monorepo that is the Capacitor subdirectory, not the git root). Keep the
comments in the repo's own language — they explain a decision to whoever reads it
next, and that is the app's repo, not this skill.

A working one ships with this skill. Copy it, do not retype it:

```bash
cp ${CLAUDE_PLUGIN_ROOT}/skills/android-run-device/scripts/run-android.sh <app-dir>/
```

It does four things the bare commands do not: finds a JDK 21 and says so clearly
when there is none, prefers a physical device and announces an emulator fallback,
honours `ANDROID_SERIAL` so a device can be forced without editing the file, and
runs the web build and sync before Gradle when the project is Capacitor.

It also **reads the application id and the launcher activity out of the project**
rather than hard-coding them, so those cannot drift. Two things do need adapting:
`ANDROID_DIR`, and the web-build command if the app does not use `npm run build`.

## Boundaries

- **Debug builds only.** It never touches the release keystore, never signs for
  distribution, and never uploads. `play-store-ship` owns all three.
- **It does not fix the app.** It gets a build onto a device and reports what failed;
  a bug that shows up there goes to `capacitor-bug-flow-review` or the app's own
  tests.
