"""Branch pipeline for the aso-keywords scripts — the deterministic part, offline.

    python3 factory/tests/test_aso_keywords.py

What is pinned: the units the keyword field is counted in (characters, though Hebrew is two
bytes a letter),
the stems that keep note/notes from both spending bytes, the popularity proxy's ordering
and its cap under Apple's head-term floor, the relevance gate, the packing rules (no word
the name or subtitle carries, a phrase's words in one locale, the limit respected), the
review verdicts, and the DER→JWS signature conversion. Nothing here touches the network:
the sources are Apple's, and a test that depends on them tests Apple.
"""
import json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "plugins", "apple-track", "skills", "aso-keywords", "scripts"))

import aso_core  # noqa: E402
import allocate  # noqa: E402
import review  # noqa: E402
import score  # noqa: E402


def main():
    fails = 0

    def check(ok, label, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'✓' if ok else '✗'} {label}" + (f"   [{detail}]" if detail and not ok else ""))

    cal = aso_core.load_calibration()

    # units
    check(aso_core.units("תזכורת", "bytes") == 12, "Hebrew counts two bytes a letter")
    check(aso_core.units("תזכורת", "characters") == 6, "…and one character a letter")
    check(aso_core.units("notes,todo", "bytes") == 10, "Latin counts one byte a letter")

    # stems
    for a, b in (("notes", "note"), ("diaries", "diary"), ("boxes", "box"),
                 ("תזכורות", "תזכורת"), ("ספרים", "ספר")):
        check(aso_core.stem(a) == aso_core.stem(b), f"{a} and {b} share a stem",
              f"{aso_core.stem(a)} / {aso_core.stem(b)}")
    check(aso_core.stem("class") == "class", "a double s is not a plural")
    check(aso_core.words("Markdown Writer — RTL") == ["markdown", "writer", "rtl"], "words split on punctuation")

    # popularity proxy
    early = {"hints": {"obs": [["ma", 1]]}}
    late = {"hints": {"obs": [["markdown edi", 6]]}}
    p_early, _ = score.popularity("markdown editor", early, cal, None, "iphone")
    p_late, _ = score.popularity("markdown editor", late, cal, None, "iphone")
    check(p_early > p_late, "suggested earlier and higher ⇒ more popular", f"{p_early} vs {p_late}")
    capped, src = score.popularity("markdown editor", early, cal, "Apple Ads week x", "iphone")
    check(capped <= cal["apple"]["absent_cap"] and "head terms" in src,
          "a term Apple's head list lacks is capped under its floor", f"{capped} {src}")
    apple, src = score.popularity("vpn", {"apple": {"pop": 78, "week": "2026-10-11"}}, cal, "x", "iphone")
    check(apple == 7.8 and src.startswith("apple-ads"), "Apple's figure wins where Apple has one")
    none, src = score.popularity("x", {}, cal, None, "iphone")
    check(none == cal["proxy"]["no_signal"] and src == "no signal", "no signal is said, not guessed")
    _, src = score.popularity("markdown editor", early, cal, None, "mac")
    check("Mac" in src, "a Mac app's proxy is labelled as iOS autocomplete")

    # gate and bands
    study = {"app": {"platform": "iphone", "ratings": {"us": [10, 4.5]}},
             "rejected": {"bad fit": "not what we do"},
             "storefronts": {"us": {"candidates": {
                 "markdown editor": {"relevance": 9, "hints": {"obs": [["mar", 2]]}},
                 "habit tracker": {"relevance": 3, "hints": {"obs": [["h", 1]]}},
                 "bad fit": {"relevance": 9},
                 "unjudged": {},
                 "notion": {"relevance": 9, "trademark": True},
                 "rtl notes": {"relevance": 9, "hints": {"unsuggested": True}},
             }}}}
    live = score.score(study, "us", cal)
    c = study["storefronts"]["us"]["candidates"]
    check(sorted(live) == ["markdown editor", "rtl notes"], "only relevant, unrejected, non-trademark terms live", live)
    check(c["habit tracker"]["band"] == "discarded" and "relevance" in c["habit tracker"]["discarded"],
          "relevance below the gate discards however popular")
    check(c["rtl notes"]["band"] == "long tail", "relevant and rare is long tail", c["rtl notes"].get("band"))
    c["markdown editor"]["review"] = {"verdict": "replace", "date": "d", "rank": [None, None]}
    score.score(study, "us", cal)
    check(c["markdown editor"]["band"] == "discarded", "a replaced term leaves the next study")

    # allocation
    study = {"storefronts": {"il": {"candidates": {
        "עורך טקסט": {"band": "core", "priority": 9},
        "תזכורת מים": {"band": "core", "priority": 8},
        "markdown editor": {"band": "core", "priority": 7},
        "writing app": {"band": "long tail", "priority": 5},
    }}}}
    listings = {"he": {"name": "Inkwell", "subtitle": "עורך מרקדאון", "keywords": ""},
                "en-GB": {"name": "Inkwell", "subtitle": "Markdown notes", "keywords": ""}}
    res = allocate.allocate(study, "il", listings, cal, set())
    he, en = res["locales"]["he"]["keywords"].split(","), res["locales"]["en-GB"]["keywords"].split(",")
    check("עורך" not in he and "טקסט" in he, "a word the subtitle has is not repeated", he)
    check("markdown" not in en and "editor" in en, "English goes to the English locale, minus the subtitle's words", en)
    check("app" not in en and "writing" in en, "stop words are not packed", en)
    check(not any(aso_core.is_hebrew(w) for w in en) and all(aso_core.is_hebrew(w) for w in he),
          "Hebrew stays in he, and Latin prefers the Latin locale")
    only_he = {"he": dict(listings["he"], subtitle="Markdown Writer")}
    res = allocate.allocate(study, "il", only_he, cal, set())
    he = res["locales"]["he"]
    check("editor" in he["keywords"].split(",") and "markdown editor (core)" in he["covered"],
          "with no Latin locale, a Latin term goes into the Hebrew one", he)
    big = {"storefronts": {"us": {"candidates": {f"term{i} word{i}": {"band": "core", "priority": 100 - i}
                                                  for i in range(40)}}}}
    res = allocate.allocate(big, "us", {"en-US": {"name": "A", "subtitle": "B", "keywords": ""}}, cal, set())
    check(res["locales"]["en-US"]["used"] <= cal["keyword_limit"], "the field never exceeds the limit",
          res["locales"]["en-US"]["used"])
    check(res["unplaced"], "what does not fit is reported, not dropped silently")
    issues = allocate.check("en-US", {"name": "Notes", "subtitle": "x", "keywords": "note, todo,todo,apps"}, cal)
    text = " ".join(m for _, m in issues)
    check("spaces" in text and "twice" in text and "name or subtitle" in text and "ignored" in text,
          "the hygiene check finds spaces, repeats, name overlap and stop words", text)
    check(cal["keyword_limit_unit"] == "characters", "the limit is counted in characters (verified 2026-10-23)")
    issues = allocate.check("he", {"name": "", "subtitle": "", "keywords": "א" * 84}, cal)
    check(not any(s == "error" for s, _ in issues), "84 Hebrew letters fit — App Store Connect accepted 155 bytes", issues)
    issues = allocate.check("he", {"name": "", "subtitle": "", "keywords": "א" * 101}, cal)
    check(any(s == "error" for s, _ in issues), "101 characters overflow", issues)

    # review verdicts
    check(review.verdict(40, 8) == "keep", "into the top 10 is keep")
    check(review.verdict(60, 25) == "keep", "up into the top 30 is keep")
    check(review.verdict(None, None) == "replace", "nowhere after a cycle is replace")
    check(review.verdict(90, 70) == "watch", "moved, not far, is watch")

    # record → review round trip
    tmp = tempfile.mkdtemp(prefix="aso-test-")
    try:
        os.makedirs(os.path.join(tmp, "ranks"))
        for date, ranks in (("2026-01-01", {"a": [None, None], "b": [50, "store-page"]}),
                            ("2026-02-01", {"a": [5, "store-page"], "b": [120, "itunes-search"]})):
            with open(os.path.join(tmp, "ranks", date + ".json"), "w") as f:
                json.dump({"ranks": {"us": ranks}}, f)
        review.append(tmp, {"type": "experiment", "id": 1, "date": "2026-01-01", "cc": "us",
                            "targets": ["a", "b"], "review_due": "2026-01-29",
                            "baseline": os.path.join(tmp, "ranks", "2026-01-01.json")})
        _, rev = review.review(tmp, None, False)
        got = {r["term"]: r["verdict"] for r in rev["terms"]}
        check(got == {"a": "keep", "b": "replace"}, "a review compares baseline with the latest", got)
    finally:
        shutil.rmtree(tmp)

    # DER → raw r||s
    der = bytes([0x30, 0x45, 0x02, 0x21, 0x00]) + b"\x81" * 32 + bytes([0x02, 0x20]) + b"\x02" * 32
    raw = aso_core.der_to_raw(der)
    check(len(raw) == 64 and raw[:32] == b"\x81" * 32 and raw[32:] == b"\x02" * 32,
          "a DER signature becomes the 64 bytes a JWS carries")

    print(f"\n{'all passed' if not fails else f'{fails} failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
