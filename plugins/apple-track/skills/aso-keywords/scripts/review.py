#!/usr/bin/env python3
"""Record a listing change as an experiment, and review it when it is due.

    review.py record ASO_DIR --cc il --locale he --field keywords --version 1.3 \\
              --before "…" --after "…" --targets "a,b,c" --hypothesis "…"
    review.py due    ASO_DIR
    review.py review ASO_DIR [--id N] [--apply] [--early]

`record` appends one line to `ASO_DIR/experiments.jsonl` **before the version ships**,
naming the snapshot that is its baseline and a review date 28 days on — ranks take about
four weeks to settle, and a review before that measures noise.

`review` compares the baseline snapshot with the newest one and gives each target term a
verdict:

    keep           in the top 10, or moved into the top 30
    watch          moved, not far enough to call
    replace        not in the top 100 after a full cycle — the bytes are better spent
    conversion     the app is seen more in search and its page is not visited more:
                   that is screenshots or a custom product page, not keywords

With --apply the verdicts go back into keywords.json, where score.py reads them: a
replaced term is discarded from the next study, a kept one is boosted. The review itself
is appended to experiments.jsonl, so the history of what was tried stays in one file.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aso_core import load_json, save_json  # noqa: E402
from track import experiments, snapshots  # noqa: E402

CYCLE_DAYS = 28


def append(aso_dir, record):
    os.makedirs(aso_dir, exist_ok=True)
    with open(os.path.join(aso_dir, "experiments.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def snapshot_on_or_before(aso_dir, date):
    best = None
    for p in snapshots(aso_dir):
        if os.path.basename(p)[:10] <= date:
            best = p
    return best


def verdict(before, after):
    if after and after <= 10:
        return "keep"
    if after and after <= 30 and (not before or after < before):
        return "keep"
    if not after or after > 100:
        return "replace"
    return "watch"


def search_rate(snap):
    """(impressions, page views) from App Store search, summed over territories."""
    s = (snap or {}).get("search") or {}
    imp = views = 0
    for ev in (s.get("search") or {}).values():
        for k, v in ev.items():
            k = k.lower()
            if "impression" in k:
                imp += v
            elif "page view" in k or "pageview" in k:
                views += v
    return imp, views


def review(aso_dir, exp_id, early):
    exps = experiments(aso_dir)
    real = [(i, e) for i, e in enumerate(exps) if e.get("type", "experiment") == "experiment"]
    if not real:
        raise SystemExit("no experiments recorded")
    idx, e = next(((i, x) for i, x in real if x.get("id") == exp_id), real[-1]) if exp_id else real[-1]
    today = datetime.date.today().isoformat()
    if today < e["review_due"] and not early:
        raise SystemExit(f"experiment {e['id']} is due {e['review_due']} — reviewing earlier "
                         "measures noise (--early to do it anyway)")
    base_path = e.get("baseline") or snapshot_on_or_before(aso_dir, e["date"])
    have = snapshots(aso_dir)
    if not base_path or not have or have[-1] == base_path:
        raise SystemExit("need a baseline snapshot and a newer one — run track.py")
    base, now = load_json(base_path), load_json(have[-1])
    cc = e["cc"]
    rows = []
    for t in e["targets"]:
        b = ((base.get("ranks") or {}).get(cc) or {}).get(t, [None])[0]
        n = ((now.get("ranks") or {}).get(cc) or {}).get(t, [None])[0]
        rows.append({"term": t, "before": b, "after": n, "verdict": verdict(b, n)})
    (bi, bv), (ni, nv) = search_rate(base), search_rate(now)
    conversion = None
    if bi and ni and ni >= bi * 1.2 and (nv / ni) < (bv / bi if bi else 0):
        conversion = (f"search impressions {bi} → {ni}, page views per impression "
                      f"{bv / bi:.1%} → {nv / ni:.1%}: seen more, chosen less — screenshots "
                      "or a custom product page, not keywords")
    return e, {"type": "review", "id": e["id"], "date": today, "baseline": os.path.basename(base_path),
               "latest": os.path.basename(have[-1]), "terms": rows, "conversion": conversion,
               "search": {"before": [bi, bv], "after": [ni, nv]}}


def apply(aso_dir, e, rev):
    path = os.path.join(aso_dir, "keywords.json")
    study = load_json(path)
    cands = study["storefronts"][e["cc"]]["candidates"]
    for r in rev["terms"]:
        c = cands.setdefault(r["term"], {"sources": ["experiment"]})
        c["review"] = {"verdict": r["verdict"], "date": rev["date"], "experiment": e["id"],
                       "rank": [r["before"], r["after"]]}
    save_json(path, study)


def main():
    ap = argparse.ArgumentParser(description="Record listing experiments and review them.")
    ap.add_argument("action", choices=["record", "due", "review"])
    ap.add_argument("aso_dir")
    ap.add_argument("--cc")
    ap.add_argument("--locale")
    ap.add_argument("--field", choices=["name", "subtitle", "keywords", "promotional_text",
                                        "screenshots", "cpp"])
    ap.add_argument("--version")
    ap.add_argument("--before", default="")
    ap.add_argument("--after", default="")
    ap.add_argument("--targets", default="", help="comma-separated target terms")
    ap.add_argument("--hypothesis", default="")
    ap.add_argument("--id", type=int, help="which experiment to review (default: the latest)")
    ap.add_argument("--apply", action="store_true", help="write the verdicts into keywords.json")
    ap.add_argument("--early", action="store_true", help="review before the due date")
    a = ap.parse_args()

    if a.action == "record":
        missing = [n for n in ("cc", "locale", "field", "version") if not getattr(a, n)]
        targets = [t.strip().lower() for t in a.targets.split(",") if t.strip()]
        if missing or not targets:
            ap.error(f"record needs --{', --'.join(missing or ['targets'])}")
        today = datetime.date.today()
        exps = experiments(a.aso_dir)
        base = snapshots(a.aso_dir)
        rec = {"type": "experiment", "id": 1 + max([x.get("id", 0) for x in exps] or [0]),
               "date": today.isoformat(), "cc": a.cc, "locale": a.locale, "field": a.field,
               "version": a.version, "before": a.before, "after": a.after, "targets": targets,
               "hypothesis": a.hypothesis,
               "baseline": base[-1] if base else None,
               "review_due": (today + datetime.timedelta(days=CYCLE_DAYS)).isoformat()}
        append(a.aso_dir, rec)
        print(f"experiment {rec['id']} recorded; review due {rec['review_due']}"
              + ("" if base else " — NO baseline snapshot yet: run track.py --force now"))
    elif a.action == "due":
        today = datetime.date.today().isoformat()
        done = {x["id"] for x in experiments(a.aso_dir) if x.get("type") == "review"}
        for x in experiments(a.aso_dir):
            if x.get("type", "experiment") == "experiment" and x["id"] not in done:
                state = "DUE" if x["review_due"] <= today else f"due {x['review_due']}"
                print(f"#{x['id']} {x['date']} {x['cc']}/{x['locale']} {x['field']} v{x['version']}: {state}")
    else:
        e, rev = review(a.aso_dir, a.id, a.early)
        print(f"experiment {e['id']} ({e['cc']}/{e['locale']} {e['field']}, v{e['version']}): "
              f"{rev['baseline']} → {rev['latest']}")
        for r in rev["terms"]:
            print(f"  {r['verdict']:8} {str(r['before'] or '—'):>4} → {str(r['after'] or '—'):>4}  {r['term']}")
        if rev["conversion"]:
            print(f"  conversion: {rev['conversion']}")
        append(a.aso_dir, rev)
        if a.apply:
            apply(a.aso_dir, e, rev)
            print("verdicts written into keywords.json — score.py reads them next run")


if __name__ == "__main__":
    main()
