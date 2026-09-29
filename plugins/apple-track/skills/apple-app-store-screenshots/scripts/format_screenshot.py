#!/usr/bin/env python3
"""
Format an arbitrary image into one of Apple's App Store screenshot sizes.

Produces a flat (no-alpha) RGB PNG at exactly the requested width and height,
choosing how to fit the source content according to --fit. Verifies the output
matches the requested dimensions before exiting.

Usage:
    python3 format_screenshot.py \\
        --input  PATH \\
        --width  W \\
        --height H \\
        --fit    {pad-white,pad-black,pad-color,blur,stretch,crop} \\
        [--bg-color "#RRGGBB"] \\
        --output PATH
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError:
    sys.stderr.write(
        "Pillow is required. Install with:  pip install --break-system-packages Pillow\n"
    )
    sys.exit(2)


def parse_hex_color(s: str) -> tuple[int, int, int]:
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"invalid hex color: {s!r}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def fit_pad(src: Image.Image, w: int, h: int, bg: tuple[int, int, int]) -> Image.Image:
    """Letterbox the source onto a solid-color canvas, preserving aspect ratio."""
    sw, sh = src.size
    scale = min(w / sw, h / sh)
    nw, nh = max(1, round(sw * scale)), max(1, round(sh * scale))
    resized = src.resize((nw, nh), Image.LANCZOS)

    canvas = Image.new("RGB", (w, h), bg)
    offset = ((w - nw) // 2, (h - nh) // 2)
    if resized.mode == "RGBA":
        canvas.paste(resized, offset, mask=resized.split()[-1])
    else:
        canvas.paste(resized.convert("RGB"), offset)
    return canvas


def fit_blur(src: Image.Image, w: int, h: int) -> Image.Image:
    """Letterbox the source onto a blurred, cover-cropped copy of itself."""
    sw, sh = src.size

    # Background: cover the whole canvas, then blur.
    cover_scale = max(w / sw, h / sh)
    bw, bh = max(1, round(sw * cover_scale)), max(1, round(sh * cover_scale))
    bg = src.convert("RGB").resize((bw, bh), Image.LANCZOS)
    bg = bg.crop(((bw - w) // 2, (bh - h) // 2, (bw - w) // 2 + w, (bh - h) // 2 + h))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=max(w, h) // 40))

    # Foreground: fit inside.
    fit_scale = min(w / sw, h / sh)
    fw, fh = max(1, round(sw * fit_scale)), max(1, round(sh * fit_scale))
    fg = src.resize((fw, fh), Image.LANCZOS)
    offset = ((w - fw) // 2, (h - fh) // 2)
    if fg.mode == "RGBA":
        bg.paste(fg, offset, mask=fg.split()[-1])
    else:
        bg.paste(fg.convert("RGB"), offset)
    return bg


def fit_stretch(src: Image.Image, w: int, h: int) -> Image.Image:
    return src.convert("RGB").resize((w, h), Image.LANCZOS)


def fit_crop(src: Image.Image, w: int, h: int) -> Image.Image:
    """Cover the canvas by scaling up and center-cropping."""
    sw, sh = src.size
    scale = max(w / sw, h / sh)
    nw, nh = max(1, round(sw * scale)), max(1, round(sh * scale))
    resized = src.convert("RGB").resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return resized.crop((left, top, left + w, top + h))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--width", required=True, type=int)
    p.add_argument("--height", required=True, type=int)
    p.add_argument(
        "--fit",
        required=True,
        choices=["pad-white", "pad-black", "pad-color", "blur", "stretch", "crop"],
    )
    p.add_argument("--bg-color", default=None, help='Hex color like "#RRGGBB". Required when --fit pad-color.')
    args = p.parse_args()

    if not args.input.exists():
        sys.stderr.write(f"Input file does not exist: {args.input}\n")
        return 1
    if args.width <= 0 or args.height <= 0:
        sys.stderr.write("Width and height must be positive integers.\n")
        return 1

    src = Image.open(args.input)
    # Normalize to RGBA so we keep alpha around for the fit step.
    if src.mode not in ("RGB", "RGBA"):
        src = src.convert("RGBA")

    w, h = args.width, args.height
    fit = args.fit

    if fit == "pad-white":
        out = fit_pad(src, w, h, (255, 255, 255))
    elif fit == "pad-black":
        out = fit_pad(src, w, h, (0, 0, 0))
    elif fit == "pad-color":
        if not args.bg_color:
            sys.stderr.write("--bg-color is required when --fit pad-color\n")
            return 1
        out = fit_pad(src, w, h, parse_hex_color(args.bg_color))
    elif fit == "blur":
        out = fit_blur(src, w, h)
    elif fit == "stretch":
        out = fit_stretch(src, w, h)
    elif fit == "crop":
        out = fit_crop(src, w, h)
    else:
        sys.stderr.write(f"unknown fit mode: {fit}\n")
        return 1

    # Final flatten to RGB just in case (Apple rejects alpha).
    if out.mode != "RGB":
        out = out.convert("RGB")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output, "PNG", optimize=True)

    # Verify the result on disk matches what Apple will accept.
    verify = Image.open(args.output)
    if verify.size != (w, h):
        sys.stderr.write(
            f"Output size mismatch: wrote {verify.size}, expected {(w, h)}\n"
        )
        return 1
    if verify.mode != "RGB":
        sys.stderr.write(f"Output mode is {verify.mode}, expected RGB\n")
        return 1

    print(f"OK  {verify.size[0]}x{verify.size[1]}  {verify.mode}  {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
