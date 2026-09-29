#!/usr/bin/env python3
"""Where Play listing text and graphics sit — in the two layouts that both exist.

`scaffold_metadata.py` and `validate_metadata.py` are told, by their own SKILL.md, to
run against the hub (`$APP_HUB/<slug>/store/play`) in the studio flow and against the
repo (`fastlane/metadata/android`) standalone. They only ever understood the second, so
in the studio flow scaffold created `store/play/fastlane/metadata/android/…` beside the
real tree, and validate read `changelogs/` and `iap/` as if they were locales and
reported every required field missing from them.

The two layouts are genuinely different, and neither is wrong:

    supply (a repo)                       hub (the studio source of truth)
    fastlane/metadata/android/            <slug>/store/play/
      <locale>/                             metadata/<locale>/
        title.txt                             title.txt
        short_description.txt                 short_description.txt
        full_description.txt                  full_description.txt
        video.txt                             video.txt
        changelogs/<versionCode>.txt        changelogs/<versionCode>/<locale>.txt
        images/…                            (none — see below)

Two differences, both deliberate:

  * **Changelogs transpose.** `supply` wants one file per locale holding that build's
    notes; the hub groups a build's notes together, which is how they are written and
    reviewed — one version, every language, side by side. `sync_from_hub.sh` maps
    between them, and reads both shapes.
  * **The hub keeps graphics somewhere else entirely**, under `<slug>/media/play/`,
    because they are produced by a different skill (`play-store-media`) at a different
    time. In the repo they have to sit inside the locale, because that is where
    `supply` looks.

**Graphics are FILES, not folders**, in both layouts: `images/icon.png` and
`images/featureGraphic.png`. Only the screenshot sets are directories. Scaffold created
`images/icon/` and `images/featureGraphic/` as directories and validate then checked
those directories, so on a correct tree it always warned "empty" — and on a tree it had
scaffolded itself, `supply` would have found no icon at all.
"""
from __future__ import annotations

from pathlib import Path

ANDROID_PARTS = ("fastlane", "metadata", "android")

TEXT_FILES = ("title.txt", "short_description.txt", "full_description.txt", "video.txt")
REQUIRED = ("title.txt", "short_description.txt", "full_description.txt")
LIMITS = {"title.txt": 30, "short_description.txt": 80, "full_description.txt": 4000}
CHANGELOG_LIMIT = 500

# Directories, in both layouts. The two single graphics are files and are listed
# separately, because that distinction is the bug this module exists to stop repeating.
SCREENSHOT_DIRS = (
    "images/phoneScreenshots",
    "images/sevenInchScreenshots",
    "images/tenInchScreenshots",
)
# (path, what it is) — `supply` reads these exact names.
SINGLE_IMAGES = (
    ("images/icon.png", "512×512 store icon"),
    ("images/featureGraphic.png", "1024×500, required to publish"),
)

# A Play locale is `xx` or `xx-YY`/`xx-Latn`/`es-419`. Used to tell a locale directory
# from a sibling like `changelogs/` or `iap/` — guessing by "is it a directory" is what
# made the validator report a changelog folder as a locale missing its title.
import re
LOCALE_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,4})?$")


class Layout:
    """Resolved paths for one listing, in whichever layout it is written.

    `kind` is "supply" or "hub". `meta_root` holds the locale directories. `media_root`
    is where per-locale `images/` live — the locale directory itself under supply, a
    separate tree under hub, and None when there is none to check.
    """

    def __init__(self, kind, meta_root, changelog_root, media_root):
        self.kind = kind
        self.meta_root = meta_root
        self.changelog_root = changelog_root      # hub only; None under supply
        self.media_root = media_root              # None when graphics are not here

    def locales(self):
        """Locale directories, by name. Anything that is not locale-shaped is skipped."""
        if not self.meta_root.is_dir():
            return []
        return sorted((d for d in self.meta_root.iterdir()
                       if d.is_dir() and LOCALE_RE.match(d.name)),
                      key=lambda d: d.name)

    def images_dir(self, locale):
        """Where `images/` sits for one locale, or None when this layout has none."""
        if self.media_root is None:
            return None
        return self.media_root / locale / "images"

    def changelogs(self, locale):
        """[(label, path)] of that locale's release notes, in either shape."""
        out = []
        if self.kind == "supply":
            d = self.meta_root / locale / "changelogs"
            if d.is_dir():
                out = [(f"changelogs/{f.name}", f) for f in sorted(d.glob("*.txt"))]
        elif self.changelog_root and self.changelog_root.is_dir():
            # A versionCode is an integer, so sort as one: a plain sort puts build 10
            # between 1 and 2, and a reader scanning for the newest reads the wrong row.
            def order(p):
                return (0, int(p.name)) if p.name.isdigit() else (1, 0, p.name)
            for vc in sorted(self.changelog_root.iterdir(), key=order):
                if vc.is_dir():
                    f = vc / f"{locale}.txt"
                    if f.is_file():
                        out.append((f"changelogs/{vc.name}/{f.name}", f))
                elif vc.suffix == ".txt":
                    # The flat shape: one file per build, the same text for every
                    # locale. `sync_from_hub.sh` accepts it, so this must too — a
                    # validator that cannot read what the syncer ships is a validator
                    # that passes a listing nobody checked.
                    out.append((f"changelogs/{vc.name} (all locales)", vc))
        return out

    def describe(self):
        bits = [f"{self.kind} layout", f"text: {self.meta_root}"]
        if self.changelog_root:
            bits.append(f"changelogs: {self.changelog_root}")
        bits.append(f"graphics: {self.media_root}" if self.media_root
                    else "graphics: not in this tree")
        return "\n".join("  " + b for b in bits)


def _looks_like_hub(root: Path) -> bool:
    """A hub store/play root: `metadata/` holding locale directories.

    Decided by structure, not by the directory's name — a studio may keep the hub
    anywhere, and `store/play` is a convention of this factory rather than a fact.
    """
    meta = root / "metadata"
    return meta.is_dir() and any(d.is_dir() and LOCALE_RE.match(d.name)
                                 for d in meta.iterdir())


def resolve(root: Path, media_override: Path | None = None) -> Layout:
    """Work out which layout `root` is, and where each part of it lives."""
    root = Path(root).expanduser().resolve()

    if _looks_like_hub(root):
        # <slug>/store/play → <slug>/media/play, when that is how the hub is arranged.
        # Derived rather than assumed: if it is not there, graphics are reported as
        # "not in this tree" instead of as missing, which is a different claim.
        media = media_override
        if media is None:
            guess = root.parent.parent / "media" / "play"
            media = guess if guess.is_dir() else None
        return Layout("hub", root / "metadata", root / "changelogs", media)

    android_root = root if root.parts[-3:] == ANDROID_PARTS else root.joinpath(*ANDROID_PARTS)
    # A root that is already the locale level (no fastlane/ under it) is honoured as-is,
    # which is what the old `resolve_android_root` fallback did and is worth keeping.
    if not android_root.is_dir() and any(d.is_dir() and LOCALE_RE.match(d.name)
                                         for d in root.iterdir() if root.is_dir()):
        android_root = root
    return Layout("supply", android_root, None, media_override or android_root)
