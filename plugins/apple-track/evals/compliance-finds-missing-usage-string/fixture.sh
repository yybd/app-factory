#!/bin/bash
# A minimal iOS project: the camera is used, its usage string is missing. Nothing else
# is wrong on purpose, so a finding that names the key is a finding about this project.
set -euo pipefail
mkdir -p Scanner.xcodeproj Scanner
cat > Scanner.xcodeproj/project.pbxproj <<'PBX'
// !$*UTF8*$!
{ archiveVersion = 1; objectVersion = 56; objects = {
  A1 /* Scanner */ = { isa = PBXNativeTarget; name = Scanner; productType = "com.apple.product-type.application"; };
  B1 = { isa = XCBuildConfiguration; buildSettings = { INFOPLIST_FILE = Scanner/Info.plist; PRODUCT_BUNDLE_IDENTIFIER = com.example.scanner; }; name = Release; };
}; rootObject = A1; }
PBX
cat > Scanner/Info.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleDisplayName</key><string>Scanner</string>
  <key>CFBundleIdentifier</key><string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
</dict></plist>
PLIST
cat > Scanner/ScannerView.swift <<'SWIFT'
import SwiftUI
import AVFoundation

struct ScannerView: View {
    var body: some View { Text("Point at a code").onAppear(perform: start) }

    func start() {
        guard let camera = AVCaptureDevice.default(for: .video) else { return }
        let session = AVCaptureSession()
        if let input = try? AVCaptureDeviceInput(device: camera) { session.addInput(input) }
        session.startRunning()
    }
}
SWIFT
