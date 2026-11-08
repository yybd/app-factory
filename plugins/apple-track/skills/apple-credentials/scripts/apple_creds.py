#!/usr/bin/env python3
"""
apple_creds.py — inventory and set up Apple certificates & auth credentials.

Subcommands:
  check                       list signing certs by type (SHA-1, expiry), detect
                              API keys (incl. $KEYS_ROOT/appstoreconnect/*/),
                              note $KEYS_ROOT/APPLE.md, and summarize what's
                              present/missing per goal
  store-creds                 create a notary keychain profile FOR the user,
                              from an app-specific password OR an API key
  setup                       print how to create an app-specific password /
                              App Store Connect API key (you do these on Apple)

macOS only (uses `security`/`xcrun`). Stdlib otherwise.
"""

import argparse
import datetime
import glob
import json
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


def keys_root():
    """$KEYS_ROOT, or None — no default here: a guessed folder is not the owner's."""
    v = os.environ.get("KEYS_ROOT")
    return os.path.expanduser(v) if v else None


def _cert_date(pem, field):
    e = subprocess.run(["openssl", "x509", "-noout", f"-{field}"], input=pem,
                       capture_output=True, text=True)
    m = re.search(r"=(.+)", e.stdout or "")
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group(1).strip(), "%b %d %H:%M:%S %Y %Z").date().isoformat()
    except ValueError:
        return None


def cert_dates():
    """SHA-1 → (issued, expires) as YYYY-MM-DD for every certificate in the search list.

    Public certificates only — `security find-certificate -p` prints the certificate,
    never the private key."""
    r = run(["security", "find-certificate", "-a", "-Z", "-p"])
    out = {}
    for sha1, pem in re.findall(r"SHA-1 hash: ([0-9A-F]+)\s+(-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----)",
                                r.stdout or "", re.S):
        out[sha1] = (_cert_date(pem, "startdate"), _cert_date(pem, "enddate"))
    return out


def backup_slug(name):
    """'Apple Development: X (ID)' → 'apple-development' — the backup file's prefix."""
    return re.sub(r"[^a-z0-9]+", "-", name.split(":")[0].lower()).strip("-")


def newest_backups(root):
    """slug → (date, path) for the newest <type>-<YYYY-MM-DD>.p12 under
    $KEYS_ROOT/apple-certificates/. Dates come from the names; no file is opened."""
    best = {}
    for f in glob.glob(os.path.join(root, "apple-certificates", "*.p12")):
        m = re.match(r"(.+)-(\d{4}-\d{2}-\d{2})\.p12$", os.path.basename(f))
        if m and (m.group(1) not in best or m.group(2) > best[m.group(1)][0]):
            best[m.group(1)] = (m.group(2), f)
    return best


def off_machine_copy(root):
    """(state, detail): whether Time Machine includes $KEYS_ROOT on a disk other than this one."""
    ex = run(["tmutil", "isexcluded", root])
    if "[Excluded]" in (ex.stdout or ""):
        return False, "Time Machine excludes it"
    di = run(["tmutil", "destinationinfo"])
    names = re.findall(r"^Name\s*:\s*(.+)$", di.stdout or "", re.M)
    if not names:
        return False, "no Time Machine destination is configured"
    boot = run(["diskutil", "info", "/"])
    m = re.search(r"Volume Name:\s*(.+)", boot.stdout or "")
    boot_name = m.group(1).strip() if m else None
    others = [n.strip() for n in names if n.strip() != boot_name]
    if not others:
        return False, f"the only Time Machine destination is the system disk ({boot_name})"
    return True, "Time Machine → " + ", ".join(others)


def list_certs():
    # No `-p codesigning`: that policy hides installer identities (3rd Party Mac
    # Developer Installer, Developer ID Installer), which made the .pkg rows report
    # "missing" on a Mac that had them.
    r = run(["security", "find-identity", "-v"])
    ids = re.findall(r'\d+\)\s+([0-9A-F]+)\s+"([^"]+)"', r.stdout or "")
    names = [n for _, n in ids]
    by_type = {}
    for sha1, n in ids:
        label = next((d for p, d in CERT_TYPES if n.startswith(p)), "other / unknown")
        by_type.setdefault(label, []).append((n, sha1))
    present_prefixes = {p for n in names for p, _ in CERT_TYPES if n.startswith(p)}
    return by_type, present_prefixes


