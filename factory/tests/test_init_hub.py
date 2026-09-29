"""Branch pipeline for init_hub.py.

    python3 factory/tests/test_init_hub.py

The property worth pinning is that it never destroys anything: a hub that already exists
is reported on, and a second `--create` touches nothing. Everything runs against throwaway
directories and a throwaway registry.
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FACTORY = os.path.dirname(HERE)
SCRIPT = os.path.join(FACTORY, "init_hub.py")


def main():
    # init_hub resolves the hub's root through grove_repo, so without grove there is
    # nothing to test rather than something failing. Skipped loudly: a build runner has
    # this repo alone, and a test that quietly reports success there would be worse than
    # one that is not run.
    sys.path.insert(0, FACTORY)
    from grove import scripts as grove_scripts
    if not grove_scripts():
        print("· skipped — grove is not on this machine, and init_hub reads its registry")
        return 0

    base = os.path.realpath(tempfile.mkdtemp(prefix="factory-hub-test-"))
    fails = 0

    def check(ok, label, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'✓' if ok else '✗'} {label}" + (f"   [{detail}]" if detail and not ok else ""))

    def run(hub, *args, **extra):
        reg = os.path.join(base, "registry.json")
        with open(reg, "w", encoding="utf-8") as f:
            json.dump({"projects": {"app-hub": {"root": hub}}}, f)
        # $APP_HUB wins over the registry now (the environment is the contract the
        # skills read), so the machine's own hub must not leak into a test of the
        # registry path.
        env = {k: v for k, v in os.environ.items() if k not in ("APP_HUB", "DEV_ROOT")}
        p = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True,
                           text=True, timeout=30, env=dict(env, GROVE_REGISTRY=reg, **extra))
        return p.returncode, p.stdout + p.stderr

    try:
        print("-- a hub that is not there --")
        gone = os.path.join(base, "nothere")
        rc, out = run(gone, )
        check(rc == 1, "reports a missing hub as a problem", f"rc={rc}")
        check("--create" in out, "and offers to create it")
        check("registry.json" in out, "or to point the registry elsewhere")
        check(not os.path.exists(gone), "reporting creates nothing")
        # A machine without grove sets $APP_HUB and has no registry; the variable must
        # be the answer, and the registry must not even be consulted.
        elsewhere = os.path.join(base, "elsewhere")
        rc, out = run(gone, APP_HUB=elsewhere)
        check("elsewhere" in out and "nothere" not in out,
              "$APP_HUB wins over the registry", out.strip().splitlines()[0] if out.strip() else "")

        print("\n-- creating one --")
        hub = os.path.join(base, "hub")
        rc, out = run(hub, "--create")
        check(rc == 0, "creates", f"rc={rc}")
        for f in ("DATA.md", "PRODUCT.md", "README.md"):
            check(os.path.isfile(os.path.join(hub, f)), f"  {f}")
        txt = open(os.path.join(hub, "DATA.md"), encoding="utf-8").read()
        check("$KEYS_ROOT" in txt, "DATA.md points at $KEYS_ROOT for the secrets")
        check("issuer id" in txt and "phone" in txt, "and names the fields a person must fill")

        print("\n-- one app's folders --")
        rc, out = run(hub, "--app", "demo")
        check(os.path.isfile(os.path.join(hub, "demo", "profile.md")), "profile.md stub")
        # Read APP_TREE from the script rather than listing the folders again here.
        # A second list is a second thing to keep true, and it did not stay true: the
        # tree was missing store/apple/release-notes, which app-store-deliver's sync
        # requires, and this test — naming four folders of its own — could not notice.
        import importlib.util
        _spec = importlib.util.spec_from_file_location("init_hub", SCRIPT)
        _ih = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_ih)
        for d in _ih.APP_TREE:
            check(os.path.isdir(os.path.join(hub, "demo", d)), f"  {d}/")

        print("\n-- never destroys --")
        open(os.path.join(hub, "DATA.md"), "w", encoding="utf-8").write("MINE\n")
        open(os.path.join(hub, "demo", "profile.md"), "w", encoding="utf-8").write("MY PROFILE\n")
        rc, out = run(hub, "--create", "--app", "demo")
        check(open(os.path.join(hub, "DATA.md"), encoding="utf-8").read() == "MINE\n",
              "an existing DATA.md is not overwritten")
        check(open(os.path.join(hub, "demo", "profile.md"), encoding="utf-8").read() == "MY PROFILE\n",
              "nor an existing profile")
        check("Nothing was touched" in out, "and it says so")

        print("\n-- reporting a hub that is set up --")
        rc, out = run(hub)
        check(rc == 0 and "1 app" in out, "counts the apps by their profile.md", out.strip()[:70])

        print("\n-- a hub with no apps yet --")
        empty = os.path.join(base, "empty")
        run(empty, "--create")
        rc, out = run(empty)
        check(rc == 0, "is not a failure", f"rc={rc}")
        check("No app has a profile.md yet" in out, "and says what is missing")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print(f"\n{'all checks passed' if not fails else str(fails) + ' failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
