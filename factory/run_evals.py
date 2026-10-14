#!/usr/bin/env python3
"""Run a track's eval suite — on a copy, because the track itself would not load.

    python3 factory/run_evals.py                      # every track that has evals/
    python3 factory/run_evals.py apple-track          # one
    python3 factory/run_evals.py apple-track --runs 1 --case 'compliance-*'

Anything after the track names goes to `claude plugin eval` unchanged.

**Why a copy.** Every track sets `defaultEnabled: false`, so it loads only where a repo
turns it on — that is the whole design. The eval sandbox turns nothing on, and on
2.1.283 `claude plugin eval plugins/apple-track` says so and runs the suite WITHOUT the
plugin: every trigger case fails, for a reason that has nothing to do with the skill.
No case field or flag enables it (checked against the plugin-evals docs). So this copies
the track to a temp directory, drops `defaultEnabled` from the copy's manifest, runs
there, and brings `evals/results/` back. The repo is never edited.

**Run it from a terminal.** The eval spawns `claude -p` children on your own credential.
Started from inside a desktop-app session they fail with "Not logged in" — the session
borrows the app's login, and the children cannot. A terminal where `claude` works is
enough.

**What it passes on its own:** `--trust-plugin` (these are this repo's own files) and
`--scaffold`, which runs each case's `fixture.sh`. Those scripts are written here and
only lay out files in the run's empty working directory — read them before adding one
that does more. Each run costs model usage on your plan; `--max-cost-usd` caps it.
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PLUGINS = os.path.join(REPO, "plugins")


def tracks_with_evals():
    return sorted(t for t in os.listdir(PLUGINS)
                  if os.path.isdir(os.path.join(PLUGINS, t, "evals")))


def run(track, passthrough):
    src = os.path.join(PLUGINS, track)
    tmp = tempfile.mkdtemp(prefix=f"af-evals-{track}-")
    try:
        dst = os.path.join(tmp, track)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("results", "__pycache__"))
        manifest = os.path.join(dst, ".claude-plugin", "plugin.json")
        with open(manifest, encoding="utf-8") as f:
            data = json.load(f)
        data.pop("defaultEnabled", None)
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"── {track} (a copy in {tmp}, defaultEnabled dropped) ──", flush=True)
        rc = subprocess.call(["claude", "plugin", "eval", dst, "--trust-plugin", "--scaffold",
                              *passthrough])
        got = os.path.join(dst, "evals", "results")
        if os.path.isdir(got):
            keep = os.path.join(src, "evals", "results")
            shutil.copytree(got, keep, dirs_exist_ok=True)
            print(f"   results → {os.path.relpath(keep, REPO)}/  (gitignored)")
        return rc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__.strip())
        return 0
    known = tracks_with_evals()
    names = [a for a in sys.argv[1:] if a in known]
    passthrough = [a for a in sys.argv[1:] if a not in known]
    if not known:
        print("No track has an evals/ directory yet.")
        return 0
    if os.environ.get("CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH"):
        print("⚠ This looks like a session inside the desktop app. Its eval children cannot "
              "log in;\n  run this from a terminal instead.\n")
    if not shutil.which("claude"):
        sys.exit("✗ `claude` is not on PATH.")
    rc = 0
    for track in names or known:
        rc = run(track, passthrough) or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
