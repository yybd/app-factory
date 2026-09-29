#!/usr/bin/env python3
"""
validate_metadata.py — validate fastlane deliver metadata against Apple's
character limits and required fields.

Usage:
    python3 validate_metadata.py <path>

<path> may be a project root (it will find fastlane/metadata and any per-app
subfolders), a fastlane/metadata folder, or a single per-app metadata folder.

Exit code 0 if no errors, 1 if any error-level problems found.
"""

import argparse
import json
import os
import re
import sys

# field file -> (max chars or None, severity_if_missing)
PER_LOCALE_LIMITS = {
    "name.txt": (30, "error"),
    "subtitle.txt": (30, "warn"),
    "keywords.txt": (100, "warn"),
    "description.txt": (4000, "error"),
    "promotional_text.txt": (170, "warn"),
    "release_notes.txt": (4000, "warn"),       # required for updates, not v1
    "support_url.txt": (None, "warn"),         # URL, required by 1.5
    "marketing_url.txt": (None, "info"),
    "privacy_url.txt": (None, "warn"),         # required if accounts/data
}

URL_FIELDS = {"support_url.txt", "marketing_url.txt", "privacy_url.txt"}

# Known App Store locale codes (folder names). Extend as Apple adds languages.
KNOWN_LOCALES = {
    "en-US", "en-GB", "en-AU", "en-CA", "de-DE", "fr-FR", "fr-CA", "es-ES",
    "es-MX", "it", "pt-BR", "pt-PT", "nl-NL", "sv", "da", "fi", "no", "ru",
    "pl", "tr", "ar-SA", "he", "ja", "ko", "zh-Hans", "zh-Hant", "th", "vi",
    "id", "ms", "hi", "cs", "sk", "hu", "ro", "uk", "el", "hr", "ca",
}

URL_RE = re.compile(r"^https?://[^\s]+$")

# --- In-App Purchases -------------------------------------------------------
# Limits verified 2026-08-23 against App Store Connect Help, "In-app purchase
# information". The 45-char description is the one that bites: the .storekit /
# marketing copy is always longer, and an over-limit description is rejected.
IAP_PER_LOCALE_LIMITS = {
    "display_name.txt": (30, "error"),
    "description.txt": (45, "error"),
}
IAP_SHARED_LIMITS = {
    "reference_name.txt": 64,
    "review_notes.txt": 4000,
}
IAP_PRODUCT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")

# The IAP reviewer screenshot must match one of the APP's screenshot specs and
# carry no alpha channel. One screenshot serves every platform (Universal
# Purchase = one shared IAP record).
LEGAL_SCREENSHOT_SIZES = {
    (1280, 800), (1440, 900), (2560, 1600), (2880, 1800),        # macOS 16:10
    (1320, 2868), (2868, 1320), (1284, 2778), (2778, 1284),      # iPhone 6.9" / 6.5"
    (2064, 2752), (2752, 2064),                                  # iPad 13"
}


def png_size(path):
    """(width, height, has_alpha) for a PNG, or None. Header-only, no deps."""
    try:
        with open(path, "rb") as f:
            head = f.read(26)
        if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
            return None
        w = int.from_bytes(head[16:20], "big")
        h = int.from_bytes(head[20:24], "big")
        colour_type = head[25]
        return w, h, colour_type in (4, 6)   # 4 = grey+alpha, 6 = RGBA
    except OSError:
        return None


