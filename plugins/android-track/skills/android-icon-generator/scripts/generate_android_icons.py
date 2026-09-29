#!/usr/bin/env python3
"""Build a complete Android launcher-icon set from one source image.

Android's icon is a stack, not a square: a 108dp background layer and a 108dp
foreground layer, of which the launcher shows only the inner 66dp and masks it to
its own shape. Anything the source draws near its edges is cropped, so the source
art is scaled to sit inside that safe zone rather than filling the canvas.

  generate_android_icons.py --source icon.png --res app/src/main/res --background "#fcfbf6"
  generate_android_icons.py --source icon.png --safe-zone-check
"""
import argparse, os, sys, xml.sax.saxutils as sx

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip3 install Pillow")

# density -> multiplier. Adaptive layers are 108dp, legacy launcher icons 48dp.
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
ADAPTIVE_DP, LEGACY_DP, SAFE_DP = 108, 48, 66
SAFE_RATIO = SAFE_DP / ADAPTIVE_DP          # 0.611 — the guaranteed-visible fraction

ADAPTIVE_XML = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="{bg}"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>{mono}
</adaptive-icon>
"""
MONO_LINE = '\n    <monochrome android:drawable="@mipmap/ic_launcher_monochrome"/>'
COLOR_XML = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">{color}</color>
</resources>
"""


def load(path):
    im = Image.open(path).convert("RGBA")
    if im.width != im.height:
        print(f"! source is {im.width}x{im.height}, not square — it will be letterboxed")
    if im.width < 512:
        print(f"! source is only {im.width}px; 1024 or more is wanted for xxxhdpi")
    return im


def opaque_bbox(im):
    """Bounding box of everything that is not fully transparent."""
    a = im.split()[-1]
    return a.getbbox()


def safe_zone_report(im):
    box = opaque_bbox(im)
    if not box:
        print("the source is fully transparent"); return
    w, h = im.size
    # the fraction of the canvas the art occupies, vs what survives masking
    art = max((box[2] - box[0]) / w, (box[3] - box[1]) / h)
    print(f"source {w}x{h}; art occupies {art:.0%} of the canvas, "
          f"safe zone keeps the middle {SAFE_RATIO:.0%}")
    if art > SAFE_RATIO + 0.02:
        print("! art reaches past the safe zone — it WILL be cropped by the launcher mask.\n"
              "  Scale the subject down, or move the edge-reaching part into the background layer.\n"
              "  This script scales it to fit; check that the result still reads.")
    else:
        print("art already fits inside the safe zone")


def scaled_into_safe_zone(im, canvas_px):
    """Fit the source's opaque art inside the safe circle of a canvas_px square."""
    out = Image.new("RGBA", (canvas_px, canvas_px), (0, 0, 0, 0))
    box = opaque_bbox(im) or (0, 0, im.width, im.height)
    art = im.crop(box)
    target = int(canvas_px * SAFE_RATIO)
    scale = min(target / art.width, target / art.height)
    art = art.resize((max(1, round(art.width * scale)), max(1, round(art.height * scale))),
                     Image.LANCZOS)
    out.paste(art, ((canvas_px - art.width) // 2, (canvas_px - art.height) // 2), art)
    return out


def circular(im):
    """Legacy round icon: mask the square to a circle."""
    from PIL import ImageDraw
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, im.width - 1, im.height - 1), fill=255)
    out = im.copy(); out.putalpha(mask)
    return out


def flatten(im, color):
    bg = Image.new("RGBA", im.size, color)
    return Image.alpha_composite(bg, im)


ROOT = ""            # paths are printed relative to --res, not to the cwd


def rel(path):
    return os.path.relpath(path, ROOT) if ROOT else path


def write(im, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, "PNG")
    print("  ", rel(path))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", required=True)
    p.add_argument("--res", help="…/app/src/main/res")
    p.add_argument("--background", default="#FFFFFF", help="colour for the background layer")
    p.add_argument("--background-image", help="use artwork instead of a flat colour")
    p.add_argument("--monochrome", action="store_true", help="also emit a themed-icon layer")
    p.add_argument("--play-icon", help="also write the 512x512 store icon here")
    p.add_argument("--safe-zone-check", action="store_true", help="report only, write nothing")
    a = p.parse_args()

    src = load(a.source)

    if a.safe_zone_check:
        safe_zone_report(src)
        return
    safe_zone_report(src)

    if a.play_icon:
        # the store icon is flat, square and must carry no alpha
        store = flatten(src.resize((512, 512), Image.LANCZOS), a.background).convert("RGB")
        os.makedirs(os.path.dirname(os.path.abspath(a.play_icon)), exist_ok=True)
        store.save(a.play_icon, "PNG")
        print("Play store icon:", a.play_icon)

    if not a.res:
        if not a.play_icon:
            sys.exit("--res is required to write the launcher icons")
        return
    if not os.path.isdir(a.res):
        sys.exit(f"no such res directory: {a.res}")

    global ROOT
    ROOT = a.res
    bgimg = load(a.background_image) if a.background_image else None
    print("launcher icons:")
    for dens, mult in DENSITIES.items():
        d = os.path.join(a.res, f"mipmap-{dens}")
        ad_px = round(ADAPTIVE_DP * mult)
        lg_px = round(LEGACY_DP * mult)

        fg = scaled_into_safe_zone(src, ad_px)
        write(fg, os.path.join(d, "ic_launcher_foreground.png"))

        if bgimg:
            write(bgimg.resize((ad_px, ad_px), Image.LANCZOS),
                  os.path.join(d, "ic_launcher_background.png"))
        if a.monochrome:
            # keep the shape, drop the colour — themed icons are tinted by the system
            mono = Image.new("RGBA", fg.size, (0, 0, 0, 0))
            mono.putalpha(fg.split()[-1])
            write(mono, os.path.join(d, "ic_launcher_monochrome.png"))

        # legacy: the same art, flattened, at launcher size
        legacy = flatten(scaled_into_safe_zone(src, lg_px), a.background)
        write(legacy, os.path.join(d, "ic_launcher.png"))
        write(circular(legacy), os.path.join(d, "ic_launcher_round.png"))

    bg_ref = "@mipmap/ic_launcher_background" if bgimg else "@color/ic_launcher_background"
    xml = ADAPTIVE_XML.format(bg=bg_ref, mono=MONO_LINE if a.monochrome else "")
    for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
        path = os.path.join(a.res, "mipmap-anydpi-v26", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(xml)
        print("  ", rel(path))

    if not bgimg:
        path = os.path.join(a.res, "values", "ic_launcher_background.xml")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(COLOR_XML.format(color=sx.escape(a.background)))
        print("  ", rel(path))

    print("\nNow look at it on a launcher with circular masking — the safe zone is a\n"
          "promise about geometry, not about whether the art survives it.")


if __name__ == "__main__":
    main()
