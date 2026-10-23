#!/usr/bin/env python3
"""Pack the keyword fields of one storefront from a scored study — or check fields.

    allocate.py STUDY.json --cc il --metadata <root> [--set he:subtitle="…"] [--exclude WORD]
    allocate.py --check --metadata <root> [--cc il] [--set he:keywords="…"]

`<root>` is a fastlane-shaped metadata tree (`<root>/<locale>/name.txt` …): the hub's
`<slug>/store/apple/metadata`, or a repo's `fastlane/metadata`.

**What it decides and what it leaves.** The name and subtitle are copy a person reads, so
the agent writes them; `--set` tries a proposal without touching a file. Given those, this
packs each keyword field the storefront indexes with the words the scored terms still
need, by band and priority, until the limit — the deterministic part, so two runs on the
same study give the same field.

The rules it packs by (see the guide for which are Apple's and which are practice):
  * a word the locale's name or subtitle already has is not repeated;
  * a phrase is covered only when **all** its words are in **one** locale — combinations
    do not cross locales — so a phrase's missing words go together into one field;
  * one stem per word (note/notes, תזכורת/תזכורות): Apple matches them, so the second
    form is wasted bytes;
  * no stop words, no category or developer words (Apple indexes those already), no term
    the study marks as a trademark or the owner rejected;
  * the limit is counted in the unit calibration.json names (characters, verified).

Prints the proposal; with --out also writes it as JSON. Never writes a metadata file —
`app-store-metadata` owns those.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aso_core import (STOP, STOREFRONTS, is_hebrew, load_calibration, load_json,  # noqa: E402
                      read_listing, save_json, stem, units, words)

ORDER = ("stretch", "core", "long tail", "reserve")


def category_words(metadata_root):
    out = set()
    for f in ("primary_category.txt", "secondary_category.txt"):
        try:
            raw = open(os.path.join(metadata_root, f), encoding="utf-8").read()
        except OSError:
            continue
        for part in raw.replace("MZGenre.", " ").replace("_", " ").replace(".", " ").split():
            out.add(stem(part.lower()))
    return out


def fits_script(term, locale):
    """A Hebrew term belongs only in the Hebrew locale. A Latin one fits anywhere — the
    Hebrew listing indexes Latin words too, and Israelis search "markdown" in Latin —
    but it prefers a Latin locale when the storefront has one (see `prefer`)."""
    return locale == "he" if is_hebrew(term) else True


def prefer(term, locale):
    return 1 if locale == "he" and not is_hebrew(term) else 0


def check(locale, listing, cal, excluded=frozenset()):
    """ASO hygiene for one locale's name/subtitle/keywords. [(severity, message)]"""
    unit, limit = cal["keyword_limit_unit"], cal["keyword_limit"]
    name, sub, kw = listing.get("name", ""), listing.get("subtitle", ""), listing.get("keywords", "")
    issues = []
    for field, text, lim in (("name", name, cal["name_limit"]), ("subtitle", sub, cal["subtitle_limit"])):
        if len(text) > lim:
            issues.append(("error", f"{field} is {len(text)} characters (limit {lim})"))
    used = units(kw, unit)
    if used > limit:
        issues.append(("error", f"keywords use {used} {unit} (limit {limit}) — over by {used - limit}"))
    elif not kw:
        issues.append(("warn", "keywords field is empty — a wasted ranking surface"))
    elif used < limit * 0.85:
        issues.append(("info", f"keywords use {used}/{limit} {unit} — room for more"))
    if ", " in kw or " ," in kw:
        issues.append(("warn", "spaces around commas waste the field — 'a,b,c'"))
    terms = [t.strip() for t in kw.split(",") if t.strip()]
    kw_words = [w for t in terms for w in words(t)]
    seen, dup = {}, set()
    for w in kw_words:
        s = stem(w)
        if s in seen and seen[s] != w:
            dup.add(f"{seen[s]}/{w}")
        elif s in seen:
            dup.add(w)
        seen.setdefault(s, w)
    if dup:
        issues.append(("warn", f"the same word twice (or singular and plural): {', '.join(sorted(dup))}"))
    ns = {stem(w) for w in words(name) + words(sub)}
    overlap = sorted({w for w in kw_words if stem(w) in ns})
    if overlap:
        issues.append(("warn", f"already in the name or subtitle: {', '.join(overlap)}"))
    waste = sorted({w for w in kw_words if w in STOP or stem(w) in excluded})
    if waste:
        issues.append(("warn", f"indexed already or ignored (stop, category, developer): {', '.join(waste)}"))
    return issues


