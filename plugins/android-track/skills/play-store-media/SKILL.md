---
name: play-store-media
description: >-
  Produce and conform the graphics a Google Play listing requires — phone, 7" and 10"
  tablet screenshots, the 1024x500 feature graphic, the 512x512 icon, and an optional
  promo video — by capturing them from a running app on an emulator or device and
  fitting them to Play's exact rules. Use whenever the user wants Play screenshots or
  graphics, a feature graphic, captures for the Play listing, needs an image resized or
  fixed for Play, or Play rejects a graphic for its size, ratio or aspect ("צילומי מסך
  לפליי", "גרפיקת פיצ'ר"). It captures with adb, conforms with ImageMagick, and writes
  into the hub media tree that play-store-deliver uploads from. The Apple counterparts
  are appstore-media (capture) and apple-app-store-screenshots (conform). It captures
  and conforms images; it does NOT upload them — play-store-deliver does.
---

# Play Store Media — capture and conform

> **Conversational language:** talk to the user — questions, summaries, reports — in the `conversational language` set in the hub `DATA.md` (`$APP_HUB/DATA.md`); fall back to the language the user writes in if it is unset. This sets the *conversation* language only — the media itself follows the app's target locales.

Play's asset rules are far looser than Apple's — there are no per-device pixel
tables, only ranges — so this one skill covers both halves that Apple needs two for:
**capturing** from a running app and **conforming** an image that already exists.

## Prerequisites

- **Tools:** `adb` (Android SDK platform-tools) with an emulator or device for capture;
  ImageMagick's `magick` (`brew install imagemagick`) to conform and verify.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — with one, files land in `$APP_HUB/<slug>/media/play/`
  and the deliver skill mirrors them; without one, in the repo's own
  `fastlane/metadata/android/<locale>/images/`, which is then the source of truth.
- **Other tracks:** `copy-edit` (shared-track) over marketing captions, per locale.

## What a listing needs

| Asset | Rule | Required |
|---|---|---|
| **Phone screenshots** | 2–8. Each side 320–3840 px, ratio at most 2:1 either way | yes |
| **7" tablet** | same limits | only if the listing claims tablet support |
| **10" tablet** | same limits | only if the listing claims tablet support |
| **Feature graphic** | exactly **1024 × 500**, PNG or JPEG, no alpha | yes |
| **App icon** | exactly **512 × 512** 32-bit PNG, no alpha, under 1 MB | yes |
| **Promo video** | a YouTube URL, not an upload | no |

Confirm the current numbers against the Console before a first submission — Play
changes them less often than Apple, but it does change them.

The feature graphic is the one people get wrong: it is a **banner**, shown cropped
at some sizes, so nothing that matters may sit near an edge, and text in it must
survive being shrunk to a thumbnail.

## Capture from a running app

Screenshots come from the device or emulator, in the locale being captured:

```bash
adb shell settings put system font_scale 1.0        # a scaled font ruins consistency
adb exec-out screencap -p > phone-01.png
adb shell wm size                                    # what you actually captured
```

Rules that keep a set usable:
- **Capture every locale.** A Hebrew listing showing English screenshots reads as
  unfinished. Switch the app's own language, not only the system's, if the app has
  its own setting.
- **Status bar**: either clean it (demo mode) or crop it. A real battery percentage
  and a stranger's notifications are noise in a store listing.
  `adb shell cmd overlay enable com.android.systemui.navigationbar.gestural` and the
  demo-mode broadcasts (`am broadcast -a com.android.systemui.demo`) give a fixed
  clock and full battery on devices that allow it.
- **Never drive a phone the user is holding** with blind `adb shell input tap` — the
  taps land on whatever holds focus, not on your app. Check
  `adb shell dumpsys window | grep mCurrentFocus` first, prefer an emulator for
  capture, and for a web/Capacitor UI drive the WebView over devtools instead.
- Capture the app **doing something**, not its empty state.

## Conform an image to Play's rules

```bash
# feature graphic — exact size, no alpha
magick in.png -resize 1024x500^ -gravity center -extent 1024x500 -background white -alpha remove feature.png
# store icon — exact size, no alpha
magick icon.png -resize 512x512 -background white -alpha remove -strip icon-512.png
# a screenshot that breaks the 2:1 ratio: pad rather than stretch
magick shot.png -resize 1080x1920 -gravity center -extent 1080x1920 -background "#fcfbf6" out.png
```

When the source aspect does not match the target, **ask the user how to fit it** —
pad on a background, blur-extend, or crop — and never silently stretch. Alpha is the
other silent failure: Play refuses an icon or feature graphic with transparency, and
the error names the file rather than the reason.

Verify before delivering:
```bash
magick identify -format "%f  %wx%h  alpha=%A\n" *.png
```

## Where the files go
Per locale, into whichever tree the app uses — the same two modes the deliver skill has:

**With a hub**, the tree `play-store-deliver` uploads from:
```
$APP_HUB/<slug>/media/play/<locale>/images/phoneScreenshots/
                                              /sevenInchScreenshots/
                                              /tenInchScreenshots/
                                              /featureGraphic.png
                                              /icon.png
```
Here `fastlane/` is not authored by hand — the deliver skill mirrors the hub into it
with `rsync --delete`, so anything written there directly is destroyed on the next run.

**Without one**, the `supply` layout in the app repo, which IS the source of truth:
```
<app-repo>/fastlane/metadata/android/<locale>/images/phoneScreenshots/  …same names…
```

## Boundaries
- Don't upload from here; `play-store-deliver` is the single send-surface, and a
  careless `supply` run **overwrites the image sets it is given** — it can wipe
  screenshots someone uploaded by hand.
- Marketing captions on screenshots are copy: run `copy-edit` over them, per locale.

## Related skills
- `play-store-deliver` — uploads what this produces.
- `play-store-metadata` — the listing text these sit beside.
- `appstore-media` · `apple-app-store-screenshots` — the Apple counterparts.
