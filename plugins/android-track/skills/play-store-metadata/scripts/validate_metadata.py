#!/usr/bin/env python3
"""Validate a Play listing against Google's limits — in either layout.

    python3 validate_metadata.py <root> [--media DIR]

`<root>` may be a project root, a `fastlane/metadata/android` root, or a hub
`<slug>/store/play` root; `play_layout.py` decides which and holds both shapes.

Exits non-zero on a hard error. Over-limit fields, a missing feature graphic and fewer
than two screenshots are the common Play listing rejections, which is what this is for.

What it used to do on a hub root: treat every directory as a locale — so `changelogs/`
and `iap/` were each reported as a locale missing its title, short description and full
description, six errors for two directories that are not locales. And it checked
`images/icon/` and `images/featureGraphic/` as *directories*, which `supply` never
creates, so a correct tree always warned that both were empty.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from play_layout import (CHANGELOG_LIMIT, LIMITS, REQUIRED,  # noqa: E402
                         SINGLE_IMAGES, resolve)


def char_len(p: Path) -> int:
    # Play does not count a trailing newline; strip a single one.
    return len(p.read_text(encoding="utf-8").rstrip("\n"))


def shots_in(d: Path) -> int:
    return len([c for c in d.iterdir() if not c.name.startswith(".")]) if d.is_dir() else 0


def validate(layout) -> int:
    if not layout.meta_root.is_dir():
        print(f"ERROR: no metadata directory at {layout.meta_root}")
        return 1

    locales = layout.locales()
    if not locales:
        print(f"ERROR: no locale folders under {layout.meta_root}")
        return 1

    errors = warnings = 0
    print("Validating a Play listing:")
    print(layout.describe())
    print()

    for loc in locales:
        print(f"[{loc.name}]")

        for name in REQUIRED:
            f = loc / name
            if not f.exists() or char_len(f) == 0:
                print(f"  ERROR  {name}: missing or empty (required)")
                errors += 1
                continue
            n, limit = char_len(f), LIMITS[name]
            if n > limit:
                errors += 1
                print(f"  ERROR  {name}: {n}/{limit} chars (over limit)")
            else:
                print(f"  ok     {name}: {n}/{limit} chars")

        v = loc / "video.txt"
        if v.exists() and char_len(v) > 0 and not v.read_text(encoding="utf-8").strip().startswith("http"):
            print("  WARN   video.txt: present but not a URL")
            warnings += 1

        for label, f in layout.changelogs(loc.name):
            n = char_len(f)
            if n > CHANGELOG_LIMIT:
                errors += 1
                print(f"  ERROR  {label}: {n}/{CHANGELOG_LIMIT} chars (over limit)")
            else:
                print(f"  ok     {label}: {n}/{CHANGELOG_LIMIT} chars")

        images = layout.images_dir(loc.name)
        if images is None:
            print("  ·      graphics live outside this tree — not checked here")
            print()
            continue

        # Files, not folders. `supply` reads these exact names.
        for rel, what in SINGLE_IMAGES:
            f = images.parent / rel
            # The shape the old scaffold created: a DIRECTORY named `images/icon`,
            # with no extension. Named explicitly, because "missing" would send
            # someone looking for a file while a folder of that name sits there —
            # and because a tree scaffolded before this fix still has one.
            legacy = images.parent / rel[: -len(".png")]
            if f.is_file():
                print(f"  ok     {rel}")
            elif legacy.is_dir():
                errors += 1
                print(f"  ERROR  {rel}: found the folder {legacy.name}/ instead — "
                      f"supply reads a FILE by this name. Move the image to {rel}.")
            else:
                print(f"  WARN   {rel}: missing ({what})")
                warnings += 1

        n = shots_in(images / "phoneScreenshots")
        if n < 2:
            print(f"  WARN   images/phoneScreenshots/: {n} (need 2-8)")
            warnings += 1
        else:
            print(f"  ok     images/phoneScreenshots/: {n}")
        print()

    print(f"Done. {errors} error(s), {warnings} warning(s).")
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description="Validate Play listing metadata.")
    ap.add_argument("root", help="project root, fastlane/metadata/android, or <slug>/store/play")
    ap.add_argument("--media", help="where per-locale images/ live (default: derived)")
    a = ap.parse_args()
    layout = resolve(Path(a.root), Path(a.media).expanduser().resolve() if a.media else None)
    sys.exit(validate(layout))


if __name__ == "__main__":
    main()
