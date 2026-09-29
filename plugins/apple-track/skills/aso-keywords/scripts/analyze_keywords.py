#!/usr/bin/env python3
"""
analyze_keywords.py — App Store Optimization audit of the search-indexed fields.

The App Store indexes the app NAME + SUBTITLE + KEYWORDS field together for
search. This script reads those (from fastlane metadata) per locale and flags the
common ASO mistakes: an under-used or over-limit keyword field, wasted spaces
after commas, words duplicated across name/subtitle/keywords (redundant — they're
indexed together), and duplicate/again-pluralized terms.

Usage: python3 analyze_keywords.py <project-root-or-metadata-root> [--json]
Stdlib only. (Search volume/difficulty needs paid data — out of scope; this is
the on-page hygiene + structure audit.)
"""

import argparse
import glob
import json
import os
import re
import sys

KNOWN_LOCALES = {
    "en-US","en-GB","en-AU","en-CA","de-DE","fr-FR","fr-CA","es-ES","es-MX","it",
    "pt-BR","pt-PT","nl-NL","sv","da","fi","no","ru","pl","tr","ar-SA","he","ja",
    "ko","zh-Hans","zh-Hant","th","vi","id","ms","hi","cs","sk","hu","ro","uk","el",
}
STOP = set("the a an and or for to of in on with your you it is are app apps".split())
NAME_LIMIT, SUBTITLE_LIMIT, KEYWORDS_LIMIT = 30, 30, 100


def read(path):
    try:
        with open(path, "r", errors="ignore") as f:
            return f.read().strip()
    except OSError:
        return ""


def words(text):
    return [w for w in re.findall(r"[\wÀ-ÿ']+", (text or "").lower()) if w]


def find_metadata_roots(path):
    path = os.path.abspath(path)
    md = os.path.join(path, "fastlane", "metadata")
    base = md if os.path.isdir(md) else path
    if not os.path.isdir(base):
        return []
    roots = []
    def is_root(d):
        try: ch = set(os.listdir(d))
        except OSError: return False
        return bool(ch & KNOWN_LOCALES) or "primary_category.txt" in ch
    if is_root(base):
        roots.append(base)
    for c in sorted(os.listdir(base)):
        sub = os.path.join(base, c)
        if os.path.isdir(sub) and is_root(sub):
            roots.append(sub)
    seen=set(); return [r for r in roots if not (r in seen or seen.add(r))]


def analyze_locale(root, loc):
    name = read(os.path.join(root, loc, "name.txt"))
    subtitle = read(os.path.join(root, loc, "subtitle.txt"))
    kw_raw = read(os.path.join(root, loc, "keywords.txt"))
    issues = []

    if len(name) > NAME_LIMIT:
        issues.append(("error", f"name is {len(name)} chars (limit {NAME_LIMIT})"))
    if len(subtitle) > SUBTITLE_LIMIT:
        issues.append(("error", f"subtitle is {len(subtitle)} chars (limit {SUBTITLE_LIMIT})"))

    kw_terms = [t.strip() for t in kw_raw.split(",") if t.strip()]
    kw_len = len(kw_raw)
    if kw_len > KEYWORDS_LIMIT:
        issues.append(("error", f"keywords is {kw_len} chars (limit {KEYWORDS_LIMIT}) — over by {kw_len-KEYWORDS_LIMIT}"))
    elif kw_len < KEYWORDS_LIMIT * 0.7 and kw_raw:
        issues.append(("info", f"keywords uses only {kw_len}/{KEYWORDS_LIMIT} chars — room for more terms"))
    elif not kw_raw:
        issues.append(("warn", "keywords field is empty — a wasted ranking surface"))

    if ", " in kw_raw:
        wasted = kw_raw.count(", ")
        issues.append(("warn", f"{wasted} space(s) after commas waste ~{wasted} of the 100 chars — use 'a,b,c' not 'a, b, c'"))

    low = [t.lower() for t in kw_terms]
    dups = sorted({t for t in low if low.count(t) > 1})
    if dups:
        issues.append(("warn", f"duplicate keyword terms: {', '.join(dups)}"))

    # overlap: name/subtitle words repeated in keywords = wasted (indexed together)
    ns_words = set(words(name)) | set(words(subtitle))
    kw_words = set(w for t in kw_terms for w in words(t))
    overlap = sorted((ns_words & kw_words) - STOP)
    if overlap:
        issues.append(("warn", f"these appear in name/subtitle AND keywords (redundant — drop from keywords to free space): {', '.join(overlap)}"))

    indexed = sorted((ns_words | kw_words) - STOP)
    return {
        "locale": loc,
        "name": name, "name_len": len(name),
        "subtitle": subtitle, "subtitle_len": len(subtitle),
        "keywords": kw_raw, "keywords_len": kw_len, "keyword_terms": kw_terms,
        "indexed_terms": indexed,
        "issues": issues,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    roots = find_metadata_roots(args.path)
    if not roots:
        print("No fastlane metadata found (need fastlane/metadata/<locale> with name/subtitle/keywords).")
        sys.exit(1)

    out = []
    for root in roots:
        locs = [d for d in sorted(os.listdir(root)) if d in KNOWN_LOCALES]
        out.append({"app": os.path.basename(root), "locales": [analyze_locale(root, l) for l in locs]})

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False)); return

    icon = {"error":"🔴","warn":"🟠","info":"⚪"}
    for app in out:
        print(f"\n=== {app['app']} ===")
        for L in app["locales"]:
            print(f"\n  [{L['locale']}]  name {L['name_len']}/30 · subtitle {L['subtitle_len']}/30 · keywords {L['keywords_len']}/100")
            if not L["issues"]:
                print("    ✅ no ASO hygiene issues")
            for sev, msg in L["issues"]:
                print(f"    {icon.get(sev,'?')} {msg}")
    print("\nTip: name + subtitle + keywords are indexed TOGETHER — don't repeat a "
          "word across them. Localize per store to multiply your indexed terms.")


if __name__ == "__main__":
    main()
