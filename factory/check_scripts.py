#!/usr/bin/env python3
"""Do the scripts the skills run still parse, and do their imports exist here?

The guards have pipelines. The scripts a skill hands to a session — `publish_aab.py`,
`verify_prices.py`, thirty-odd of them — had nothing. A typo in one of those does not
surface at deploy; it surfaces at the single moment it is used, which for the shipping
scripts is halfway through a release with a signed artifact already built.

Three questions, and the split between them is the point:

    parse    the file compiles. Cheap, total, and catches the whole class of "someone
             edited it and did not run it".
    imports  every module imported at the top level can actually be found on this
             machine — stdlib or installed.
    --help   the script gets as far as printing its own usage.

**The first two execute nothing.** Parsing is static, and imports are resolved with
`find_spec`, which locates a module without running it.

**The third runs `--help`, and only `--help`**, because parse-and-import was not
enough. `reviews.py` referred to `ship.DEFAULT_KEY`, a name its sibling module never
defined: the file parsed, every import resolved, and the AttributeError fired while
argparse was still being built — so the skill could not run at all, and this checker
said it was fine. An attribute that does not exist is invisible to static analysis in
Python, and `--help` is the cheapest thing that would have caught it.

Why `--help` is safe here, and not a licence to run anything else: with argparse it
exits inside `parse_args()`, before a single line of the script's own work. That was
checked rather than assumed — every script here does nothing at module level beyond
imports, constants, `sys.path` inserts and definitions. A script with no
`if __name__` guard is a module, not a command, and is skipped. A script that takes no
options at all cannot answer `--help`, so it is **reported, never failed on** — the
same treatment Pillow gets. Nothing is ever run with real arguments, because these
scripts sign artifacts and upload builds, and a checker that exercised them properly
would be a checker that ships something by accident.

An import that resolves to something outside the standard library is COUNTED, not
failed. Pillow cannot be written in stdlib, and three image scripts rightly use it. What
the count is for: this factory mostly stands on the standard library — `publish_aab.py`
builds its own JWT out of `urllib` rather than pulling in a client — and that line
moving is a decision worth seeing at deploy rather than discovering on a machine where
the package happens to be missing.
"""
import ast, importlib.util, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# Where a skill's scripts live, plus the factory's own commands. The guards are left
# out on purpose: they each have a branch pipeline that already runs them.
ROOTS = [os.path.join(REPO, "plugins"), HERE]
SKIP = {"tests", "__pycache__", "node_modules", ".git", "dashboard"}
STDLIB = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()
THIRD_PARTY = {}                                     # module → the scripts that import it


def files():
    for root in ROOTS:
        for base, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP]
            for n in sorted(names):
                if n.endswith((".py", ".sh")):
                    yield os.path.join(base, n)


