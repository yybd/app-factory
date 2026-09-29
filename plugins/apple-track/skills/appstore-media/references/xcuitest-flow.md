# Writing the demo flow (XCUITest)

One test class per app drives everything: screenshots, App Preview footage, and marketing-video raw footage. The flow must be **deterministic** (same result every run), **locale-independent** (works in he and en-US without changes), and **watchable** (paced like a human, because the same run is recorded as video).

## Target setup

If the project has no UI testing target: Xcode → File → New → Target → UI Testing Bundle, name it `<App>UITests`. Make sure the scheme's Test action includes it (`xcodebuild -list` to confirm the scheme).

## The flow skeleton

```swift
import XCTest

final class DemoFlowTests: XCTestCase {

    var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments += ["-DemoMode", "-CaptureMode"]
        // Locale comes from xcodebuild -testLanguage / -testRegion — do NOT hardcode it here.
        setupSnapshot(app)   // only if fastlane snapshot is used; otherwise delete
        app.launch()
    }

    func testDemoFlow() throws {
        // Beat 1 — hero screen (the strongest feature, agreed in Phase 0)
        humanPause(2.0)
        shoot("01_Hero")

        // Beat 2 — core action
        app.buttons["newDocumentButton"].tap()
        humanPause(0.8)
        let editor = app.textViews["mainEditor"]
        editor.tap()
        typeLikeAHuman(editor, demoText)
        shoot("02_Editor")

        // Beat 3, 4, ... one beat per agreed screen
    }
}
```

## Helpers — include these in the test target

```swift
extension XCTestCase {
    /// Pause so the recording breathes; no-op cost for screenshots.
    func humanPause(_ seconds: Double) { Thread.sleep(forTimeInterval: seconds) }
}

extension DemoFlowTests {
    /// Types character-by-character so video looks human, not pasted.
    func typeLikeAHuman(_ element: XCUIElement, _ text: String, delay: UInt32 = 60_000) {
        for ch in text { element.typeText(String(ch)); usleep(delay) }
    }

    /// Unified screenshot: fastlane snapshot if present, else XCTAttachment.
    func shoot(_ name: String) {
        #if canImport(SimulatorStatusMagic) // heuristic: fastlane snapshot setups
        snapshot(name)
        #else
        let shot = XCUIScreen.main.screenshot()
        let att = XCTAttachment(screenshot: shot)
        att.name = name
        att.lifetime = .keepAlways   // critical — otherwise attachments are deleted on pass
        add(att)
        #endif
    }
}
```

(If the project does use fastlane, just call `snapshot(name)` directly and drop the `#if`.)

## Rules that keep the flow professional

- **Wait for existence, not for luck**: before tapping, `XCTAssertTrue(element.waitForExistence(timeout: 5))`. Flaky flows produce half-finished videos.
- **Demo text must be real and localized.** Pull strings from a small `DemoContent` struct keyed by `Locale.current.language` so Hebrew runs type Hebrew. Never type Lorem Ipsum or English text in a Hebrew capture.
- **Hebrew/RTL**: verify the flow visually once in `he` — element positions mirror under RTL, but identifier-based queries are unaffected. Coordinate-based gestures (swipes) may need mirroring; prefer element APIs over coordinates.
- **Pacing budget for a 15–30s preview**: ~2s hero, then 4–6s per beat, 3–5 beats total. Time a dry run; if the test takes 45s, the video gets trimmed in iMovie anyway, so err slightly long (35–40s) and never short.
- **No alerts/popovers**: handle permission dialogs with `addUIInterruptionMonitor`, or better, avoid triggering them in `-CaptureMode`.

## macOS differences

The same skeleton works for Mac apps with these substitutions:

- `tap()` → `click()`, `app.buttons[...]` queries are identical.
- Fix the window size first so captures are consistent:

```swift
// In the app, under -CaptureMode:
if ProcessInfo.processInfo.arguments.contains("-CaptureMode") {
    window.setContentSize(NSSize(width: 1440, height: 900)) // 16:10 for screenshots
    // For App Preview footage use 1920×1080-proportioned content (16:9).
}
```

- Menu bar actions: `app.menuBarItems["File"].menuItems["New"].click()`.
- There is no status bar to clean, but hide the Dock/desktop clutter — `capture_mac.sh` captures only the window region, which solves most of it.
- **Segmented `Picker` → radio buttons.** A SwiftUI `.pickerStyle(.segmented)` exposes its segments as `radioButtons` on macOS, not `buttons`. Query `app.radioButtons["Text"]` (fall back to `app.buttons[...]`).
- **System Events can't drive SwiftUI.** AppleScript/`System Events` often sees an *empty* accessibility tree for SwiftUI apps, so don't drive the flow that way — XCUITest's element API works where System Events doesn't.
- **Off-screen rows aren't hittable.** List rows below the fold report a zero-size frame and fail `click()` with "not hittable". Set `continueAfterFailure = true` and guard each optional tap with `element.waitForExistence(...)` + `element.isHittable`; prefer on-screen targets (or scroll first).
- **Bundle the demo asset (sandbox + isolated HOME).** A sandboxed app launched by XCUITest gets an isolated HOME, so reading demo files from `~/...` fails (you get a placeholder). Load from `Bundle.main` and have the capture script copy the asset into the built `.app/Contents/Resources` before the run.

### Recording the App Preview while the flow drives (macOS)
- Run `capture_mac.sh -m video` (it has Screen Recording) and the XCUITest concurrently; the test launches/positions the app, the screencapture records the window region. The agent's own process usually lacks Screen Recording (TCC) — the recording runs in the **user's** terminal.
- **Trim the tail.** When the flow ends, app teardown / a window resize can leak into the last 1–2 seconds of the recording. End the last beat on real UI and **trim ~2s before the flow ends** when encoding (e.g. `ffmpeg -t 28` on a ~30s take) so the preview closes cleanly on app content, not a resizing window.

## Running per locale

Never bake the language into the test. The capture script passes it:

```bash
xcodebuild test -scheme MyApp \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max' \
  -only-testing:MyAppUITests/DemoFlowTests \
  -testLanguage he -testRegion he_IL \
  -resultBundlePath out/he.xcresult
```

`-testLanguage`/`-testRegion` set the app's locale for the run; combined with locale-aware `DemoContent`, one flow covers every market.

## fastlane (recommended when stills are the priority)

If the user wants the full screenshot matrix with minimal scripting, set up `fastlane snapshot`:

```ruby
# Snapfile
devices(["iPhone 17 Pro Max", "iPad Pro 13-inch (M4)"])
languages(["en-US", "<the app's other locales>"])
scheme("MyApp")
output_directory("./AppStoreMedia/MyApp/fastlane")
clear_previous_screenshots(true)
override_status_bar(true)
```

Then `fastlane frameit` (or AppScreens) for marketing framing. Video still goes through `capture_ios.sh` — fastlane doesn't record video.
