#!/usr/bin/env python3
"""The real search results — who ranks for a term, how strong they are, and where we are.

    serp.py --cc us --platform mac --term "markdown editor" [--app-id 123]   (printed)
    serp.py STUDY.json --cc us [--all]        annotate the study's relevant candidates

The store's own web search page (`apps.apple.com/{cc}/{iphone|mac}/search?term=`) carries
its results as JSON in `<script id="serialized-server-data">`: about a dozen apps, in the
order the store shows them, each with its title, subtitle and rating count. That is the
difficulty data, with no second call. An editorial card can sit among them; it is skipped.

Past the first dozen, our rank comes from the iTunes Search API (`limit=200`), whose order
is close to the store's and not identical — so a rank from there is stored with
`"rank_source": "itunes-search"`, and a rank from the page with `"store-page"`.

**Fragile by nature.** The page is not an API. When its shape changes this prints what it
found instead of guessing; fix `_lockups()` and note it in LESSONS.md.
"""
import argparse
import datetime
import json
import os
import re
import statistics
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aso_core import STOREFRONTS, fetch, load_json, save_json, stem, words  # noqa: E402

PAGE = "https://apps.apple.com/{cc}/{platform}/search?term={q}"
ITUNES = "https://itunes.apple.com/search?term={q}&country={cc}&entity={entity}&limit=200"
LOOKUP = "https://itunes.apple.com/lookup?id={id}&country={cc}"
BY_BUNDLE = "https://itunes.apple.com/lookup?bundleId={bid}&country={cc}&entity={entity}"
DATA = re.compile(r'<script[^>]*id="serialized-server-data"[^>]*>(.*?)</script>', re.S)


def _count(v):
    """The page abbreviates: '497', '2.8K', '1.2M'. Anything else counts as none."""
    s = str(v or "").replace(",", "").strip().upper()
    mult = {"K": 1_000, "M": 1_000_000}.get(s[-1:], 1)
    try:
        return int(float(s[:-1] if mult > 1 else s) * mult)
    except ValueError:
        return 0


def _lockups(page):
    out = []
    for shelf in page.get("shelves", []):
        for item in shelf.get("items", []):
            lk = item.get("lockup") if isinstance(item, dict) else None
            if lk and lk.get("adamId"):
                out.append(lk)
        if out:
            break                     # the first shelf with apps is the result list
    return out


def serp(term, cc, platform="iphone"):
    """[{rank, adam_id, title, subtitle, rating, ratings}] as the store's page orders them."""
    html = fetch(PAGE.format(cc=cc, platform=platform, q=urllib.parse.quote(term)))
    m = DATA.search(html)
    if not m:
        raise RuntimeError("no serialized-server-data on the search page — its shape changed")
    data = json.loads(m.group(1))
    page = (data.get("data") or [{}])[0].get("data", {})
    return [{"rank": i, "adam_id": str(lk["adamId"]), "title": lk.get("title", ""),
             "subtitle": lk.get("subtitle", ""), "rating": lk.get("rating"),
             "ratings": _count(lk.get("ratingCount"))}
            for i, lk in enumerate(_lockups(page), 1)]


def itunes_rank(term, cc, platform, adam_id):
    entity = "macSoftware" if platform == "mac" else "software"
    raw = fetch(ITUNES.format(q=urllib.parse.quote(term), cc=cc, entity=entity), delay=3.0)
    ids = [str(r.get("trackId")) for r in json.loads(raw).get("results", [])]
    return ids.index(str(adam_id)) + 1 if str(adam_id) in ids else None


def app_ratings(adam_id, cc):
    """(rating count, average) of one app in one storefront, from iTunes lookup."""
    raw = fetch(LOOKUP.format(id=adam_id, cc=cc))
    res = json.loads(raw).get("results", [])
    if not res:
        return 0, None
    return res[0].get("userRatingCount") or 0, res[0].get("averageUserRating")


