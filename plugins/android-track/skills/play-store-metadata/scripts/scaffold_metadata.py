#!/usr/bin/env python3
"""Scaffold the Play listing tree — in whichever of the two layouts you point it at.

    python3 scaffold_metadata.py <root> --locales en-US,de-DE,iw-IL

`<root>` may be a project root, a `fastlane/metadata/android` root, or a hub
`<slug>/store/play` root. Which layout it is, is decided by looking at the tree rather
than at the name — see `play_layout.py`, which holds both shapes and the reason they
differ.

**Non-destructive.** An existing file is never overwritten and never emptied; it is
reported as left alone. Running it twice changes nothing the second time.

Two things it used to get wrong, both silent:

  * Told to scaffold a hub root, it appended `fastlane/metadata/android` and built a
    second, empty tree *beside* the real one. Nothing errored; the listing simply was
    not where anybody looked.
  * It created `images/icon/` and `images/featureGraphic/` as directories. `supply`
    reads `images/icon.png` and `images/featureGraphic.png` — files — so a tree this
    script scaffolded would upload with no icon and no feature graphic.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from play_layout import SCREENSHOT_DIRS, SINGLE_IMAGES, TEXT_FILES, resolve  # noqa: E402


def scaffold(layout, locales):
    created, skipped, dirs = [], [], []

    def rel(p):
        try:
            return str(p.relative_to(layout.meta_root.parent))
        except ValueError:
            return str(p)

    for loc in locales:
        locdir = layout.meta_root / loc
        locdir.mkdir(parents=True, exist_ok=True)

        for name in TEXT_FILES:
            f = locdir / name
            if f.exists():
                skipped.append(rel(f))
            else:
                f.write_text("", encoding="utf-8")
                created.append(rel(f))

        # Release notes: one directory per locale under supply, one per build under hub.
        # The hub's are created by the release, not here — a versionCode is not known
        # at scaffold time, and an empty `changelogs/7/` would be a lie about build 7.
        if layout.kind == "supply":
            (locdir / "changelogs").mkdir(exist_ok=True)
            dirs.append(rel(locdir / "changelogs"))

        images = layout.images_dir(loc)
        if images is None:
            continue
        for d in SCREENSHOT_DIRS:
            p = images.parent / d
            if not p.is_dir():
                p.mkdir(parents=True, exist_ok=True)
                dirs.append(rel(p))
            # git does not carry an empty directory, and these are empty by design
            # until the media skill fills them.
            keep = p / ".gitkeep"
            if not keep.exists():
                keep.write_text("", encoding="utf-8")

    print(layout.describe())
    print(f"  locales: {', '.join(locales)}\n")
    print(f"Created {len(created)} file(s) and {len(dirs)} folder(s); "
          f"left {len(skipped)} existing file(s) untouched.")
    for c in created:
        print(f"  + {c}")
    for d in dirs:
        print(f"  + {d}/")
    for s in skipped:
        print(f"  = {s} (exists)")

    # The two single graphics are named, never created: an empty `icon.png` is a file
    # `supply` would try to upload. Saying where they go is the useful half.
    if layout.media_root is not None:
        print("\nThe two single graphics are files, not folders — put them at:")
        for path, what in SINGLE_IMAGES:
            print(f"  {path}   ({what})")
    else:
        print("\nGraphics are not in this tree; in the hub they live under "
              "<slug>/media/play/<locale>/images/ and are produced by play-store-media.")


def main():
    ap = argparse.ArgumentParser(
        description="Scaffold Play listing metadata, in the supply or hub layout.")
    ap.add_argument("root", help="project root, fastlane/metadata/android, or <slug>/store/play")
    ap.add_argument("--locales", required=True,
                    help="comma-separated Play locale codes, e.g. en-US,de-DE,iw-IL")
    ap.add_argument("--media", help="where per-locale images/ live (default: derived)")
    a = ap.parse_args()

    locales = [x.strip() for x in a.locales.split(",") if x.strip()]
    if not locales:
        ap.error("no locales given")

    layout = resolve(Path(a.root), Path(a.media).expanduser().resolve() if a.media else None)
    scaffold(layout, locales)


if __name__ == "__main__":
    main()
