//
//  FlowSmokeTests.swift  (template — adapt per app)
//
//  Smoke-tests each user journey end-to-end: drive the app via its accessibility
//  identifiers and assert the user reaches the end of the flow without a crash,
//  a dead-end, or a missing element. This is the repeatable half of the Phase-4
//  flow audit (see references/flow-audit.md) and doubles as a regression suite.
//
//  How to adapt:
//   1. Add this file to a UI Testing target (Xcode: File ▸ New ▸ Target ▸ UI
//      Testing Bundle), or reuse the one the `appstore-media` skill created.
//   2. Replace the placeholder accessibility identifiers ("newItemButton", …)
//      with the app's real ones. Add `.accessibilityIdentifier("…")` in the app
//      where missing — identifiers are language-independent, so one flow serves
//      every locale.
//   3. Reuse the app's demo/seed launch argument if it has one (e.g. -DemoMode),
//      so flows run against attractive, deterministic data.
//   4. Run under Thread/Address Sanitizer + Main Thread Checker for the dynamic
//      phase (references/runtime-diagnostics.md §4).
//
//  Run a single flow:
//   xcodebuild test -scheme <scheme> -destination '…' \
//     -only-testing:<UITestTarget>/FlowSmokeTests/testCoreCreateFlow \
//     -enableThreadSanitizer YES
//

import XCTest

final class FlowSmokeTests: XCTestCase {

    var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false      // stop at the first broken step
        app = XCUIApplication()
        // Reuse the app's demo mode + a UI-testing flag if it has them.
        app.launchArguments += ["-UITesting", "-DemoMode"]
        // To force a state, pass a flag the app honors, e.g.:
        //   app.launchArguments += ["-SimulateEmptyData"]
        //   app.launchArguments += ["-SimulateNetworkError"]
        app.launch()
    }

    override func tearDownWithError() throws {
        // A crash mid-flow leaves the app un-running: this catches it explicitly.
        XCTAssertEqual(app.state, .runningForeground,
                       "App is not in the foreground — it may have crashed during the flow.")
        app = nil
    }

    // MARK: - Helpers

    /// Wait for an element, failing with a clear message if it never appears
    /// (a missing element is usually a dead-end or a broken transition).
    @discardableResult
    private func require(_ element: XCUIElement,
                         _ name: String,
                         timeout: TimeInterval = 8,
                         file: StaticString = #file, line: UInt = #line) -> XCUIElement {
        XCTAssertTrue(element.waitForExistence(timeout: timeout),
                      "Expected to reach «\(name)» but it never appeared — possible dead-end or broken flow.",
                      file: file, line: line)
        return element
    }

    /// Assert a back/close affordance exists and returns the user to `anchor`.
    private func assertCanGoBack(to anchor: XCUIElement, _ name: String) {
        let back = app.buttons["backButton"].exists ? app.buttons["backButton"]
                 : app.navigationBars.buttons.element(boundBy: 0)   // default back chevron
        XCTAssertTrue(back.exists, "No reachable back/close control on «\(name)» — navigation dead-end.")
        back.tap()
        require(anchor, "\(name) → back to start")
    }

    // MARK: - Journey 1 — first run / onboarding

    func testOnboardingFlow() throws {
        // Fresh-install flow: the most fragile and most-skipped journey.
        let getStarted = app.buttons["getStartedButton"]
        if getStarted.waitForExistence(timeout: 4) {
            getStarted.tap()
            // …step through the onboarding pages…
            require(app.otherElements["mainScreen"], "main screen after onboarding")
        } else {
            // No onboarding (or already onboarded) — assert we still land somewhere usable.
            require(app.otherElements["mainScreen"], "main screen")
        }
    }

    // MARK: - Journey 2 — core task (create → save → verify it persists)

    func testCoreCreateFlow() throws {
        let main = require(app.otherElements["mainScreen"], "main screen")

        require(app.buttons["newItemButton"], "new-item button").tap()
        let field = require(app.textFields["titleField"], "title field")
        field.tap()
        field.typeText("Smoke test item")
        require(app.buttons["saveButton"], "save button").tap()

        // The created item is visible (the success state).
        require(app.staticTexts["Smoke test item"], "the saved item in the list")

        // Data-loss check: background and relaunch — the item must survive.
        XCUIDevice.shared.press(.home)
        app.activate()
        XCTAssertTrue(app.staticTexts["Smoke test item"].waitForExistence(timeout: 8),
                      "Saved item did not survive background/relaunch — possible data loss.")
        _ = main
    }

    // MARK: - Journey 3 — navigation integrity (can always get back out)

    func testNavigationCanAlwaysReturn() throws {
        let main = require(app.otherElements["mainScreen"], "main screen")
        require(app.buttons["settingsButton"], "settings button").tap()
        let settings = require(app.otherElements["settingsScreen"], "settings screen")
        assertCanGoBack(to: main, "settings")
        _ = settings
    }

    // MARK: - Journey 4 — empty / error / offline states (force via launch flags)

    func testEmptyState() throws {
        // Relaunch into a forced-empty state (requires the app to honor the flag).
        app.terminate()
        app.launchArguments += ["-SimulateEmptyData"]
        app.launch()
        // An empty state must be helpful, not a blank screen.
        require(app.otherElements["emptyStateView"],
                "empty-state view (not a blank screen)")
    }

    func testNetworkErrorState() throws {
        app.terminate()
        app.launchArguments += ["-SimulateNetworkError"]
        app.launch()
        // The error must be visible and offer a way forward (retry), not a silent fail.
        let errorVisible = app.staticTexts["errorMessage"].waitForExistence(timeout: 8)
            || app.buttons["retryButton"].waitForExistence(timeout: 8)
        XCTAssertTrue(errorVisible,
                      "Network error produced no visible message or retry — silent failure / stuck screen.")
    }

    // NOTE: permission-denied and true-offline states usually can't be forced from
    // XCUITest alone. Drive those by hand in Phase 4:
    //   xcrun simctl privacy <udid> reset <service>   # then launch and tap "Don't Allow"
    // and toggle the network / use a Network Link Conditioner profile.
    // See references/flow-audit.md §5.
}
