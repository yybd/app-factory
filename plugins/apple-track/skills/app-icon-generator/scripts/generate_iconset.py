#!/usr/bin/env python3
"""
generate_iconset.py — build an Xcode AppIcon set from one source image.

Resizes a square source PNG (ideally 1024x1024) to every size Apple requires for
the chosen platform(s) using `sips` (built into macOS), writes the PNGs into the
target `.../<name>.appiconset/`, and writes a correct Contents.json.

Usage:
    generate_iconset.py --source ICON.png --xcassets PATH --name AppIcon --platform macos
    generate_iconset.py --source ICON.png --appiconset PATH/Foo.appiconset --platform all

--platform: ios | macos | all   (ios uses a single 1024 "single-size" icon)
--xcassets may be a .xcassets folder OR a project root (it will try to locate one).
--name is the AppIcon set name (read ASSETCATALOG_COMPILER_APPICON_NAME from the
  project if unsure; it is not always "AppIcon").
"""

import argparse
import glob
import json
import os
import subprocess
import sys

# macOS: (point_size, scale, pixels). Files are deduped by pixel size.
MAC_ENTRIES = [
    (16, "1x", 16), (16, "2x", 32),
    (32, "1x", 32), (32, "2x", 64),
    (128, "1x", 128), (128, "2x", 256),
    (256, "1x", 256), (256, "2x", 512),
    (512, "1x", 512), (512, "2x", 1024),
]


def sips_dims(path):
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                         capture_output=True, text=True)
    w = h = None
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith("pixelWidth:"):
            w = int(line.split(":")[1])
        elif line.startswith("pixelHeight:"):
            h = int(line.split(":")[1])
    return w, h


def sips_has_alpha(path):
    out = subprocess.run(["sips", "-g", "hasAlpha", path], capture_output=True, text=True)
    return "hasAlpha: yes" in out.stdout


def resize(src, px, dest):
    r = subprocess.run(["sips", "-z", str(px), str(px), src, "--out", dest],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"sips failed for {px}px: {r.stderr.strip()}")


def locate_xcassets(path):
    path = os.path.abspath(path)
    if path.endswith(".xcassets") and os.path.isdir(path):
        return [path]
    if path.endswith(".appiconset"):
        return [path]
    found = glob.glob(os.path.join(path, "**", "*.xcassets"), recursive=True)
    found = [f for f in found if "DerivedData" not in f]
    return found


def build_mac(appiconset, src):
    written = []
    pixels = sorted({px for _, _, px in MAC_ENTRIES})
    for px in pixels:
        dest = os.path.join(appiconset, f"icon_{px}.png")
        resize(src, px, dest)
        written.append(os.path.basename(dest))
    images = [{
        "filename": f"icon_{px}.png",
        "idiom": "mac",
        "scale": scale,
        "size": f"{pt}x{pt}",
    } for (pt, scale, px) in MAC_ENTRIES]
    return images, written


def build_ios_singlesize(appiconset, src):
    dest = os.path.join(appiconset, "icon_1024.png")
    resize(src, 1024, dest)
    images = [{
        "filename": "icon_1024.png",
        "idiom": "universal",
        "platform": "ios",
        "size": "1024x1024",
    }]
    return images, ["icon_1024.png"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--xcassets", help=".xcassets folder or project root")
    g.add_argument("--appiconset", help="direct path to a .appiconset folder")
    ap.add_argument("--name", default="AppIcon", help="AppIcon set name (default AppIcon)")
    ap.add_argument("--platform", choices=["ios", "macos", "all"], default="macos")
    args = ap.parse_args()

    src = os.path.abspath(args.source)
    if not os.path.isfile(src):
        print(f"❌ source not found: {src}"); sys.exit(1)

    warnings = []
    w, h = sips_dims(src)
    if w is None:
        print(f"❌ could not read image dimensions (is it a valid image?): {src}"); sys.exit(1)
    if w != h:
        warnings.append(f"source is {w}x{h}, NOT square — the icon will be distorted; crop to a square first")
    if min(w, h) < 1024:
        warnings.append(f"source is only {w}x{h}; 1024x1024+ recommended (upscaling looks soft)")
    if sips_has_alpha(src) and args.platform in ("ios", "all"):
        warnings.append("source has transparency; iOS / App Store icons must be opaque — flatten over a background first")

    # resolve appiconset path
    if args.appiconset:
        appiconset = os.path.abspath(args.appiconset)
    else:
        cats = locate_xcassets(args.xcassets)
        if not cats:
            print(f"❌ no .xcassets found under {args.xcassets}"); sys.exit(1)
        if len(cats) > 1 and not cats[0].endswith(".appiconset"):
            print("⚠️  multiple asset catalogs found — pass the specific one with --xcassets:")
            for c in cats:
                print(f"   {c}")
            sys.exit(1)
        base = cats[0]
        appiconset = base if base.endswith(".appiconset") else os.path.join(base, f"{args.name}.appiconset")
    os.makedirs(appiconset, exist_ok=True)

    images, written = [], []
    if args.platform in ("macos", "all"):
        im, wr = build_mac(appiconset, src); images += im; written += wr
    if args.platform in ("ios", "all"):
        im, wr = build_ios_singlesize(appiconset, src); images += im; written += wr

    contents = {"images": images, "info": {"author": "xcode", "version": 1}}
    with open(os.path.join(appiconset, "Contents.json"), "w") as f:
        json.dump(contents, f, indent=2)

    print(f"✅ wrote AppIcon set: {appiconset}")
    print(f"   platform: {args.platform}   source: {w}x{h}")
    print(f"   PNGs ({len(set(written))}): {', '.join(sorted(set(written)))}")
    print(f"   Contents.json: {len(images)} image entries")
    if warnings:
        print("\n⚠️  warnings:")
        for wmsg in warnings:
            print(f"   - {wmsg}")
    print("\nNext: in Xcode, set the target's App Icon to this set "
          f"(ASSETCATALOG_COMPILER_APPICON_NAME = {args.name}) and build.")


if __name__ == "__main__":
    main()
