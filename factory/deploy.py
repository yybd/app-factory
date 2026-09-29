#!/usr/bin/env python3
"""Put what this repo holds onto the machine, in the order that actually works.

Editing the factory changes nothing by itself. A skill, a guard and a hooks.json all
live in a plugin, and a plugin is a COPY in ~/.claude/plugins/cache — so between "I
committed it" and "it is running" there are two steps that nothing performs for you,
and one of them is opening a new session. That gap has already produced the exact
failure it looks like it would: code committed, reported as fixed, and the machine
still running the old copy.

    python3 factory/deploy.py           sync, refresh the copies, verify
    python3 factory/deploy.py --check   report only, change nothing

**This is the maintainer's tool, and it needs grove.** Step 1 reads grove's registry
to decide which repo loads which track, so without that checkout the run stops — which
is correct for the person editing this repo and wrong for anyone else, so: **nobody
installing these skills ever runs this.** They run `claude plugin install`, and
`factory/enable.py` for the per-repo setting. That distinction was in no document, and
the failure message read as "go install grove".

Four steps, in this order, because each one's output is the next one's input:

1. **The registry into the settings files.** Which tracks a repo loads is declared in
   grove's registry and written into each repo's .claude/settings.json. Do this
   first: refreshing a copy before the settings that decide whether it loads at all
   just means doing it twice.

2. **The repo into the installed copies.** Per plugin, and NOT always the same command
   — `claude plugin update` is a no-op once the recorded version equals HEAD, so a
   copy holding content from no commit needs uninstall + install instead. That
   distinction is measured, not guessed, and it already lives in
   warn_stale_plugin_cache.py; this reuses its findings rather than re-deriving them.

3. **The commit-msg hook.** A commit message ships with the repo and is the one thing
   here that no check was reading. `core.hooksPath` is per-clone git config and is not
   committed, so a fresh checkout has it off and nothing says so — which is why it is
   deployed rather than left to a person to remember.

4. **Verify.** The pipelines, and a byte-for-byte comparison of every installed copy
   against this repo.

**Commit first.** `update` copies the working tree but labels it with HEAD, so
deploying uncommitted work puts bytes in the cache under a commit that does not
contain them — and because `update` then sees a matching version, it can never repair
that copy again. The refusal below is not tidiness; it is avoiding a state whose only
exit is a reinstall.

**And it still needs a new session.** Nothing here changes what is already loaded.
"""
import argparse, glob, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import grove as _grove                                         # noqa: E402
SCRIPTS = _grove.scripts()
GROVE = _grove.root()
MARKETPLACE = "app-factory"
# warn_stale_plugin_cache is grove's and answers about grove unless told otherwise. It is
# imported in-process below, so the environment has to say which repo and which
# marketplace BEFORE that import — set after the fact, it compares grove against grove
# and reports "everything matches" about a tree it never looked at.
os.environ.setdefault("GROVE_REPO", REPO)
os.environ.setdefault("GROVE_MARKETPLACE", MARKETPLACE)
INSTALLED = os.path.expanduser("~/.claude/plugins/installed_plugins.json")
CACHE = os.path.expanduser("~/.claude/plugins/cache")
if SCRIPTS:
    sys.path.insert(0, SCRIPTS)


def sh(cmd, timeout=300, env=None):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       cwd=REPO, env=env)
    return p.returncode, (p.stdout + p.stderr).strip()


def dirty_plugin_files():
    """Uncommitted changes under plugins/ — the ones that would deploy mislabelled."""
    rc, out = sh(["git", "-C", REPO, "status", "--porcelain", "--", "plugins"])
    if rc != 0:
        return []
    # Split on the status code rather than slicing three characters off the front:
    # sh() strips the combined output, which eats the leading space of ` M path` and
    # made the first filename come out a character short. A status code never
    # contains a space, so this holds whether or not the line was stripped.
    out_lines = []
    for ln in out.splitlines():
        parts = ln.split(maxsplit=1)
        if len(parts) == 2:
            out_lines.append(parts[1])
    return out_lines


def findings():
    """(lines, error) — what is stale in the installed copies, and the fix for each."""
    try:
        import warn_stale_plugin_cache as stale
        return stale.findings(), None
    except Exception as e:
        return None, str(e)[:200]


