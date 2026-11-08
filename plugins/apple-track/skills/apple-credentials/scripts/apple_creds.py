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
  init                        write $KEYS_ROOT/APPLE.md from references/
                              APPLE.md.template and what check finds; refuses
                              to overwrite; leaves {{ASK: …}} for the user
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
        subj = subprocess.run(["openssl", "x509", "-noout", "-subject"], input=pem,
                              capture_output=True, text=True).stdout or ""
        m = re.search(r"OU\s*=\s*([A-Z0-9]{10})", subj)
        if m:
            CERT_TEAM[sha1] = m.group(1)
    return out


CERT_TEAM = {}                  # SHA-1 → team ID (the certificate's OU), filled by cert_dates()


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


def backup_fingerprints(root):
    """SHA-1 → .p12 path, read from each backup's certificate.

    Only the public certificate is extracted (`-nokeys`); the password is handed to
    openssl as `file:` and never read here. Empty when there is no password file or
    openssl cannot open the files — the caller then falls back to names and dates."""
    d = os.path.join(root, "apple-certificates")
    pw = os.path.join(d, "p12-password.txt")
    if not os.path.isfile(pw):
        return {}
    out = {}
    for f in glob.glob(os.path.join(d, "*.p12")):
        c = subprocess.run(["openssl", "pkcs12", "-legacy", "-in", f, "-passin", f"file:{pw}", "-nokeys"],
                           capture_output=True, text=True)
        for pem in re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", c.stdout or "", re.S):
            fp = subprocess.run(["openssl", "x509", "-noout", "-fingerprint", "-sha1"], input=pem,
                                capture_output=True, text=True)
            m = re.search(r"=([0-9A-F:]+)", fp.stdout or "")
            if m:
                out[m.group(1).replace(":", "")] = f
    return out


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


def readiness(present):
    """(goal, has a certificate for it) — the current types only, not the legacy ones."""
    def has(pref): return pref in present
    return [
        ("Development (run on devices)", has("Apple Development")),
        ("App Store / Mac App Store", has("Apple Distribution")),
        ("Mac App Store installer (.pkg)", has("Mac Installer Distribution") or has("3rd Party Mac Developer Installer")),
        ("Direct Mac (DMG + notarize)", has("Developer ID Application")),
        ("Direct Mac installer (.pkg)", has("Developer ID Installer")),
    ]


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
        by_sha1 = backup_fingerprints(root)
        if by_sha1:
            print("  (matched by SHA-1, read from each backup's certificate)")
        for items in by_type.values():
            for n, sha1 in items:
                slug = backup_slug(n)
                if by_sha1:
                    f = by_sha1.get(sha1)
                    if f:
                        ok(f"{slug}: {os.path.basename(f)}")
                    else:
                        miss(f"{slug} ({sha1[:8]}…): no backup holds this certificate — export it "
                             "(ask first; references/profiles-and-backup.md)")
                    continue
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
    for name, present_ok in readiness(present):
        (ok if present_ok else miss)(f"{name}: {'cert present' if present_ok else 'missing cert'}")
    print("\n  Which cert/credential for which goal → references/*.md."
          "\n  Missing a cert? Create it: Xcode → Settings → Accounts → Manage Certificates → +")


HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "..", "references")
PROFILE_DIR = os.path.expanduser("~/Library/MobileDevice/Provisioning Profiles")


