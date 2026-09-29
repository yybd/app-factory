#!/usr/bin/env python3
"""Every path this repo's own records point at — does it still exist?

The cheap half of staleness. A record is written true and the world moves; nothing
connects the event that invalidated it to the record itself, so nobody looks. Measured
on this machine: seven memories pointed at directories that had been gone for weeks and
not one was marked stale, and a single migration broke 39 script references across two
repos — one of them in an `import`, so the skill could not load at all.

    python3 factory/check_references.py

Most staleness is not mechanically detectable — "the price is 9.99" reads as correct
when it is wrong, and only asking the store settles it. **A path is the exception.**
Either it is there or it is not, and that one question catches the whole class of
breakage that a move produces: the class where the person who caused it was standing
somewhere else.

Deliberately narrow. It checks paths this repo WRITES — skills, declarations, docs — and
says nothing about prose, numbers, or claims. A checker that guessed at those would
report noise, and a noisy checker is one nobody runs.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOME = os.path.expanduser("~")

# A path worth checking is one written as a path: it has a separator or a known
# extension, and it is not a URL, a glob, or a placeholder someone fills in later.
CAND = re.compile(r"`([^`\n]{3,120})`")
# A markdown link target is a path too, and it was invisible here: the candidate pattern
# only ever looked inside backticks. Five broken links survived that blind spot in this
# repo — three of them created the same day, by renaming the files they pointed at.
LINK = re.compile(r"\]\(([^)\s]{3,200})\)")
# `$` used to be here, and removing it is the point of the anchors: a skill that says
# `$APP_HUB/DATA.md` is naming a real file, and skipping it would have taken 102
# references out of this checker's sight on the same day they became portable.
# `${…}` stays skipped — `${CLAUDE_PLUGIN_ROOT}` resolves inside the plugin cache, not here.
SKIP = ("http://", "https://", "<", ">", "*", "{", "|", " ")
EXT = (".py", ".md", ".json", ".js", ".ts", ".html", ".css", ".sh", ".yml", ".toml")
# top-level names in THIS repo — a path starting with one of them is ours to judge
ANCHORS = ("factory", "plugins", "docs", "rules")
# Content matchers, not output: they are looked for INSIDE the documents, and the
# documents are written in both languages. Dropping the Hebrew ones when the tools
# moved to English would have made this checker report paths a Hebrew line already
# says are gone.
GONE = ("no longer exists", "was deleted", "deleted in", "removed in",
        "נמחק", "אינו קיים", "לא קיים")


_IGNORED = {}


def gitignored(path):
    """A path git is told to ignore — a generated file, named on purpose in the docs."""
    if path not in _IGNORED:
        try:
            r = subprocess.run(["git", "-C", REPO, "check-ignore", "-q", path],
                               capture_output=True, timeout=5)
            _IGNORED[path] = r.returncode == 0
        except Exception:
            _IGNORED[path] = False
    return _IGNORED[path]


def looks_like_path(t):
    """Strict on purpose. The first version flagged 258 things, most of which were not
    paths at all — `svh/dvh`, `next/font`, `@astrojs/sitemap`, the URL `/apps`. A
    checker that reports noise is one nobody runs, so the bar is: it must name a FILE
    (a known extension) or a DIRECTORY (a trailing slash). Everything else is prose that
    happens to contain a slash."""
    if any(s in t for s in SKIP) or t.startswith("@"):
        return False
    # A path in the user's own home is per-machine, not this repo's to keep — the same
    # reason an `$ANCHOR` path is reported and never failed on. `~/.claude/CLAUDE.md`
    # exists on a set-up machine and on no build runner, and its absence is not a broken
    # reference; it is an installation that has not happened.
    if t.startswith("~/") or t.startswith("$HOME/"):
        return False
    if "/" not in t or not t.endswith(EXT):
        return False
    # A trailing-slash directory was tried and dropped: `data/`, `media/`, `text/` are
    # conventions these skills TEACH a reader to create, not paths that exist here.
    # Naming a file is the only form specific enough to judge.
    if t.startswith("./") and "/" not in t[2:]:
        # `./capture.sh` — a file the skill tells the reader to CREATE and then run,
        # in their folder, not ours. Same class as `data/`: a bare name in the current
        # directory is an instruction, not a reference.
        return False
    if t.startswith(("~/", "/", "./", "../", "$")) or t.split("/")[0] in ANCHORS:
        return True
    # A relative path naming one of OUR OWN structural directories — `references/x.md`,
    # `scripts/y.py`, `assets/z` — is a reference to a file that should be sitting beside
    # the document, and it is resolved that way below. Without this the bar was "starts
    # with a repo top-level name", so `page-builder/references/checklists/pre-delivery.md`
    # — cited from a skill that is not page-builder, and resolving nowhere — was never
    # even considered a candidate. Two such citations were live, one of them across a
    # plugin boundary no variable can cross.
    return t.split("/")[0] in ("references", "scripts", "assets") or (
        "/references/" in t or "/scripts/" in t or "/assets/" in t)


def resolve(t, origin):
    # `$APP_HUB/DATA.md` is how a skill names a place on a machine it cannot know. The
    # variable is the portable half; expanding it here is what keeps this checker able
    # to answer the only question it asks — is the file still there.
    if t.startswith("$"):
        return expand_anchor(t)
    if t.startswith("~"):
        return os.path.expanduser(t)
    if t.startswith("/"):
        return t
    # normpath, not lstrip: `lstrip("./")` eats the dots off `../` as well, which
    # turned every ../sibling.md into a lookup in the wrong directory and manufactured
    # ten false positives on the first run.
    return os.path.normpath(os.path.join(os.path.dirname(origin), t))


UNSET = []                       # anchors that name a place this machine has not set up
ELSEWHERE = []                   # anchored paths missing in a tree that IS set up
GENERATED = []                   # gitignored paths: made by a run, absent on a clean clone


def anchor_missing(t):
    """The anchor this path stands on, when that place does not exist here.

    A path under `$APP_HUB` is not a broken reference on a machine that has no hub
    yet — it is a reference to something not set up. The first `deploy.py` on a fresh
    clone reported forty of those as failures, which is how a new install looks broken
    on the day it is installed. Counted and named once, never listed as faults.
    """
    if not t.startswith("$"):
        return None
    name = t[1:].split("/", 1)[0].strip("{}")
    base = VARS().get(name)
    return name if (base and not os.path.exists(base)) else None


def expand_anchor(t):
    """`$APP_HUB/x` → the real path here. Unknown variable → a path that cannot exist,
    which is the honest answer: a skill naming a variable nobody defines is broken."""
    name = t[1:].split("/", 1)[0].strip("{}")
    rest = t[1 + len(name):].lstrip("/{}")
    base = VARS().get(name)
    return os.path.join(base, rest) if base else os.path.join("/nonexistent-anchor", t)


_ANCHORS = None


def VARS():
    """One table, defined in grove_repo, shared with deploy. See anchors() there.

    Empty when grove is not on this machine — a build runner has this repo and nothing
    else. Every `$ANCHOR` path then lands in UNSET and is reported rather than failed,
    which is the same answer this checker already gives for an anchor a tree has not
    set up yet. Crashing here would fail the whole check over a variable it cannot know.
    """
    global _ANCHORS
    if _ANCHORS is None:
        _ANCHORS = {}
        try:
            sys.path.insert(0, HERE)
            from grove import scripts as _gs
            g = _gs()
            if g:
                sys.path.insert(0, g)
                import grove_repo as fr
                _ANCHORS = fr.anchors() or {}
        except Exception:
            pass
    return _ANCHORS


def files():
    for root, dirs, names in os.walk(REPO):
        dirs[:] = [d for d in dirs
                   if d not in (".git", "node_modules", "__pycache__", "worktrees")]
        for n in names:
            if n.endswith((".md", ".json")):
                yield os.path.join(root, n)


def _help_only():
    """`--help` must answer, not run. These take no options, so the docstring IS the
    usage — but a script that ignores `-h` and starts a full scan instead teaches you
    that its flags are not to be trusted."""
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__.strip())
        raise SystemExit(0)


def main():
    _help_only()
    broken, checked = [], 0
    for f in files():
        try:
            text = open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        lines = text.splitlines()
        seen = set()
        for m, is_link in ([(x, False) for x in CAND.finditer(text)]
                           + [(x, True) for x in LINK.finditer(text)]):
            t = m.group(1).split("#")[0].strip()
            # A link target needs no slash to be a path: `[x](SKILLS.he.md)` is one, while
            # a backticked bare name is usually prose. That asymmetry is why the two are
            # judged differently.
            if is_link:
                if (not t or t.startswith(("http", "mailto:", "<", "{"))
                        or not t.endswith(EXT)):
                    continue
            elif not looks_like_path(t):
                continue
            if t in seen:
                continue
            # A line that says the path is gone is not a stale record — it is an
            # accurate one about a deletion, and the two docs that cite the reference
            # broken by the skills migration are exactly that. Reporting them for ever
            # is how a checker teaches you to skip its output.
            # The explanation usually follows the citation rather than sharing its
            # line — "this path does not exist" sits under the bullet that names it.
            n = text.count("\n", 0, m.start())
            window = " ".join(lines[n:n + 2])
            if any(w in window for w in GONE):
                continue
            gone_anchor = anchor_missing(t)
            if gone_anchor:
                if gone_anchor not in UNSET:
                    UNSET.append(gone_anchor)
                continue
            seen.add(t)
            p = resolve(t, f)
            # relative-to-repo is the other reading a writer might have meant
            if not os.path.exists(p) and not os.path.exists(os.path.join(REPO, t)):
                # A gitignored path is a GENERATED or machine-local one — the dashboard
                # page, a registry someone symlinked. Absent on a clean clone and
                # present after a run, so neither state is a fault. It used to be
                # skipped silently, which is how `.gitignore` came to promise a
                # `factory/registry.example.json` that has never existed anywhere:
                # ignored meant unexamined. Named now, in its own section, and still
                # never failed on — the same treatment $ANCHOR paths already get.
                if gitignored(os.path.join(REPO, t)):
                    checked += 1
                    if (os.path.relpath(f, REPO), t) not in GENERATED:
                        GENERATED.append((os.path.relpath(f, REPO), t))
                    continue
                checked += 1
                if t.startswith("$"):
                    # A path in ANOTHER repo. This checker keeps THIS repo's records
                    # honest, and it cannot tell "stale" from "not created there yet" —
                    # prices.json is optional, media is written later, a slug folder
                    # appears when its app does. Reported, never failed on: the first
                    # deploy after creating a hub reported one of these as a fault, and
                    # a fresh install that looks broken teaches people to ignore it.
                    ELSEWHERE.append((os.path.relpath(f, REPO), t))
                else:
                    broken.append((os.path.relpath(f, REPO), t))
            else:
                checked += 1

    print(f"Checked {checked} paths that were written as paths.")
    if UNSET:
        print(f"Not checked: paths under ${', $'.join(UNSET)} — "
              f"{'that place is' if len(UNSET) == 1 else 'those places are'} not set up here yet.")
    if ELSEWHERE:
        names = sorted({t.split("/")[0] for _, t in ELSEWHERE})
        print(f"Not found under {', '.join(names)}: {len(ELSEWHERE)} paths — that tree is "
              f"not this repo's to keep, and they may simply not exist there yet.")
    if GENERATED:
        print(f"Generated or machine-local (gitignored), so absent on a clean clone: "
              + ", ".join(sorted({t for _, t in GENERATED})))
    print()
    if not broken:
        print("✓ every path mentioned exists.")
        return 0
    by_file = {}
    for f, t in broken:
        by_file.setdefault(f, []).append(t)
    for f in sorted(by_file):
        print(f"  {f}")
        for t in sorted(set(by_file[f])):
            print(f"      ✗ {t}")
    print(f"\n{len(broken)} references to paths that do not exist.")
    print("Each was right when written. What moved them sat somewhere else, so nobody saw.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
