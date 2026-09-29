#!/usr/bin/env python3
"""A commit message ships with the repo. Check it like one.

    python3 factory/check_commit_message.py --install     # run it on every commit here
    python3 factory/check_commit_message.py --check       # is the hook installed?
    python3 factory/check_commit_message.py --last 20     # sweep messages already written
    python3 factory/check_commit_message.py --range a1b2..HEAD
    python3 factory/check_commit_message.py .git/COMMIT_EDITMSG    # one message file

**Why this exists.** `factory/tests/test_portability.py` scans the files that ship and
asks whether they name the maintainer's machine, sites or products. Git history ships
with those files and was never scanned. On 2026-09-15 a commit body named two private
sites, an app, and three key names out of one of their translation catalogs — caught
because a person read it, which is precisely the thing that check was written to stop
relying on.

**Why `commit-msg` and not `pre-commit`.** `pre-commit` runs before the message exists,
so it cannot see one. `commit-msg` is handed the file and can still refuse, which is the
only moment that is cheap: after the commit is written the fix is a rewrite, and once it
is pushed there is no fix at all.

**What it looks for** — the same three things the portability test asks of a shipped
file, imported from here so the two cannot drift apart:

  machine paths   `~/Developer`, `$HOME/Developer`, `/Users/…`
  fingerprints    a live App Store id, or a URL that is not a vendor's documentation
  product names   the list in `~/.claude/.app-factory/fingerprints.txt`, which lives
                  OUTSIDE the repo on purpose — a list of them inside it would itself
                  be the fingerprint

**When the names list is absent it says so and passes.** A machine that does not have
the list cannot answer the question, and a hook that blocks every commit there is a
hook someone disables. Silence would be worse than either: this prints the reason.

**Escape hatch:** `git commit --no-verify`. The check is a reminder, not a lock — and a
deliberate mention (a public repo of the maintainer's own, say) is a real case.
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# Kept here, imported by factory/tests/test_portability.py. One definition: tightening
# the list in one place and not the other is how a check goes quietly loose.
NEEDLES = ("~/Developer", "$HOME/Developer", "/Users/")

FINGERPRINTS = [
    (r"\bid\d{9,10}\b", "a live App Store id"),
    (r"https?://[^\s`)\]]*\.(?:io|com|app|dev|net)/(?!\s)[^\s`)\]]*", "a live URL"),
]

# URLs that are legitimately named: a vendor's own documentation and endpoints.
ALLOWED = re.compile(
    r"(apple|google|developer|play|github|githubusercontent|sparkle-project|fastlane|"
    r"anthropic|claude|vercel|w3|schema|mozilla|npmjs|python|ruby|indexnow|bing|"
    r"yandex|seznam|example|your-site|your-domain|localhost|jsdelivr|cdnjs|unpkg|"
    r"fonts\.googleapis|gstatic|creativecommons|opensource\.org|semver)", re.I)

NAMES_FILE = os.path.expanduser(
    os.environ.get("APP_FACTORY_FINGERPRINTS") or "~/.claude/.app-factory/fingerprints.txt")

SCISSORS = re.compile(r"^#\s*-+\s*>8\s*-+", re.M)
HOOK_DIR = os.path.join("factory", "hooks")


def product_names():
    """(names, path). An empty list means the file is not there — not that it is clean."""
    if not os.path.isfile(NAMES_FILE):
        return [], NAMES_FILE
    with open(NAMES_FILE, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")], NAMES_FILE


def name_pattern(name):
    """A product name as a word, in any case.

    `_` and `.` count as the edge of a word, because that is how a name reaches a file:
    `\\w` treated `_` as a letter, so `<Name>_preview.mp4` was not a match, and a
    case-sensitive search missed the name's own domain in lower case. Both were in the
    tree while the check reported it clean.
    """
    return re.compile(r"(?<![A-Za-z0-9-])" + re.escape(name) + r"(?![A-Za-z0-9-])", re.I)


def body(text):
    """What git will actually keep: no comment lines, nothing past the scissors.

    `git commit -v` puts the whole diff in the file below that line. Scanning it would
    report the diff's own contents as if they were the message.
    """
    cut = SCISSORS.search(text)
    if cut:
        text = text[:cut.start()]
    return "\n".join(ln for ln in text.splitlines() if not ln.startswith("#"))


def scan(text, names):
    """[(line number, what it is, the matched text)] — line numbers are 1-based."""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for needle in NEEDLES:
            if needle in line:
                hits.append((i, "a path on one particular machine", needle))
        for pattern, what in FINGERPRINTS:
            for m in re.finditer(pattern, line):
                if not ALLOWED.search(m.group(0)):
                    hits.append((i, what, m.group(0)[:60]))
        for n in names:
            if name_pattern(n).search(line):
                hits.append((i, "a product name", n))
    return hits


def report(label, text, names):
    hits = scan(text, names)
    for line, what, sample in hits:
        print(f"  {label}:{line}  {what}: {sample}", file=sys.stderr)
    return hits


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args],
                          capture_output=True, text=True).stdout


# ── installing ────────────────────────────────────────────────────────────────

def hooks_path():
    return git("config", "--get", "core.hooksPath").strip()


def install(indent=""):
    """Point core.hooksPath here. Also called by factory/deploy.py, which sets indent."""
    def say(text):
        print("\n".join(indent + ln for ln in text.splitlines()))

    current = hooks_path()
    if current == HOOK_DIR:
        say(f"already installed — core.hooksPath is {HOOK_DIR}")
        return 0
    if current:
        say(f"core.hooksPath is already {current!r}, set by something else.\n"
            f"Refusing to take it over — add a commit-msg there that runs this file,\n"
            f"or clear it first: git config --unset core.hooksPath")
        return 1
    subprocess.run(["git", "-C", REPO, "config", "core.hooksPath", HOOK_DIR], check=True)
    say(f"installed — core.hooksPath is now {HOOK_DIR}.\n"
        f"It applies to this clone only; git config is not committed, so every clone\n"
        f"runs this once. `--no-verify` still skips it, deliberately.")
    return 0


def uninstall():
    if hooks_path() != HOOK_DIR:
        print("not installed by this script — leaving core.hooksPath alone")
        return 0
    subprocess.run(["git", "-C", REPO, "config", "--unset", "core.hooksPath"], check=True)
    print("removed — commit messages are no longer checked on commit")
    return 0


def installed_check():
    names, path = product_names()
    where = hooks_path()
    ok = where == HOOK_DIR
    print(f"{'✓' if ok else '✗'} hook: "
          + (f"core.hooksPath is {HOOK_DIR}" if ok else
             f"not installed — python3 factory/check_commit_message.py --install"
             + (f" (core.hooksPath is {where!r})" if where else "")))
    print(f"{'✓' if names else '·'} names: "
          + (f"{len(names)} product names from {path}" if names else
             f"no {path} — product names cannot be checked on this machine"))
    return 0 if ok else 1


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Check commit messages for things that should not ship.")
    ap.add_argument("file", nargs="?", help="a commit-message file (what the hook passes)")
    ap.add_argument("--range", dest="rng", help="a git revision range, e.g. main..HEAD")
    ap.add_argument("--last", type=int, metavar="N", help="the last N commit messages")
    ap.add_argument("--install", action="store_true", help="run this on every commit here")
    ap.add_argument("--uninstall", action="store_true", help="stop running it")
    ap.add_argument("--check", action="store_true", help="is it installed? change nothing")
    args = ap.parse_args()

    if args.install:
        return install()
    if args.uninstall:
        return uninstall()
    if args.check:
        return installed_check()

    names, path = product_names()
    if not names:
        print(f"check_commit_message: no {path} — the product names are not derivable, "
              f"so list them there, one per line. Paths and URLs are still checked.",
              file=sys.stderr)

    hits = []
    if args.file:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            hits += report("message", body(fh.read()), names)
    elif args.rng or args.last:
        rev = args.rng or f"-n{args.last}"
        shas = git("log", "--format=%H", rev).split()
        for sha in shas:
            hits += report(sha[:9], body(git("log", "-1", "--format=%B", sha)), names)
        print(f"checked {len(shas)} commit message(s) against "
              f"{len(names)} product name(s).")
    else:
        ap.error("give a message file, --range, or --last (or --install / --check)")

    if hits:
        print(f"\n{len(hits)} thing(s) in this message ship with the repo and should not.\n"
              f"Reword it — keep the evidence, drop the name. If the mention is "
              f"deliberate: git commit --no-verify", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
