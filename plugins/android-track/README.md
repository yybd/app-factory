# android-track

Google Play, and getting an Android build onto a device to look at. Enable it in a
repo that builds an Android app.

<!-- generated:track -->
*Generated from the skills themselves by `factory/render_track_readmes.py` —
edit a skill, not this table.*

## The 9 skills

| Skill | What it is for | scripts | refs |
|---|---|---|---|
| `android-credentials` | The single owner of Android signing and Google Play credentials — the upload keystore, Play App Signing, the SHA-1/SHA-256 fingerprints other servi… |  |  |
| `android-icon-generator` | Generate a complete Android launcher-icon set from one source image — the adaptive icon (separate foreground and background layers, correct safe zo… | 1 |  |
| `android-run-device` | Build a debug APK and run it on a connected Android phone or emulator — the development loop, not a store release. | 1 |  |
| `play-store-compliance` | Audit an Android app against Google Play's policies and the Console declarations that gate a release, and fix what would get it rejected or removed… |  |  |
| `play-store-deliver` | The single send-surface to Google Play — sync the app's Play listing metadata, graphics, changelogs, AND in-app products / subscriptions from the h… | 3 | 1 |
| `play-store-media` | Produce and conform the graphics a Google Play listing requires — phone, 7" and 10" tablet screenshots, the 1024x500 feature graphic, the 512x512 i… |  |  |
| `play-store-metadata` | Author and validate a Google Play listing's text: title, short and full description, release notes per versionCode, and the graphics the listing re… | 3 | 1 |
| `play-store-reviews-responder` | Read Google Play user reviews and write and post replies to them, through the Play Developer API. | 1 |  |
| `play-store-ship` | Verify an Android app is release-ready and ship it to Google Play — the FINAL Play step: confirm the content is in place (signing key, versionCode,… | 1 |  |

**What it costs.** 7,634 characters of description ≈ 1,908 tokens, in every session
that enables this track. A skill's body is read only when the skill fires; its description
is in context always.

**What it needs on the machine**, from the scripts that call it: `fastlane`, `gradle`, `adb`, `Pillow`, `openssl`, `node / npm`.
<!-- /generated:track -->
