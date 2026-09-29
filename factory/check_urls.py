#!/usr/bin/env python3
"""Do the URLs the stores will read actually resolve?

    python3 factory/check_urls.py            # every URL in the hub's DATA.md
    python3 factory/check_urls.py --slug x   # with {app-slug} substituted for one app

**A dead privacy URL fails App Review.** That is the one hard requirement a website
places on this whole system, and it is checkable in a second — so it is checked here
rather than discovered by a rejection three days later.

**It is not run by `deploy.py`, and that is deliberate.** This is the only thing in the
factory that reaches the network: it is slow by comparison, it fails when you are offline,
and a check that cries wolf on a train is a check people learn to skip. It belongs before
a submission, not after every edit.

What it does NOT judge: whether the page says anything sensible. A 200 with an empty
privacy policy passes here and fails review. This answers "is something there", which is
the half a machine can answer.

A 403 is reported as unknown rather than as failure — anti-bot blocking is not proof of
absence, and reporting it as a fault would be the noise that gets a checker ignored.
"""
import argparse, os, re, sys, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from grove import scripts as _grove_scripts, MISSING as _GROVE_MISSING   # noqa: E402


class _Grove:
    """grove_repo, resolved on first use instead of at import.

    This block used to call `sys.exit()` at module level when grove was not on the
    machine. That is the right answer for a run — this script reads grove's registry
    and cannot work without it — but it is the wrong answer for `--help`, which
    exited the same way. So on a machine with only this repo, the script could not
    even say what it was for, and `check_scripts.py`'s usage check failed on it.

    Deferring costs nothing: the first attribute access happens well after argparse,
    and the message is unchanged.
    """

    _mod = None

    def __getattr__(self, name):
        if _Grove._mod is None:
            s = _grove_scripts()
            if not s:
                sys.exit("\u2717 " + _GROVE_MISSING)
            sys.path.insert(0, s)
            import grove_repo
            _Grove._mod = grove_repo
        return getattr(_Grove._mod, name)


fr = _Grove()

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
URL = re.compile(r"https?://[^\s`<>\"'|)\]]+")
TIMEOUT = 10


def hub_data():
    """The hub's DATA.md, where the studio's URLs are declared. None when there is none.

    $APP_HUB first, then $DEV_ROOT/app-hub, then grove's registry — the same order the
    skills use, so a machine without grove gets the same answer they do.
    """
    root = os.environ.get("APP_HUB")
    root = os.path.expanduser(root) if root else None
    if not root and os.environ.get("DEV_ROOT"):
        root = os.path.join(os.path.expanduser(os.environ["DEV_ROOT"]), "app-hub")
    if not root and _grove_scripts():
        try:
            import json
            with open(fr.registry_path(), encoding="utf-8") as f:
                reg = json.load(f)
        except Exception:
            reg = {}
        entry = (reg.get("projects") or {}).get("app-hub")
        root = fr.resolve_root(entry.get("root") if isinstance(entry, dict) else None or "app-hub")
    p = os.path.join(root, "DATA.md") if root else None
    return p if p and os.path.isfile(p) else None


# The three the stores read. DATA.md also holds API endpoints and a dashboard behind
# auth, and the first version of this checker reported both as failures — which is the
# noise the factory's own rule says gets a checker ignored.
WANTED = re.compile(r"\b(marketing|support|privacy)\b", re.I)


def urls_in(path, slug=None):
    """The store-facing URLs, `{app-slug}` substituted when a slug was given.

    A URL counts when its own line names one of the three, or when it sits under a
    heading that does — so both `- privacy: https://…` and a `## Default URLs` block are
    read, and nothing else is.
    """
    out = []
    under_wanted = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.lstrip().startswith("#"):
                under_wanted = bool(WANTED.search(line)) or "url" in line.lower()
                continue
            if not (under_wanted or WANTED.search(line)):
                continue
            for m in URL.finditer(line):
                u = m.group(0).rstrip(".,;")
                if "{app-slug}" in u or "<" in u:
                    if not slug:
                        continue                 # a template with nothing to fill it
                    u = u.replace("{app-slug}", slug)
                if "<" in u or ">" in u:
                    continue                     # still a placeholder; not a URL yet
                if u not in out:
                    out.append(u)
    return out


def reach(url):
    """(status, detail). A browser UA, because some hosts refuse the default one."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return ("ok", str(r.status))
    except urllib.error.HTTPError as e:
        if e.code in (403, 405, 429):
            # 405: the host refuses HEAD but may serve GET. Neither is proof of absence.
            return ("unknown", f"HTTP {e.code}")
        return ("fail", f"HTTP {e.code}")
    except Exception as e:
        return ("fail", type(e).__name__)


def main():
    ap = argparse.ArgumentParser(description="Do the store-facing URLs resolve?")
    ap.add_argument("--slug", help="substitute this app slug for {app-slug}")
    a = ap.parse_args()

    data = hub_data()
    if not data:
        print("No hub DATA.md to read — nothing to check.")
        print("The URLs the stores read are declared there; see docs/contracts/hub.md.")
        return 0
    urls = urls_in(data, a.slug)
    if not urls:
        print(f"No concrete URLs in {data}.")
        if not a.slug:
            print("Templates with {app-slug} are skipped — pass --slug <app> to fill them in.")
        return 0

    print(f"Checking {len(urls)} URLs from the hub's DATA.md"
          + (f", for slug '{a.slug}'" if a.slug else "") + ":\n")
    bad = 0
    for u in urls:
        state, detail = reach(u)
        mark = {"ok": "✓", "unknown": "?", "fail": "✗"}[state]
        print(f"  {mark} {detail:>10}  {u}")
        bad += state == "fail"
    print()
    if not bad:
        print("✓ everything reachable. A 200 is not a promise the page says anything —")
        print("  read the privacy page yourself before submitting.")
        return 0
    print(f"{bad} URLs do not resolve. A dead privacy URL fails App Review.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
