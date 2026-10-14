#!/bin/bash
# A small, otherwise-clean iOS app: settings in UserDefaults, a session timer on
# systemUptime, and no PrivacyInfo.xcprivacy. Info.plist carries what an upload needs, so
# the manifest is the finding that matters — not one item in a list of plist gaps.
set -euo pipefail
mkdir -p Timer.xcodeproj Timer
cat > Timer.xcodeproj/project.pbxproj <<'PBX'
// !$*UTF8*$!
{ archiveVersion = 1; objectVersion = 56; objects = {
  A1 /* Timer */ = { isa = PBXNativeTarget; name = Timer; productType = "com.apple.product-type.application"; };
  B1 = { isa = XCBuildConfiguration; buildSettings = { INFOPLIST_FILE = Timer/Info.plist; PRODUCT_BUNDLE_IDENTIFIER = com.example.focustimer; SDKROOT = iphoneos; IPHONEOS_DEPLOYMENT_TARGET = 17.0; TARGETED_DEVICE_FAMILY = 1; }; name = Release; };
}; rootObject = A1; }
PBX
cat > Timer/Info.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleDisplayName</key><string>Focus Timer</string>
  <key>CFBundleIdentifier</key><string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
  <key>CFBundleExecutable</key><string>$(EXECUTABLE_NAME)</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>UILaunchScreen</key><dict/>
  <key>ITSAppUsesNonExemptEncryption</key><false/>
</dict></plist>
PLIST
cat > Timer/FocusSession.swift <<'SWIFT'
import Foundation

/// One focus session. Elapsed time is measured on the monotonic clock so that a change
/// to the wall clock mid-session does not corrupt it.
final class FocusSession {
    private var startedAt: TimeInterval = 0

    func start() { startedAt = ProcessInfo.processInfo.systemUptime }

    var elapsed: TimeInterval { ProcessInfo.processInfo.systemUptime - startedAt }
}

/// The user's settings, kept on this device only.
enum Settings {
    static var sessionMinutes: Int {
        get { UserDefaults.standard.integer(forKey: "sessionMinutes") }
        set { UserDefaults.standard.set(newValue, forKey: "sessionMinutes") }
    }
}
SWIFT
cat > Timer/TimerView.swift <<'SWIFT'
import SwiftUI

struct TimerView: View {
    @State private var session = FocusSession()
    var body: some View {
        VStack {
            Text("Focus for \(Settings.sessionMinutes) minutes")
            Button("Start") { session.start() }
        }
    }
}
SWIFT
