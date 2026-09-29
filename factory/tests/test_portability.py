"""Would these skills work on a second machine?

    python3 factory/tests/test_portability.py

The half of this question that belongs here is the one about the skills. A skill is
**copied to the next machine verbatim and read as instruction**, so a path like
`~/Developer/app-hub` inside one is not a convenience — it is a lie told to whoever
installs it next. `$APP_HUB` is the form that survives, and grove's deploy is what makes
the variable real.

The other half — that a relative root in the registry resolves against the tree's base,
and that the same registry works under a different base — is grove's, and its own
`tools/tests/test_portability.py` asks it by building a second machine in a tempdir.
Asking it twice, in two repos, is how two answers to one question drift apart.
"""
import glob, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
# The three things that must not ship are the same three whether they sit in a skill or
# in a commit message, so they are defined once — in the script the commit-msg hook runs
# — and imported here. Two copies of this list is how one of them goes quietly loose.
sys.path.insert(0, os.path.join(REPO, "factory"))
from check_commit_message import ALLOWED, FINGERPRINTS, NAMES_FILE, NEEDLES, name_pattern
# Every file that ships, not only the ones a person reads. This scanned `.md` and
# `.json` alone, and seven scripts carried `$HOME/Developer/app-hub` as a default
# while the suite reported "no skill names the path of any particular machine" —
# a true sentence about half the tree, read as a claim about all of it.
EXTS = (".md", ".json", ".sh", ".py", ".rb", ".swift", ".yml", ".yaml", ".txt")


