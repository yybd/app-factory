#!/usr/bin/env python3
"""
scaffold_metadata.py — create the fastlane deliver metadata file tree for a set
of locales, non-destructively (never overwrites an existing file).

Usage:
    python3 scaffold_metadata.py <metadata-root> --locales en-US,de-DE,he
    python3 scaffold_metadata.py ./fastlane/metadata --locales en-US,de-DE

<metadata-root> is the per-app metadata folder (or fastlane/metadata for a
single-app project). Existing files are left untouched; only missing files and
folders are created (empty), so you can fill them in.

Two files are pre-filled rather than left empty, from the hub's DATA.md (the
"### support mail" rule): every locale's support_url.txt gets the app's own page +
#contact from the rule's per-app table — never the studio home — and
review_information/email_address.txt gets the support address. The app is found by
--slug, or from a hub path (<slug>/store/apple/metadata). An app with no row in the
table gets an empty support_url.txt and a warning; nothing is invented.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "shared")))
try:
    import support_mail  # noqa: E402
except ImportError:                     # an old copy of the track without shared/
    support_mail = None

PER_LOCALE_FILES = [
    "name.txt",
    "subtitle.txt",
    "description.txt",
    "keywords.txt",
    "promotional_text.txt",
    "release_notes.txt",
    "support_url.txt",
    "marketing_url.txt",
    "privacy_url.txt",
]

SHARED_FILES = [
    "copyright.txt",
    "primary_category.txt",
    "primary_first_sub_category.txt",
    "primary_second_sub_category.txt",
    "secondary_category.txt",
    "secondary_first_sub_category.txt",
    "secondary_second_sub_category.txt",
]

REVIEW_FILES = [
    "first_name.txt",
    "last_name.txt",
    "phone_number.txt",
    "email_address.txt",
    "demo_user.txt",
    "demo_password.txt",
    "notes.txt",
]


def touch(path, created, content=""):
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(content)
        created.append(path)


def slug_from_path(root):
    """<hub>/<slug>/store/apple/metadata → <slug>; None when the path is not that shape."""
    parts = os.path.abspath(root).rstrip(os.sep).split(os.sep)
    if "store" in parts:
        i = len(parts) - 1 - parts[::-1].index("store")
        if i > 0:
            return parts[i - 1]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("metadata_root")
    ap.add_argument("--locales", required=True,
                    help="comma-separated App Store locale codes, e.g. en-US,de-DE,he")
    ap.add_argument("--no-review", action="store_true",
                    help="skip the review_information folder")
    ap.add_argument("--slug", help="the app's hub slug (default: read from a hub path)")
    args = ap.parse_args()

    root = os.path.abspath(args.metadata_root)
    locales = [s.strip() for s in args.locales.split(",") if s.strip()]
    os.makedirs(root, exist_ok=True)
    created, skipped = [], []

    slug = args.slug or slug_from_path(root)
    sm = support_mail.load() if support_mail else {"address": None, "urls": {}, "warnings": []}
    surl = support_mail.support_url(sm, slug) if support_mail else None
    notes = list(sm.get("warnings", []))
    if not surl:
        notes.append(f"no support-URL row for '{slug or '?'}' in DATA.md's support-mail table — "
                     "support_url.txt left empty. Add the row (the app's page + #contact); "
                     "do not fall back to the studio home.")
    prefill = {"support_url.txt": surl or "", "email_address.txt": sm.get("address") or ""}

    # shared files
    for fn in SHARED_FILES:
        p = os.path.join(root, fn)
        (created if not os.path.exists(p) else skipped).append(p)
        touch(p, created)

    # review information
    if not args.no_review:
        rdir = os.path.join(root, "review_information")
        os.makedirs(rdir, exist_ok=True)
        for fn in REVIEW_FILES:
            p = os.path.join(rdir, fn)
            if os.path.exists(p):
                skipped.append(p)
            touch(p, created, prefill.get(fn, ""))

    # per-locale files
    for loc in locales:
        ldir = os.path.join(root, loc)
        os.makedirs(ldir, exist_ok=True)
        for fn in PER_LOCALE_FILES:
            p = os.path.join(ldir, fn)
            if os.path.exists(p):
                skipped.append(p)
            touch(p, created, prefill.get(fn, ""))

    rel = lambda p: os.path.relpath(p, root)
    print(f"Metadata root: {root}")
    print(f"Locales: {', '.join(locales)}")
    print(f"\nCreated {len(created)} file(s):")
    for p in created:
        print(f"  + {rel(p)}")
    if skipped:
        print(f"\nLeft {len(skipped)} existing file(s) untouched:")
        for p in skipped[:40]:
            print(f"  = {rel(p)}")
        if len(skipped) > 40:
            print(f"  … and {len(skipped) - 40} more")
    if surl or sm.get("address"):
        print(f"\nFrom DATA.md: support_url = {surl or '(none)'}, review email = {sm.get('address') or '(none)'}"
              " — written only into files that were created now.")
    for n in notes:
        print(f"  ! {n}")
    print("\nNext: fill the fields, then run validate_metadata.py before uploading.")


if __name__ == "__main__":
    main()
