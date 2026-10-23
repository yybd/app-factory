#!/usr/bin/env python3
"""Take a rank snapshot of an app's tracked terms — the evidence a review compares.

    track.py ASO_DIR [--force] [--key-json …]       ASO_DIR holds keywords.json

Tracked terms: every term the study banded stretch, core or long tail, in each storefront,
plus every target of a recorded experiment. For each, our rank in the store's own results
(or the iTunes Search API past the first dozen, marked as such). With an App Store
Connect key that can read analytics, the snapshot also carries the app's App Store
**search** impressions and page views for the last 28 days.

Writes `ASO_DIR/ranks/YYYY-MM-DD.json`. Weekly is enough — ranks settle over weeks, and a
snapshot is a few dozen requests per storefront — so a snapshot younger than seven days is
returned as it is unless --force. That is what lets the hub's daily stats collector call
`snapshot()` every day.
"""
import argparse
import datetime
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aso_core import load_json, save_json  # noqa: E402
import serp as serp_mod  # noqa: E402

TRACKED = ("stretch", "core", "long tail")


def experiments(aso_dir):
    p = os.path.join(aso_dir, "experiments.jsonl")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def tracked_terms(study, exps):
    out = {}
    for cc, sf in (study.get("storefronts") or {}).items():
        out[cc] = sorted(t for t, c in sf.get("candidates", {}).items() if c.get("band") in TRACKED)
    for e in exps:
        if e.get("type", "experiment") != "experiment":
            continue
        cc = e.get("cc")
        for t in e.get("targets", []):
            if cc and t not in out.setdefault(cc, []):
                out[cc].append(t)
    return out


def snapshots(aso_dir):
    return sorted(glob.glob(os.path.join(aso_dir, "ranks", "*.json")))


def snapshot(aso_dir, force=False, key_json=None, max_age=7):
    """(path, data) of today's snapshot, or of a recent enough one."""
    have = snapshots(aso_dir)
    if have and not force:
        last = os.path.basename(have[-1])[:10]
        if (datetime.date.today() - datetime.date.fromisoformat(last)).days < max_age:
            return have[-1], load_json(have[-1])
    study = load_json(os.path.join(aso_dir, "keywords.json"))
    if not study:
        raise SystemExit(f"no keywords.json in {aso_dir} — run a study first")
    app = study.get("app") or {}
    adam_id, platform = app.get("adam_id"), app.get("platform", "iphone")
    if not adam_id:
        raise SystemExit("the study has no app id — serp.py STUDY --bundle-id … sets it")
    data = {"date": datetime.date.today().isoformat(), "adam_id": adam_id,
            "platform": platform, "ranks": {}, "ratings": {}}
    for cc, terms in tracked_terms(study, experiments(aso_dir)).items():
        data["ranks"][cc] = {}
        for t in terms:
            s = serp_mod.summarize(t, serp_mod.serp(t, cc, platform), adam_id, cc, platform)
            data["ranks"][cc][t] = [s["our_rank"], s["rank_source"]]
        data["ratings"][cc] = list(serp_mod.app_ratings(adam_id, cc))
    data["search"] = search_feedback(adam_id, key_json)
    path = os.path.join(aso_dir, "ranks", data["date"] + ".json")
    save_json(path, data)
    return path, data


def search_feedback(adam_id, key_json):
    """App-level search impressions from App Store Connect, or why there are none."""
    try:
        import asc_analytics as asc_mod
        args = argparse.Namespace(key_json=key_json, key_id=None, issuer=None, p8=None)
        return asc_mod.search(asc_mod.client(args), adam_id, 28)
    except SystemExit as e:                       # the client's errors are messages, not crashes
        return {"error": str(e).splitlines()[0]}
    except Exception as e:
        return {"error": f"{e.__class__.__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser(description="Rank snapshot of an app's tracked terms.")
    ap.add_argument("aso_dir", help="the app's aso/ folder (holds keywords.json)")
    ap.add_argument("--force", action="store_true", help="take one even if a recent one exists")
    ap.add_argument("--key-json", help="App Store Connect key that can read analytics")
    a = ap.parse_args()
    path, data = snapshot(a.aso_dir, a.force, a.key_json)
    print(f"snapshot {path}")
    for cc, ranks in data["ranks"].items():
        top10 = sum(1 for r, _ in ranks.values() if r and r <= 10)
        top100 = sum(1 for r, _ in ranks.values() if r and r <= 100)
        print(f"  {cc}: {len(ranks)} terms · top 10: {top10} · top 100: {top100}")
    s = data.get("search") or {}
    print(f"  search feedback: {s.get('error') or 'from ' + s.get('since', '?')}")


if __name__ == "__main__":
    main()
