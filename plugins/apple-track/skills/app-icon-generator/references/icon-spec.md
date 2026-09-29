# Apple app icon spec (by platform)

last-verified: 2026-06-02
sources:
- https://developer.apple.com/design/human-interface-guidelines/app-icons
- Xcode asset catalog (AppIcon) requirements

## Universal rules
- **Format**: PNG, sRGB (or Display P3), flattened.
- **Shape**: full **square** canvas. Don't pre-round iOS corners — the system
  masks. (macOS is the exception: you design the rounded shape with padding.)
- **App Store / marketing icon**: 1024×1024, **no alpha/transparency** (opaque).
  iOS app icons must also be opaque. macOS icons may use alpha (transparent
  corners).
- **Source**: design at 1024×1024 and downscale. Never upscale a small icon.
- Modern Xcode supports a **single-size** 1024 icon for iOS/watchOS (one image,
  the system derives the rest). macOS still needs the full size set.

## iOS / iPadOS
Single-size (recommended, what the generator emits): one **1024×1024** image,
idiom `universal`, platform `ios`, no scale.

Classic full set (point sizes × scale → pixels), if you need explicit sizes:
| Use | pt | scales | pixels |
|-----|----|--------|--------|
| iPhone notification | 20 | 2x,3x | 40, 60 |
| iPhone settings | 29 | 2x,3x | 58, 87 |
| iPhone spotlight | 40 | 2x,3x | 80, 120 |
| iPhone app | 60 | 2x,3x | 120, 180 |
| iPad notification | 20 | 1x,2x | 20, 40 |
| iPad settings | 29 | 1x,2x | 29, 58 |
| iPad spotlight | 40 | 1x,2x | 40, 80 |
| iPad app | 76 | 2x | 152 |
| iPad Pro app | 83.5 | 2x | 167 |
| App Store | 1024 | 1x | 1024 |
Rules: square, opaque, no rounded corners.

## macOS
Full set required (point size × scale, with file dedup since 16@2x == 32@1x):
| pt | scale | pixels |
|----|-------|--------|
| 16 | 1x | 16 |
| 16 | 2x | 32 |
| 32 | 1x | 32 |
| 32 | 2x | 64 |
| 128 | 1x | 128 |
| 128 | 2x | 256 |
| 256 | 1x | 256 |
| 256 | 2x | 512 |
| 512 | 1x | 512 |
| 512 | 2x | 1024 |
Unique pixel files needed: 16, 32, 64, 128, 256, 512, 1024.
Idiom: `mac`. Design with the standard macOS padding + rounded-rect shape inside
the square canvas; alpha allowed (transparent outside the shape).

## watchOS
Single-size **1024×1024** (idiom `universal`, platform `watchos`) on modern
Xcode; the system derives sizes. Icon is **circular-masked** — keep important
content centered, full-bleed background, opaque.

## tvOS
App icon is a **layered** image stack (parallax), not a single flat PNG —
authored as a `.brandassets` / layered set, plus a top-shelf image. Different
workflow; the generator does NOT produce these. Follow Apple's tvOS layered icon
guidance and create them in Xcode.

## visionOS
App icon is **layered** (a stack of 2–3 layers for depth), authored as a layered
set. The generator does NOT produce these; follow Apple's visionOS guidance.

## Contents.json idioms reference
- iOS single-size: `{"idiom":"universal","platform":"ios","size":"1024x1024"}`
  (no `scale`).
- macOS: entries with `"idiom":"mac"`, `"scale":"1x"|"2x"`, `"size":"NxN"` (pt).
- A single AppIcon set may contain multiple idioms (e.g. mac + ios) for a
  multiplatform target.

If Apple has changed sizes since `last-verified`, verify against the App Icons
HIG page and Xcode's AppIcon set (add an empty AppIcon set in Xcode and read
which wells it shows).