def fix_commands(items):
    """The commands the findings prescribe, parsed back out of their own advice.

    The advice text is the single source of which repair each case needs, so reading
    it back beats deciding again here and risking the two disagreeing.
    """
    cmds = []
    for _, line in items:
        for raw in line.splitlines():
            raw = raw.strip()
            if raw.startswith("claude plugin "):
                for part in raw.split("&&"):
                    part = part.strip()
                    if part.startswith("claude plugin "):
                        cmds.append(part.split())
    return cmds


def prune_cache(check):
    """Delete cached plugin versions nothing points at any more.

    Every deploy writes a new <sha> directory beside the old ones and nothing ever
    removes them: seven tracks had accumulated 41 copies, 34 of them dead, before
    anyone noticed. Only the version named in installed_plugins.json is live, and
    only app-factory's tree is touched — another marketplace's cache is not ours.
    """
    try:
        data = json.load(open(INSTALLED, encoding="utf-8"))["plugins"]
    except Exception as e:
        return None, str(e)[:120]
    live = {k.split("@")[0]: os.path.basename(v[0]["installPath"])
            for k, v in data.items() if k.endswith("@" + MARKETPLACE) and v}
    base = os.path.join(CACHE, MARKETPLACE)
    freed = n = 0
    for track in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        tp = os.path.join(base, track)
        if not os.path.isdir(tp):
            continue
        for ver in sorted(os.listdir(tp)):
            vp = os.path.join(tp, ver)
            if not os.path.isdir(vp) or ver == live.get(track):
                continue
            size = sum(os.path.getsize(os.path.join(dp, f))
                       for dp, _, fs in os.walk(vp) for f in fs
                       if os.path.exists(os.path.join(dp, f)))
            n += 1
            freed += size
            if not check:
                shutil.rmtree(vp, ignore_errors=True)
    return (n, freed), None


