# Screenshots — iOS automation vs macOS manual

The two platforms differ fundamentally here, which is why the skill asks "text
only or text + screenshots" and branches on platform.

## iOS — automatable with `fastlane snapshot`

`snapshot` drives a UI test that navigates the app and captures screenshots
across the device sizes and locales you list, fully automated and repeatable.

Setup (guide the user; ask before adding test code):
1. `fastlane snapshot init` — creates `SnapshotHelper.swift` and a `Snapfile`.
2. Add `SnapshotHelper.swift` to a **UI Testing** target; call `setupSnapshot`
   in the test's `setUp`, then `snapshot("01MainScreen")` at each screen.
3. In `Snapfile`, list `devices` and `languages` (use the same locale codes as
   the metadata).
4. Run `fastlane snapshot`. Optionally `frameit` to wrap shots in device frames
   with a title.
5. `deliver` picks up `fastlane/screenshots/<locale>/...` on upload.

Required iOS screenshot sizes are driven by display, not by you choosing pixels:
provide at least the **6.9" / 6.7" iPhone** and (if universal) the **13" iPad**
sizes; App Store Connect scales some others. Verify the current required set in
App Store Connect, since Apple updates device requirements with new hardware.

## macOS — NO snapshot automation; capture manually

There is no `fastlane snapshot` equivalent for Mac apps. Screenshots are taken
by hand and must be delivered at exact pixel dimensions.

Accepted Mac App Store screenshot sizes (pixels), pick one set and be consistent:
- **1280 × 800**
- **1440 × 900**
- **2560 × 1600**
- **2880 × 1800**

Guide the user to:
1. Run the app, arrange the window/feature to showcase.
2. Capture (⌘⇧4 then Space for a window, or ⌘⇧5). Note: a window grab includes
   shadow and won't be an exact size.
3. Conform each image to one accepted size WITHOUT distortion — hand off to the
   **`apple-app-store-screenshots`** skill, which resizes/pads/crops to the
   exact App Store dimensions and handles aspect-ratio mismatches properly.
4. Place the results in `fastlane/screenshots/<app>/<locale>/` and let `deliver`
   upload them.

Because macOS screenshots are manual, if the user wants screenshots for many
locales, flag the effort — each locale needs its own localized captures.

## Tips for both
- Screenshots must reflect the actual app (Guideline 2.3.3) — no fabricated UI.
- Keep the first 1–2 screenshots strong; they show in search results.
- App preview videos are optional and uploaded the same way (per locale).
