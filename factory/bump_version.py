#!/usr/bin/env python3
"""Move the version — in all eight places, and in the one order that works.

    python3 factory/bump_version.py patch      0.1.0 → 0.1.1
    python3 factory/bump_version.py minor      0.1.0 → 0.2.0
    python3 factory/bump_version.py 0.3.0      an exact version
    python3 factory/bump_version.py --check    what the version is, and whether it agrees

**Why a script for eight numbers.** A user gets an update only when the version moves:
`claude plugin update` compares versions, not content, so a release whose version did
not change reaches nobody — measured, on 2026-09-11, as six tracks reporting "already
at the latest version" over a cache that was demonstrably stale. And the version lives
in seven `plugin.json` files plus `marketplace.json`, which have to agree: `ci.py`
fails when they do not, and eight hand edits is how they stop agreeing.

**What it does not do.** It does not commit, does not tag and does not push. It prints
the release procedure, because the steps after the number are the ones that actually
publish — and a script that ran them would be a script that publishes by accident.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def files():
    """Every file that states the version, and the JSON path inside it."""
    out = [(os.path.join(REPO, ".claude-plugin", "marketplace.json"), ("metadata", "version"))]
    for p in sorted(glob.glob(os.path.join(REPO, "plugins", "*", ".claude-plugin", "plugin.json"))):
        out.append((p, ("version",)))
    return out


def read(path, keys):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    for k in keys[:-1]:
        d = d.get(k) or {}
    return d.get(keys[-1])


def write(path, keys, value):
    """Rewrite the one line, so the file's own formatting survives untouched."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    old = read(path, keys)
    pat = re.compile(r'("version"\s*:\s*)"' + re.escape(old) + '"')
    new, n = pat.subn(lambda m: m.group(1) + f'"{value}"', text, count=1)
    if n != 1:
        sys.exit(f"✗ {os.path.relpath(path, REPO)}: could not find the version line to rewrite.")
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)


def current():
    """(version, disagreements). One version across the marketplace, or the reason not."""
    seen = {}
    for path, keys in files():
        v = read(path, keys)
        seen.setdefault(v, []).append(os.path.relpath(path, REPO))
    if len(seen) == 1:
        return next(iter(seen)), []
    return None, [f"{v}: {', '.join(where)}" for v, where in sorted(seen.items(), key=lambda kv: str(kv[0]))]


def next_version(cur, spec):
    m = SEMVER.match(spec)
    if m:
        return spec
    major, minor, patch = (int(x) for x in SEMVER.match(cur).groups())
    if spec == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if spec == "minor":
        return f"{major}.{minor + 1}.0"
    if spec == "major":
        return f"{major + 1}.0.0"
    sys.exit(f"✗ '{spec}' is neither patch/minor/major nor an x.y.z version.")


def changelog_has(version):
    p = os.path.join(REPO, "CHANGELOG.md")
    try:
        text = open(p, encoding="utf-8").read()
    except OSError:
        return None
    return re.search(r"^## +" + re.escape(version) + r"\s*$", text, re.M) is not None


def main():
    ap = argparse.ArgumentParser(description="Move the version everywhere it is written.")
    ap.add_argument("version", nargs="?",
                    help="patch | minor | major | an exact x.y.z")
    ap.add_argument("--check", action="store_true", help="report only, change nothing")
    a = ap.parse_args()

    cur, disagree = current()
    if disagree:
        print("✗ the version is not the same everywhere:")
        for d in disagree:
            print(f"    {d}")
        if not a.version:
            print("\n  Pass an exact version to make them agree:  python3 factory/bump_version.py 0.1.1")
            return 1
        cur = sorted(d.split(":")[0] for d in disagree)[-1]
    else:
        print(f"version: {cur}   (in {len(files())} files, all agreeing)")

    if a.check or not a.version:
        ok = changelog_has(cur)
        if ok is False:
            print(f"·  CHANGELOG.md has no `## {cur}` section — the release it names is unwritten.")
        elif ok:
            print("✓  CHANGELOG.md has a section for it.")
        return 0

    new = next_version(cur, a.version)
    if new == cur:
        print(f"✓ already {new}. Nothing to do.")
        return 0
    for path, keys in files():
        write(path, keys, new)
        print(f"  {cur} → {new}   {os.path.relpath(path, REPO)}")

    print(f"\n{new} is written. What publishes it, in order — none of it done here:")
    print(f"  1. CHANGELOG.md: rename `## Unreleased` to `## {new}`, and open a new Unreleased.")
    print( "  2. python3 factory/ci.py            everything that can be checked without installing")
    print(f'  3. git commit -am "{new}"')
    print(f'  4. git tag -a v{new} -m "{new}"     the tag is how someone finds this release later')
    print( "  5. git push && git push --tags      publishes it; until this, nobody has it")
    print( "  6. python3 factory/deploy.py        this machine's own copies")
    print( "\nA user receives it on their next `claude plugin update` — the version is what")
    print( "makes that command act at all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