def allocate(study, cc, listings, cal, excluded, fill=True):
    """{locale: {keywords, used, covered, ...}} for the storefront's locales in use."""
    unit, limit = cal["keyword_limit_unit"], cal["keyword_limit"]
    cands = study.get("storefronts", {}).get(cc, {}).get("candidates", {})
    locales = [loc for loc in STOREFRONTS[cc]["locales"] if loc in listings]
    have = {loc: {stem(w) for w in words(listings[loc]["name"]) + words(listings[loc]["subtitle"])}
            for loc in locales}
    field = {loc: [] for loc in locales}
    plan = {loc: {"covered": [], "by_name_subtitle": []} for loc in locales}
    unplaced = []

    def stems(loc):
        return have[loc] | {stem(w) for w in field[loc]}

    terms = sorted((t for t, c in cands.items() if c.get("band") in ORDER),
                   key=lambda t: (ORDER.index(cands[t]["band"]), -cands[t].get("priority", 0)))
    for term in terms:
        c = cands[term]
        if c["band"] == "reserve" and not fill:
            continue
        need = [w for w in dict.fromkeys(words(term)) if w not in STOP and stem(w) not in excluded]
        options = []
        for loc in locales:
            if not fits_script(term, loc):
                continue
            missing = [w for w in need if stem(w) not in stems(loc)]
            if not missing:
                options = [(-1, 0, loc, [])]
                break
            cost = units(",".join(field[loc] + missing), unit)
            if cost <= limit:
                options.append((prefer(term, loc), cost, loc, missing))
        if not options:
            if c["band"] != "reserve":
                unplaced.append(term)
            continue
        _, cost, loc, missing = min(options, key=lambda o: (o[0], o[1], locales.index(o[2])))
        field[loc] += missing
        key = "covered" if missing else (
            "by_name_subtitle" if all(stem(w) in have[loc] for w in need) else "covered")
        plan[loc][key].append(f"{term} ({c['band']})")

    out = {}
    for loc in locales:
        kw = ",".join(field[loc])
        out[loc] = {"keywords": kw, "used": units(kw, unit), "limit": limit, "unit": unit,
                    "name": listings[loc]["name"], "subtitle": listings[loc]["subtitle"], **plan[loc]}
    subtitle_ideas = [t for t in terms if cands[t]["band"] in ("stretch", "core")
                      and not any(all(stem(w) in have[loc] for w in words(t) if w not in STOP)
                                  for loc in locales)][:6]
    return {"cc": cc, "locales": out, "unplaced": unplaced,
            "not_in_listing": [loc for loc in STOREFRONTS[cc]["locales"] if loc not in listings],
            "subtitle_ideas": subtitle_ideas}


def parse_sets(sets):
    out = {}
    for s in sets:
        loc_field, _, text = s.partition("=")
        loc, _, fld = loc_field.partition(":")
        if fld not in ("name", "subtitle", "keywords") or not loc:
            raise SystemExit(f"--set wants LOCALE:name|subtitle|keywords=TEXT, got {s!r}")
        out.setdefault(loc, {})[fld] = text
    return out


def load_listings(root, sets):
    locs = [d for d in sorted(os.listdir(root))
            if os.path.isdir(os.path.join(root, d)) and os.path.exists(os.path.join(root, d, "name.txt"))]
    out = {loc: read_listing(root, loc) for loc in locs}
    for loc, fields in sets.items():
        out.setdefault(loc, {"name": "", "subtitle": "", "keywords": ""}).update(fields)
    return out


def main():
    ap = argparse.ArgumentParser(description="Pack a storefront's keyword fields from a "
                                 "scored study, or check existing fields.")
    ap.add_argument("study", nargs="?", help="the scored study (keywords.json)")
    ap.add_argument("--metadata", required=True, help="fastlane-shaped metadata root")
    ap.add_argument("--cc", default="us", choices=sorted(STOREFRONTS))
    ap.add_argument("--set", action="append", default=[], help='LOCALE:FIELD=TEXT, e.g. he:subtitle="…"')
    ap.add_argument("--exclude", action="append", default=[], help="a word never to pack (developer name …)")
    ap.add_argument("--no-fill", action="store_true", help="do not fill leftover room from the reserve")
    ap.add_argument("--check", action="store_true", help="only check the fields as they are (with --set)")
    ap.add_argument("--out", help="also write the proposal here as JSON")
    a = ap.parse_args()

    cal = load_calibration()
    listings = load_listings(a.metadata, parse_sets(a.set))
    excluded = category_words(a.metadata) | {stem(w) for x in a.exclude for w in words(x)}
    icon = {"error": "🔴", "warn": "🟠", "info": "⚪"}

    if a.check:
        bad = 0
        for loc in [x for x in STOREFRONTS[a.cc]["locales"] if x in listings] or sorted(listings):
            L = listings[loc]
            print(f"\n[{loc}] name {len(L['name'])}/30 · subtitle {len(L['subtitle'])}/30 · "
                  f"keywords {units(L['keywords'], cal['keyword_limit_unit'])}/{cal['keyword_limit']} {cal['keyword_limit_unit']}")
            issues = check(loc, L, cal, excluded)
            bad += sum(1 for s, _ in issues if s == "error")
            for sev, msg in issues or [("ok", "no hygiene issues")]:
                print(f"  {icon.get(sev, '✅')} {msg}")
        sys.exit(1 if bad else 0)

    if not a.study:
        ap.error("give the scored study, or --check")
    study = load_json(a.study)
    if not study:
        ap.error(f"{a.study} does not exist")
    res = allocate(study, a.cc, listings, cal, excluded, fill=not a.no_fill)
    for loc, r in res["locales"].items():
        print(f"\n[{loc}] {r['name']} — {r['subtitle']}")
        print(f"  keywords ({r['used']}/{r['limit']} {r['unit']}): {r['keywords'] or '—'}")
        if r["by_name_subtitle"]:
            print(f"  covered by name+subtitle: {'; '.join(r['by_name_subtitle'])}")
        if r["covered"]:
            print(f"  covered with the field:   {'; '.join(r['covered'])}")
        for sev, msg in check(loc, {**r}, cal, excluded):
            print(f"  {icon[sev]} {msg}")
    if res["unplaced"]:
        print(f"\ndid not fit anywhere: {', '.join(res['unplaced'])}")
    if res["subtitle_ideas"]:
        print(f"strong terms no name/subtitle carries (subtitle candidates): {', '.join(res['subtitle_ideas'])}")
    if res["not_in_listing"]:
        print(f"locales {a.cc} indexes that the listing does not have (each is another keyword "
              f"field): {', '.join(res['not_in_listing'])}")
    if a.out:
        save_json(a.out, res)


if __name__ == "__main__":
    main()
