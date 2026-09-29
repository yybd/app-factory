# macOS capture — permission-free, script-driven (recommended path)

The smoothest macOS flow (validated in production): **generate one tailored `capture.sh`
in the app's media folder and offer it to the user to run in their terminal.** It
auto-captures everything it can and prints exactly what to do for anything it can't.
**Stills need NO system permission; only the App Preview video needs Screen Recording.**

Offer it like: *"I've put a `capture.sh` in the media folder — run `./capture.sh` for the
screenshots (no permissions needed) and `./capture.sh video` for the App Preview. It
captures what it can and tells you what to do for the rest."*

## Why this beats driving the UI with clicks
- macOS apps are drag-drop / `NSOpenPanel` heavy → XCUITest/pixel-clicking is fragile.
- `screencapture` and System Events window control need TCC grants the controlling
  terminal usually lacks (and granting Screen Recording to that terminal may require
  quitting it — which kills a Claude session).
- Instead the **app renders its OWN window** to a PNG (always allowed), driven by
  launch-argument demo scenes. One launch captures every still scene.

## Mechanism 1 — stills via in-app self-render (zero permissions)
In `-CaptureMode -CaptureAll`, from a **single launch**, the app cycles each demo scene,
renders its own window to a 2× PNG, and writes it into the app's sandbox tmp; the script
flattens to RGB and moves it to `screenshots/`. A 1440×900 window → exactly 2880×1800.

```swift
// In capture mode the app sizes its own window (no Accessibility / System Events):
w.setContentSize(NSSize(width: 1440, height: 900))           // → 2880×1800 @2x
// Render the window to a 2× PNG and write to the sandbox tmp:
guard let rep = view.bitmapImageRepForCachingDisplay(in: view.bounds) else { return }
view.cacheDisplay(in: view.bounds, to: rep)
let data = rep.representation(using: .png, properties: [:])
try? data?.write(to: FileManager.default.temporaryDirectory.appendingPathComponent("\(name).png"))
// Cycle ALL scenes in ONE launch (apply scene → settle → snapshot), then NSApp.terminate.
```
The script then: `ffmpeg … format=rgb24` to drop alpha (App Store rejects alpha), and
moves the files from `~/Library/Containers/<bundle-id>/Data/tmp/` to `screenshots/`.

## Mechanism 2 — App Preview video via screencapture (needs Screen Recording)
The app self-drives a timed `-DemoScene video` while `screencapture -v -R <region>`
records. Get the window id/region from a tiny `CGWindowListCopyWindowInfo` helper keyed
by PID (no Accessibility). The script **probes Screen Recording first**; if missing, it
prints the exact grant steps instead of producing a black recording.

## The `capture.sh` contract (generate this; it's the deliverable the user runs)
- `./capture.sh` → the still screenshots (no permissions).
- `./capture.sh video` → the App Preview (needs Screen Recording; auto-converts to 1920×1080).
- `./capture.sh video-ai` (or similar) → a long staged recording for an interactive feature.
- `REBUILD=1 ./capture.sh …` → fresh build first.
It builds, copies the bundled demo art into the built `.app/Contents/Resources`, captures
stills permission-free, probes+records (or instructs) for video, then converts and runs
`verify_assets.py`, reporting what's upload-ready vs what needs a manual step.

## App-side hooks to add in Phase 2 (all gated by launch args — never affect normal use)
- Args: `-DemoMode` `-DemoScene <name>` `-CaptureMode` `-CaptureAll` `-VideoSize`.
- A `DemoScene` enum + per-scene seeding on the view model (load bundled demo art, set
  toggles/style, fill prompts, force-unlock Pro except the paywall scene).
- Window self-sizing in `-CaptureMode`: 1440×900 stills (16:10 → 2880×1800), 1600×900 for
  `-VideoSize`/video (16:9 → 1920×1080 with no letterbox).
- Bundle the demo art; the script copies it into Resources before launch (a sandboxed app
  can't read it from an external path).

## Hard-won gotchas — do not relearn these
1. **Never wrap the SwiftUI `body` in a `ZStack`** to add a capture overlay — it silently
   breaks window creation in demo mode (the app launches window-less). Use `.overlay { if cond { … } }`.
2. **One launch, all still scenes.** Per-scene relaunch + `NSApp.terminate` is flaky:
   window-creation races and state-restoration cascades produce window-less launches.
   Cycling scenes in one process is reliable; if you must relaunch, retry until the window
   actually appears and guard the `read` that consumes the window frame.
3. **Bash + non-ASCII is a landmine.** `echo "Building $APP…"` — a multibyte char (`…`, `—`)
   *directly after* `$VAR` gets folded into the variable name under a UTF-8 locale →
   `bash: APP…: unbound variable` (shown as `APP?`). Always brace (`${APP}`) and use ASCII
   (`...`) in shell code strings. It may not reproduce in a C-locale shell — it bites the user.
4. **Self-size + capture by window-id/region** avoids Accessibility entirely; only Screen
   Recording remains, and only for video.
5. **Trim dead tails; mind bleed.** A self-driving video over-runs the action — trim the
   static tail. Use **output-side** `-ss/-to` (input-side `-t` miscounts variable-fps screen
   recordings). Window-region recording can catch *another app* (e.g. the Terminal you
   launched from) bleeding over the window — tell the user to keep other windows off the
   capture region, and sample frames to confirm none crept in.
6. **Pin the intended IAP price** in the **IAP reviewer** paywall shot — StoreKit may fetch
   the real (often stale) App Store Connect price; force the intended one, and note that the
   live ASC product still needs updating. This applies **only** to the reviewer screenshot:
   a price never goes into a listing screenshot, App Preview or caption (see the hard rules
   in `SKILL.md`), so there is no "marketing shot" of a paywall to pin a price into.

## Interactive features (Image Playground, share/photo pickers) — staged manual capture
A self-driving demo can OPEN a system sheet but can't complete it. So:
- Add a scene that **stages** the app (feature ready, Pro on, prompt filled) in a 16:9
  window; the script records a LONG window clip (~50s) while the **user** performs the real
  action. The system sheet renders **within the window region**, so window-region recording
  captures it.
- Afterward, cut the relevant ~6–8s and splice it into the preview, or make a standalone
  ≥15s **second App Preview** (Apple allows up to 3 per locale).
- **PRIVACY — always check.** Image Playground's first ("Person") suggestion shows the
  user's own photo + name; share sheets show contacts; pickers show real files. Blur such
  regions before use:
  ```bash
  ffmpeg -i in.mp4 -filter_complex \
    "[0:v]crop=W:H:X:Y,boxblur=24:2[b];[0:v][b]overlay=X:Y:enable='lte(t,7)'[v]" \
    -map "[v]" -map 0:a -c:v libx264 -profile:v high -level 4.0 -pix_fmt yuv420p -r 30 \
    -b:v 11000k -c:a copy out.mp4
  ```
  Sample frames across the blurred range to confirm full coverage and no leftover smudge.
