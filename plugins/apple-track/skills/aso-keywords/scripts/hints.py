#!/usr/bin/env python3
"""App Store autocomplete — the free signal for what people type, and how often.

    hints.py STUDY.json expand  --cc us --seed markdown --seed "writing app" [--alphabet]
    hints.py STUDY.json measure --cc us [--all] [--max-len 30]
    hints.py --cc il --term תזכו                       (one query, printed)

`expand` asks the store's autocomplete for each seed (and, with --alphabet, for
"seed a" … "seed z" — or א … ת for a Hebrew seed) and adds every suggestion to the
study as a candidate. `measure` takes each candidate the agent judged relevant and types
it one letter at a time until the store suggests it — the shorter the prefix and the
higher the position, the more people search it. That is the popularity proxy `score.py`
turns into a number.

**What the signal is, and is not.** Apple returns at most ten terms, in order, with no
score. The order is the signal; nothing here invents a volume. It is the iOS store's
autocomplete — the Mac App Store's is not reachable without a token — so for a Mac app
these are what iPhone users type, which `score.py` labels as such.

Writes only the study file it is given. Each response is cached for a day (aso_core).
"""
import argparse
import datetime
import os
import plistlib
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aso_core import STOREFRONTS, fetch, is_hebrew, load_json, save_json  # noqa: E402

HINTS = ("https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints"
         "?clientApplication=Software&term=")
LATIN = "abcdefghijklmnopqrstuvwxyz"
HEB = "אבגדהוזחטיכלמנסעפצקרשת"
APP_NAME_SEPARATORS = (": ", " - ", " — ", " – ", " | ")


def hints(term, cc):
    """The store's suggestions for what has been typed so far, in its order."""
    front = STOREFRONTS[cc]["front"]
    raw = fetch(HINTS + urllib.parse.quote(term), {"X-Apple-Store-Front": front})
    try:
        data = plistlib.loads(raw.encode("utf-8"))
    except Exception:
        return []
    return [h.get("term", "").strip().lower() for h in data.get("hints", []) if h.get("term")]


def candidates_of(study, cc):
    sf = study.setdefault("storefronts", {}).setdefault(cc, {})
    return sf.setdefault("candidates", {})


def observe(cand, term, typed, pos, today):
    """Record that `term` was suggested at position `pos` after `typed` was typed."""
    h = cand.setdefault("hints", {"obs": []})
    ob = [typed, pos]
    if ob not in h["obs"]:
        h["obs"].append(ob)
    h["date"] = today


def add(cands, term, source, today):
    c = cands.setdefault(term, {"sources": []})
    if source not in c["sources"]:
        c["sources"].append(source)
    # A suggestion shaped "brand: what it does" (or "brand - …") is an app's own name, not a search; the
    # agent decides, but it is marked so nobody packs a competitor's brand by accident.
    if any(sep in term for sep in APP_NAME_SEPARATORS):
        c["looks_like_app_name"] = True
    return c


def expand(study, cc, seeds, alphabet):
    cands, today = candidates_of(study, cc), datetime.date.today().isoformat()
    queries = []
    for seed in seeds:
        seed = seed.strip().lower()
        add(cands, seed, "seed", today)
        queries.append(seed)
        if alphabet:
            letters = HEB if is_hebrew(seed) else LATIN
            queries += [f"{seed} {ch}" for ch in letters]
    for q in queries:
        for pos, term in enumerate(hints(q, cc), 1):
            observe(add(cands, term, "autocomplete", today), term, q, pos, today)
    return len(queries)


def prefix_lengths(length, max_len):
    """Which prefixes to type: every letter at first, where the signal is, then sparser,
    then the whole term. Typing all of a 25-letter phrase letter by letter is 25 requests
    for a difference the proxy cannot use."""
    steps = [n for n in (1, 2, 3, 4, 5, 6, 8, 10, 13, 16, 20) if n < length]
    return [n for n in steps if n <= max_len] + ([length] if length <= max_len else [])


def measure(study, cc, gate, everything, max_len):
    """Type each relevant candidate a letter at a time until the store suggests it."""
    cands, today, asked = candidates_of(study, cc), datetime.date.today().isoformat(), 0
    for term, c in cands.items():
        if not everything and (c.get("relevance") or 0) < gate:
            continue
        if c.get("hints", {}).get("measured") == today:
            continue
        found = False
        for n in prefix_lengths(len(term), max_len):
            typed = term[:n]
            asked += 1
            got = hints(typed, cc)
            if term in got:
                observe(c, term, typed, got.index(term) + 1, today)
                found = True
                break
        c.setdefault("hints", {"obs": []})["measured"] = today
        c["hints"].pop("unsuggested", None)
        if not found and len(term) <= max_len:
            c["hints"]["unsuggested"] = True     # typed in full, never offered: rare search
    return asked


def main():
    ap = argparse.ArgumentParser(description="App Store autocomplete: expand seeds into "
                                 "candidates, or measure how early each is suggested.")
    ap.add_argument("study", nargs="?", help="the study file (keywords.json)")
    ap.add_argument("action", nargs="?", choices=["expand", "measure"])
    ap.add_argument("--cc", default="us", choices=sorted(STOREFRONTS), help="storefront")
    ap.add_argument("--seed", action="append", default=[], help="seed term (repeatable)")
    ap.add_argument("--alphabet", action="store_true", help="also query 'seed a' … 'seed z'")
    ap.add_argument("--all", action="store_true", help="measure every candidate, not only relevant ones")
    ap.add_argument("--max-len", type=int, default=30, help="longest prefix to type when measuring")
    ap.add_argument("--term", help="ask once and print the suggestions")
    a = ap.parse_args()

    if a.term:
        for i, t in enumerate(hints(a.term, a.cc), 1):
            print(f"{i:2}  {t}")
        return
    if not (a.study and a.action):
        ap.error("give a study file and an action, or --term")
    study = load_json(a.study, {"schema": 1})
    if a.action == "expand":
        if not a.seed:
            ap.error("expand needs at least one --seed")
        n = expand(study, a.cc, a.seed, a.alphabet)
    else:
        from aso_core import load_calibration
        n = measure(study, a.cc, load_calibration()["relevance_gate"], a.all, a.max_len)
    save_json(a.study, study)
    print(f"{a.action}: {n} autocomplete queries · {len(candidates_of(study, a.cc))} "
          f"candidates in {a.cc} · {a.study}")


if __name__ == "__main__":
    main()