def main():
    fails = 0

    def check(ok, label, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'✓' if ok else '✗'} {label}" + (f"   [{detail}]" if detail and not ok else ""))

    print("-- what the skills say, and what their scripts do --")
    offenders, scanned = [], 0
    for f in glob.glob(os.path.join(REPO, "plugins", "**", "*"), recursive=True):
        if not f.endswith(EXTS) or "__pycache__" in f:
            continue
        try:
            txt = open(f, encoding="utf-8").read()
        except Exception:
            continue
        scanned += 1
        for i, line in enumerate(txt.splitlines(), 1):
            for needle in NEEDLES:
                if needle in line:
                    offenders.append((f"{os.path.relpath(f, REPO)}:{i}", needle))
    check(not offenders, f"no shipped file names the path of any particular machine "
                         f"({scanned} files in "
                         f"{len(glob.glob(os.path.join(REPO, 'plugins', '*', 'skills', '*')))} skills)",
          "; ".join(f"{f} [{n}]" for f, n in offenders[:4])
          + (f" … +{len(offenders) - 4}" if len(offenders) > 4 else ""))

    # A skill is copied to the next machine verbatim, so a product name, a live store
    # id or a real domain inside one is a fingerprint of the studio that wrote it. They
    # are also the class that a sweep declares clean and is not: the 2026-09-11 product
    # plan recorded "fingerprints — zero remain" while eleven were still in shipped text.
    # The lesson from that is not "sweep harder"; it is that a sweep has to be a check
    # that runs, and has to VERIFY IT COMES BACK EMPTY rather than count what it fixed.
    print("\n-- and what they give away about whoever wrote them --")
    # A concrete identifier: a live App Store / Play id, or a bare registrable domain
    # written as one. Names of products are not detectable in general — this is the
    # half a machine can answer, and it is the half that is unambiguous.
    import re as _re
    marks = []
    for f in glob.glob(os.path.join(REPO, "plugins", "**", "*"), recursive=True):
        if not f.endswith((".md", ".json", ".sh", ".py", ".rb", ".swift")) or "__pycache__" in f:
            continue
        try:
            txt = open(f, encoding="utf-8").read()
        except Exception:
            continue
        for i, line in enumerate(txt.splitlines(), 1):
            for pat, what in FINGERPRINTS:
                for m in _re.finditer(pat, line):
                    if ALLOWED.search(m.group(0)):
                        continue
                    marks.append((f"{os.path.relpath(f, REPO)}:{i}", what, m.group(0)[:52]))
    check(not marks, f"no shipped file names a real app or site of whoever wrote it",
          "; ".join(f"{w} [{what}: {g}]" for w, what, g in marks[:4]))

    # The half a machine cannot derive: the NAMES. "Word and Excel apps from one
    # project" and "Pure (Markdown, writers…)" survived every sweep above because a
    # product name in prose has no shape. So the names come from a file OUTSIDE the
    # repo — a list of them inside it would be the fingerprint — one per line, and the
    # check says so out loud when there is none, rather than reporting clean.
    names_file = NAMES_FILE
    if not os.path.isfile(names_file):
        print(f"· skipped — no {names_file}: the product names to look for are not "
              f"derivable, so list them there, one per line")
    else:
        names = [ln.strip() for ln in open(names_file, encoding="utf-8")
                 if ln.strip() and not ln.startswith("#")]
        # Every tracked file, not only `plugins/`: `marketplace add` clones the whole
        # repo, and a public repo is read whole. Scoped to `plugins/`, this passed while a
        # decision record under `docs/` named a product's domain.
        import subprocess
        tracked = subprocess.run(["git", "-C", REPO, "ls-files", "-z"], capture_output=True,
                                 text=True).stdout.split("\0")
        pats = [(n, name_pattern(n)) for n in names]
        hits, scanned = [], 0
        for rel in filter(None, tracked):
            try:
                txt = open(os.path.join(REPO, rel), encoding="utf-8").read()
            except Exception:
                continue
            scanned += 1
            for i, line in enumerate(txt.splitlines(), 1):
                for n, pat in pats:
                    if pat.search(line):
                        hits.append((f"{rel}:{i}", n))
        check(scanned and not hits, f"no tracked file names one of the {len(names)} products "
                                    f"listed in {os.path.basename(names_file)} "
                                    f"({scanned} files)",
              "; ".join(f"{w} [{n}]" for w, n in hits[:4])
              + (f" … +{len(hits) - 4}" if len(hits) > 4 else ""))

    # The anchors a skill is allowed to stand on are the ones grove actually writes.
    # A skill saying `$STORE_ROOT` is as unportable as a hardcoded path — it expands to
    # nothing, silently, and the skill reads as if it named a directory.
    print("\n-- and the anchors they stand on --")
    from grove import scripts as grove_scripts
    gs = grove_scripts()
    if not gs:
        # Not a failure: a build runner has a checkout and nothing else, and this half of
        # the test needs grove to say which anchors a deploy actually writes. Skipped
        # loudly, so it cannot quietly stop being checked anywhere.
        print("· skipped — grove is not on this machine, so the anchor list is unknown")
    else:
        sys.path.insert(0, gs)
        import grove_repo as fr
        # The anchors a skill here is entitled to stand on. The live registry's names are
        # added, but they cannot be the whole answer: on a FRESH CLONE the registry holds
        # only examples, so `$APP_HUB` would be reported as invented in exactly the
        # installation where a newcomer runs this first. These six are the contract —
        # written by a deploy on any tree that has them, and documented in the README.
        CONTRACT = {"DEV_ROOT", "GROVE", "APP_FACTORY", "APP_HUB", "SITE", "KEYS_ROOT"}
        known = set(fr.anchors(None) or {}) | CONTRACT
        # Shell variables a skill defines in its own snippet, and the plugin runtime's
        # own. They look identical to an anchor and are not one.
        LOCAL = {"APP", "VAR", "PWD", "HOME", "PATH", "TMPDIR", "USER", "SHELL",
                 "CLAUDE_PLUGIN_ROOT", "CI", "GITHUB_TOKEN",
                 # The app repo the session is working in. Not an anchor — no deploy
                 # writes it and it names no place in the tree; it is how a standalone
                 # (no-hub) run says which repo holds the `fastlane/` that IS the
                 # source of truth, alongside --repo and the working directory.
                 "APP_REPO"}
        # A third category, and the reason this list needed a comment rather than a
        # name: variables the USER or a CI runner sets to point at a credential. An
        # anchor is written by a deploy and names a place in this tree; these name a
        # secret that is deliberately NOT in the tree, and each is documented by the
        # resolver that reads it (`<track>/shared/credentials.py`). Listing them here
        # is what lets the check keep failing on a genuinely invented `$STORE_ROOT`.
        LOCAL |= {"ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_KEY_PATH", "NOTARY_PROFILE",
                  "NOTARY_PASSWORD", "PLAY_SERVICE_ACCOUNT", "ANDROID_KEYSTORE_PROPERTIES",
                  "ANDROID_HOME", "JAVA_HOME", "JAVA_VERSION", "SUFEED_URL", "SPARKLE_PUBKEY",
                  "FRAMESHOT_FONT", "FRAMESHOT_FONT_RTL"}
        import re
        used = set()
        for f in glob.glob(os.path.join(REPO, "plugins", "**", "*.md"), recursive=True):
            try:
                used |= set(re.findall(r"\$\{?([A-Z][A-Z0-9_]{2,})\}?",
                                       open(f, encoding="utf-8").read()))
            except Exception:
                pass
        unknown = sorted(used - known - LOCAL)
        check(not unknown, f"{len(used & known)} anchors used, all of them written by a deploy",
              ", ".join(unknown[:6]))

    print(f"\n{'all checks passed' if not fails else str(fails) + ' failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