def adam_id_of(bundle_id, cc, platform):
    """Our app's Apple id, from its bundle id — so a study needs nothing App Store Connect knows."""
    entity = "macSoftware" if platform == "mac" else "software"
    res = json.loads(fetch(BY_BUNDLE.format(bid=bundle_id, cc=cc, entity=entity))).get("results", [])
    return str(res[0]["trackId"]) if res else None


def title_has(term, title):
    want = {stem(w) for w in words(term)}
    return bool(want) and want <= {stem(w) for w in words(title)}


def summarize(term, results, adam_id, cc, platform):
    """The difficulty inputs for one term, and where our app stands."""
    others = [r for r in results if r["adam_id"] != str(adam_id)][:10]
    ours = next((r["rank"] for r in results if r["adam_id"] == str(adam_id)), None)
    source = "store-page" if ours else None
    if ours is None and adam_id:
        ours = itunes_rank(term, cc, platform, adam_id)
        source = "itunes-search" if ours else None
    return {
        "date": datetime.date.today().isoformat(),
        "platform": platform,
        "top": [[r["adam_id"], r["title"], r["ratings"]] for r in others],
        "median_ratings": int(statistics.median([r["ratings"] for r in others])) if others else 0,
        "title_matches": sum(1 for r in others if title_has(term, r["title"])),
        "our_rank": ours,
        "rank_source": source,
    }


def annotate(study, cc, gate, everything):
    app = study.get("app") or {}
    adam_id, platform = app.get("adam_id"), app.get("platform", "iphone")
    cands = study.get("storefronts", {}).get(cc, {}).get("candidates", {})
    n = 0
    for term, c in cands.items():
        if not everything and (c.get("relevance") or 0) < gate:
            continue
        c["serp"] = summarize(term, serp(term, cc, platform), adam_id, cc, platform)
        n += 1
    if adam_id:
        count, avg = app_ratings(adam_id, cc)
        app.setdefault("ratings", {})[cc] = [count, avg]
    return n


def main():
    ap = argparse.ArgumentParser(description="Real App Store search results: difficulty "
                                 "inputs and our rank.")
    ap.add_argument("study", nargs="?", help="the study file (keywords.json)")
    ap.add_argument("--cc", default="us", choices=sorted(STOREFRONTS))
    ap.add_argument("--platform", choices=["iphone", "mac"], help="defaults to the study's app")
    ap.add_argument("--term", help="search once and print")
    ap.add_argument("--app-id", help="our app's Apple id, to find our rank")
    ap.add_argument("--bundle-id", help="our app's bundle id; looked up and stored in the study")
    ap.add_argument("--all", action="store_true", help="every candidate, not only relevant ones")
    a = ap.parse_args()

    if a.term:
        res = serp(a.term, a.cc, a.platform or "iphone")
        for r in res:
            mark = "  ← us" if a.app_id and r["adam_id"] == str(a.app_id) else ""
            print(f"{r['rank']:2}  {r['ratings']:>8}  {r['title']} — {r['subtitle']}{mark}")
        if a.app_id:
            s = summarize(a.term, res, a.app_id, a.cc, a.platform or "iphone")
            print(f"our rank: {s['our_rank'] or 'not in the top 200'} ({s['rank_source'] or '—'})")
        return
    if not a.study:
        ap.error("give a study file, or --term")
    study = load_json(a.study)
    if not study:
        ap.error(f"{a.study} does not exist — run hints.py expand first")
    app = study.setdefault("app", {})
    if a.platform:
        app["platform"] = a.platform
    if a.app_id:
        app["adam_id"] = str(a.app_id)
    if a.bundle_id:
        app["bundle_id"] = a.bundle_id
        app["adam_id"] = adam_id_of(a.bundle_id, a.cc, app.get("platform", "iphone"))
        if not app["adam_id"]:
            print(f"{a.bundle_id} is not on the {a.cc} store for {app.get('platform', 'iphone')} — "
                  "ranks will be empty", file=sys.stderr)
    from aso_core import load_calibration
    n = annotate(study, a.cc, load_calibration()["relevance_gate"], a.all)
    save_json(a.study, study)
    print(f"serp: {n} terms searched in {a.cc} · {a.study}")


if __name__ == "__main__":
    main()
