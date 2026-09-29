#!/usr/bin/env python3
"""
apple_creds.py — inventory and set up Apple certificates & auth credentials.

Subcommands:
  check                       list signing certs by type, detect API keys,
                              and summarize what's present/missing per goal
  store-creds                 create a notary keychain profile FOR the user,
                              from an app-specific password OR an API key
  setup                       print how to create an app-specific password /
                              App Store Connect API key (you do these on Apple)

macOS only (uses `security`/`xcrun`). Stdlib otherwise.
"""

import argparse
import glob
import os
import re
import subprocess
import sys

# The certificate table is shared with the other signing skill — see
# `shared/apple-specs.json` at the track root. Two copies had already drifted in three
# of their ten descriptions.
_SHARED = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "..", "..", "shared"))
sys.path.insert(0, _SHARED)
from apple_specs import cert_types                            # noqa: E402
# `credentials` (the same shared/ directory) is imported lazily inside cmd_check so
# that a broken resolver cannot take `list` and `setup` down with it.

CERT_TYPES = cert_types()

API_KEY_DIRS = [
    os.path.expanduser("~/.appstoreconnect/private_keys"),
    os.path.expanduser("~/private_keys"),
    os.path.expanduser("~/.private_keys"),
    "./fastlane",
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ok(m):   print(f"  ✅ {m}")
def warn(m): print(f"  ⚠️  {m}")
def miss(m): print(f"  ❌ {m}")
def step(m): print(f"\n▶ {m}")


def list_certs():
    r = run(["security", "find-identity", "-v", "-p", "codesigning"])
    names = re.findall(r'\d+\)\s+[0-9A-F]+\s+"([^"]+)"', r.stdout or "")
    by_type = {}
    for n in names:
        label = next((d for p, d in CERT_TYPES if n.startswith(p)), "other / unknown")
        by_type.setdefault(label, []).append(n)
    present_prefixes = {p for n in names for p, _ in CERT_TYPES if n.startswith(p)}
    return by_type, present_prefixes


def find_api_keys():
    keys = []
    for d in API_KEY_DIRS:
        if os.path.isdir(d):
            keys += glob.glob(os.path.join(d, "AuthKey_*.p8")) + glob.glob(os.path.join(d, "*.p8"))
    return sorted(set(keys))


def cmd_check(args):
    by_type, present = list_certs()
    step("Signing certificates in keychain")
    if not by_type:
        miss("none found")
    for label, names in by_type.items():
        for n in names:
            print(f"  • [{label}] {n}")

    step("App Store Connect API key")
    # The track's resolver is what every shipping script asks — the environment, then
    # $KEYS_ROOT/credentials.json. This check used to look in four folders of its own
    # and report "none found" on a machine where asc_common.rb was authenticating
    # fine, because the documented place was not one of the four.
    try:
        import credentials as shared
        c = shared.asc_key(required=False)
    except Exception as e:                                   # resolver unreadable: say so, go on
        c, shared = None, None
        warn(f"could not run the credential resolver: {e}")
    if c:
        ok(f"{c['key_id']} (issuer {c['issuer_id'][:8]}…) — from {c['_from']}")
        (ok if os.path.isfile(c["p8"]) else miss)(f".p8 at {c['p8']}")
    else:
        print("  (none resolved — create one in App Store Connect → Users and Access →")
        print("   Integrations, then record it in $KEYS_ROOT/credentials.json or the environment)")
    keys = find_api_keys()
    if keys and not (c and c["p8"] in keys):
        print("  also on disk, not recorded anywhere the scripts look:")
        for k in keys:
            print(f"  • {k}")

    step("Notary keychain profile")
    prof = None
    try:
        prof = shared.notary_profile(required=False) if shared else None
    except Exception:
        pass
    if prof:
        ok(f"{prof['name'] if isinstance(prof, dict) else prof} — recorded; profiles cannot be listed via CLI")
    else:
        print("  none recorded. Create one with `store-creds` here, then record its name in")
        print("  $KEYS_ROOT/credentials.json (notary.profile) or $NOTARY_PROFILE.")

    step("Readiness by goal")
    def has(pref): return pref in present
    rows = [
        ("Development (run on devices)", has("Apple Development")),
        ("App Store / Mac App Store", has("Apple Distribution")),
        ("Mac App Store installer (.pkg)", has("Mac Installer Distribution") or has("3rd Party Mac Developer Installer")),
        ("Direct Mac (DMG + notarize)", has("Developer ID Application")),
        ("Direct Mac installer (.pkg)", has("Developer ID Installer")),
    ]
    for name, present_ok in rows:
        (ok if present_ok else miss)(f"{name}: {'cert present' if present_ok else 'missing cert'}")
    print("\n  Which cert/credential for which goal → references/*.md."
          "\n  Missing a cert? Create it: Xcode → Settings → Accounts → Manage Certificates → +")


def cmd_store_creds(args):
    cred = []
    if args.key and args.key_id and args.issuer:
        if not os.path.isfile(args.key):
            miss(f"API key file not found: {args.key}"); sys.exit(1)
        cred = ["--key", args.key, "--key-id", args.key_id, "--issuer", args.issuer]
        source = "App Store Connect API key"
    else:
        import getpass
        pw = args.password or os.environ.get("NOTARY_PASSWORD")
        if not pw:
            pw = getpass.getpass("App-specific password (hidden): ") if sys.stdin.isatty() else sys.stdin.readline().strip()
        if not pw:
            miss("no app-specific password (use NOTARY_PASSWORD env, stdin, or --password) "
                 "and no API key trio (--key/--key-id/--issuer)")
            sys.exit(1)
        if not (args.apple_id and args.team_id):
            miss("--apple-id and --team-id are required with an app-specific password")
            sys.exit(1)
        cred = ["--apple-id", args.apple_id, "--team-id", args.team_id, "--password", pw]
        source = "app-specific password"

    step(f"Creating notary keychain profile '{args.profile}' ({source})")
    r = run(["xcrun", "notarytool", "store-credentials", args.profile, *cred])
    print((r.stdout or "").strip())
    if r.returncode != 0:
        miss("could not store credentials:"); print((r.stderr or "").strip()); sys.exit(1)
    ok(f"profile '{args.profile}' stored in the keychain")
    print(f"\n  Reusable from now on:")
    print(f"    notarytool ... --keychain-profile {args.profile}")
    print(f"    (no password needed again — it's saved securely.)")


def cmd_setup(args):
    print("""Create the credential (you do these on Apple's sites; no tool can):

APP-SPECIFIC PASSWORD (for notarytool / notary profile):
  account.apple.com → Sign-In & Security → App-Specific Passwords → + →
  name it, copy it once (abcd-efgh-ijkl-mnop). Then:
    NOTARY_PASSWORD='abcd-...' apple_creds.py store-creds \\
      --profile MyNotary --apple-id you@example.com --team-id ABCDE12345

APP STORE CONNECT API KEY (for fastlane / CI / uploads):
  App Store Connect → Users and Access → Integrations → App Store Connect API →
  + → generate. Note Issuer ID + Key ID, download the .p8 ONCE, place at
  ~/.appstoreconnect/private_keys/AuthKey_<KEYID>.p8. Then for notarytool:
    apple_creds.py store-creds --profile MyNotary \\
      --key ~/.appstoreconnect/private_keys/AuthKey_XXX.p8 --key-id XXX --issuer <uuid>

See references/auth-credentials.md for which to use when.""")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check").set_defaults(func=cmd_check)

    s = sub.add_parser("store-creds")
    s.add_argument("--profile", required=True)
    s.add_argument("--apple-id"); s.add_argument("--team-id")
    s.add_argument("--password", help="prefer NOTARY_PASSWORD env or stdin")
    s.add_argument("--key"); s.add_argument("--key-id"); s.add_argument("--issuer")
    s.set_defaults(func=cmd_store_creds)

    sub.add_parser("setup").set_defaults(func=cmd_setup)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
