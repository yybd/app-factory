#!/usr/bin/env python3
"""Everything that can be checked without installing anything.

    python3 factory/ci.py             run every check; exit non-zero if one fails
    python3 factory/ci.py --metrics   the same, and print the numbers as JSON
    python3 factory/ci.py --record    …and append them to factory/metrics.jsonl

**Why this exists next to `deploy.py`.** Deploy answers "is this machine set up", and
most of what it does is install: it writes each repo's settings from the registry and
refreshes the plugin copies in the cache. None of that is true of a clean checkout on a
build runner, which has no plugins installed and no registry to read. Running deploy
there would report problems that are not problems.

What is left when you remove the machine is what a **push** should be gated on: the
checks that read files, and the tests. That set is this file, and it runs **without
grove** — a runner that has only this repo still gets an answer, and the one check that
genuinely needs grove says out loud that it was skipped.

**It installs nothing and touches no settings.**
"""
import argparse, glob, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HISTORY = os.path.join(HERE, "metrics.jsonl")

CHECKS = [
    ("references", [sys.executable, os.path.join(HERE, "check_references.py")]),
    ("scripts",    [sys.executable, os.path.join(HERE, "check_scripts.py")]),
    # --strict, because the two things it treats as notes by default — a description
    # that never says what the skill is NOT for, and a body with no Boundaries — are
    # exactly how a library this size grows two skills that both claim one job. Every
    # skill satisfies both today; the gate is what keeps the 39th honest.
    ("skills",     [sys.executable, os.path.join(HERE, "check_skills.py"), "--strict"]),
    ("bilingual",  [sys.executable, os.path.join(HERE, "check_bilingual.py")]),
    # Apple's accepted dimensions, in one place. The generated reference table must be
    # current, and no size written anywhere in the track may be one Apple does not
    # accept. Seven copies of these numbers had already produced one disagreement
    # nobody could see, because each copy reads correctly on its own.
    ("apple-specs", [sys.executable, os.path.join(
        REPO, "plugins", "apple-track", "shared", "render_specs.py"), "--check"]),
    # Each track's README is generated from the skills it holds. Every count in this
    # repo has been wrong at least once — Android as 7 when it was 8, the total as 40,
    # 38 and 35 in six documents on one day — and a generated table cannot drift.
    ("track-readmes", [sys.executable, os.path.join(HERE, "render_track_readmes.py"), "--check"]),
]


def tests():
    return [(os.path.basename(p)[:-3], [sys.executable, p])
            for p in sorted(glob.glob(os.path.join(HERE, "tests", "test_*.py")))]


def manifests():
    """Do the two manifests still agree with each other and with the disk?

    A plugin is described twice: in `.claude-plugin/marketplace.json`, which is what a
    catalogue shows, and in its own `plugin.json`, which is **what loads into every
    session that enables it**. Nothing kept them together, and they had already drifted —
    one track's marketplace line had lost a sentence its plugin.json still carried. The
    same class as a stale cache: the text people read and the text that runs, diverging
    quietly.
    """
    import json
    out = []
    mp = os.path.join(REPO, ".claude-plugin", "marketplace.json")
    try:
        m = json.load(open(mp, encoding="utf-8"))
    except Exception as e:
        return [f"marketplace.json could not be read: {e}"]
    listed = set()
    for pl in m.get("plugins", []):
        name = pl.get("name", "?")
        listed.add(name)
        src = os.path.normpath(os.path.join(REPO, pl.get("source", "")))
        pj = os.path.join(src, ".claude-plugin", "plugin.json")
        if not os.path.isfile(pj):
            out.append(f"{name}: listed in the marketplace, no plugin.json at {pl.get('source')}")
            continue
        try:
            d = json.load(open(pj, encoding="utf-8"))
        except Exception as e:
            out.append(f"{name}: plugin.json could not be read: {e}")
            continue
        if d.get("name") != name:
            out.append(f"{name}: its plugin.json calls it '{d.get('name')}'")
        if d.get("description") != pl.get("description"):
            out.append(f"{name}: the marketplace description and plugin.json's have drifted")
    on_disk = {os.path.basename(os.path.dirname(os.path.dirname(p)))
               for p in glob.glob(os.path.join(REPO, "plugins", "*", ".claude-plugin", "plugin.json"))}
    for extra in sorted(on_disk - listed):
        out.append(f"{extra}: a plugin on disk that the marketplace does not list")

    # ONE version across the marketplace. The tracks are not independent — a deliver
    # script runs shared-track's copy measurer, price-sync reads apple-track's credential
    # resolver — so per-track versions would need a compatibility matrix, and a
    # compatibility matrix nobody maintains is worse than no version at all. A user gets
    # an update only when the version moves, so this is also what makes a release a
    # release rather than a silent cache refresh.
    versions = {}
    for pj in sorted(glob.glob(os.path.join(REPO, "plugins", "*", ".claude-plugin", "plugin.json"))):
        try:
            d = json.load(open(pj, encoding="utf-8"))
        except Exception:
            continue
        versions.setdefault(d.get("version"), []).append(d.get("name", "?"))
    if None in versions:
        out.append(f"no version in: {', '.join(sorted(versions[None]))}")
        del versions[None]
    if len(versions) > 1:
        out.append("the tracks are on different versions: "
                   + " · ".join(f"{v} ({', '.join(sorted(n))})" for v, n in sorted(versions.items())))
    mv = (m.get("metadata") or {}).get("version")
    if versions and mv and mv not in versions:
        out.append(f"marketplace.json says {mv}; the plugins say {', '.join(sorted(versions))}")
    return out


