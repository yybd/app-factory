#!/usr/bin/env python3
"""Where the cross-repo layer is, from inside the app factory.

The guards, the registry and the anchors live in their own repo now — RepoGuards — and this
repo is one of the marketplaces that stands on them. Everything here that needs
`guards_repo` (which resolves a relative root against this machine's tree) has to find
that checkout first, and the answer differs per machine.

Three places are tried, in the order that is right rather than the order that is easy:

1. `$REPO_GUARDS`, the anchor RepoGuards' own deploy writes into `~/.claude/settings.json`
   (`$GROVE` too — the name before RepoGuards 0.2.0, still written for one release).
2. `<base>/repo-guards` beside this repo — the layout the install instructions produce,
   and the one that works before any deploy has run — or `<base>/cross-repo-guards`, the
   directory an older clone has.
3. The installed plugin copy, which carries `guards_repo.py` and nothing else. Enough to
   resolve a root; not enough to run RepoGuards' tools.

Raising is the wrong answer for a checker that might be running on a machine where only
the app skills were installed, so `scripts()` returns None and each caller says what it
cannot do without it.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def root():
    """The RepoGuards checkout, or None."""
    for var in ("REPO_GUARDS", "GROVE"):                     # GROVE: the name before 0.2.0
        env = os.environ.get(var)
        if env and os.path.isdir(os.path.join(env, "tools")):
            return env
    for name in ("repo-guards", "cross-repo-guards"):        # a fresh clone, an older one
        beside = os.path.join(os.path.dirname(REPO), name)
        if os.path.isdir(os.path.join(beside, "tools")):
            return beside
    return None


def scripts():
    """The directory holding `guards_repo.py`, or None. The repo first, the copy after."""
    r = root()
    if r:
        p = os.path.join(r, "plugins", "repo-guards", "hooks", "scripts")
        if os.path.isfile(os.path.join(p, "guards_repo.py")):
            return p
    cache = os.path.expanduser("~/.claude/plugins/cache/repo-guards/repo-guards")
    if os.path.isdir(cache):
        for sha in sorted(os.listdir(cache), reverse=True):
            p = os.path.join(cache, sha, "hooks", "scripts")
            if os.path.isfile(os.path.join(p, "guards_repo.py")):
                return p
    return None


def tool(name):
    """Path to one of RepoGuards' tools, or None when RepoGuards is not a checkout here."""
    r = root()
    p = os.path.join(r, "tools", name) if r else None
    return p if p and os.path.isfile(p) else None


MISSING = ("this needs RepoGuards' registry, and RepoGuards is not on this machine.\n"
           "  RepoGuards is OPTIONAL — it is the multi-repo layer (a registry, guards, anchors).\n"
           "  For one repo you do not need it: set the variable this script asked for\n"
           "  ($KEYS_ROOT, $APP_HUB) in your shell or in ~/.claude/settings.json under `env`,\n"
           "  and enable tracks with `python3 factory/enable.py`.\n"
           "  With many repos: clone https://github.com/yybd/repo-guards beside this\n"
           "  one, or set $REPO_GUARDS, and run `python3 tools/deploy.py` there.")