def validate_iap_tree(iap_root):
    """Validate <slug>/store/apple/iap/<product-id>/ trees. Returns issue list."""
    issues = []
    for product_id in sorted(os.listdir(iap_root)):
        pdir = os.path.join(iap_root, product_id)
        if not os.path.isdir(pdir):
            continue
        tag = f"iap:{product_id}"

        if not IAP_PRODUCT_ID_RE.match(product_id):
            issues.append(("error", tag,
                           "product id must be <=100 chars of letters/numbers/._- "
                           "(and is permanent once saved in App Store Connect)"))

        for fn, limit in IAP_SHARED_LIMITS.items():
            content = read(os.path.join(pdir, fn))
            if content and len(content) > limit:
                issues.append(("error", tag,
                               f"{fn} is {len(content)} chars (limit {limit})"))
        if not read(os.path.join(pdir, "price.txt")):
            issues.append(("warn", tag, "price.txt is missing/empty"))

        locales = [d for d in sorted(os.listdir(pdir))
                   if os.path.isdir(os.path.join(pdir, d)) and d in KNOWN_LOCALES]
        if not locales:
            issues.append(("error", tag, "no locale folder with display_name.txt / description.txt"))
        for loc in locales:
            for fn, (limit, sev) in IAP_PER_LOCALE_LIMITS.items():
                content = read(os.path.join(pdir, loc, fn))
                if not content:
                    issues.append((sev, f"{tag}/{loc}", f"{fn} is missing/empty"))
                elif len(content) > limit:
                    issues.append(("error", f"{tag}/{loc}",
                                   f"{fn} is {len(content)} chars (limit {limit}) — "
                                   f"over by {len(content) - limit}"))

        # The reviewer screenshot: present, legal size, no alpha.
        shot = None
        for cand in ("review/screenshot.png", "review_screenshot.png"):
            c = os.path.join(pdir, cand)
            if os.path.isfile(c):
                shot = c
                break
        if shot is None:
            issues.append(("warn", tag,
                           "no reviewer screenshot in the store tree yet — required "
                           "before the product can be submitted"))
        else:
            info = png_size(shot)
            if info is None:
                issues.append(("warn", tag, "reviewer screenshot is not a readable PNG"))
            else:
                w, h, alpha = info
                if (w, h) not in LEGAL_SCREENSHOT_SIZES:
                    issues.append(("error", tag,
                                   f"reviewer screenshot is {w}x{h} — must match an app "
                                   "screenshot spec (Mac 2880x1800, iPhone 1320x2868, iPad 2064x2752, ...)"))
                if alpha:
                    issues.append(("error", tag,
                                   "reviewer screenshot has an alpha channel — App Store "
                                   "Connect rejects transparency; re-encode with format=rgb24"))
    return issues


def read(path):
    try:
        with open(path, "r", errors="ignore") as f:
            return f.read().strip()
    except OSError:
        return None