def _sections(md):
    """'## N. Title' → body, for a markdown file; headings inside code fences ignored."""
    out, cur, fence = {}, None, False
    for line in md.split("\n"):
        if line.startswith("```"):
            fence = not fence
        if not fence and line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
            continue
        if cur:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def _demote(text):
    """## → ###, ### → #### — outside code fences, so an included section nests."""
    lines, fence = [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            fence = not fence
        if not fence and line.startswith("#"):
            line = "#" + line
        lines.append(line)
    return "\n".join(lines)


def _policy_and_backup():
    with open(os.path.join(REFS, "profiles-and-backup.md"), encoding="utf-8") as f:
        secs = _sections(f.read())
    def local(text):
        # The reference names its own sections and calls the map `APPLE.md`; inside the
        # map itself those become "above" and "this file".
        text = re.sub(r"\s*\(section \d\)", " (above)", text)
        text = text.replace("Which key to pass is in `APPLE.md`.", "Which key to pass is in section 3.")
        return text.replace("`APPLE.md`", "this file")
    pick = lambda pre: next((f"### {re.sub(r'^[0-9]+[.] ', '', k)}\n\n" + _demote(local(v)))
                            for k, v in secs.items() if k.startswith(pre))
    policy = "\n\n".join([pick("1."), pick("2."), pick("4.")])
    backup = _demote(local(next(v for k, v in secs.items() if k.startswith("3."))))
    return policy, backup


def manual_profiles():
    """(name, team, expires, app id) for each profile in the manual-profile folder."""
    import plistlib
    out = []
    for f in sorted(glob.glob(os.path.join(PROFILE_DIR, "*"))):
        r = subprocess.run(["security", "cms", "-D", "-i", f], capture_output=True)
        if r.returncode != 0:
            continue
        try:
            d = plistlib.loads(r.stdout)
        except Exception:
            continue
        ent = d.get("Entitlements") or {}
        app = ent.get("application-identifier") or ent.get("com.apple.application-identifier") or ""
        exp = d.get("ExpirationDate")
        out.append((d.get("Name", "?"), ",".join(d.get("TeamIdentifier") or []),
                    exp.date().isoformat() if exp else "?", app))
    return out


def _ask(what):
    return "{{ASK: " + what + "}}"


def build_apple_md(root):
    """The filled template and the facts it was filled from."""
    with open(os.path.join(REFS, "APPLE.md.template"), encoding="utf-8") as f:
        t = f.read()
    by_type, present = list_certs()
    dates = cert_dates()
    certs = [(label, n, sha1) for label, items in by_type.items() for n, sha1 in items]
    teams = sorted({CERT_TEAM[s] for _, _, s in certs if s in CERT_TEAM})
    personal = sorted({m.group(1) for _, n, _ in certs if n.startswith("Apple Development")
                       for m in [re.search(r"\(([A-Z0-9]{10})\)\s*$", n)] if m and m.group(1) not in teams})
    keys = find_keys_root_api_keys()
    issuers = set()
    for name, _, _ in keys:
        try:
            with open(os.path.join(root, "appstoreconnect", name, "api_key.json"), encoding="utf-8") as f:
                iss = json.load(f).get("issuer_id")
            if iss:
                issuers.add(iss)
        except Exception:
            pass
    by_sha1 = backup_fingerprints(root)
    backups = newest_backups(root)
    today = datetime.date.today()

    rows = ["| Certificate | SHA-1 | Expires | Use |", "|---|---|---|---|"]
    for label, n, sha1 in certs:
        rows.append(f"| **{n}** | `{sha1[:8]}…{sha1[-4:]}` | {(dates.get(sha1) or (None, '?'))[1]} | {label} |")
    cert_table = "\n".join(rows) if certs else _ask("no signing certificate in the keychain — create them first (apple-credentials step 3)")

    missing = [goal for goal, ok_ in readiness(present) if not ok_]
    cert_missing = ("a certificate for " + "; ".join(missing) + ". " + _ask("whether this account needs it, and why not if not")) if missing else "nothing — every goal has its certificate."
    soon = sorted((dates[s][1], n) for _, n, s in certs if s in dates and dates[s][1]
                  and dates[s][1] <= (today + datetime.timedelta(days=183)).isoformat())
    cert_renew = ", ".join(f"{n} ({d})" for d, n in soon) if soon else "none within six months."

    if keys:
        rows = ["| Folder | Key ID | Purpose |", "|---|---|---|"]
        rows += [f"| `{name}` | `{kid}` | {_ask('what ' + kid + ' is used for')} |" for name, kid, _ in keys]
        key_table = "\n".join(rows)
    else:
        key_table = _ask("no key under $KEYS_ROOT/appstoreconnect/ — where the App Store Connect API keys are, and what each serves")

    def where(sub, what):
        pth = os.path.join(root, sub)
        return f"`$KEYS_ROOT/{sub}/`" if os.path.isdir(pth) else _ask(f"where the {what} is, if there is one")

    profs = manual_profiles()
    if profs:
        rows = ["| Name | Team | Expires | App ID |", "|---|---|---|---|"]
        rows += [f"| {n} | `{tm}` | {e} | `{a}` |" for n, tm, e, a in profs]
        prof_table = "\n".join(rows)
    else:
        prof_table = "none in `~/Library/MobileDevice/Provisioning Profiles`."

    lines = []
    for label, n, sha1 in certs:
        f = by_sha1.get(sha1)
        if not f and not by_sha1:
            b = backups.get(backup_slug(n))
            f = b[1] if b else None
        lines.append(f"- {n}: " + (f"`{os.path.basename(f)}`" if f else "**no backup** — export one"))
    has_copy, detail = off_machine_copy(root)
    lines.append(f"- Off-machine copy of `$KEYS_ROOT`: {'yes' if has_copy else '**no**'} — {detail}.")
    backup_state = "\n".join(lines)

    policy, backup = _policy_and_backup()
    fill = {
        "KEYS_ROOT": root.replace(os.path.expanduser("~"), "~", 1),
        "TODAY": today.isoformat(),
        "TEAM_ID": ", ".join(f"`{x}`" for x in teams) or _ask("the team ID (Xcode → Settings → Accounts, or developer.apple.com → Membership)"),
        "PERSONAL_ID": ", ".join(f"`{x}`" for x in personal) or "—",
        "ISSUER_ID": ", ".join(f"`{x}`" for x in sorted(issuers)) or _ask("the Issuer ID (App Store Connect → Users and Access → Integrations)"),
        "CERT_TABLE": cert_table, "CERT_MISSING": cert_missing, "CERT_RENEW": cert_renew,
        "KEY_TABLE": key_table,
        "APPLEADS": where("appleads", "Apple Ads API key"),
        "SPARKLE": where("Sparkle", "Sparkle EdDSA private key"),
        "NOTARY": _ask("the notary keychain profile's name, or which API key notarization uses"),
        "PROFILE_TABLE": prof_table, "BACKUP_STATE": backup_state,
        "INCLUDE:POLICY": policy, "INCLUDE:BACKUP": backup,
    }
    for k, v in fill.items():
        t = t.replace("{{" + k + "}}", v)
    facts = ([("team", x) for x in teams] + [("certificate", s[:8]) for _, _, s in certs]
             + [("API key", kid) for _, kid, _ in keys] + [("profile", n) for n, *_ in profs]
             + [("backup", os.path.basename(f)) for f in set(by_sha1.values())])
    return t, facts


def cmd_init(args):
    root = keys_root()
    if not root:
        miss("$KEYS_ROOT is not set — there is no place for APPLE.md. Set it, then run init again.")
        sys.exit(1)
    target = os.path.join(root, "APPLE.md")
    text, facts = build_apple_md(root)
    if os.path.exists(target):
        with open(target, encoding="utf-8") as f:
            have = f.read()
        warn(f"{target} exists — not overwritten. What this machine shows, against the file:")
        for kind, v in facts:
            print(f"  {'=' if v in have else '+'} {kind}: {v}" + ("" if v in have else "   ← not in the file"))
        print("\n  '+' lines are facts the file does not mention. Update the file by hand, in its own"
              "\n  language and section order; init never overwrites.")
        sys.exit(2)
    if args.stdout:
        print(text)
        return
    os.makedirs(root, exist_ok=True)
    old = os.umask(0o077)
    try:
        with open(target, "x", encoding="utf-8") as f:
            f.write(text)
    finally:
        os.umask(old)
    asks = re.findall(r"\{\{ASK: [^}]*\}\}", text)
    ok(f"wrote {target}")
    print(f"  {len(asks)} {{{{ASK: …}}}} marker(s) left — resolve each with the user:")
    for a in asks:
        print(f"  • {a[7:-2]}")


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

    i = sub.add_parser("init", help="write $KEYS_ROOT/APPLE.md from the template and what this machine shows")
    i.add_argument("--stdout", action="store_true", help="print instead of writing")
    i.set_defaults(func=cmd_init)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
