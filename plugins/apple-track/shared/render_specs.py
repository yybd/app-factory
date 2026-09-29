#!/usr/bin/env python3
"""Write Apple's size tables into the reference documents, from the one JSON file.

    python3 render_specs.py            # rewrite the generated blocks
    python3 render_specs.py --check    # are they current? change nothing

A generated block sits between two markers:

    <!-- apple-specs:begin -->
    …written by this script…
    <!-- apple-specs:end -->

Everything outside the markers is the document's own prose and is never touched.

**Why generate rather than maintain.** The same numbers were written out in seven
places, and two of them disagreed about which iPhone family 1290×2796 belongs to. A
disagreement between seven hand-kept tables is not findable by reading — each one looks
right. `--check` runs in CI, so the next time Apple adds a size the failure arrives at a
push rather than at a rejected submission.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from apple_specs import render_markdown                       # noqa: E402

TRACK = os.path.dirname(HERE)
BEGIN = "<!-- apple-specs:begin -->"
END = "<!-- apple-specs:end -->"

# The documents that state Apple's sizes. A document not listed here may still MENTION a
# size in prose; what it must not do is carry a second copy of the table.
TARGETS = [
    "skills/apple-app-store-screenshots/references/apple-sizes.md",
]


def blocks(text):
    return re.search(re.escape(BEGIN) + r"\n(.*?)\n?" + re.escape(END), text, re.S)


# A `1234×5678` or `1234 x 5678` written anywhere in the track. Curated documents may
# quote a subset with guidance around it — what they must not do is quote a size Apple
# does not accept, which is how the 6.7"/6.9" disagreement survived in two tables.
DIMS = re.compile(r"\b(\d{3,4})\s*[×x]\s*(\d{3,4})\b")
# Aspect ratios written with the same separator.
NOT_A_SIZE = {(16, 10), (4, 3), (3, 2)}


def contradictions():
    """[(file, line, w, h)] where a size is written that apple-specs.json does not list."""
    from apple_specs import screenshot_sizes, preview_sizes, load
    d = load()
    known = set(screenshot_sizes()) | set(preview_sizes())
    iap = d.get("iap_review_screenshot", {}).get("min")
    if iap:
        known.add(tuple(iap))
    icon = d.get("icons", {}).get("source")
    if icon:
        known.add(tuple(icon))
    # Dimensions the documents name deliberately and that are NOT store sizes — capture
    # inputs, window geometry, the worked example of a grab that must be padded. Each
    # carries its reason in the JSON, so the exception list is data rather than a
    # growing set of numbers nobody can justify later.
    for entry in d.get("not_store_sizes", {}).get("sizes", []):
        known.add(tuple(entry["size"]))
    out = []
    for base, dirs, names in os.walk(TRACK):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for n in names:
            if not n.endswith((".md", ".py", ".sh", ".rb")):
                continue
            f = os.path.join(base, n)
            if os.path.realpath(f) == os.path.realpath(SPECS_JSON):
                continue
            try:
                text = open(f, encoding="utf-8").read()
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for w, h in DIMS.findall(line):
                    pair = (int(w), int(h))
                    if pair in known or pair in NOT_A_SIZE or pair[::-1] in NOT_A_SIZE:
                        continue
                    out.append((os.path.relpath(f, TRACK), i, pair))
    return out


SPECS_JSON = os.path.join(HERE, "apple-specs.json")


def main():
    ap = argparse.ArgumentParser(description="Render Apple's size tables from apple-specs.json.")
    ap.add_argument("--check", action="store_true", help="report drift, change nothing")
    a = ap.parse_args()

    body = render_markdown()
    stale, missing, ok = [], [], 0
    for rel in TARGETS:
        p = os.path.join(TRACK, rel)
        if not os.path.isfile(p):
            missing.append(rel)
            continue
        t = open(p, encoding="utf-8").read()
        m = blocks(t)
        if not m:
            missing.append(rel + "  (no apple-specs markers)")
            continue
        if m.group(1).strip() == body.strip():
            ok += 1
            continue
        stale.append(rel)
        if not a.check:
            open(p, "w", encoding="utf-8").write(
                t[:m.start(1)] + body.strip() + t[m.end(1):])

    for rel in missing:
        print(f"  ✗ {rel}")
    for rel in stale:
        print(f"  {'✗' if a.check else '→'} {rel}")
    print()
    if missing:
        print(f"{len(missing)} documents cannot be rendered into. Add the markers, or "
              f"remove them from TARGETS.")
        return 1
    if a.check and stale:
        print(f"{len(stale)} generated tables are out of date with apple-specs.json.\n"
              f"  python3 {os.path.relpath(__file__, os.path.dirname(TRACK))}")
        return 1

    bad = contradictions()
    if bad:
        print("Sizes written in this track that apple-specs.json does not list:")
        for rel, line, (w, h) in bad:
            print(f"  ✗ {rel}:{line}  {w}×{h}")
        print("\nEither Apple added it — put it in the JSON — or it is wrong, and a\n"
              "submission with it would be rejected.")
        return 1
    print(f"✓ {ok + len(stale)} generated tables match apple-specs.json."
          if not a.check else f"✓ {ok} generated tables are current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
