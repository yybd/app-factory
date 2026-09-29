#!/usr/bin/env python3
"""Does every place that states a price still state the same one?

    python3 verify_prices.py                      # every app
    python3 verify_prices.py --app <slug>         # one
    python3 verify_prices.py --prices <file>      # an explicit prices.json
    python3 verify_prices.py --stores             # also ask App Store Connect

A price is not kept in one place. It is in the store, in the app's own StoreKit
configuration, on the website, and in whatever document the copy was written from — and
**every price bug so far came from copying one of those into another**, never from a
store being wrong. That is what this checks: not "what should the price be", but "do the
places that already claim to know it still agree".

`prices.json` is the authority and the only file allowed to state a price on its own.
Everything else is compared against it.

```json
{
  "_roots": {
    "_comment": "Where the places are. $ANCHORS and ~ are expanded; a relative path is relative to this file.",
    "site": "$SITE",
    "apps": "$DEV_ROOT"
  },
  "apps": {
    "<slug>": {
      "name": "Display Name",
      "store": "9.99",
      "direct": "8.90",
      "asc_app_id": "0000000000",
      "iap_id": "0000000000",
      "repo": "path/to/the/app",
      "site_paths": ["sites/x/page.html"],
      "docs": ["<slug>/profile.md"]
    }
  }
}
```

**What it reports and does not do.** It reads. It never edits a file, never calls a
store's write API, and never changes what a customer pays — that is the owner's
decision and not something done while tidying files. Where a place disagrees it prints
the place, the line and both values.

**Why the store half is optional.** Reading App Store Connect needs a credential and a
network; the document scan needs neither and catches the bugs that actually happen. So
the scan is the default and `--stores` adds the live read on top.

**Providers other than Apple** — a direct-sale platform, a payment processor — are
declared per app and reported as places a person must check, with the value to compare.
Their APIs differ in every way that matters and several have no read endpoint at all,
so a claim to have verified one would be a claim this script cannot keep.
"""
import argparse
import json
import os
import re
import sys

# A price as it appears in text: an optional symbol, digits, and a two-digit decimal
# part — the decimal is required, because a bare integer in prose is a version, a count
# or a year far more often than it is money. Deliberately not anchored to one currency.
#
# The lookarounds reject a longer NUMBER and nothing else. An earlier version used
# `(?![\w.])`, which also rejected a price followed by a full stop — so "$8.90." at the
# end of a sentence was invisible, and a page stating two prices reported one. That is
# the worst possible failure for this script: a silent pass on the file it was pointed at.
PRICE = re.compile(r"(?<![\d.])([$€£₪]?\s?\d{1,4}[.,]\d{2})(?!\d)")


def anchors(text, base):
    """Expand $ANCHORS, ~ and a path relative to prices.json."""
    if not text:
        return None
    p = os.path.expanduser(os.path.expandvars(text))
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


def find_prices_json(explicit=None):
    for c in (explicit,
              os.path.join(os.environ.get("APP_HUB", ""), "prices.json") if os.environ.get("APP_HUB") else None,
              "prices.json"):
        if c and os.path.isfile(os.path.expanduser(c)):
            return os.path.abspath(os.path.expanduser(c))
    return None


# A number shaped like a price is not a price. A CSS threshold, a page size in inches,
# an image's aspect ratio and a scroll margin all match, and a first run over one real
# site produced 23 findings of which none was about money. The repo's own rule is that a
# checker reporting noise is a checker nobody runs — so a match counts only in a PRICE
# CONTEXT: it carries a currency symbol, or its line says it is about paying.
CURRENCY = re.compile(r"[$€£₪]")
PRICE_WORD = re.compile(
    r"\b(price|priced|pricing|cost|costs|buy|purchase|pay|paid|USD|EUR|GBP|ILS|"
    r"one[- ]time|per month|per year|subscription|upgrade|pro version|"
    r"מחיר|עולה|לרכישה|תשלום)\b", re.I)


def numbers_in(path, wanted):
    """[(line_no, text, matched)] where a price appears — in a price context.

    Every match in context is returned, not only the disagreeing ones: the useful
    output is "this line says 12.99 and the price is 9.99", and for that the agreeing
    lines have to be counted too.
    """
    out = []
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return out
    for i, line in enumerate(text.splitlines(), 1):
        priced_line = bool(PRICE_WORD.search(line))
        for m in PRICE.finditer(line):
            raw = m.group(1).strip()
            if not (CURRENCY.search(raw) or priced_line):
                continue
            digits = re.sub(r"[^\d.,]", "", raw).replace(",", ".")
            if not digits or "." not in digits:
                continue                      # a bare integer is a version, a count, a year
            out.append((i, line.strip()[:110], digits))
    return out


