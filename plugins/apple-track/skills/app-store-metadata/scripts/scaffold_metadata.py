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
"""

import argparse
import os

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


def touch(path, created):
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("")
        created.append(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("metadata_root")
    ap.add_argument("--locales", required=True,
                    help="comma-separated App Store locale codes, e.g. en-US,de-DE,he")
    ap.add_argument("--no-review", action="store_true",
                    help="skip the review_information folder")
    args = ap.parse_args()

    root = os.path.abspath(args.metadata_root)
    locales = [s.strip() for s in args.locales.split(",") if s.strip()]
    os.makedirs(root, exist_ok=True)
    created, skipped = [], []

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
            touch(p, created)

    # per-locale files
    for loc in locales:
        ldir = os.path.join(root, loc)
        os.makedirs(ldir, exist_ok=True)
        for fn in PER_LOCALE_FILES:
            p = os.path.join(ldir, fn)
            if os.path.exists(p):
                skipped.append(p)
            touch(p, created)

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
    print("\nNext: fill the fields, then run validate_metadata.py before uploading.")


if __name__ == "__main__":
    main()