def main():
    ap = argparse.ArgumentParser(description="Deploy the factory onto this machine.")
    ap.add_argument("--check", action="store_true", help="report only, change nothing")
    ap.add_argument("--dirty", action="store_true",
                    help="deploy uncommitted plugin changes anyway (see the module docstring)")
    a = ap.parse_args()
    problems = 0

    # The registry, the guards and the anchors are grove's. This repo is a marketplace
    # that stands on them, and runs THEIR control plane against its own checkout rather
    # than keeping a second copy — two copies of one answer is how the two drift.
    if not GROVE:
        print("✗ " + _grove.MISSING)
        return 2
    env = dict(os.environ, GROVE_REPO=REPO, GROVE_MARKETPLACE="app-factory",
               GROVE_PLUGINS=os.path.join(REPO, "plugins"))

    print("── 1. the registry → the settings files ──")
    rc, out = sh([sys.executable, _grove.tool("sync_project_settings.py")]
                 + (["--check"] if a.check else []), env=env)
    # Everything except the rows that say "already synced". Printing only the last three
    # lines meant that with 11 registered repos you saw two arbitrary "=" rows, and a
    # `✗ the registry asks for a track that does not exist` line printed above them went
    # unread — which is how the swallowed exit code below stayed invisible.
    rows = [ln for ln in out.splitlines() if ln.strip()]
    shown = [ln for ln in rows if not ln.lstrip().startswith("=")] or rows[-1:]
    print("\n".join("   " + ln for ln in shown))
    # Any non-zero is a problem, in BOTH modes. The old condition added zero whenever
    # --check was on, so `deploy.py --check` printed sync's ✗ and then answered
    # "✓ everything is in place" with exit 0 — reproduced 2026-09-09 with a registry
    # naming a track that does not exist. In check mode drift IS the finding; in write
    # mode sync has already repaired drift, so a non-zero there means it could not.
    if rc != 0:
        problems += 1

    print("\n── 2. the repo → the installed copies ──")
    dirty = dirty_plugin_files()
    if dirty and not a.check and not a.dirty:
        print(f"   ✗ {len(dirty)} uncommitted changes under plugins/:")
        for f in dirty[:5]:
            print(f"       {f}")
        print("   `update` copies the WORKING TREE but tags it with HEAD, so deploying now")
        print("   puts bytes in the cache that are in no commit — and from then on `update`")
        print("   cannot fix the copy, only a reinstall can. Commit first, or --dirty if deliberate.")
        return 1
    if dirty and a.dirty:
        print(f"   ⚠ deploying with {len(dirty)} uncommitted changes — the cache will be tagged"
              f" with HEAD without them in it.")

    items, err = findings()
    if err:
        print(f"   ✗ cannot compare against the cache: {err}")
        problems += 1
    elif not items:
        print("   ✓ every installed copy already matches the repo. Nothing to deploy.")
    else:
        for _, line in items:
            print("   · " + line.splitlines()[0].lstrip("· "))
        cmds = fix_commands(items)
        if a.check:
            print(f"   {len(cmds)} commands needed. To run them:  python3 factory/deploy.py")
            problems += len(items)
        else:
            for cmd in cmds:
                print(f"   → {' '.join(cmd)}")
                rc, out = sh(cmd)
                if rc != 0:
                    print(f"     ✗ {out.splitlines()[-1][:120] if out else 'failed'}")
                    problems += 1
            # `claude plugin update` compares VERSIONS, not content: with plugin.json
            # still at the same version it answers "already at the latest" and copies
            # nothing, while the findings above are byte comparisons and still stand.
            # Measured on 2026-09-11: six tracks "updated", six still stale. Between
            # releases the only refresh that works is a reinstall, so do that for
            # whatever is still stale — and say so, because the fix for a RELEASE is
            # the version bump, not this.
            still, err = findings()
            if still and not err:
                names = sorted({ln.split(":")[0].strip("· ") for _, ln in still
                                for ln in [ln.splitlines()[0]]})
                print(f"   · still stale after update (same version, so update was a no-op): "
                      f"{', '.join(names)} — reinstalling")
                for n in names:
                    spec = f"{n}@{MARKETPLACE}"
                    for cmd in (["claude", "plugin", "uninstall", spec],
                                ["claude", "plugin", "install", spec]):
                        rc, out = sh(cmd)
                        if rc != 0:
                            print(f"     ✗ {' '.join(cmd)}: {out.splitlines()[-1][:120] if out else 'failed'}")
                            problems += 1

    got, err = prune_cache(a.check)
    if err:
        print(f"   ⚠ cleaning old versions failed: {err}")
    elif got and got[0]:
        n, freed = got
        verb = "would remove" if a.check else "removed"
        print(f"   {verb} {n} old versions from the cache ({freed / 1024 / 1024:.1f} MB)")

    print("\n── 3. the commit-msg hook ──")
    import check_commit_message as ccm                         # same directory
    where, (names, names_file) = ccm.hooks_path(), ccm.product_names()
    if where == ccm.HOOK_DIR:
        print(f"   ✓ installed — core.hooksPath is {ccm.HOOK_DIR}")
    elif a.check:
        print("   ✗ not installed — a commit message would go out unchecked")
        print("     python3 factory/check_commit_message.py --install")
        problems += 1
    else:
        problems += ccm.install(indent="   ")
    if not names:
        print(f"   · no {names_file} — the product names are not derivable, so paths and "
              f"URLs are checked here and names are not")

    print("\n── 4. verification ──")
    # Paths this repo's own records point at. Printed whole when it fails: the list is
    # short by design — a checker that reported everything with a slash in it was tried
    # first and found 258 things, most of which were prose.
    rc_ref, out_ref = sh([sys.executable, os.path.join(HERE, "check_references.py")])
    if rc_ref != 0:
        for ln in out_ref.splitlines():
            if ln.strip() and not ln.startswith("Checked "):
                print("   " + ln.rstrip())
        problems += 1
    # The scripts a skill hands to a session had no check of any kind: a typo in
    # publish_aab.py surfaces halfway through a release, not here. Static only —
    # nothing is executed, because executing these is how something ships by accident.
    # Would this work on a second machine? Asked by building one in a tempdir and
    # resolving every registry root against it — not by reading the registry and hoping.
    # The credentials folder is the one thing the shipping skills need that no repo can
    # carry. Reported, never created behind your back: a folder for secrets is something
    # a person decides the place of.
    # The hub is reported only when something actually needs it. For an installation that
    # uses the mechanics alone — the registry, the guards, close.py — there is no hub and
    # no reason to be told about one on every deploy. An app in the registry is what makes
    # it relevant, because every app skill reads it.
    try:
        with open(os.path.join(GROVE, "tools", "registry.json"), encoding="utf-8") as f:
            _reg = json.load(f)
        _has_apps = any(not k.startswith("_") and isinstance(v, dict)
                        for k, v in (_reg.get("apps") or {}).items())
    except Exception:
        _has_apps = False
    if _has_apps:
        rc_hub, out_hub = sh([sys.executable, os.path.join(HERE, "init_hub.py")])
        if rc_hub != 0:
            for ln in out_hub.splitlines():
                print("   " + ln.rstrip())
            problems += 1

    # Same condition as the hub, for the same reason: signing keys and store credentials
    # are what the SHIPPING tracks need. Someone using the mechanics alone — the registry,
    # the guards, close.py — has nothing to sign, and telling them to create a folder for
    # App Store keys on every deploy is how a report becomes noise.
    if _has_apps:
        rc_keys, out_keys = sh([sys.executable, os.path.join(HERE, "init_keys.py")])
        if rc_keys != 0:
            for ln in out_keys.splitlines():
                print("   " + ln.rstrip())
            problems += 1
    # Every test beside this file, not a named one. test_check_ownership had been broken
    # since the logic it calls moved — and nothing noticed, because only one test in this
    # directory was ever run. A suite that is only partly run is a suite that rots.
    for test in sorted(glob.glob(os.path.join(HERE, "tests", "test_*.py"))):
        rc_t, out_t = sh([sys.executable, test])
        if rc_t != 0:
            print(f"   ✗ {os.path.basename(test)}")
            for ln in out_t.splitlines():
                if ln.startswith(("✗", "Traceback", "  File")) or "Error" in ln:
                    print("      " + ln.rstrip()[:110])
            problems += 1
    # Two copies of the same document, edited in different sessions, with nothing that
    # compares them. The pair failures are mechanical and block; the number differences
    # are printed and never do, because only a person can read one.
    rc_bi, out_bi = sh([sys.executable, os.path.join(HERE, "check_bilingual.py")])
    if rc_bi != 0:
        for ln in out_bi.splitlines():
            if ln.strip() and not ln.startswith("Checked "):
                print("   " + ln.rstrip())
        problems += 1
    # A skill's shape is its interface: the description is what decides whether it ever
    # loads, and it is the one thing here that costs every session that enables the track.
    rc_spec, out_spec = sh([sys.executable, os.path.join(
        REPO, "plugins", "apple-track", "shared", "render_specs.py"), "--check"])
    if rc_spec != 0:
        for ln in out_spec.splitlines():
            if ln.strip() and not ln.startswith("✓"):
                print("   " + ln.rstrip())
        problems += 1
    rc_sk, out_sk = sh([sys.executable, os.path.join(HERE, "check_skills.py"), "--strict"])
    if rc_sk != 0:
        for ln in out_sk.splitlines():
            if ln.strip() and not ln.startswith(("Checked ", "Descriptions:", "  largest")):
                print("   " + ln.rstrip())
        problems += 1
    rc_scr, out_scr = sh([sys.executable, os.path.join(HERE, "check_scripts.py")])
    if rc_scr != 0:
        for ln in out_scr.splitlines():
            if ln.strip() and not ln.startswith(("Checked ", "Outside the standard library")):
                print("   " + ln.rstrip())
        problems += 1
    rc, out = sh([sys.executable, _grove.tool("verify_guards.py")], env=env)
    for ln in out.splitlines():
        if ln.startswith(("  ✗", "✗")) or "failed" in ln:
            print("   " + ln.strip())
    print("   " + (out.splitlines()[-1] if out.splitlines() else ""))
    if rc != 0:
        problems += 1

    print()
    if problems:
        print(f"✗ {problems} things are not in place. See above.")
        return 1
    if a.check:
        print("✓ everything is in place.")
        return 0
    print("✓ deployed.  **Open a new session** — skills and hooks load at session start,\n"
          "  and nothing here changed what is already loaded in this one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