def check_app(slug, app, roots, base):
    """[(severity, place, detail)] for one app."""
    found = []
    # `store`/`direct` is the shape a real prices.json already uses; `price`/`direct_price`
    # reads better and is accepted too. Both, because the existing file IS the contract —
    # inventing field names for a format that already has them would mean every existing
    # hub reporting every app as having no price, which is a clean pass on a broken check.
    price = str(app.get("store") or app.get("price") or "").strip()
    direct = str(app.get("direct") or app.get("direct_price") or "").strip()
    if not price:
        return [("skip", slug,
                 "no `store` or `price` in prices.json — nothing to compare against")]
    known = {price, direct} - {""}

    # ── the app's own StoreKit configuration ────────────────────────────────
    repo = anchors(app.get("repo"), roots.get("apps") or base)
    if repo and os.path.isdir(repo):
        for base_dir, dirs, names in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "build", "Pods")]
            for n in names:
                if not n.endswith(".storekit"):
                    continue
                f = os.path.join(base_dir, n)
                try:
                    raw = open(f, encoding="utf-8").read()
                except Exception:
                    continue
                for m in re.finditer(r'"displayPrice"\s*:\s*"([\d.,]+)"', raw):
                    v = m.group(1).replace(",", ".")
                    if v not in known:
                        found.append(("differs", os.path.relpath(f, repo),
                                      f'displayPrice "{v}" — prices.json says {price}'))
                    else:
                        found.append(("ok", os.path.relpath(f, repo), f"displayPrice {v}"))

    # ── the website, and any document the copy is written from ──────────────
    for key, root_key in (("site_paths", "site"), ("docs", "hub")):
        root = roots.get(root_key) or base
        for rel in app.get(key) or []:
            f = anchors(rel, root)
            if not f or not os.path.exists(f):
                found.append(("missing", rel, f"declared in prices.json, not on disk at {f}"))
                continue
            # A declared place may be a page or a DIRECTORY of them — `apps/<slug>/` is a
            # normal thing to write, and treating it as a missing file reported a real
            # directory as gone.
            files = [f] if os.path.isfile(f) else [
                os.path.join(b, n)
                for b, ds, ns in os.walk(f)
                for n in ns if n.endswith((".html", ".md", ".json", ".txt", ".js", ".ts"))]
            hits = [h for one in files for h in numbers_in(one, known)]
            off = [(ln, txt, v) for ln, txt, v in hits if v not in known]
            if not hits:
                found.append(("quiet", rel, "no price-shaped number — nothing to disagree"))
            elif off:
                for ln, txt, v in off[:6]:
                    found.append(("check", f"{rel}:{ln}", f'{v} — "{txt}"'))
            else:
                found.append(("ok", rel, f"{len(hits)} mention(s), all {'/'.join(sorted(known))}"))

    # ── places only a person can close ──────────────────────────────────────
    for prov in app.get("providers") or []:
        found.append(("person", prov.get("name", "provider"),
                      f"set to {prov.get('price', price)} — check at {prov.get('where', 'its dashboard')}"))
    return found


def store_price(app):
    """The live App Store price tier, or a reason it could not be read."""
    shared = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..",
        "apple-track", "shared"))
    if not os.path.isdir(shared):
        return None, "apple-track is not installed, so there is no ASC credential resolver"
    sys.path.insert(0, shared)
    try:
        import credentials as apple
        c = apple.asc_key()
    except Exception as e:
        return None, str(e).splitlines()[0]
    return None, (f"reading the live price needs an App Store Connect call this script does "
                  f"not make; the credential resolves ({c['key_id']}), so a fastlane or "
                  f"spaceship read will work")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prices", help="an explicit prices.json (default: $APP_HUB/prices.json)")
    ap.add_argument("--app", help="one app slug")
    ap.add_argument("--stores", action="store_true", help="also try the live store price")
    a = ap.parse_args()

    path = find_prices_json(a.prices)
    if not path:
        sys.exit("✗ no prices.json. Pass --prices <file>, or set $APP_HUB.\n"
                 "  Its shape is in this script's docstring and in the skill's SKILL.md.")
    base = os.path.dirname(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    roots = {k: anchors(v, base) for k, v in (data.get("_roots") or {}).items()
             if not k.startswith("_")}
    roots.setdefault("hub", base)
    # `site_paths` are relative to the SITE, not to the hub, and a prices.json that
    # predates `_roots` does not say so. The anchors a deploy writes are the right
    # default: without them every site path was resolved against the hub and reported
    # as missing — a true statement about the wrong directory.
    for key, env in (("site", "SITE"), ("apps", "DEV_ROOT")):
        if not roots.get(key) and os.environ.get(env):
            roots[key] = os.path.expanduser(os.environ[env])
    apps = {k: v for k, v in (data.get("apps") or {}).items() if not k.startswith("_")}
    if a.app:
        if a.app not in apps:
            sys.exit(f"✗ no app '{a.app}' in {path}. There is: {', '.join(sorted(apps))}")
        apps = {a.app: apps[a.app]}

    print(f"prices: {path}")
    for k, v in sorted(roots.items()):
        print(f"  {k}: {v}{'' if v and os.path.isdir(v) else '   (not on this machine)'}")
    print()

    disagree = 0
    for slug, app in sorted(apps.items()):
        rows = check_app(slug, app, roots, base)
        bad = [r for r in rows if r[0] in ("differs", "check", "missing")]
        disagree += len(bad)
        mark = "✗" if bad else "✓"
        shown = app.get("store") or app.get("price") or "—"
        direct_shown = app.get("direct") or app.get("direct_price")
        print(f"{mark} {slug}  ({shown}"
              + (f" · direct {direct_shown}" if direct_shown else "") + ")")
        for sev, place, detail in rows:
            sym = {"ok": "  ok   ", "differs": "  DIFF ", "check": "  CHECK",
                   "missing": "  GONE ", "quiet": "  ·    ", "person": "  →    ",
                   "skip": "  ·    "}[sev]
            print(f"{sym} {place}: {detail}")
        if a.stores:
            _, why = store_price(app)
            print(f"  →     App Store: {why}")
        print()

    if disagree:
        print(f"{disagree} place(s) to look at.\n"
              "Not every one is wrong: a competitor's price, a historical note, and a caption\n"
              "describing an image all state a number that must NOT change. Read each.")
        return 1
    print("✓ every declared place agrees with prices.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
