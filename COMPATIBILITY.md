# What has to be installed, and where this runs

**Nothing is needed to install the marketplace.** Tools are needed by individual skills,
at the moment they run, and a skill that needs one says so and stops rather than failing
halfway. The table exists so you can see the cost of a track before you enable it.

---

## The platform

| | |
|---|---|
| **macOS** | required for everything Apple: `xcodebuild`, `xcrun`, `notarytool`, the keychain, `sips`. There is no way around this — Apple's toolchain is macOS-only. |
| **Linux / Windows** | the Android, web, design and cross-store tracks work. The Apple track does not, and will say so rather than produce something wrong. |
| **Python 3.9+** | every script here. Standard library only, except where the table says otherwise. |
| **Claude Code** | the plugin runtime. `claude plugin validate` passing is the compatibility statement. |

Nothing here has a package to install. There is no `pip install`, no `npm install`, and
no dependency file — the scripts are standard-library Python, shell, and Ruby that
fastlane already brings.

---

## Per track

| Track | Needs | For what |
|---|---|---|
| **design-track** | nothing beyond Python 3 | |
| **web-track** | the project's own toolchain | the audit is pure Python; publishing runs whatever the site uses |
| **capacitor-track** | `adb`, Node | inspecting the WebView on a device |
| **shared-track** | `fastlane` (some paths), Node or Gradle to read a version | the copy measurer and the profile work need nothing |
| **android-track** | JDK (the version the project declares), Gradle wrapper, `adb`, `keytool`, `apksigner` / `jarsigner` | building, signing and verifying an AAB |
| | `fastlane` (`supply`) | uploading a listing |
| | Pillow, ImageMagick | icons and store graphics |
| **apple-track** | Xcode command line tools | `xcodebuild`, `xcrun`, `swift`, `sips` |
| | `fastlane` (`deliver`, `snapshot`) | uploading a listing, capturing screenshots |
| | Ruby gems `spaceship`, `xcodeproj` | the App Store Connect API, and editing a project |
| | `ffmpeg` | App Preview video conversion and verification |
| | **Pillow built with RAQM** | framing a right-to-left caption. Plain Pillow renders the characters in the wrong order, silently, and only someone who reads that language will notice |
| | `notarytool`, `stapler`, `hdiutil` | notarisation and DMG packaging |
| | Sparkle's `generate_keys` / `sign_update` | direct macOS distribution only |

Checking Pillow's RAQM support, which is the one that fails invisibly:

```bash
python3 -c "from PIL import features; print(features.check('raqm'))"
```

---

## Credentials, and what each one unlocks

None is needed to install, and none is needed by the skills that only read and report.

| | Needed by | Where it comes from |
|---|---|---|
| App Store Connect API key | uploading anything to Apple | App Store Connect → Users and Access → Integrations |
| Apple signing certificate | building for distribution | your Apple Developer account |
| Notary credential | notarising a Mac app | `notarytool store-credentials`, kept in the login keychain |
| Play service account | uploading anything to Google | Play Console → Setup → API access |
| Android upload keystore | signing an AAB | you create it once, and losing it is unrecoverable |

All of them are named — never held — in `$KEYS_ROOT/credentials.json`. See
[TRUST.md](TRUST.md) for what the skills do and do not do with them.

---

## Optional, and genuinely optional

| | What it adds | Without it |
|---|---|---|
| **a data repo** ("hub") | one source of truth for listing text, media and prices across several apps | the app repo's own `fastlane/` is the source of truth, and the delivery skills detect that |
| **grove** | per-repo track allocation from one registry, and guards against writing into the wrong repo | `factory/enable.py` enables tracks per repo; the guards are what you give up |
| **a website** | a privacy URL you control, and app pages | the stores need a privacy URL that **resolves**; where it is hosted is nobody's business |

---

## Versions this was built against

Recorded so a future failure can be told from a version drift. Nothing pins these — if
a vendor changes something, the skill is what needs updating.

| | |
|---|---|
| Apple screenshot and preview specifications | checked 2026-09-11, with the date in `apple-specs.json` |
| fastlane | `deliver`, `supply`, `snapshot`, `match` as of 2.2x |
| Play Developer API | AndroidPublisher v3 |
| App Store Connect API | the `v1` endpoints `spaceship` uses |

**The largest maintenance surface here is not the code.** A store field that was
renamed, a review rule that moved, a `fastlane` flag that changed — nothing in this
repo can notice any of it. That is checked by using the skills, and by reading the
vendor's own release notes, not by a test.
