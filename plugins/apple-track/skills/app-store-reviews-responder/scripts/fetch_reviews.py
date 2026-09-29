#!/usr/bin/env python3
"""
fetch_reviews.py — pull App Store customer reviews (public RSS, no auth) and
summarize them, so you can triage and draft responses.

Uses Apple's public customer-reviews RSS feed (no credentials needed). Posting a
developer response is a separate, authenticated step (App Store Connect website
or API) — this script is read-only.

Usage:
    fetch_reviews.py --app-id 1234567890 [--countries us,il,de] [--json]
    fetch_reviews.py --bundle-id com.you.app [--countries us] [--json]

Stdlib only (urllib). Requires network.
"""

import argparse
import json
import re
import sys
import urllib.request
import urllib.parse
from collections import Counter

STOP = set("the a an and or but to of for in on with is are was app this that it "
           "i you my me we they very really just so not no can cant don't dont "
           "would could should have has had get got use using used would will "
           "your their his her its our as at be been being do does did from "
           "more most some any all out up down if then than too also".split())


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "reviews-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def lookup_app_id(bundle_id, country):
    url = f"https://itunes.apple.com/lookup?bundleId={urllib.parse.quote(bundle_id)}&country={country}"
    data = http_json(url)
    results = data.get("results") or []
    if not results:
        return None, None
    return results[0].get("trackId"), results[0].get("trackName")


def fetch_country(app_id, country, max_pages=3):
    out = []
    for page in range(1, max_pages + 1):
        url = (f"https://itunes.apple.com/{country}/rss/customerreviews/"
               f"page={page}/id={app_id}/sortby=mostrecent/json")
        try:
            data = http_json(url)
        except Exception:
            break
        entries = (data.get("feed") or {}).get("entry")
        if not entries:
            break
        if isinstance(entries, dict):
            entries = [entries]
        # first entry on page 1 is the app itself (has im:name but no im:rating)
        for e in entries:
            if "im:rating" not in e:
                continue
            out.append({
                "country": country,
                "author": ((e.get("author") or {}).get("name") or {}).get("label"),
                "rating": int(((e.get("im:rating") or {}).get("label") or "0")),
                "version": ((e.get("im:version") or {}).get("label")),
                "title": (e.get("title") or {}).get("label"),
                "body": (e.get("content") or {}).get("label"),
                "updated": (e.get("updated") or {}).get("label"),
            })
    return out


def themes(reviews):
    words = Counter()
    for r in reviews:
        text = f"{r.get('title','')} {r.get('body','')}".lower()
        for w in re.findall(r"[a-z']{3,}", text):
            if w not in STOP:
                words[w] += 1
    return words.most_common(12)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--app-id")
    g.add_argument("--bundle-id")
    ap.add_argument("--countries", default="us")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    countries = [c.strip() for c in args.countries.split(",") if c.strip()]
    app_id, app_name = args.app_id, None
    if args.bundle_id:
        app_id, app_name = lookup_app_id(args.bundle_id, countries[0])
        if not app_id:
            print(f"❌ no App Store app found for bundle id {args.bundle_id} "
                  f"in '{countries[0]}'. Try another --countries or pass --app-id.")
            sys.exit(1)

    reviews = []
    for c in countries:
        reviews += fetch_country(app_id, c)

    report = {
        "app_id": app_id, "app_name": app_name, "countries": countries,
        "total_reviews_fetched": len(reviews),
        "reviews": reviews,
    }
    if reviews:
        ratings = [r["rating"] for r in reviews if r["rating"]]
        report["average_rating"] = round(sum(ratings) / len(ratings), 2) if ratings else None
        report["distribution"] = {str(s): sum(1 for r in ratings if r == s) for s in range(5, 0, -1)}
        report["negative"] = [r for r in reviews if r["rating"] <= 3]
        report["negative_themes"] = themes(report["negative"])

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False)); return

    print(f"=== Reviews: {app_name or app_id}  (countries: {', '.join(countries)}) ===")
    if not reviews:
        print("No public reviews found (new app, or none in these countries). "
              "Note: the public RSS feed only covers iOS/Mac apps with reviews; "
              "try more --countries.")
        return
    print(f"fetched {len(reviews)} recent reviews · avg {report['average_rating']}★")
    print("distribution: " + "  ".join(f"{s}★:{report['distribution'][s]}" for s in ["5","4","3","2","1"]))
    print(f"\n▶ Negative/neutral (≤3★): {len(report['negative'])}")
    for r in report["negative"][:10]:
        print(f"   [{r['rating']}★ {r['country']} v{r['version']}] {r['title']}")
        print(f"        {(r['body'] or '')[:140]}")
    if report["negative_themes"]:
        print("\n▶ Common terms in negative reviews:")
        print("   " + ", ".join(f"{w}({n})" for w, n in report["negative_themes"]))
    print("\nNext: triage these, draft responses (see references/response-guidelines.md), "
          "and post via App Store Connect (auth required).")


if __name__ == "__main__":
    main()
