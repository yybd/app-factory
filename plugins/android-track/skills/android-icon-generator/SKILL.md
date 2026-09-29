---
name: android-icon-generator
description: >-
  Generate a complete Android launcher-icon set from one source image — the adaptive
  icon (separate foreground and background layers, correct safe zone), the legacy
  mipmaps at every density, the round icon, the optional monochrome layer for themed
  icons, and the 512x512 Play store icon — written into the right res/ folders with
  correct mipmap-anydpi-v26 XML. Use whenever an Android app needs its launcher icon
  created, replaced, resized or fixed, when the icon looks cropped or off-centre on the
  launcher, when Play rejects the store icon, when adding an adaptive or themed
  (monochrome) icon, or when porting an iOS icon to Android ("אייקון לאנדרואיד", "תכין
  אייקונים"). The Apple counterpart is app-icon-generator; this is a separate skill
  because Android's icon is a layered, heavily masked format, not a flat square. It does
  NOT produce store screenshots or the feature graphic; play-store-media owns those.
---

# Android Icon Generator

> **Conversational language:** talk to the user — questions, summaries, reports — in the `conversational language` set in the hub `DATA.md` (`$APP_HUB/DATA.md`); fall back to the language the user writes in if it is unset. This sets the *conversation* language only.

## Prerequisites

- **Tools:** `Pillow` (`pip3 install Pillow`) for the generator script; nothing else
  beyond Claude Code and Android Studio.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — `--play-icon` writes the 512 px store icon into
  `$APP_HUB/<slug>/media/play/`; without a hub, drop the flag and keep the icon elsewhere.
- **Other tracks:** none.

## Why this is not the Apple skill with a flag

Apple's icon is **one flat square**, masked lightly by the system. Android's is a
**stack**: a background layer and a foreground layer, each 108dp, of which the
system shows only the inner **66dp** — and it masks that to whatever shape the
launcher wants, circle on one phone, squircle on another. The outer ring exists so
the icon can be animated and parallaxed, and it **will be cropped**.

The practical consequence, and the reason to look at the art before converting
anything: **an iOS icon fed straight into an Android adaptive icon loses its
edges.** Artwork that runs to the corners — a full-bleed background, a border, a
frame — comes out cut on Android. Ask for or produce a version whose subject sits
inside the middle 61%, and put the colour or texture that used to reach the edge
into the *background layer*, where being cropped costs nothing.

## What a complete set is

| Piece | Where | Size |
|---|---|---|
| Adaptive foreground | `mipmap-<density>/ic_launcher_foreground.png` | 108dp → 108/162/216/324/432 px |
| Adaptive background | a colour in `values/ic_launcher_background.xml`, or a matching PNG | same |
| Adaptive XML | `mipmap-anydpi-v26/ic_launcher.xml` + `ic_launcher_round.xml` | — |
| Legacy launcher | `mipmap-<density>/ic_launcher.png` + `_round.png` | 48/72/96/144/192 px |
| Monochrome (themed, Android 13+) | referenced from the same XML | 108dp |
| Play store icon | delivered from the media tree, never from `res/` | **512 × 512**, 32-bit PNG, **no alpha** |

Densities are mdpi / hdpi / xhdpi / xxhdpi / xxxhdpi = ×1 / ×1.5 / ×2 / ×3 / ×4.

## Generate

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/android-icon-generator/scripts/generate_android_icons.py \
  --source icon-1024.png \
  --res <android-root>/app/src/main/res \
  --background "#fcfbf6" \
  --play-icon $APP_HUB/<slug>/media/play/icon-512.png   # or <app-repo>/fastlane/metadata/android/<locale>/images/icon.png
```

- `--background` takes a colour (written as a colour resource — the lightest option
  and what most apps want) or `--background-image` for artwork.
- `--monochrome` derives a single-colour layer from the source's shape for themed
  icons; check the result, since a detailed icon flattens into mud.
- `--safe-zone-check` reports how much of the source would be cropped **without**
  writing anything — run it first on any icon you did not design for Android.
- Requires Pillow (`pip3 install Pillow`).

## After generating
- Confirm the manifest points at it: `android:icon="@mipmap/ic_launcher"` and
  `android:roundIcon="@mipmap/ic_launcher_round"`.
- **Look at it on a device or emulator**, on a launcher with circular masking. The
  safe zone is a promise about geometry, not about whether the art survives it.
- Capacitor projects: `@capacitor/assets` will regenerate icons from
  `assets/icon.png` and **overwrite** what this wrote. Decide which owns the icon,
  and if it is this skill, keep the source out of `assets/`.
- The **Play store icon is not the launcher icon**: it is a separate 512×512 with no
  transparency, delivered from the media tree by `play-store-deliver`, and it is
  the one users see in the listing.

## Boundaries

- **Store graphics are not icons.** The feature graphic, the screenshots and the
  store listing icon are `play-store-media`'s; this skill produces the launcher icon
  set that ships inside the app.
- **It does not decide the artwork.** Given a source image it produces every density
  and shape Android needs; designing that image is not its job.
- The Apple counterpart is `app-icon-generator`, and the two do not share a source
  file — Android's adaptive shape crops differently.

## Related skills
- `play-store-media` — the rest of the Play graphics (feature graphic, screenshots).
- `play-store-deliver` — uploads the store icon.
- `app-icon-generator` — the Apple counterpart (flat square, `.xcassets`).
