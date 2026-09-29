import CoreGraphics
import Foundation

// Prints "<windowID> <x> <y> <w> <h>" for the largest on-screen layer-0 window
// owned by the given PID. Used by capture.sh to grab the app window by id/region
// without needing Accessibility (System Events) permission.
//   usage: swift winframe.swift <pid>

let pid = Int(CommandLine.arguments.dropFirst().first ?? "") ?? -1
let opts = CGWindowListOption(arrayLiteral: .optionOnScreenOnly, .excludeDesktopElements)
guard let list = CGWindowListCopyWindowInfo(opts, kCGNullWindowID) as? [[String: Any]] else { exit(1) }

var best: (id: Int, x: Int, y: Int, w: Int, h: Int, area: Int)?
for win in list {
    guard let owner = win[kCGWindowOwnerPID as String] as? Int, owner == pid,
          let layer = win[kCGWindowLayer as String] as? Int, layer == 0,
          let id = win[kCGWindowNumber as String] as? Int,
          let b = win[kCGWindowBounds as String] as? [String: Any] else { continue }
    let x = Int(b["X"] as? Double ?? 0), y = Int(b["Y"] as? Double ?? 0)
    let w = Int(b["Width"] as? Double ?? 0), h = Int(b["Height"] as? Double ?? 0)
    let area = w * h
    if best == nil || area > best!.area { best = (id, x, y, w, h, area) }
}
guard let f = best else { exit(2) }
print("\(f.id) \(f.x) \(f.y) \(f.w) \(f.h)")