def run(argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=600, cwd=REPO)
        return p.returncode, (p.stdout + p.stderr)
    except Exception as e:
        return 1, f"could not run: {e}"


def counted(text):
    return sum(1 for ln in text.splitlines() if ln.startswith(("✓", "✗")))


def measure():
    """What this repo IS, counted from disk — never copied from a document."""
    md = [p for p in glob.glob(os.path.join(REPO, "**", "*.md"), recursive=True)
          if ".git" not in p and "/worktrees/" not in p]
    per_track = {}
    for d in sorted(glob.glob(os.path.join(REPO, "plugins", "*", ".claude-plugin", "plugin.json"))):
        track = os.path.basename(os.path.dirname(os.path.dirname(d)))
        per_track[track] = len(glob.glob(os.path.join(
            REPO, "plugins", track, "skills", "*", "SKILL.md")))
    return {
        "tracks": len(per_track),
        "skills": sum(per_track.values()),
        "skills_per_track": per_track,
        "declared_operations": len(glob.glob(os.path.join(
            REPO, "plugins", "*", "skills", "*", "places.json"))),
        "docs": len(md),
        "doc_pairs": len([p for p in md if p.endswith(".he.md")]),
        "python": len([p for p in glob.glob(os.path.join(REPO, "**", "*.py"), recursive=True)
                       if ".git" not in p and "/worktrees/" not in p]),
    }


def head():
    try:
        p = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return p.stdout.strip() or "?"
    except Exception:
        return "?"


def main():
    ap = argparse.ArgumentParser(description="Every check that needs no installation.")
    ap.add_argument("--metrics", action="store_true", help="print the numbers as JSON")
    ap.add_argument("--record", action="store_true",
                    help="append the numbers to factory/metrics.jsonl")
    a = ap.parse_args()

    failed, checks_run = [], 0
    print("── checks that read files ──")
    for label, argv in CHECKS:
        rc, out = run(argv)
        last = [ln for ln in out.splitlines() if ln.strip()]
        print(f"  {'✓' if rc == 0 else '✗'} {label:<12} {last[-1][:80] if last else ''}")
        if rc != 0:
            failed.append((label, out))

    bad_manifests = manifests()
    print(f"  {'✓' if not bad_manifests else '✗'} {'manifests':<12} "
          + ("the marketplace and every plugin.json agree" if not bad_manifests
             else f"{len(bad_manifests)} disagreements"))
    if bad_manifests:
        failed.append(("manifests", "\n".join("✗ " + b for b in bad_manifests)))

    print("\n── tests ──")
    vacuous = []
    for label, argv in tests():
        rc, out = run(argv)
        n = counted(out)
        checks_run += n
        skipped = sum(1 for ln in out.splitlines() if ln.startswith("· skipped"))
        note = f"{n} checks" + (f", {skipped} skipped" if skipped else "")
        # A test that ran zero checks and exited 0 is not a pass; it is a test that
        # did not happen. On a runner without grove `test_init_hub` skips itself
        # entirely, and it showed as ✓ in every CI run — a gate that never closed.
        # Not a failure (the skip is legitimate and says why), but not a tick either.
        sym = "✓" if rc == 0 and n else ("✗" if rc else "·")
        if rc == 0 and not n:
            vacuous.append(label)
            note += " — NOTHING VERIFIED"
        print(f"  {sym} {label:<24} {note}")
        if rc != 0:
            failed.append((label, out))

    m = measure()
    m["test_checks"] = checks_run
    m["date"] = time.strftime("%Y-%m-%d")
    m["head"] = head()
    m["failed"] = [label for label, _ in failed]
    m["vacuous"] = vacuous

    print(f"\n{m['skills']} skills in {m['tracks']} tracks · "
          f"{m['declared_operations']} operation(s) declare their places · "
          f"{checks_run} checks · {m['doc_pairs']} bilingual pairs of {m['docs']} documents")

    if vacuous:
        print(f"\n· {len(vacuous)} test(s) verified nothing on this machine: "
              f"{', '.join(vacuous)} — green here is not green.")

    if failed:
        # The whole output of whatever failed, not a filtered slice of it. The first CI
        # run reported "3 scripts that would break" and named none of them, because the
        # filter only kept lines starting with ✗ — a gate you cannot act on is a gate
        # someone turns off.
        for label, out in failed:
            print(f"\n── {label} ──")
            for ln in out.splitlines():
                print("  " + ln.rstrip())
        print(f"\n{len(failed)} failed: {', '.join(label for label, _ in failed)}")
    else:
        print("\n✓ everything that can be checked without installing is in place.")

    if a.metrics or a.record:
        print("\n" + json.dumps(m, ensure_ascii=False, sort_keys=True))
    if a.record:
        with open(HISTORY, "a", encoding="utf-8") as f:
            f.write(json.dumps(m, ensure_ascii=False, sort_keys=True) + "\n")
        print(f"appended to {os.path.relpath(HISTORY, REPO)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
