#!/usr/bin/env python3
"""frameshot.py — turn a raw simulator capture into a framed, captioned App Store screenshot.

Part of the appstore-media skill. This is the framing step: it is what produces the
store-ready image, so the look stays identical across shots, locales and releases
instead of drifting each time someone reframes by hand.

  frameshot.py --preset iphone69 --in raw.png --caption "Your saved replies" --out 01.png
  frameshot.py --preset iphone69 --in raw.png --caption "טקסט בעברית" --rtl   # any RTL string; --rtl sets the direction --out 01_he.png
  frameshot.py --manifest shots.json
  frameshot.py --preset universal16x9 --in raw/hero.png --caption "Notes that stay yours" --out creative/universal.png

Output is exact-size PNG with no alpha channel, which is what App Store Connect requires.

Hebrew and Arabic need --rtl. Pillow does the bidi reordering through RAQM; check it is
present with `python3 -c "from PIL import features; print(features.check('raqm'))"`.
Without RAQM the text renders in logical order, i.e. backwards, so the script refuses.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, features
except ImportError:
    if not {"-h", "--help"} & set(sys.argv[1:]):  # the usage needs no Pillow
        sys.exit("✗ Pillow is not installed (with RAQM, for RTL captions):\n"
                 "    brew install libraqm && python3 -m pip install --upgrade pillow\n"
                 "  Check: python3 -c \"from PIL import features; print(features.check('raqm'))\"")

# Largest size per family is all App Store Connect needs — it scales down to the rest.
#
# The Duo pair are their own sets, not scaled from anything: one per display, and the
# store shows the one that matches the way the device is held. Their corner ratios are
# an estimate from the published screen sizes, not a measured bezel — check one framed
# shot in App Store Connect's preview before framing a whole set.
#
# The `banner` presets are the creative assets — the product page header and the search
# results tile. They are a different layout (caption beside the device, not above it)
# because they are landscape, and because the store crops them per device: the header
# is shown at different widths on iPhone and iPad, so everything that matters is kept
# inside a centred safe area (`--safe`) and the edges carry only background.
PRESETS = {
    "iphone69":  {"size": (1320, 2868), "corner": 0.092, "kind": "phone"},
    "iphone65":  {"size": (1284, 2778), "corner": 0.088, "kind": "phone"},
    "ipad13":    {"size": (2064, 2752), "corner": 0.036, "kind": "pad"},
    "duo_outer": {"size": (1398, 2034), "corner": 0.080, "kind": "phone"},
    "duo_inner": {"size": (2007, 2853), "corner": 0.050, "kind": "pad"},
    # creative assets — see apple-specs.json `creative_assets`
    "header21x9":    {"size": (3840, 1646), "kind": "banner"},
    "universal16x9": {"size": (5244, 2950), "kind": "banner"},
    "search3x2":     {"size": (3840, 2560), "kind": "banner"},
}

# The caption font. `--font` overrides both; these are the fallbacks.
#
# The RTL one is a SEPARATE setting and not a nicety: a system font that covers a
# script is not the same as one that covers a script AND the punctuation a caption uses.
# SFHebrew has no comma and no em-dash, so a caption with either renders .notdef boxes
# mid-sentence — and only someone who reads that language would ever notice. Arial Bold
# is the macOS face that covers both, which is why it is the fallback here rather than
# the system default.
FONT_LATIN = os.environ.get("FRAMESHOT_FONT") or "/System/Library/Fonts/SFNS.ttf"
FONT_RTL = (os.environ.get("FRAMESHOT_FONT_RTL")
            or "/System/Library/Fonts/Supplemental/Arial Bold.ttf")

DEFAULT_BG = "#0B1A2E"
DEFAULT_FG = "#FFFFFF"
BEZEL = "#F2F2F4"       # light bezel, as on the shipped set


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype(FONT_LATIN, size)


def _wrap(draw, text, font, max_width, rtl):
    """Greedy wrap. Measured with the same direction the caption is drawn with."""
    direction = "rtl" if rtl else "ltr"
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        width = draw.textlength(trial, font=font, direction=direction)
        if width <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _trim_bottom(im: Image.Image, keep_margin: float = 0.02) -> Image.Image:
    """Cut a uniform empty band off the bottom of a capture.

    A phone screen usually fills; an iPad one often does not, and the empty half then eats
    a third of the framed shot. `--bleed` cannot help there — on a wide device the width is
    the binding constraint, so enlarging the device changes nothing. Cropping the source does.
    """
    px = im.load()
    step = max(1, im.width // 300)
    # Sample the middle 80% only: the outer edges carry rounded corners and stray cursor
    # artifacts, which would make an otherwise empty row look like content.
    x0, x1 = int(im.width * 0.10), int(im.width * 0.90)
    tol = 12
    last = im.height - 1
    while last > im.height // 3:
        row = [px[x, last] for x in range(x0, x1, step)]
        r = [c[0] for c in row]; g = [c[1] for c in row]; b = [c[2] for c in row]
        flat = (max(r) - min(r) <= tol) and (max(g) - min(g) <= tol) and (max(b) - min(b) <= tol)
        if not flat:
            break
        last -= 1
    cut = min(im.height, last + int(im.height * keep_margin))
    return im.crop((0, 0, im.width, cut)) if cut < im.height else im


def _rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([(0, 0), (size[0] - 1, size[1] - 1)],
                                           radius=radius, fill=255)
    return mask



def _trim_border(im: Image.Image, tol: int = 10) -> Image.Image:
    """Drop a uniform margin around a window capture — macOS bakes the drop shadow into the
    file, and the frame draws its own. Returns the image unchanged when there is no margin."""
    bg = im.getpixel((0, 0))
    if not isinstance(bg, tuple):
        return im
    diff = Image.new("L", im.size, 0)
    px, dp = im.load(), diff.load()
    step = max(1, min(im.width, im.height) // 400)
    for y in range(0, im.height, step):
        for x in range(0, im.width, step):
            c = px[x, y]
            if abs(c[0]-bg[0]) + abs(c[1]-bg[1]) + abs(c[2]-bg[2]) > tol:
                dp[x, y] = 255
    box = diff.getbbox()
    return im.crop(box) if box and (box[2]-box[0]) > im.width * 0.3 else im


def _device_image(shot: Image.Image, target_w: int, pad: int, radius_ratio: float, bezel: str):
    """Scale a capture to `target_w` and wrap it in a rounded bezel. Returns (image, mask)."""
    scale = (target_w - 2 * pad) / shot.width
    sw, sh = int(shot.width * scale), int(shot.height * scale)
    shot = shot.resize((sw, sh), Image.LANCZOS)
    dev_w, dev_h = sw + 2 * pad, sh + 2 * pad
    radius = int(dev_w * radius_ratio)
    device = Image.new("RGB", (dev_w, dev_h), bezel)
    inner = _rounded_mask((sw, sh), max(radius - pad, 2))
    rounded = Image.new("RGB", (sw, sh), bezel)
    rounded.paste(shot, (0, 0), inner)
    device.paste(rounded, (pad, pad))
    return device, _rounded_mask((dev_w, dev_h), radius)


def composite(srcs, out: Path, preset: str, caption: str, rtl: bool,
              bg: str, fg: str, bezel: str, font_scale: float) -> None:
    """Two captures in one frame — the shot that says 'the same thing, on both devices'.

    The first source is the wide one (a Mac window) and sits behind; the second is the
    phone and overlaps its lower-right. One image carries the claim that two side-by-side
    screenshots only imply.
    """
    if len(srcs) != 2:
        sys.exit("error: --composite takes exactly two inputs, wide first then phone.")
    spec = PRESETS[preset]
    W, H = spec["size"]
    canvas = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(canvas)

    band = int(H * 0.19)
    side = int(W * 0.085)
    font_size = int(W * 0.072 * font_scale)
    font = _font(FONT_RTL if rtl else FONT_LATIN, font_size)
    lines = _wrap(draw, caption, font, W - 2 * side, rtl) if caption else []
    if len(lines) > 3:
        sys.exit(f"error: caption wraps to {len(lines)} lines; shorten it.")
    leading = int(font_size * 1.22)
    y = max(int(H * 0.055), (band - leading * len(lines)) // 2)
    for line in lines:
        draw.text((W // 2, y), line, font=font, fill=fg, anchor="ma",
                  direction="rtl" if rtl else "ltr")
        y += leading

    pad = int(W * 0.010)
    first = _trim_border(Image.open(srcs[0]).convert("RGB"))
    second = _trim_border(Image.open(srcs[1]).convert("RGB"))

    # The layout follows the first capture's shape. A landscape window sits behind with the
    # phone over its corner; a portrait window (a menu-bar app) reads better shoulder to
    # shoulder, because stacking two tall devices just hides one of them.
    landscape = first.width > first.height * 1.2
    if landscape:
        wide, wide_mask = _device_image(first, int(W * 0.92), pad, 0.022, bezel)
        phone, phone_mask = _device_image(second, int(W * 0.46), pad, 0.085, bezel)
        dx = wide.width - int(phone.width * 0.72)
        dy = wide.height - int(phone.height * 0.44)
    else:
        wide, wide_mask = _device_image(first, int(W * 0.58), pad, 0.030, bezel)
        phone, phone_mask = _device_image(second, int(W * 0.50), pad, 0.085, bezel)
        dx = wide.width - int(phone.width * 0.22)
        dy = int(phone.height * 0.13)

    block_w = max(wide.width, dx + phone.width)
    block_h = max(wide.height, dy + phone.height)
    wx = max((W - block_w) // 2, 0)
    wy = band + max((H - band - block_h) // 2, int(H * 0.01))

    canvas.paste(wide, (wx, wy), wide_mask)
    # Clamped so the phone never runs off the right edge — a clipped device reads as a mistake.
    px = min(wx + dx, W - phone.width - int(W * 0.02))
    py = wy + dy
    shadow = Image.new("RGB", (phone.width + 24, phone.height + 24), bg)
    canvas.paste(shadow, (px - 12, py - 12),
                 _rounded_mask(shadow.size, int(shadow.width * 0.09)))
    canvas.paste(phone, (px, py), phone_mask)

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG")
    print(f"{out}  {W}x{H}  composite  \"{caption}\"")


def banner(srcs, out: Path, preset: str, caption: str, rtl: bool,
           bg: str, fg: str, bezel: str, font_scale: float, safe: float = 0.62) -> None:
    """A creative asset: caption on the reading side, one or two devices on the other.

    Landscape, so the caption sits BESIDE the device rather than above it — the start
    side for the script (left for LTR, right for RTL), which is where the eye lands
    first. Everything that carries meaning is kept inside a centred box `safe` of the
    width and 80% of the height: Apple crops the header differently per device and asks
    for the focal point in the centre, and a caption clipped at the edge on one device
    is worse than a little empty background on all of them.
    """
    if rtl and not features.check("raqm"):
        sys.exit("error: --rtl needs Pillow built with RAQM, otherwise Hebrew renders reversed.")
    if not 1 <= len(srcs) <= 2:
        sys.exit("error: a banner takes one or two captures.")
    W, H = PRESETS[preset]["size"]
    canvas = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(canvas)

    sw_, sh_ = int(W * safe), int(H * 0.80)
    sx, sy = (W - sw_) // 2, (H - sh_) // 2
    text_w = int(sw_ * 0.46) if caption else 0
    gap = int(sw_ * 0.04) if caption else 0
    dev_box_w = sw_ - text_w - gap

    # Devices: phones side by side, the second slightly lower — two screens read as "more
    # of the app", which is the point of a header. Each is sized to the box height first.
    pad = int(H * 0.010)
    shots = [Image.open(x).convert("RGB") for x in srcs]
    n = len(shots)
    devs = []
    for shot in shots:
        target_h = sh_ if n == 1 else int(sh_ * 0.92)
        w_for_h = int((target_h - 2 * pad) * shot.width / shot.height) + 2 * pad
        w_cap = dev_box_w if n == 1 else int(dev_box_w * 0.52)
        corner = 0.085 if shot.height > shot.width * 1.3 else 0.03
        devs.append(_device_image(shot, min(w_for_h, w_cap), pad, corner, bezel))
    total_w = sum(d.width for d, _ in devs) + (int(dev_box_w * 0.04) if n == 2 else 0)
    dev_x0 = (sx + sw_ - total_w) if not rtl else sx      # devices on the far side
    x = dev_x0
    for i, (d, m) in enumerate(devs):
        y = sy + (sh_ - d.height) // 2 + (int(sh_ * 0.06) if i == 1 else 0)
        canvas.paste(d, (x, y), m)
        x += d.width + int(dev_box_w * 0.04)

    if caption:
        # Fit to two lines by shrinking, not by wrapping further: a banner is read at a
        # glance, and a third line is where one orphaned word ends up on its own. The
        # floor is 60% of the starting size — below that the phrase is too long, and
        # saying so beats a caption nobody can read on a phone.
        start = int(H * 0.085 * font_scale)
        font_size = start
        while True:
            font = _font(FONT_RTL if rtl else FONT_LATIN, font_size)
            lines = _wrap(draw, caption, font, text_w, rtl)
            if len(lines) <= 2 or font_size <= start * 0.6:
                break
            font_size = int(font_size * 0.92)
        if len(lines) > 2:
            sys.exit(f"error: caption needs {len(lines)} lines even at 60% size; a header "
                     f"carries one short phrase — shorten it.")
        leading = int(font_size * 1.22)
        ty = sy + (sh_ - leading * len(lines)) // 2
        # anchored on the start edge of the text column, in the script's direction
        tx, anchor = ((sx + sw_, "ra") if rtl else (sx, "la"))
        for line in lines:
            draw.text((tx, ty), line, font=font, fill=fg, anchor=anchor,
                      direction="rtl" if rtl else "ltr")
            ty += leading

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG")                     # RGB — creative assets may not be transparent
    print(f"{out}  {W}x{H}  banner  {'rtl' if rtl else 'ltr'}  \"{caption}\"")


def frame(src: Path, out: Path, preset: str, caption: str, rtl: bool,
          bg: str, fg: str, bezel: str, font_scale: float, bleed: float = 0.0,
          trim_bottom: bool = False) -> None:
    if rtl and not features.check("raqm"):
        sys.exit("error: --rtl needs Pillow built with RAQM, otherwise Hebrew renders reversed.")
    if preset not in PRESETS:
        sys.exit(f"error: unknown preset {preset!r}; choose from {', '.join(PRESETS)}")

    spec = PRESETS[preset]
    W, H = spec["size"]
    canvas = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(canvas)

    # Caption sits in the top band; the device gets everything below it.
    band = int(H * 0.19)
    side = int(W * 0.085)
    font_size = int(W * (0.072 if spec["kind"] == "phone" else 0.052) * font_scale)
    font = _font(FONT_RTL if rtl else FONT_LATIN, font_size)

    lines = _wrap(draw, caption, font, W - 2 * side, rtl) if caption else []
    if len(lines) > 3:
        sys.exit(f"error: caption wraps to {len(lines)} lines; shorten it or lower --font-scale.")

    leading = int(font_size * 1.22)
    block = leading * len(lines)
    y = max(int(H * 0.055), (band - block) // 2)
    for line in lines:
        draw.text((W // 2, y), line, font=font, fill=fg,
                  anchor="ma", direction="rtl" if rtl else "ltr")
        y += leading

    # Device: bezel rounded-rect with the capture inset, centred in the space that is left.
    avail_h = H - band - int(H * 0.03)
    avail_w = W - 2 * int(W * 0.075)
    shot = Image.open(src).convert("RGB")
    if trim_bottom:
        shot = _trim_bottom(shot)
    pad = int(W * 0.012)                       # bezel thickness

    # --bleed enlarges the device and lets its lower part run off the bottom edge. It is the
    # standard store look, and it reclaims the dead space a screen that does not fill leaves behind.
    avail_h = int(avail_h * (1.0 + bleed))
    scale = min((avail_w - 2 * pad) / shot.width, (avail_h - 2 * pad) / shot.height)
    sw, sh = int(shot.width * scale), int(shot.height * scale)
    shot = shot.resize((sw, sh), Image.LANCZOS)

    dev_w, dev_h = sw + 2 * pad, sh + 2 * pad
    radius = int(dev_w * spec["corner"])
    device = Image.new("RGB", (dev_w, dev_h), bezel)
    device.paste(shot, (pad, pad))

    inner = _rounded_mask((sw, sh), max(radius - pad, 2))
    rounded_shot = Image.new("RGB", (sw, sh), bezel)
    rounded_shot.paste(shot, (0, 0), inner)
    device.paste(rounded_shot, (pad, pad))

    dx = (W - dev_w) // 2
    dy = band + (avail_h - dev_h) // 2 if bleed == 0 else band + int(H * 0.015)
    canvas.paste(device, (dx, dy), _rounded_mask((dev_w, dev_h), radius))

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG")                     # RGB — no alpha, as the store requires
    print(f"{out}  {W}x{H}  {'rtl' if rtl else 'ltr'}  \"{caption}\"")


def main() -> None:
    ap = argparse.ArgumentParser(description="Frame a raw capture into an App Store screenshot.")
    ap.add_argument("--manifest", type=Path,
                    help="JSON list of shots; each entry takes the same keys as the flags below.")
    ap.add_argument("--in", dest="src", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--preset", default="iphone69", choices=list(PRESETS))
    ap.add_argument("--caption", default="")
    ap.add_argument("--rtl", action="store_true")
    ap.add_argument("--bg", default=DEFAULT_BG)
    ap.add_argument("--fg", default=DEFAULT_FG)
    ap.add_argument("--bezel", default=BEZEL)
    ap.add_argument("--font-scale", type=float, default=1.0)
    ap.add_argument("--composite", nargs=2, metavar=("WIDE", "PHONE"),
                    help="two captures in one frame — a Mac window behind, a phone overlapping it.")
    ap.add_argument("--trim-bottom", action="store_true",
                    help="cut a uniform empty band off the bottom of the capture before framing "
                         "— for a screen that does not fill, typically on iPad.")
    ap.add_argument("--safe", type=float, default=0.62,
                    help="banner presets only: the share of the width that carries caption and "
                         "devices; the rest is background the store may crop.")
    ap.add_argument("--bleed", type=float, default=0.0,
                    help="0.0 fits the whole device; 0.25 enlarges it by a quarter and runs the "
                         "bottom off the canvas — use it when the captured screen does not fill.")
    a = ap.parse_args()

    if a.manifest:
        shots = json.loads(a.manifest.read_text())
        for s in shots:
            pre = s.get("preset", a.preset)
            if PRESETS[pre]["kind"] == "banner":
                srcs = s["in"] if isinstance(s["in"], list) else [s["in"]]
                banner([Path(x) for x in srcs], Path(s["out"]), pre, s.get("caption", ""),
                       bool(s.get("rtl", False)), s.get("bg", a.bg), s.get("fg", a.fg),
                       s.get("bezel", a.bezel), float(s.get("font_scale", 1.0)),
                       float(s.get("safe", a.safe)))
                continue
            if isinstance(s["in"], list):
                composite([Path(x) for x in s["in"]], Path(s["out"]), s.get("preset", a.preset),
                          s.get("caption", ""), bool(s.get("rtl", False)),
                          s.get("bg", a.bg), s.get("fg", a.fg), s.get("bezel", a.bezel),
                          float(s.get("font_scale", 1.0)))
                continue
            frame(Path(s["in"]), Path(s["out"]), s.get("preset", a.preset),
                  s.get("caption", ""), bool(s.get("rtl", False)),
                  s.get("bg", a.bg), s.get("fg", a.fg), s.get("bezel", a.bezel),
                  float(s.get("font_scale", 1.0)), float(s.get("bleed", 0.0)),
                  bool(s.get("trim_bottom", False)))
        return

    if PRESETS[a.preset]["kind"] == "banner":
        srcs = a.composite or ([a.src] if a.src else [])
        if not srcs or not a.out:
            ap.error("a banner preset needs --in (or --composite A B) and --out")
        banner([Path(x) for x in srcs], a.out, a.preset, a.caption, a.rtl,
               a.bg, a.fg, a.bezel, a.font_scale, a.safe)
        return

    if a.composite:
        if not a.out:
            ap.error("--out is required with --composite")
        composite([Path(x) for x in a.composite], a.out, a.preset, a.caption, a.rtl,
                  a.bg, a.fg, a.bezel, a.font_scale)
        return

    if not a.src or not a.out:
        ap.error("--in and --out are required without --manifest")
    frame(a.src, a.out, a.preset, a.caption, a.rtl, a.bg, a.fg, a.bezel, a.font_scale, a.bleed,
          a.trim_bottom)


if __name__ == "__main__":
    main()
