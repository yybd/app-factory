---
name: app-icon-generator
description: >-
  Generate a complete Xcode app-icon set from a single source image (or create a starter
  icon if the user has none), sized to Apple's current icon spec for the target
  platform(s) — iOS/iPadOS, macOS, watchOS, tvOS, visionOS — and place it in the right
  .xcassets AppIcon set with a correct Contents.json. Use this whenever the user wants
  to create, generate, resize, replace, or fix an app icon / AppIcon set, mentions icon
  sizes or "all the icon sizes", gets an Xcode/App Store icon error (missing sizes,
  alpha, wrong dimensions), or is setting up icons for a new app or platform ("תכין
  אייקון", "כל הגדלים של האייקון"). It asks for the source image or offers to generate
  one, checks Apple's icon requirements, and validates the result. It makes the icon set
  only; it does NOT produce store screenshots (appstore-media owns those).
---

# App Icon Generator

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

Apple needs the app icon at specific pixel sizes per platform, in the right
format (square, sRGB PNG; no transparency for the App Store / iOS icon; macOS
icons use padding + rounded corners), wired up in an `AppIcon` set inside an
asset catalog. Getting any of that wrong is an Xcode build error or an upload
rejection. This skill produces the whole set correctly from one good source
image, using `sips` (built into macOS) — no extra dependencies.

## Prerequisites

- **Tools:** `sips` (built into macOS); `swift` from the Xcode command line tools only
  for `scripts/make_starter_icon.swift`; Python 3, stdlib only.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — only the conversational-language default in `DATA.md`.
- **Other tracks:** none.

## Workflow

### 1. Get the source image — ask or generate
Ask the user which they want:
- **They have an image** — ask for its path. Ideal: a **1024×1024 PNG, square,
  flat (no transparency)**. If it's smaller, not square, or has alpha, say so
  (upscaling small icons looks bad; alpha must be flattened for iOS/App Store)
  and offer to proceed, fix, or get a better source.
- **They don't have one** — offer to generate a simple starter icon (gradient +
  a letter/glyph) so they're unblocked, and be clear it's a placeholder to
  refine later. Use the generator:
  ```bash
  swift ${CLAUDE_PLUGIN_ROOT}/skills/app-icon-generator/scripts/make_starter_icon.swift \
    --out /tmp/appicon-source.png --text "W" --bg1 "#2E6BD6" --bg2 "#1B3F87" --fg "#FFFFFF"
  ```
  If a richer/custom design is wanted, that's a design task — offer to refine the
  starter, or suggest a real design tool; don't pretend a generated placeholder
  is finished art.

### 2. Determine platform(s) and the AppIcon set
- **Platform(s)** — iOS/iPadOS, macOS, watchOS, tvOS, visionOS. Sizes and rules
  differ per platform; see [references/icon-spec.md](references/icon-spec.md).
  Detect from the project (SDKROOT) or ask.
- **Which AppIcon set** — the asset-catalog set the target actually uses. It is
  NOT always named `AppIcon`: read `ASSETCATALOG_COMPILER_APPICON_NAME` from the
  project (a project may have several, e.g. one per app target). Confirm the set
  name and the `.xcassets` before writing, so you update the icon the app
  actually ships.

### 3. Generate and place the set
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/app-icon-generator/scripts/generate_iconset.py \
  --source /path/to/icon-1024.png \
  --xcassets /path/to/Assets.xcassets \
  --name AppIcon \
  --platform macos        # or ios / all
```
The script validates the source, resizes to every required size with `sips`,
writes the PNGs into `<xcassets>/<name>.appiconset/`, and writes a correct
`Contents.json`. It is non-destructive about the catalog structure and reports
exactly what it wrote. If `--xcassets` is a project root it will try to locate
the catalog; confirm the choice when there is more than one.

### 4. Validate
The generator prints a summary and flags problems (non-square source, alpha on
an iOS/App Store icon, source smaller than the largest required size). Resolve
flags before building. For the App Store 1024 marketing icon specifically,
ensure it is opaque — if the source has alpha, flatten it (the starter generator
outputs opaque PNGs; for a user image, composite over a background first).

## Notes on getting it right
- **One source, many sizes**: always downscale from the largest (1024). Never
  upscale a small icon — it will look soft and can be rejected.
- **iOS/iPadOS**: square, full-bleed, NO transparency, NO pre-rounded corners
  (the system masks them). Modern Xcode accepts a single 1024 "single-size"
  icon; the script uses that by default for iOS.
- **macOS**: the design should include the standard padding and rounded-rect
  shape inside the canvas (macOS does not mask for you), and alpha is allowed
  (the corners are transparent). The script emits the full mac size set.
- **watchOS/visionOS/tvOS**: have special shapes/layers (circular, layered
  parallax). The script covers iOS + macOS fully; for the others, follow
  [references/icon-spec.md](references/icon-spec.md) and confirm before relying
  on generated output.

## Boundaries

- **It does not produce store media.** Screenshots and App Previews are
  `appstore-media`'s; a single image resized to a store size is
  `apple-app-store-screenshots`'.
- **It does not design.** Given a 1024×1024 source it writes every size and the
  contents.json; choosing what the icon shows is a design decision, not a
  generation step.

## Reference files
- [references/icon-spec.md](references/icon-spec.md) — Apple icon sizes, formats,
  and per-platform rules; the source of truth for what gets generated.
- [scripts/generate_iconset.py](scripts/generate_iconset.py) — source image →
  full AppIcon set + Contents.json (uses `sips`).
- [scripts/make_starter_icon.swift](scripts/make_starter_icon.swift) — render a
  1024 opaque starter icon (gradient + glyph) when the user has no image.
