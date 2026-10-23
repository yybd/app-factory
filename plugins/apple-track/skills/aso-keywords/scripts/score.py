#!/usr/bin/env python3
"""Score every candidate of a study: popularity, difficulty, chance, priority, band.

    score.py STUDY.json --cc us [--top 40]

Deterministic: the same study and the same calibration.json give the same scores, so a
later run can be compared with this one. It reads what the other scripts stored —
autocomplete observations (hints.py), Apple's popularity when present (apple_ads.py),
the real results (serp.py) — and the **relevance the agent wrote by hand** (1–10, with a
one-line reason). Relevance is a gate, not a weight: below the calibrated gate a term is
discarded however popular it is.

Every number is stored with where it came from (`popularity_source`), and a term with no
signal is scored as having none — never guessed upward.
"""
import argparse
import datetime
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aso_core import STOREFRONTS, load_calibration, load_json, save_json  # noqa: E402


def clamp(x, lo=1.0, hi=10.0):
    return max(lo, min(hi, x))


def popularity(term, c, cal, apple_read, platform):
    """(1–10, source). Apple's figure when Apple has one; the autocomplete proxy otherwise."""
    apple = c.get("apple") or {}
    if apple.get("pop"):
        return round(apple["pop"] / 10, 1), f"apple-ads {apple.get('week', '')}".strip()
    p = cal["proxy"]
    h = c.get("hints") or {}
    best = None
    for typed, pos in h.get("obs", []):
        if term.startswith(typed):
            completion = 1 - len(typed) / max(len(term), 1)
        else:
            completion = p["contained_completion"]
        score = p["completion_weight"] * completion + p["position_weight"] * (11 - pos) / 10
        best = score if best is None else max(best, score)
    if best is not None:
        value, source = 1 + 9 * best, "autocomplete-proxy"
    elif h.get("unsuggested"):
        value, source = p["unsuggested"], "autocomplete-proxy (never suggested)"
    else:
        value, source = p["no_signal"], "no signal"
    if apple_read:
        value = min(value, cal["apple"]["absent_cap"])
        source += f"; not in Apple's head terms ({apple_read})"
    if platform == "mac" and source.startswith("autocomplete"):
        source += "; iOS autocomplete, for a Mac app"
    return round(clamp(value), 1), source


def difficulty(serp, cal):
    if not serp or not serp.get("top"):
        return None
    d = cal["difficulty"]
    by_ratings = 10 * math.log10(serp["median_ratings"] + 1) / math.log10(d["ratings_ceiling"] + 1)
    by_title = 10 * serp["title_matches"] / len(serp["top"])
    return round(clamp(d["ratings_weight"] * by_ratings + d["title_weight"] * by_title), 1)


def chance(serp, our_ratings):
    if not serp or not serp.get("top"):
        return None
    c = clamp(5 + 2.5 * math.log10((our_ratings + 1) / (serp["median_ratings"] + 1)))
    rank = serp.get("our_rank")
    if rank and rank <= 10:
        c = max(c, 8.0)
    elif rank and rank <= 30:
        c = max(c, 6.0)
    return round(c, 1)


def discard_reason(term, c, cal, rejected):
    if term in rejected:
        return f"rejected by the owner: {rejected[term]}"
    if c.get("trademark"):
        return "a competitor's or a trademarked name (Guideline 2.3.7)"
    if c.get("relevance") is None:
        return "relevance not judged yet"
    if c["relevance"] < cal["relevance_gate"]:
        return f"relevance {c['relevance']} < {cal['relevance_gate']}"
    rv = c.get("review") or {}
    if rv.get("verdict") == "replace" and not c.get("retry"):
        return (f"replaced after review {rv.get('date')} (rank {rv.get('rank')}) — "
                "set retry: true to try it again")
    if c.get("looks_like_app_name") and not c.get("not_a_brand"):
        return "looks like an app's name — set not_a_brand: true if it is a real search"
    return None


def score(study, cc, cal):
    sf = study.get("storefronts", {}).get(cc, {})
    cands = sf.get("candidates", {})
    app = study.get("app") or {}
    platform = app.get("platform", "iphone")
    ours = ((app.get("ratings") or {}).get(cc) or [0])[0] or 0
    apple_read = sf.get("apple_read")
    rejected = study.get("rejected", {})
    today = datetime.date.today().isoformat()
    live = []
    for term, c in cands.items():
        c["popularity"], c["popularity_source"] = popularity(term, c, cal, apple_read, platform)
        c["difficulty"] = difficulty(c.get("serp"), cal)
        c["chance"] = chance(c.get("serp"), ours)
        why = discard_reason(term, c, cal, rejected)
        if why:
            c["band"], c["priority"], c["discarded"] = "discarded", 0, why
            continue
        c.pop("discarded", None)
        prio = c["relevance"] * c["popularity"] / (c["difficulty"] or 5.0)
        if (c.get("review") or {}).get("verdict") == "keep":
            prio *= cal["review"]["keep_boost"]   # proven to rank: worth keeping its bytes
        c["priority"] = round(prio, 2)
        c["scored"] = today
        live.append(term)
    band(cands, live, cal["bands"])
    return live


def band(cands, live, b):
    order = sorted(live, key=lambda t: -cands[t]["priority"])
    for t in order:
        cands[t]["band"] = "reserve"
    low_chance = [t for t in live if (cands[t]["chance"] or 5) < b["stretch_chance_below"]]
    for t in sorted(low_chance, key=lambda t: -cands[t]["popularity"])[:b["stretch"]]:
        cands[t]["band"] = "stretch"
    tail = [t for t in order if cands[t]["band"] == "reserve"
            and cands[t]["relevance"] >= b["long_tail_relevance"]
            and cands[t]["popularity"] <= b["long_tail_popularity"]]
    for t in tail[:b["long_tail"]]:
        cands[t]["band"] = "long tail"
    core = [t for t in order if cands[t]["band"] == "reserve"]
    for t in core[:b["core"]]:
        cands[t]["band"] = "core"


def main():
    ap = argparse.ArgumentParser(description="Score a study's candidates: relevance gate, "
                                 "popularity, difficulty, chance, priority, band.")
    ap.add_argument("study", help="the study file (keywords.json)")
    ap.add_argument("--cc", default="us", choices=sorted(STOREFRONTS))
    ap.add_argument("--top", type=int, default=40, help="how many rows to print")
    a = ap.parse_args()
    study = load_json(a.study)
    if not study:
        ap.error(f"{a.study} does not exist")
    cal = load_calibration()
    live = score(study, a.cc, cal)
    save_json(a.study, study)
    cands = study["storefronts"][a.cc]["candidates"]
    rows = sorted(live, key=lambda t: -cands[t]["priority"])[:a.top]
    print(f"{a.cc}: {len(live)} live · {len(cands) - len(live)} discarded · {a.study}\n")
    print(f"{'band':9} {'prio':>5} {'rel':>3} {'pop':>4} {'diff':>4} {'chn':>4} {'rank':>4}  term  [popularity source]")
    for t in rows:
        c = cands[t]
        rank = (c.get("serp") or {}).get("our_rank") or "—"
        print(f"{c['band']:9} {c['priority']:5.2f} {c['relevance']:3} {c['popularity']:4} "
              f"{c['difficulty'] or '—':>4} {c['chance'] or '—':>4} {rank:>4}  {t}  [{c['popularity_source']}]")


if __name__ == "__main__":
    main()