def imported(tree):
    """Top-level module names this file imports. Nested imports are deliberate and skipped."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:          # `from .x import y` is local
                out.add(node.module.split(".")[0])
    return out


_LOCAL = None


# What this repo imports out of grove. Real modules, in another checkout — so when grove
# is not on this machine (a build runner has this repo alone) they are known-absent
# rather than missing. Reporting them would fail eight scripts over something this repo
# cannot fix, which is the noise that gets a checker skipped.
FROM_GROVE = {"grove_repo", "warn_stale_plugin_cache"}

# Third-party packages these skills legitimately use. Declared rather than discovered,
# because `find_spec` cannot tell "not installed on THIS machine" from "a typo": on a
# build runner nothing is installed, and four image scripts were reported as broken for
# importing Pillow. Named here, they are reported as a dependency and never failed on —
# and a name that is NOT here still fails, which is what keeps the check sharp.
THIRD_PARTY_OK = {"PIL"}


def importable(name):
    """Is this module actually on THIS machine? Cached — find_spec is not free."""
    global _IMPORTABLE
    if name not in _IMPORTABLE:
        try:
            _IMPORTABLE[name] = importlib.util.find_spec(name) is not None
        except Exception:
            _IMPORTABLE[name] = False
    return _IMPORTABLE[name]


_IMPORTABLE = {}
# A declared dependency that is NOT on this machine. Kept apart from THIRD_PARTY so the
# report can say "installed" only when it is true — on a build runner nothing is.
ABSENT = {}


def local_module(name):
    """A module this repo carries. Scripts reach them with sys.path.insert, and where
    exactly is not decidable statically — so the question asked is the one a person
    would ask: is there a file by that name in this repo at all?"""
    global _LOCAL
    if _LOCAL is None:
        _LOCAL = set()
        roots = [REPO]
        # grove carries `grove_repo`, which several scripts here import through
        # sys.path.insert. It is not in this repo and it is not third-party either —
        # reporting it as missing would be the false alarm that gets a checker skipped.
        sys.path.insert(0, HERE)
        try:
            from grove import scripts as _grove_scripts
            g = _grove_scripts()
            if g:
                roots.append(g)
            else:
                _LOCAL.update(FROM_GROVE)
        except Exception:
            _LOCAL.update(FROM_GROVE)
        for root in roots:
            for base, dirs, names in os.walk(root):
                dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
                _LOCAL.update(n[:-3] for n in names if n.endswith(".py"))
    return name in _LOCAL


# A command answers --help; a module does not have to. Anything without the guard is
# imported by something else and is not this check's business.
MAIN_GUARD = re.compile(r"""^if\s+__name__\s*==\s*['"]__main__['"]""", re.M)
NO_HELP = {}                                         # script → why it could not answer
NEEDS_DEP = {}                                       # script → the declared dep it wants


def smoke(path, src, wants=()):
    """Run `--help` and report what came back. [] when it printed its usage.

    Runs from a scratch directory with no arguments but the flag, so a script that
    somehow ignored argparse still has nothing to act on.

    `wants` names declared third-party dependencies (THIRD_PARTY_OK) that are not on
    this machine. A script that refuses to start without one cannot answer `--help`
    here, and that is not a fault in the script — it is the same "not installed on THIS
    machine" that the import check above already declines to fail on. Reported, never
    failed on, and the exemption is narrow on purpose: it applies only to a name in
    THIRD_PARTY_OK that `find_spec` genuinely cannot find, so a real breakage in one of
    these scripts still fails wherever Pillow IS installed — which is every machine that
    runs the skill.
    """
    if not MAIN_GUARD.search(src):
        return []                                    # a module, not a command
    if os.sep + "hooks" + os.sep in path:
        # A hook is driven by a JSON payload on stdin, not by flags. It has no usage to
        # print, and its contract is exercised by running it with a payload — which is
        # what its own tests do. Parsing and imports above still apply.
        return []
    try:
        p = subprocess.run([sys.executable, path, "--help"], capture_output=True,
                           text=True, timeout=30, cwd=tempfile.gettempdir(),
                           # No stdin. A hook script's first act is to read a payload
                           # from it, so with an inherited terminal the check hangs for
                           # its whole timeout — which is what happened the moment the
                           # first hook was added here. DEVNULL makes that read return
                           # EOF at once, and the script exits the way it would with a
                           # payload it cannot parse.
                           stdin=subprocess.DEVNULL,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    except subprocess.TimeoutExpired:
        return [("--help did not return", "30s timeout — is it doing work before parsing args?")]
    except Exception as e:
        return [("--help could not be run", str(e)[:80])]
    if p.returncode == 0:
        return []
    out = (p.stdout + p.stderr).strip()
    last = [ln for ln in out.splitlines() if ln.strip()]
    last = last[-1] if last else f"exit {p.returncode}, no output"
    # A script with no option parsing cannot be expected to answer. Counted, not failed:
    # failing it would push every small script towards argparse it does not need.
    if "argparse" not in src:
        NO_HELP[os.path.relpath(path, REPO)] = last[:90]
        return []
    if wants:
        NEEDS_DEP[os.path.relpath(path, REPO)] = ", ".join(sorted(wants))
        return []
    return [("--help failed", f"exit {p.returncode}: {last[:110]}")]


def check(path):
    """[(kind, detail)] for one file. Empty means it parses, resolves and answers --help."""
    if path.endswith(".sh"):
        try:
            p = subprocess.run(["bash", "-n", path], capture_output=True, text=True,
                               timeout=20)
            return [] if p.returncode == 0 else [("syntax", p.stderr.strip()[:120])]
        except Exception as e:
            return [("cannot be checked", str(e)[:80])]

    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename=path)
    except SyntaxError as e:
        return [("syntax", f"line {e.lineno}: {e.msg}")]
    except Exception as e:
        return [("cannot be read", str(e)[:80])]

    gaps, wants = [], set()
    for name in sorted(imported(tree)):
        if name in STDLIB or name in THIRD_PARTY_OK or local_module(name):
            if name in THIRD_PARTY_OK:
                if importable(name):
                    THIRD_PARTY.setdefault(name, []).append(path)
                else:
                    ABSENT.setdefault(name, []).append(path)
                    wants.add(name)
            continue
        try:
            spec = importlib.util.find_spec(name)
        except Exception:
            spec = None
        if spec is None:
            gaps.append(("import not found here", name))
        else:
            # Installed and outside the standard library. Not a fault — Pillow cannot be
            # written in stdlib — but worth counting, because it is the difference
            # between a script that runs anywhere and one that runs on THIS machine.
            THIRD_PARTY.setdefault(name, []).append(path)
    # Only worth running when the file is otherwise sound: a missing import would fail
    # --help for a reason already reported, twice.
    if not gaps:
        gaps += smoke(path, src, wants)
    return gaps


