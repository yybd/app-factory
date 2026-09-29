#!/usr/bin/env python3
"""Say, once, when a repo looks like an app and no track is enabled in it.

This is the only thing in this marketplace that is on everywhere, and that is exactly
what it is for. A track is enabled per repo, which is right — App Store skills have no
business loading in a website. But it produces a failure with no symptom:

    a repo where no track was enabled  looks identical to
    a repo where the skills decided they were not relevant

Both are silence. Grove's own analysis named this and left it open, because the cost of
the alternative — every track on in every directory — is worse. The answer is not to
change the allocation; it is to make the absence audible, once, in the repo where it is
wrong.

**It reports. It changes nothing**, installs nothing, and writes no settings. The repair
is one command, and it is the reader's to run.

**Once per repo, not once per session.** A message that returns every morning is a
message people learn to scroll past, so a repo that has been told is remembered in
`~/.claude/.app-factory/offered/`. Deleting that file asks again.

Fails silent. A hook that raises at session start is worse than a hook that says nothing.
"""
import hashlib
import json
import os
import subprocess
import sys

STATE = os.path.expanduser(
    os.environ.get("APP_FACTORY_OFFER_STATE") or "~/.claude/.app-factory/offered")
MARKETPLACE = "app-factory"

# The same evidence `factory/enable.py` reads. Kept in step by being the same question
# asked the same way — a hook that proposed different tracks from the tool that enables
# them would be worse than no hook.
SIGNS = [
    ("apple-track", ["*.xcodeproj", "*.xcworkspace", "Package.swift"]),
    ("android-track", ["build.gradle", "build.gradle.kts", "settings.gradle",
                       "settings.gradle.kts"]),
    ("capacitor-track", ["capacitor.config.ts", "capacitor.config.js",
                         "capacitor.config.json"]),
]


def looks_like_an_app(root):
    """The markers found, at most two levels down. Empty means: not our business."""
    import glob
    found = {}
    for track, markers in SIGNS:
        for m in markers:
            hits = (glob.glob(os.path.join(root, m))
                    or glob.glob(os.path.join(root, "*", m))
                    or glob.glob(os.path.join(root, "*", "*", m)))
            hits = [h for h in hits if "/node_modules/" not in h]
            if hits:
                found[track] = os.path.relpath(sorted(hits, key=len)[0], root)
                break
    return found


BROKEN = []                                        # settings files that exist and do not parse


def enabled_here(root):
    """Tracks from this marketplace switched on for this repo, at any scope."""
    on = set()
    for rel in (os.path.join(".claude", "settings.json"),
                os.path.join(".claude", "settings.local.json")):
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            # A file that is there and does not parse enables nothing — and looks, from
            # the session, exactly like a repo nobody set up. Say which it is.
            BROKEN.append(p)
            continue
        for k, v in (d.get("enabledPlugins") or {}).items():
            if k.endswith("@" + MARKETPLACE) and v:
                on.add(k.split("@")[0])
    # A track enabled at USER scope loads here too, and telling someone to enable what
    # is already on would be the noise that gets this switched off.
    try:
        with open(os.path.expanduser("~/.claude/settings.json"), encoding="utf-8") as f:
            d = json.load(f)
        for k, v in (d.get("enabledPlugins") or {}).items():
            if k.endswith("@" + MARKETPLACE) and v:
                on.add(k.split("@")[0])
    except Exception:
        pass
    return on


def already_told(root):
    key = hashlib.sha256(os.path.realpath(root).encode()).hexdigest()[:16]
    return os.path.join(STATE, key)


def enable_command():
    """A command that will actually run on THIS machine, or the placeholder.

    The tool ships beside this hook, inside the plugin — so the first candidate is a
    sibling directory of the hooks, which exists wherever this file is running from,
    cache included. The marketplace checkout is the second, for a reader who would
    rather see a path they recognise. The placeholder is the last resort, and printing
    it was the old behaviour in every case.
    """
    beside = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "scripts", "enable.py")
    if os.path.isfile(beside):
        return f"python3 {beside}"
    try:
        with open(os.path.expanduser("~/.claude/plugins/known_marketplaces.json"),
                  encoding="utf-8") as f:
            entry = json.load(f).get(MARKETPLACE) or {}
        loc = entry.get("installLocation") or (entry.get("source") or {}).get("path")
        for rel in (("plugins", "factory-setup", "scripts", "enable.py"),
                    ("factory", "enable.py")):
            if loc and os.path.isfile(os.path.join(loc, *rel)):
                return f"python3 {os.path.join(loc, *rel)}"
    except Exception:
        pass
    return "python3 <app-factory>/factory/enable.py"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    cwd = payload.get("cwd")
    if not cwd or not os.path.isdir(cwd):
        return

    # The repo, because that is what a person enables — but the message names the
    # SESSION's directory too when they differ, since Claude Code reads settings from
    # where the session opened and not from the git root.
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=5)
        root = r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else cwd
    except Exception:
        root = cwd

    # The session's directory first: in a monorepo the app is `apps/mobile/`, three
    # levels below the root, which is one more than the search reaches from there.
    found = looks_like_an_app(cwd) or looks_like_an_app(root)
    if not found:
        return                                     # not an app: nothing to say
    at_root, at_cwd = enabled_here(root), enabled_here(cwd)
    nested = os.path.realpath(root) != os.path.realpath(cwd)
    if at_cwd or (at_root and not nested):
        return                                     # already set up, where it counts
    # Enabled at the git root, session opened below it: Claude Code reads the settings
    # of the directory the session opened in, so the root's file does nothing here.
    # This is the trap the skill documents — and the hook used to be silent in exactly
    # this case, because "enabled anywhere in the repo" read as "set up".
    marker = already_told(cwd if nested else root)
    if os.path.exists(marker):
        return                                     # said once is enough

    try:
        os.makedirs(STATE, exist_ok=True)
        with open(marker, "w", encoding="utf-8") as f:
            f.write(os.path.realpath(root) + "\n")
    except Exception:
        pass                                       # unable to remember: still say it once now

    tracks = sorted(found) + ["shared-track"]
    if at_root and nested:
        lines = [
            f"app-factory tracks are enabled at {root}, but this session opened in "
            f"{cwd} — and settings are read from where the session opens, so none of "
            f"the store skills will load here.",
            "",
            f"  cd {root} && claude          # open the session at the repo root",
            f"  {enable_command()} --yes     # or enable the tracks here as well",
        ]
    else:
        lines = [
            "This repo looks like an app, and no app-factory track is enabled in it — so "
            "none of the store skills will load here.",
            "",
        ]
        lines += [f"  {t:18} {found.get(t, 'the cross-store work: naming, copy, release, prices')}"
                  for t in tracks]
        lines += [
            "",
            f"  {enable_command()} --yes",
            "",
            "Then open a new session: skills load at session start.",
        ]
        if nested:
            lines += ["", f"(Settings are read from where the session opened — {cwd} — not "
                          f"from the git root. Enable it in the directory you actually work in.)"]
    if BROKEN:
        lines += ["", "Also: this settings file exists and is not valid JSON, so it enables "
                      "nothing: " + ", ".join(BROKEN)]
    print(json.dumps({"systemMessage": "\n".join(lines)}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass                                       # fail silent, always
