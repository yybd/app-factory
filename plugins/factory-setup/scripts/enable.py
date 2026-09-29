#!/usr/bin/env python3
"""Turn on the right tracks for one repo — without needing grove.

    cd <your app repo>
    python3 <this file>            # look, propose, ask
    python3 <this file> --yes      # take the proposal
    python3 <this file> --tracks apple-track,shared-track
    python3 <this file> --check    # what is on here, change nothing

**Where this file is.** It ships INSIDE the `factory-setup` plugin, so it is on any
machine that installed the marketplace — including one that added it from GitHub,
where the checkout is `~/.claude/plugins/marketplaces/app-factory/` and a reader who
was told to run `factory/enable.py` had no such path to run. `factory/enable.py` in
the checkout is a shim that runs this file. The session hook prints whichever of the
two actually exists.

**Why this exists.** A plugin installed at user scope loads in *every* directory on the
machine, which is how a website session ends up carrying App Store skills. The fix is
per-repo enablement, and Claude Code supports it: `enabledPlugins` in the repo's own
`.claude/settings.json` turns a track on there and nowhere else.

Grove does this from a central registry, which is the right answer for someone with ten
repos. For one app it is two extra installs and a registry to learn, and that is where a
reader following the README gave up — or worse, did not, and ended with a machine where
no skill loaded and nothing said so.

**What it writes.** Only the `@app-factory` keys inside `enabledPlugins`, in this repo's
`.claude/settings.json`. Every other key in that file, and every plugin from another
marketplace, is left exactly as found — the file belongs to the repo, not to this tool.

**What it does not do.** It does not install anything, does not touch the user's global
settings, and does not commit. The file it writes belongs in the repo's own history, and
whether to commit it is the repo's decision.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MARKETPLACE = "app-factory"


def repo():
    """The marketplace checkout — where `plugins/<track>/` can be listed.

    Three places, in the order that is right rather than the order that is easy: two
    directories up (this file inside the checkout's own `plugins/factory-setup/`),
    then where the machine recorded the marketplace, then the plugin cache's own
    parent, which has the tracks but not the repo. Returns None when none of them
    holds `plugins/` — the tool still works, it just cannot list what is shipped.
    """
    up = os.path.dirname(os.path.dirname(HERE))          # …/plugins/factory-setup → …/plugins
    cand = [os.path.dirname(up)]
    try:
        with open(os.path.expanduser("~/.claude/plugins/known_marketplaces.json"),
                  encoding="utf-8") as f:
            entry = json.load(f).get(MARKETPLACE) or {}
        loc = entry.get("installLocation") or (entry.get("source") or {}).get("path")
        if loc:
            cand.append(loc)
    except Exception:
        pass
    for c in cand:
        if c and os.path.isdir(os.path.join(c, "plugins")):
            return c
    return None


REPO = repo()

# What a repo looks like, and what follows. Ordered: the first match that is not
# `capacitor` decides the platform, and the markers are files a project has whether or
# not anyone remembered to describe it.
SIGNS = [
    ("apple-track", ["*.xcodeproj", "*.xcworkspace", "Package.swift", "*.xcodeproj/project.pbxproj"]),
    ("android-track", ["build.gradle", "build.gradle.kts", "settings.gradle",
                       "settings.gradle.kts", "android/build.gradle", "app/build.gradle"]),
    ("capacitor-track", ["capacitor.config.ts", "capacitor.config.js", "capacitor.config.json"]),
    ("web-track", ["astro.config.mjs", "next.config.js", "next.config.mjs", "_config.yml",
                   "index.html", "public/index.html", "src/index.html"]),
]


def looks_like(root):
    """Tracks this repo has evidence for, and the file that is the evidence."""
    import glob
    found = {}
    for track, markers in SIGNS:
        for m in markers:
            # Two levels down, not one: a Capacitor app's Xcode project is at
            # `ios/App/App.xcodeproj`, which is the standard generated layout — and
            # searching one level found the Android half of such a repo and not the
            # Apple half, which is exactly the case this proposal exists for.
            hits = (glob.glob(os.path.join(root, m))
                    or glob.glob(os.path.join(root, "*", m))
                    or glob.glob(os.path.join(root, "*", "*", m)))
            hits = [h for h in hits if "/node_modules/" not in h and "/build/" not in h]
            if hits:
                found[track] = os.path.relpath(sorted(hits, key=len)[0], root)
                break
    return found


def propose(found):
    """The tracks that follow from the evidence, and why each one."""
    tracks, why = [], []
    for t in ("apple-track", "android-track", "capacitor-track"):
        if t in found:
            tracks.append(t)
            why.append(f"{t}: {found[t]}")
    if tracks:
        tracks.append("shared-track")
        why.append("shared-track: the naming, copy, release and price work is the same "
                   "whichever store an app ships to")
    if "web-track" in found and "capacitor-track" in found \
            and os.path.basename(found["web-track"]) == "index.html":
        # The only web evidence is the HTML the native shell loads. That is the app's
        # UI, not a site — and web-track's SEO and analytics skills have nothing to do
        # in it. A real site marker (a framework config) still counts.
        found = dict(found)
        found.pop("web-track")
    if "web-track" in found:
        tracks += ["web-track", "design-track"]
        why.append(f"web-track: {found['web-track']}")
        why.append("design-track: visual craft, which any HTML interface needs")
    elif tracks and "capacitor-track" in found:
        tracks.append("design-track")
        why.append("design-track: a Capacitor app's UI is HTML and CSS")
    return sorted(set(tracks)), why


# The seven this marketplace ships. Read from disk when the checkout is reachable, and
# from this list when it is not — a machine that installed from GitHub has the plugins
# in a cache keyed by version and no `plugins/` directory to walk, and `--tracks` has
# to keep rejecting a typo there too.
KNOWN = ["android-track", "apple-track", "capacitor-track", "design-track",
         "factory-setup", "shared-track", "web-track"]


def shipped():
    import glob
    if not REPO:
        return KNOWN
    found = sorted(os.path.basename(os.path.dirname(os.path.dirname(p)))
                   for p in glob.glob(os.path.join(REPO, "plugins", "*", ".claude-plugin", "plugin.json")))
    return found or KNOWN


def settings_path(root):
    return os.path.join(root, ".claude", "settings.json")


def read(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        sys.exit(f"✗ {path} is not readable JSON ({e}).\n"
                 f"  Fix or move it — this will not overwrite a file it cannot parse.")


def write(path, tracks, current):
    """Only our keys change. Everything else in the file survives byte for byte."""
    enabled = dict(current.get("enabledPlugins") or {})
    for k in [k for k in enabled if k.endswith("@" + MARKETPLACE)]:
        enabled.pop(k)
    for t in tracks:
        enabled[f"{t}@{MARKETPLACE}"] = True
    merged = dict(current)
    if enabled:
        merged["enabledPlugins"] = enabled
    else:
        merged.pop("enabledPlugins", None)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")


def installed(track):
    """Is this track installed on the machine? Enabling names it; installing copies it."""
    try:
        with open(os.path.expanduser("~/.claude/plugins/installed_plugins.json"),
                  encoding="utf-8") as f:
            return f"{track}@{MARKETPLACE}" in (json.load(f).get("plugins") or {})
    except Exception:
        return False


def git_root(start):
    try:
        r = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None if r.returncode == 0 else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="Enable app-factory tracks in one repo.",
                                 epilog="Run it from the repo you want the tracks in.")
    ap.add_argument("--tracks", help="comma-separated, instead of the proposal")
    ap.add_argument("--yes", action="store_true", help="take the proposal without asking")
    ap.add_argument("--check", action="store_true", help="report only, change nothing")
    ap.add_argument("--none", action="store_true", help="turn every track off here")
    ap.add_argument("--repo", help="the repo (default: the working directory's git root)")
    a = ap.parse_args()

    cwd = os.getcwd()
    top = git_root(cwd) or cwd
    if a.repo:
        root = os.path.abspath(a.repo)
    elif os.path.realpath(top) != os.path.realpath(cwd) and looks_like(cwd):
        # A monorepo: the session opens in `apps/mobile/`, which is an app in its own
        # right, and Claude Code reads settings from THERE — the directory the session
        # opened in — not from the git root. Enabling at the root would be writing a
        # file no session in this directory reads; and searching two levels down from
        # the root never reached this app at all, so the answer was "not an app".
        root = cwd
        print(f"(this directory is an app inside a larger repo — enabling here, "
              f"not at {top})")
    else:
        root = top
    path = settings_path(root)
    have = read(path)
    # A key set to `false` is OFF — the hook reads it that way, and so does Claude
    # Code. This used to count keys and not values, so a track a person had switched
    # off was reported as on, by the one tool whose job is to say what is on.
    on = sorted(k.split("@")[0] for k, v in (have.get("enabledPlugins") or {}).items()
                if k.endswith("@" + MARKETPLACE) and v)

    print(f"repo: {root}")
    print(f"  settings: {path}{'' if os.path.isfile(path) else '   (does not exist yet)'}")
    print(f"  tracks on here: {', '.join(on) if on else 'none'}")

    if a.check:
        print()
        if on:
            missing = [t for t in on if not installed(t)]
            if missing:
                print("Enabled here but NOT installed on this machine, so they load nothing:")
                for t in missing:
                    print(f"    claude plugin install {t}@{MARKETPLACE}")
                return 1
            print("✓ every enabled track is installed on this machine.")
        if not on:
            found = looks_like(root)
            want, why = propose(found)
            if want:
                print("No track is enabled here, and this looks like a repo that wants:")
                for w in why:
                    print(f"    {w}")
                print(f"\n  python3 {__file__}")
            else:
                print("No track is enabled here, and nothing suggests one is needed.")
        return 0

    if a.none:
        want, why = [], []
    elif a.tracks:
        want = [t.strip() for t in a.tracks.split(",") if t.strip()]
        why = ["asked for explicitly"]
        unknown = [t for t in want if t not in shipped()]
        if unknown:
            sys.exit(f"✗ not shipped here: {', '.join(unknown)}\n"
                     f"  There is: {', '.join(shipped())}")
    else:
        found = looks_like(root)
        want, why = propose(found)
        if not want:
            print("\nNothing here looks like an app or a site, so there is no proposal.")
            print("  Name the tracks yourself:  --tracks apple-track,shared-track")
            where = os.path.join(REPO, "plugins") if REPO else "<app-factory>/plugins"
            print(f"  Or see what each is for:   {where}/<track>/README.md")
            return 0
        print("\nProposed, from what is in the repo:")
        for w in why:
            print(f"    {w}")

    if want == on and not a.none:
        print("\n✓ already exactly that. Nothing was changed.")
        return 0

    if not (a.yes or a.tracks or a.none):
        me = os.path.relpath(__file__, os.getcwd())
        me = __file__ if me.startswith("..") else me       # a path a person can paste
        print(f"\n  python3 {me} --yes      to take it")
        print(f"  python3 {me} --tracks a,b  to choose")
        return 0

    write(path, want, have)
    print(f"\n→ {path}")
    print(f"  {', '.join(want) if want else 'no tracks'}")
    if want:
        todo = [t for t in want if not installed(t)]
        if todo:
            print("\nInstall them once on this machine:")
            if REPO:
                print(f"    claude plugin marketplace add {REPO}")
            for t in todo:
                print(f"    claude plugin install {t}@{MARKETPLACE}")
            if not installed("factory-setup"):
                print(f"    claude plugin install factory-setup@{MARKETPLACE}   "
                      f"# optional: says when a repo has no track on")
            print("\n  If the CLI then says a plugin is \"disabled by default — enable it with\n"
                  "  `claude plugin enable`\", do NOT: that switches it on for every directory\n"
                  "  on the machine. The file above is what enables it, here and only here.")
        else:
            print("\n✓ all of them are already installed on this machine.")
    print("\n**Open a new session in this repo** — skills load at session start, and this\n"
          "changed nothing about the one you are in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