def find_api_keys():
    keys = []
    for d in API_KEY_DIRS:
        if os.path.isdir(d):
            keys += glob.glob(os.path.join(d, "AuthKey_*.p8")) + glob.glob(os.path.join(d, "*.p8"))
    return sorted(set(keys))


def find_keys_root_api_keys():
    """Keys kept one folder per purpose: $KEYS_ROOT/appstoreconnect/<name>/.

    Returns (name, key_id, p8 path) for each. The key id comes from the folder's
    api_key.json (only its `key_id` field is read) or else from the AuthKey_<ID>.p8
    filename. The .p8 itself is never opened."""
    root = keys_root()
    if not root:
        return []
    found = []
    for d in sorted(glob.glob(os.path.join(root, "appstoreconnect", "*", ""))):
        name = os.path.basename(os.path.dirname(d))
        p8s = sorted(glob.glob(os.path.join(d, "private_keys", "*.p8")) + glob.glob(os.path.join(d, "*.p8")))
        if not p8s:
            continue
        kid = None
        try:
            with open(os.path.join(d, "api_key.json"), encoding="utf-8") as f:
                kid = json.load(f).get("key_id")
        except Exception:
            pass
        for p8 in p8s:
            m = re.match(r"AuthKey_([A-Z0-9]+)\.p8$", os.path.basename(p8))
            found.append((name, kid or (m.group(1) if m else "?"), p8))
    return found


def cmd_check(args):
    root = keys_root()
    step("Owner's map ($KEYS_ROOT/APPLE.md)")
    if not root:
        print("  $KEYS_ROOT is not set — no map to read or keep")
    elif os.path.isfile(os.path.join(root, "APPLE.md")):
        ok(f"{os.path.join(root, 'APPLE.md')} — read it and reconcile it with what follows")
    else:
        print(f"  none at {os.path.join(root, 'APPLE.md')} — offer to create it from this output")

    by_type, present = list_certs()
    dates = cert_dates()
    expiries = {k: v[1] for k, v in dates.items()}
    today = datetime.date.today().isoformat()
    soon = (datetime.date.today() + datetime.timedelta(days=60)).isoformat()
    step("Signing certificates in keychain")
    if not by_type:
        miss("none found")
    for label, items in by_type.items():
        for n, sha1 in items:
            exp = expiries.get(sha1)
            note = f"expires {exp}" if exp else "expiry unknown"
            if exp and exp < today:
                note = f"EXPIRED {exp}"
            elif exp and exp <= soon:
                note = f"expires {exp} — renew soon"
            print(f"  • [{label}] {n}  ({sha1[:8]}…{sha1[-4:]}, {note})")

    step("Backup of the signing keys ($KEYS_ROOT/apple-certificates/)")
    if not root:
        print("  $KEYS_ROOT is not set — nowhere to look")
    else:
        backups = newest_backups(root)
        for items in by_type.values():
            for n, sha1 in items:
                slug = backup_slug(n)
                issued = (dates.get(sha1) or (None, None))[0]
                b = backups.get(slug)
                if not b:
                    miss(f"{slug}: no backup — export it (ask first; references/profiles-and-backup.md)")
                elif issued and issued > b[0]:
                    warn(f"{slug}: newest backup {os.path.basename(b[1])} pre-dates the certificate (issued {issued}) — re-export")
                else:
                    ok(f"{slug}: {os.path.basename(b[1])}")
        if backups and not os.path.isfile(os.path.join(root, "apple-certificates", "p12-password.txt")):
            warn("p12-password.txt is not beside the backups")
        has_copy, detail = off_machine_copy(root)
        (ok if has_copy else warn)(f"off-machine copy of $KEYS_ROOT: {detail}"
                                   + ("" if has_copy else " — .p8 and Sparkle keys have no other copy"))

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
    keys = [k for k in find_api_keys() if not (c and k == c["p8"])]
    if keys:
        print("  also on disk, not recorded anywhere the scripts look:")
        for k in keys:
            print(f"  • {k}")
    rooted = find_keys_root_api_keys()
    if rooted:
        print("  under $KEYS_ROOT/appstoreconnect/ (one folder per purpose — APPLE.md says which serves what):")
        for name, kid, p8 in rooted:
            mark = "  ← the resolver's" if c and os.path.realpath(p8) == os.path.realpath(c["p8"]) else ""
            print(f"  • {name}: {kid} — {os.path.relpath(p8, root)}{mark}")

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
