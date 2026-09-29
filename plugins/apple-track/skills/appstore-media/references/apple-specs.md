# Apple App Store media specifications

Source of truth (re-check here if anything is rejected — specs change occasionally):
- Screenshots: https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/
- App Previews: https://developer.apple.com/help/app-store-connect/reference/app-information/app-preview-specifications/
- Upload rules: https://developer.apple.com/help/app-store-connect/manage-app-information/upload-app-previews-and-screenshots

Verified against Apple's pages: June 2026.

## Screenshots

1–10 per device size per locale. Formats: .png / .jpg / .jpeg. Exact pixel sizes only — App Store Connect rejects anything else. Upload only the largest required size; Apple auto-scales down for smaller devices.

| Device class | Required? | Accepted sizes (portrait; landscape = swapped) |
|---|---|---|
| iPhone 6.9" (16/17 Pro Max, Air) | **Required** for iPhone apps (or 6.5") | 1320×2868, 1290×2796 |
| iPhone 6.5" (legacy alternative) | Alternative to 6.9" | 1242×2688, 1284×2778 |
| iPad 13" (Pro M4/M5, Air M2+) | **Required** if app runs on iPad | 2064×2752, 2048×2732 |
| Mac | **Required** for Mac apps | 1280×800, 1440×900, 2560×1600, 2880×1800 (16:10, landscape) |

Notes:
- iPhone 6.9" simulator screenshots come out at the right size natively (e.g. iPhone 17 Pro Max → 1320×2868). Mac screenshots almost never do — plan to compose/pad to a 16:10 size (2880×1800 recommended).
- Marketing-styled screenshots (device frame on a background with a caption) are allowed and standard practice — the composed image must still be exactly one of the accepted sizes.

## App Previews (videos)

Optional; up to 3 per device size per locale.

| Requirement | Value |
|---|---|
| Length | 15–30 seconds |
| Max file size | 500 MB |
| Frame rate | max 30 fps, progressive |
| Container | .mov / .m4v / .mp4 (H.264) or .mov (ProRes 422 HQ) |
| H.264 | up to High Profile Level 4.0, target 10–12 Mbps |
| Audio | Stereo AAC 256 kbps, 44.1/48 kHz (required and format-checked — add a silent track if there is no sound) |
| Poster frame | defaults to the 5-second mark — make sure second 5 looks great, or set it manually in App Store Connect |

**Accepted video resolutions** (note: these are NOT the device's native resolution — raw simulator recordings must be downscaled):

| Device class | Portrait | Landscape |
|---|---|---|
| iPhone (6.9" / 6.5" / 6.3" / 6.1") | 886×1920 | 1920×886 |
| iPad 13" / 11" | 1200×1600 | 1600×1200 |
| Mac | — (landscape only) | 1920×1080 |

A 6.9" preview is auto-scaled to all smaller iPhones if you provide only that one; same for iPad 13".

## App Preview content rules (App Review enforces these)

- Footage must be captured from the app itself, on-device/simulator. Screen recordings only.
- No device frames (bezels), no hands/fingers, no people, no lifestyle/B-roll footage.
- No pure marketing intro/outro cards. The video should open and close on real app UI.
- Text overlays on top of real footage are fine — keep them short, truthful, and localized per locale.
- Show only your app's UI; don't show other apps, notifications, or copyrighted content.
- Each localization can (and should) have its own preview with localized UI and overlays.

## Practical capture sources

| Target | Capture command/source | Native output | Needs conversion? |
|---|---|---|---|
| iPhone 6.9" screenshots | iPhone 17/16 Pro Max simulator, `simctl screenshot` or XCTest attachment | 1320×2868 | No |
| iPad 13" screenshots | iPad Pro 13" (M4) simulator | 2064×2752 | No |
| iPhone App Preview | `xcrun simctl io <udid> recordVideo` | 1320×2868 video | **Yes → 886×1920** |
| iPad App Preview | same | 2064×2752 video | **Yes → 1200×1600** |
| Mac screenshots | `screencapture -R` of the app window region | window size × scale | Usually — compose to 2880×1800 |
| Mac App Preview | `screencapture -v -R` of the window region | region size | **Yes → 1920×1080** |

`convert_preview.sh` performs the video conversions; `verify_assets.py` validates everything against the tables above.