def find_metadata_roots(path):
    """Return list of per-app metadata roots (folders that contain locale dirs
    and/or the shared category files)."""
    path = os.path.abspath(path)
    candidates = []
    # If user passed a project root, descend into fastlane/metadata.
    md = os.path.join(path, "fastlane", "metadata")
    base = md if os.path.isdir(md) else path
    if not os.path.isdir(base):
        return []

    def looks_like_root(d):
        try:
            children = set(os.listdir(d))
        except OSError:
            return False
        if children & KNOWN_LOCALES:
            return True
        if "copyright.txt" in children or "primary_category.txt" in children:
            return True
        return False

    if looks_like_root(base):
        candidates.append(base)
    # also check immediate subfolders (multi-app: metadata/<app>/)
    for child in sorted(os.listdir(base)):
        sub = os.path.join(base, child)
        if os.path.isdir(sub) and looks_like_root(sub):
            candidates.append(sub)
    # dedupe, keep order
    seen, out = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def validate_root(root):
    issues = []  # (severity, locale_or_'-', message)
    name = os.path.basename(root.rstrip("/"))

    locale_dirs = [d for d in sorted(os.listdir(root))
                   if os.path.isdir(os.path.join(root, d)) and d != "review_information"]

    # review_information/notes.txt — App Review reads it, and App Store Connect
    # rejects it over 4000 characters. It was never checked here: the only 4000
    # entry above is `review_notes.txt`, which belongs to an IAP, so a 5,718-char
    # notes.txt passed clean and failed at upload instead.
    rn = os.path.join(root, "review_information", "notes.txt")
    if os.path.isfile(rn):
        n = len(open(rn, encoding="utf-8").read())
        if n > 4000:
            issues.append(("error", "-", f"review_information/notes.txt: {n} chars, limit 4000 (over by {n - 4000})"))
        elif n > 3900:
            issues.append(("warn", "-", f"review_information/notes.txt: {n} chars — within 100 of the 4000 limit"))
    recognized = [d for d in locale_dirs if d in KNOWN_LOCALES]
    unrecognized = [d for d in locale_dirs if d not in KNOWN_LOCALES]

    if not recognized:
        issues.append(("error", "-", "no recognized locale folders found"))
    for d in unrecognized:
        issues.append(("warn", d, f"folder '{d}' is not a known App Store locale code — deliver may reject it"))

    # per-locale field checks
    for loc in recognized:
        ldir = os.path.join(root, loc)
        for fn, (limit, miss_sev) in PER_LOCALE_LIMITS.items():
            p = os.path.join(ldir, fn)
            content = read(p)
            if content is None or content == "":
                # name/description empty is serious for the primary language;
                # report at the configured severity, model decides primary.
                if miss_sev in ("error", "warn"):
                    issues.append((miss_sev, loc, f"{fn} is missing/empty"))
                continue
            if limit is not None and len(content) > limit:
                issues.append(("error", loc,
                               f"{fn} is {len(content)} chars (limit {limit}) — over by {len(content) - limit}"))
            if fn in URL_FIELDS and not URL_RE.match(content):
                issues.append(("warn", loc, f"{fn} is not a valid http(s) URL: '{content[:40]}'"))
            if fn == "keywords.txt" and ", " in content:
                issues.append(("info", loc, "keywords.txt has spaces after commas — they count toward the 100-char limit; remove them"))

    # cross-locale completeness: name present everywhere?
    names_present = {loc: bool(read(os.path.join(root, loc, "name.txt"))) for loc in recognized}
    if any(names_present.values()) and not all(names_present.values()):
        missing = [loc for loc, ok in names_present.items() if not ok]
        issues.append(("warn", "-", f"name.txt present in some locales but missing in: {', '.join(missing)} (non-primary locales fall back to primary — make sure the primary is complete)"))

    # shared required-ish
    if not read(os.path.join(root, "primary_category.txt")):
        issues.append(("warn", "-", "primary_category.txt is empty"))

    # In-App Purchases live beside the metadata tree in the hub layout
    # (<slug>/store/apple/{metadata,iap}), so look one level up as well.
    for cand in (os.path.join(root, "iap"),
                 os.path.join(os.path.dirname(root.rstrip("/")), "iap")):
        if os.path.isdir(cand):
            issues.extend(validate_iap_tree(cand))
            break

    return {"app": name, "root": root, "locales": recognized, "issues": issues}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    roots = find_metadata_roots(args.path)
    if not roots:
        print("No fastlane metadata found. Expected fastlane/metadata/ with locale folders.")
        sys.exit(1)

    results = [validate_root(r) for r in roots]
    if args.json:
        print(json.dumps(results, indent=2))

    errors = 0
    sev_icon = {"error": "🔴", "warn": "🟠", "info": "⚪"}
    for res in results:
        print(f"\n=== {res['app']}  ({len(res['locales'])} locales: {', '.join(res['locales']) or 'none'}) ===")
        if not res["issues"]:
            print("  ✅ no issues")
            continue
        for sev, loc, msg in res["issues"]:
            if sev == "error":
                errors += 1
            loc_part = f"[{loc}] " if loc != "-" else ""
            print(f"  {sev_icon.get(sev, '?')} {loc_part}{msg}")

    print(f"\n{'❌' if errors else '✅'} {errors} error(s) across {len(results)} app(s).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