def _help_only():
    """`--help` must answer, not run. These take no options, so the docstring IS the
    usage — but a script that ignores `-h` and starts a full scan instead teaches you
    that its flags are not to be trusted."""
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__.strip())
        raise SystemExit(0)


def main():
    _help_only()
    checked = 0
    found = []
    for path in files():
        checked += 1
        for kind, detail in check(path):
            found.append((os.path.relpath(path, REPO), kind, detail))

    print(f"Checked {checked} scripts — parsed and imports resolved statically; "
          f"the Python commands also ran `--help`, and nothing else.")
    if THIRD_PARTY:
        deps = ", ".join(f"{k} ({len(v)})" for k, v in sorted(THIRD_PARTY.items()))
        print(f"Outside the standard library, and installed here: {deps}")
    if ABSENT:
        deps = ", ".join(f"{k} ({len(v)})" for k, v in sorted(ABSENT.items()))
        print(f"Declared and NOT installed here: {deps} — the scripts that need it are "
              f"checked statically only.")
    if NEEDS_DEP:
        print(f"Could not answer --help without it: {len(NEEDS_DEP)} — "
              + ", ".join(sorted(os.path.basename(k) for k in NEEDS_DEP)))
    if NO_HELP:
        print(f"No option parsing, so no usage to print: {len(NO_HELP)} — "
              + ", ".join(sorted(os.path.basename(k) for k in NO_HELP)))
    print()
    if not found:
        if NEEDS_DEP:
            print(f"✓ all of them parse and every import resolves here. {len(NEEDS_DEP)} "
                  f"could not be asked for a usage,\n  because a dependency they declare "
                  f"is not on this machine — nothing is broken, less was checked.")
        else:
            print("✓ all of them parse, every import resolves here, and each one prints "
                  "its usage.")
        return 0
    for rel, kind, detail in found:
        print(f"  ✗ {rel}\n      {kind}: {detail}")
    print(f"\n{len(found)} scripts that would break only at the moment they are used.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
