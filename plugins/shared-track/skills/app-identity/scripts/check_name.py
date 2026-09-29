#!/usr/bin/env python3
"""check_name.py — audit an App Store name + subtitle against the live store.

Part of the app-identity skill. It answers the two questions taste cannot:

  1. Does this name collide with listings that already exist? A tail that duplicates a live
     app's tail is what Guideline 4.3 comparisons are made of, not a coincidence.
  2. Does the differentiator in the subtitle actually differentiate? A feature a quarter of
     the category already advertises is a category descriptor, however true it is.

  check_name.py --name "Quicknote: Templates Keyboard" \\
                --subtitle "Fills from the message you got" \\
                --category "text expander,snippet manager,paste keyboard" \\
                --claims "fills from the message,placeholder,encrypt"

Reads the public iTunes Search API — no credentials, no account.
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request

NAME_LIMIT = 30
SUBTITLE_LIMIT = 30
# Words too common to count as a collision on their own.
STOP = {"the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "your", "my"}


def search(term, limit=60):
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": term, "entity": "software", "country": "us", "limit": limit})
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.load(r)["results"]
    except Exception as e:                                  # noqa: BLE001
        print(f"  ! search failed for {term!r}: {e}", file=sys.stderr)
        return []


def norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def main():
    ap = argparse.ArgumentParser(description="Audit an App Store name and subtitle.")
    ap.add_argument("--name", required=True, help='full App Store name, e.g. "Brand: keyword tail"')
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--category", required=True,
                    help="comma-separated search terms that describe the category")
    ap.add_argument("--claims", default="",
                    help="comma-separated phrases the subtitle/description claims as "
                         "differentiators; each is counted across the category")
    a = ap.parse_args()

    pool = {}
    for t in [x.strip() for x in a.category.split(",") if x.strip()]:
        for r in search(t):
            pool[r["trackId"]] = r
        time.sleep(0.35)
    print(f"category pool: {len(pool)} apps\n")

    # ── lengths ──
    for label, value, lim in (("name", a.name, NAME_LIMIT), ("subtitle", a.subtitle, SUBTITLE_LIMIT)):
        if value:
            mark = "OK" if len(value) <= lim else f"OVER by {len(value) - lim}"
            print(f"{label:9s} {len(value):2d}/{lim}  {mark}   {value}")

    # ── a word in both fields buys nothing: Apple indexes them as one pool ──
    if a.subtitle:
        shared = ({w for w in norm(a.name).split() if w not in STOP}
                  & {w for w in norm(a.subtitle).split() if w not in STOP})
        print(f"\nrepeated between name and subtitle: "
              f"{sorted(shared) if shared else 'none — good'}")

    # ── collisions: the whole tail, then each adjacent word pair ──
    tail = a.name.split(":", 1)[1].strip() if ":" in a.name else a.name
    tail_n = norm(tail)
    names = {r["trackId"]: (r.get("trackName") or "") for r in pool.values()}
    print(f"\ntail: {tail!r}")
    exact = [n for n in names.values() if tail_n and tail_n in norm(n)]
    print(f"  exact tail in another listing: {len(exact)}")
    for n in exact[:5]:
        print(f"      ⚠️  {n}")

    words = [w for w in tail_n.split()]
    pairs = [" ".join(words[i:i + 2]) for i in range(len(words) - 1)]
    for p in pairs:
        if all(w in STOP for w in p.split()):
            continue
        hit = [n for n in names.values() if p in norm(n)]
        flag = "⚠️ " if hit else "   "
        print(f"  {flag}'{p}': {len(hit)}" + (f"  ← {', '.join(hit[:2])[:64]}" if hit else ""))

    # ── does the claim differentiate, or is it the category's table stakes? ──
    if a.claims:
        print("\nclaims, counted across the category's descriptions:")
        for c in [x.strip() for x in a.claims.split(",") if x.strip()]:
            rx = re.compile(re.escape(c).replace(r"\ ", r"[\s\-]{0,3}"), re.I)
            n = sum(1 for r in pool.values() if rx.search(r.get("description") or ""))
            verdict = ("differentiates" if n <= 1
                       else "rare, but not unique" if n <= 4
                       else "TABLE STAKES — do not sell on this")
            print(f"  {c!r}: {n}/{len(pool)}  → {verdict}")

    print("\nCollisions and counts are evidence, not a verdict — but do not present a name "
          "whose tail already sits on a live listing.")


if __name__ == "__main__":
    main()
