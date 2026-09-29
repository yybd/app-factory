#!/usr/bin/env python3
"""
scan_localization.py — audit in-app localization for an Xcode project.

Checks the things that cause shipped bugs and untranslated UI:
  - cross-locale completeness: keys missing / extra / empty / untranslated
    (identical to the base language) per locale
  - code vs catalog: keys referenced in Swift but not defined (missing), and
    keys defined but never referenced (unused/dead)
  - hardcoded UI strings: SwiftUI text literals not wrapped for localization
    (heuristic — candidates to confirm)

Supports classic `.strings` (Localizable.strings per .lproj) and `.xcstrings`
String Catalogs.

Usage: python3 scan_localization.py <project-root> [--base en] [--json]
Stdlib only.
"""

import argparse
import glob
import json
import os
import re
import sys

CODE_EXTS = (".swift", ".m", ".mm")
SKIP_DIRS = {".git", "Pods", "Carthage", "DerivedData", "build", ".build", "node_modules", "fastlane"}

STRINGS_ENTRY = re.compile(r'"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;')
REF_PATTERNS = [
    re.compile(r'NSLocalizedString\(\s*"((?:[^"\\]|\\.)*)"'),
    re.compile(r'String\(\s*localized:\s*"((?:[^"\\]|\\.)*)"'),
]
# Heuristic: SwiftUI initializers/modifiers that take a user-facing string.
HARDCODED = re.compile(
    r'(?:Text|Button|Label|Toggle|Picker|TextField|SecureField|Stepper|Link)\(\s*"([^"]{2,})"'
    r'|\.(?:navigationTitle|help|accessibilityLabel)\(\s*"([^"]{2,})"'
)


def iter_code(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if fn.endswith(CODE_EXTS):
                yield os.path.join(dp, fn)


def rel(root, p):
    try: return os.path.relpath(p, root)
    except ValueError: return p


def parse_strings(path):
    out = {}
    try:
        with open(path, "r", errors="ignore") as f:
            text = f.read()
    except OSError:
        return out
    for m in STRINGS_ENTRY.finditer(text):
        out[m.group(1)] = m.group(2)
    return out


def parse_xcstrings(path):
    """Return {locale: {key: value}} from a String Catalog."""
    try:
        with open(path, "r", errors="ignore") as f:
            data = json.load(f)
    except Exception:
        return {}
    locales = {}
    for key, entry in (data.get("strings") or {}).items():
        for loc, loc_entry in (entry.get("localizations") or {}).items():
            unit = (loc_entry.get("stringUnit") or {})
            locales.setdefault(loc, {})[key] = unit.get("value", "")
    return locales


def collect_catalogs(root):
    """Return {locale: {key: value}} merged across classic .strings + .xcstrings."""
    locales = {}
    # classic .strings in *.lproj
    for sp in glob.glob(os.path.join(root, "**", "*.lproj", "*.strings"), recursive=True):
        if "DerivedData" in sp:
            continue
        loc = os.path.basename(os.path.dirname(sp)).replace(".lproj", "")
        locales.setdefault(loc, {}).update(parse_strings(sp))
    # modern .xcstrings
    for xp in glob.glob(os.path.join(root, "**", "*.xcstrings"), recursive=True):
        if "DerivedData" in xp:
            continue
        for loc, kv in parse_xcstrings(xp).items():
            locales.setdefault(loc, {}).update(kv)
    return locales


def collect_referenced_keys(root):
    refs = {}
    for path in iter_code(root):
        try:
            with open(path, "r", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for rx in REF_PATTERNS:
                for m in rx.finditer(line):
                    refs.setdefault(m.group(1), (rel(root, path), i))
    return refs


def find_hardcoded(root):
    hits = []
    for path in iter_code(root):
        try:
            with open(path, "r", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if "NSLocalizedString" in line or "String(localized:" in line:
                continue
            for m in HARDCODED.finditer(line):
                lit = m.group(1) or m.group(2)
                if lit and not lit.startswith(("http", "systemName", "sf")):
                    hits.append({"file": rel(root, path), "line": i, "text": lit[:60]})
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--base", default=None, help="base locale (default: en, else first)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    catalogs = collect_catalogs(root)
    if not catalogs:
        print("No .strings/.xcstrings localization found."); sys.exit(1)
    locales = sorted(catalogs)
    base = args.base or ("en" if "en" in catalogs else locales[0])
    base_keys = set(catalogs.get(base, {}))

    per_locale = {}
    for loc in locales:
        keys = set(catalogs[loc])
        missing = sorted(base_keys - keys)
        extra = sorted(keys - base_keys)
        empty = sorted(k for k, v in catalogs[loc].items() if not v.strip())
        untranslated = [] if loc == base else sorted(
            k for k in (keys & base_keys)
            if catalogs[loc][k] and catalogs[loc][k] == catalogs[base].get(k))
        per_locale[loc] = {"count": len(keys), "missing": missing, "extra": extra,
                           "empty": empty, "untranslated_same_as_base": untranslated}

    refs = collect_referenced_keys(root)
    referenced = set(refs)
    missing_in_catalog = sorted(referenced - base_keys)     # used in code, not defined
    unused = sorted(base_keys - referenced)                 # defined, never used
    hardcoded = find_hardcoded(root)

    report = {
        "base_locale": base, "locales": locales,
        "per_locale": per_locale,
        "code": {
            "referenced_keys": len(referenced),
            "missing_in_catalog": missing_in_catalog,
            "unused_keys": unused,
        },
        "hardcoded_candidates": hardcoded,
    }
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False)); return

    print(f"=== Localization audit: {root} ===")
    print(f"base: {base}   locales: {', '.join(locales)}\n")
    print("▶ Per-locale completeness (vs base)")
    for loc in locales:
        d = per_locale[loc]
        flags = []
        if d["missing"]: flags.append(f"{len(d['missing'])} missing")
        if d["extra"]: flags.append(f"{len(d['extra'])} extra")
        if d["empty"]: flags.append(f"{len(d['empty'])} empty")
        if d["untranslated_same_as_base"]: flags.append(f"{len(d['untranslated_same_as_base'])} untranslated?")
        status = "✅ complete" if not flags else "⚠️  " + ", ".join(flags)
        print(f"   {loc}: {d['count']} keys — {status}")
        for k in d["missing"][:8]:
            print(f"        missing: {k}")
    print("\n▶ Code vs catalog")
    if missing_in_catalog:
        print(f"   🔴 {len(missing_in_catalog)} key(s) used in code but NOT defined:")
        for k in missing_in_catalog[:10]:
            print(f"        {k}  ({refs[k][0]}:{refs[k][1]})")
    else:
        print("   ✅ every referenced key is defined")
    if unused:
        print(f"   ⚠️  {len(unused)} defined key(s) never referenced in code (possibly dead):")
        for k in unused[:10]:
            print(f"        {k}")
    print(f"\n▶ Hardcoded UI string candidates (heuristic): {len(hardcoded)}")
    for h in hardcoded[:12]:
        print(f"   {h['file']}:{h['line']}  \"{h['text']}\"")
    if len(hardcoded) > 12:
        print(f"   … and {len(hardcoded)-12} more")
    print("\n(Confirm hardcoded candidates against the code — some literals are intentional.)")


if __name__ == "__main__":
    main()
