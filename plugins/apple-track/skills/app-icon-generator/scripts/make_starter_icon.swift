#!/usr/bin/env swift
//
// make_starter_icon.swift — render a 1024x1024 OPAQUE starter app icon
// (diagonal gradient + a centered letter/glyph) as PNG, using AppKit.
//
// This is a PLACEHOLDER to unblock development — refine with real artwork later.
//
// Usage:
//   swift make_starter_icon.swift --out icon.png --text "W" \
//       --bg1 "#2E6BD6" --bg2 "#1B3F87" --fg "#FFFFFF"
//
// Notes: macOS only (needs AppKit). Output is opaque (valid for iOS/App Store).

import AppKit
import Foundation

func arg(_ name: String, _ def: String) -> String {
    let a = CommandLine.arguments
    if let i = a.firstIndex(of: name), i + 1 < a.count { return a[i + 1] }
    return def
}

func color(_ hex: String) -> NSColor {
    var s = hex.trimmingCharacters(in: .whitespaces)
    if s.hasPrefix("#") { s.removeFirst() }
    guard s.count == 6, let v = Int(s, radix: 16) else { return .gray }
    return NSColor(srgbRed: CGFloat((v >> 16) & 0xff) / 255.0,
                   green: CGFloat((v >> 8) & 0xff) / 255.0,
                   blue: CGFloat(v & 0xff) / 255.0, alpha: 1.0)
}

let outPath = arg("--out", "appicon-source.png")
let text = arg("--text", "A")
let bg1 = color(arg("--bg1", "#2E6BD6"))
let bg2 = color(arg("--bg2", "#1B3F87"))
let fg = color(arg("--fg", "#FFFFFF"))

let size = 1024
let rect = NSRect(x: 0, y: 0, width: size, height: size)

// Draw straight into an exact-size, OPAQUE bitmap (no alpha channel, and not
// affected by the display's backing scale the way NSImage.lockFocus would be).
guard let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: size, pixelsHigh: size,
        bitsPerSample: 8, samplesPerPixel: 3,   // 3 = RGB, no alpha
        hasAlpha: false, isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0, bitsPerPixel: 0) else {
    FileHandle.standardError.write("failed to create bitmap\n".data(using: .utf8)!)
    exit(1)
}

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)

// Opaque diagonal gradient background (full bleed; system masks corners on iOS).
if let gradient = NSGradient(starting: bg1, ending: bg2) {
    gradient.draw(in: NSBezierPath(rect: rect), angle: -45)
} else {
    bg1.setFill(); rect.fill()
}

// Centered glyph.
let fontSize = CGFloat(size) * 0.52
let style = NSMutableParagraphStyle()
style.alignment = .center
let attrs: [NSAttributedString.Key: Any] = [
    .font: NSFont.systemFont(ofSize: fontSize, weight: .bold),
    .foregroundColor: fg,
    .paragraphStyle: style,
]
let str = NSAttributedString(string: text, attributes: attrs)
let textSize = str.size()
let textRect = NSRect(x: 0,
                      y: (CGFloat(size) - textSize.height) / 2.0,
                      width: CGFloat(size),
                      height: textSize.height)
str.draw(in: textRect)

NSGraphicsContext.restoreGraphicsState()

// Encode opaque PNG.
guard let png = rep.representation(using: .png, properties: [:]) else {
    FileHandle.standardError.write("failed to render PNG\n".data(using: .utf8)!)
    exit(1)
}
do {
    try png.write(to: URL(fileURLWithPath: outPath))
    print("✅ wrote \(size)x\(size) starter icon: \(outPath)")
    print("   (placeholder — replace with real artwork before release)")
} catch {
    FileHandle.standardError.write("write failed: \(error)\n".data(using: .utf8)!)
    exit(1)
}
