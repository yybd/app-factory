#!/usr/bin/env python3
"""Where the cross-repo layer is, from inside the app factory.

The guards, the registry and the anchors live in their own repo now — grove — and this
repo is one of the marketplaces that stands on them. Everything here that needs
`grove_repo` (which resolves a relative root against this machine's tree) has to find
that checkout first, and the answer differs per machine.

Three places are tried, in the order that is right rather than the order that is easy:

1. `$GROVE`, the anchor grove's own deploy writes into `~/.claude/settings.json`.
2. `<base>/cross-repo-guards`, beside this repo — the layout the install instructions
   produce, and the one that works before any deploy has run.
3. The installed plugin copy, which carries `grove_repo.py` and nothing else. Enough to
   resolve a root; not enough to run grove's tools.

Raising is the wrong answer for a checker that might be running on a machine where only
the app skills were installed, so `scripts()` returns None and each caller says what it
cannot do without it.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def root():
    """The grove checkout, or None."""
    env = os.environ.get("GROVE")
    if env and os.path.isdir(os.path.join(env, "tools")):
        return env
    beside = os.path.join(os.path.dirname(REPO), "cross-repo-guards")
    if os.path.isdir(os.path.join(beside, "tools")):
        return beside
    return None


def scripts():
    """The directory holding `grove_repo.py`, or None. The repo first, the copy after."""
    r = root()
    if r:
        p = os.path.join(r, "plugins", "grove", "hooks", "scripts")
        if os.path.isfile(os.path.join(p, "grove_repo.py")):
            return p
    cache = os.path.expanduser("~/.claude/plugins/cache/grove/grove")
    if os.path.isdir(cache):
        for sha in sorted(os.listdir(cache), reverse=True):
            p = os.path.join(cache, sha, "hooks", "scripts")
            if os.path.isfile(os.path.join(p, "grove_repo.py")):
                return p
    return None


def tool(name):
    """Path to one of grove's tools, or None when grove is not a checkout here."""
    r = root()
    p = os.path.join(r, "tools", name) if r else None
    return p if p and os.path.isfile(p) else None


MISSING = ("this needs grove's registry, and grove is not on this machine.\n"
           "  grove is OPTIONAL — it is the multi-repo layer (a registry, guards, anchors).\n"
           "  For one repo you do not need it: set the variable this script asked for\n"
           "  ($KEYS_ROOT, $APP_HUB) in your shell or in ~/.claude/settings.json under `env`,\n"
           "  and enable tracks with `python3 factory/enable.py`.\n"
           "  With many repos: clone https://github.com/yybd/cross-repo-guards beside this\n"
           "  one, or set $GROVE, and run `python3 tools/deploy.py` there.")
