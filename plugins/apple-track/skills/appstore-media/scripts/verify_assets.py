#!/usr/bin/env python3
"""verify_assets.py — validate App Store media against Apple's accepted specs.

Usage:
    python3 verify_assets.py <file-or-directory> [...]

Checks every .png/.jpg/.jpeg/.mp4/.mov/.m4v found (directories are walked).
Images:  exact accepted screenshot sizes.
Videos:  exact accepted App Preview resolutions, 15-30s duration, <=30fps,
         <=500MB, stereo audio track present.

Exits non-zero if anything fails, so it can gate a release script.
Specs source: developer.apple.com App Store Connect reference (verified 2026-06).
If Apple rejects an asset this script passed, re-check the live spec pages —
they change occasionally — and update `shared/apple-specs.json`, which this file and
the reference documents both read.
"""
import json
import os
import subprocess
import sys

# Apple's accepted dimensions come from ONE place — `shared/apple-specs.json` at the
# track root — because they used to be written out here AND in two reference documents
# AND in the sibling screenshot skill, and those had already drifted: 1290×2796 was
# filed under 6.7" in one table and 6.9" in another. Apple says 6.9", and the table this
# file used to carry was the one that was right, which is exactly why nobody looked.
_SHARED = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "..", "..", "shared"))
sys.path.insert(0, _SHARED)
from apple_specs import screenshot_sizes, preview_sizes       # noqa: E402

SCREENSHOT_SIZES = screenshot_sizes()
PREVIEW_SIZES = preview_sizes()

IMG_EXT = {".png", ".jpg", ".jpeg"}
VID_EXT = {".mp4", ".mov", ".m4v"}

failures = []


def report(path, ok, msg):
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {path}: {msg}")
    if not ok:
        failures.append(path)


def check_image(path):
    try:
        out = subprocess.check_output(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", "-g", "hasAlpha",
             "-g", "bitsPerSample", path], text=True)
        w = int([l for l in out.splitlines() if "pixelWidth" in l][0].split()[-1])
        h = int([l for l in out.splitlines() if "pixelHeight" in l][0].split()[-1])
        alpha_lines = [l for l in out.splitlines() if "hasAlpha" in l]
        has_alpha = bool(alpha_lines) and alpha_lines[0].split()[-1].lower() == "yes"
        bps_lines = [l for l in out.splitlines() if "bitsPerSample" in l]
        bits = int(bps_lines[0].split()[-1]) if bps_lines else None
    except Exception as e:
        report(path, False, f"could not read image: {e}")
        return
    label = SCREENSHOT_SIZES.get((w, h))
    if not label:
        near = min(SCREENSHOT_SIZES, key=lambda s: abs(s[0]-w) + abs(s[1]-h))
        report(path, False,
               f"{w}x{h} is NOT an accepted screenshot size "
               f"(closest accepted: {near[0]}x{near[1]} = {SCREENSHOT_SIZES[near]})")
    elif has_alpha:
        # App Store Connect rejects screenshots with an alpha channel.
        report(path, False,
               f"{w}x{h} ({label}) but has an ALPHA channel — App Store Connect "
               f"rejects screenshots with alpha. Flatten to RGB (no alpha) before upload.")
    elif bits and bits > 8:
        # App Store wants 8 bits/channel (24-bit RGB). 16-bit/48-bit PNGs — the
        # default output of ImageMagick Q16 builds — upload as COMPLETE via the API
        # but fail/look wrong at submission. Force 8-bit.
        report(path, False,
               f"{w}x{h} ({label}) but is {bits}-bit/channel — App Store wants 8-bit/channel "
               f"(24-bit RGB). Convert: magick in.png -depth 8 -define png:color-type=2 out.png")
    else:
        report(path, True, f"{w}x{h} — accepted ({label}), {bits or 8}-bit, no alpha")


def ffprobe(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", path], text=True)
    return json.loads(out)


def check_video(path):
    try:
        info = ffprobe(path)
    except FileNotFoundError:
        report(path, False, "ffprobe not found — brew install ffmpeg")
        return
    except Exception as e:
        report(path, False, f"could not probe: {e}")
        return

    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    problems = []

    if v is None:
        report(path, False, "no video stream")
        return
    w, h = int(v["width"]), int(v["height"])
    label = PREVIEW_SIZES.get((w, h))
    if not label:
        near = min(PREVIEW_SIZES, key=lambda s: abs(s[0]-w) + abs(s[1]-h))
        problems.append(f"{w}x{h} not an accepted preview resolution "
                        f"(closest: {near[0]}x{near[1]}) — run convert_preview.sh")

    dur = float(info["format"]["duration"])
    if not (15.0 <= dur <= 30.5):
        problems.append(f"duration {dur:.1f}s outside 15-30s")

    num, _, den = v.get("r_frame_rate", "30/1").partition("/")
    fps = float(num) / float(den or 1)
    if fps > 30.05:
        problems.append(f"frame rate {fps:.2f} > 30fps")

    size_mb = os.path.getsize(path) / 1_048_576
    if size_mb > 500:
        problems.append(f"file size {size_mb:.0f}MB > 500MB")

    if a is None:
        problems.append("no audio track (Apple requires stereo AAC — convert_preview.sh adds a silent one)")
    elif int(a.get("channels", 0)) != 2:
        problems.append(f"audio has {a.get('channels')} channel(s), needs stereo")

    if problems:
        report(path, False, "; ".join(problems))
    else:
        report(path, True,
               f"{w}x{h} ({label}), {dur:.1f}s, {fps:.0f}fps, {size_mb:.0f}MB, stereo audio")


def walk(target):
    if os.path.isfile(target):
        yield target
        return
    for root, dirs, files in os.walk(target):
        # raw captures are expected to be non-compliant — skip them
        if os.path.basename(root) == "raw":
            dirs[:] = []
            continue
        for f in files:
            yield os.path.join(root, f)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    checked = 0
    for target in sys.argv[1:]:
        if not os.path.exists(target):
            # "0 files checked" with exit 0 on a typo'd path is a green light for a
            # release script that gates on this — the docstring promises a gate.
            report(target, False, "no such file or directory")
            continue
        for path in walk(target):
            ext = os.path.splitext(path)[1].lower()
            if ext in IMG_EXT:
                check_image(path); checked += 1
            elif ext in VID_EXT:
                check_video(path); checked += 1
    print(f"\n{checked} file(s) checked, {len(failures)} failed.")
    if checked == 0:
        print("Nothing to check (note: 'raw/' directories are skipped by design).")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
