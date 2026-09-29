#!/usr/bin/env python3
"""
notarize_dmg.py — locate a built .app, notarize the app itself, package it as a
signed DMG, notarize the DMG, staple, and verify that everything (app + DMG) is
signed and notarized.

The standard flow notarizes the APP *before* it goes into the DMG, then notarizes
the DMG too — so the app validates offline even after a user drags it out of the
DMG. `build` refuses to package an un-notarized app unless you explicitly waive it.

Subcommands (run them in order; the two `notarize*` steps hit the network, so they
are separate and should be confirmed with the user first):

  locate       <archive-or-dir>             find the .app and summarize its signing
  list                                      show signing identities + notary creds
  notarize-app --app A.app  <creds>         notarize + staple the .app  (BEFORE build)
  build        --app A.app --out DIR [...]  build + sign the DMG from the stapled app
  notarize     --dmg D.dmg  <creds>         submit the DMG to Apple, wait, staple
  verify       [--app A.app] [--dmg D.dmg]  full signature + notarization checks
  setup        (prints credential setup steps; does not run them)

`<creds>` is either `--keychain-profile NAME` or the API-key trio
`--api-key AuthKey.p8 --api-key-id KEYID --api-issuer ISSUER-UUID`.

Prerequisites:
  - A "Developer ID Application" certificate in the login keychain (signing).
  - Notary credentials stored once via `xcrun notarytool store-credentials`
    (see the `setup` subcommand). Direct-distribution (Developer ID) flow —
    NOT the Mac App Store flow.

Everything shells out to xcrun/codesign/hdiutil/spctl/stapler (all built in).
"""

import argparse
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile


def run(cmd, capture=True, check=False):
    r = subprocess.run(cmd, capture_output=capture, text=True)
    if check and r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout or "") + "\n")
        raise SystemExit(f"command failed ({r.returncode}): {' '.join(cmd)}")
    return r


def ok(msg):  print(f"  ✅ {msg}")
def warn(msg): print(f"  ⚠️  {msg}")
def bad(msg):  print(f"  ❌ {msg}")
def step(msg): print(f"\n▶ {msg}")


# --------------------------------------------------------------------------- #
# locate
# --------------------------------------------------------------------------- #
def find_app(path):
    """Find a .app given an .xcarchive, an export dir, or a direct .app path."""
    path = os.path.abspath(path)
    if path.endswith(".app") and os.path.isdir(path):
        return path
    candidates = []
    if path.endswith(".xcarchive"):
        appdir = os.path.join(path, "Products", "Applications")
        if os.path.isdir(appdir):
            candidates += [os.path.join(appdir, d) for d in os.listdir(appdir) if d.endswith(".app")]
    if not candidates and os.path.isdir(path):
        for dp, dns, _ in os.walk(path):
            if "DerivedData" in dp:
                continue
            for d in dns:
                if d.endswith(".app"):
                    candidates.append(os.path.join(dp, d))
    return candidates[0] if candidates else None


def codesign_info(app):
    r = run(["codesign", "-dvvv", app])
    text = (r.stderr or "") + (r.stdout or "")
    authority = re.findall(r"Authority=(.+)", text)
    has_devid = any("Developer ID Application" in a for a in authority)
    flags = re.search(r"flags=0x[0-9a-fA-F]+\(([^)]*)\)", text)
    runtime = bool(flags and "runtime" in flags.group(1))
    timestamp = bool(re.search(r"Timestamp=", text))
    ident = re.search(r"Identifier=(.+)", text)
    return {
        "authorities": authority,
        "developer_id": has_devid,
        "hardened_runtime": runtime,
        "secure_timestamp": timestamp,
        "identifier": ident.group(1) if ident else None,
        "signed": "code object is not signed" not in text,
    }


def summarize_app(app):
    info = codesign_info(app)
    print(f"  app: {app}")
    print(f"  bundle id: {info['identifier']}")
    (ok if info["signed"] else bad)("signed" if info["signed"] else "NOT signed")
    (ok if info["developer_id"] else warn)(
        "Developer ID Application certificate" if info["developer_id"]
        else "no Developer ID Application authority (needed for direct distribution)")
    (ok if info["hardened_runtime"] else warn)(
        "Hardened Runtime enabled" if info["hardened_runtime"]
        else "Hardened Runtime OFF (notarization will fail)")
    (ok if info["secure_timestamp"] else warn)(
        "secure timestamp present" if info["secure_timestamp"]
        else "no secure timestamp (sign with --timestamp)")
    return info


def cmd_locate(args):
    app = find_app(args.path)
    if not app:
        bad(f"no .app found under {args.path}")
        sys.exit(1)
    step("Located application")
    summarize_app(app)
    print(f"\nNext (standard flow): notarize-app --app \"{app}\" <creds>   then  build")


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #
def detect_devid_identity():
    r = run(["security", "find-identity", "-v", "-p", "codesigning"])
    ids = re.findall(r'"(Developer ID Application: [^"]+)"', r.stdout or "")
    return ids


def detect_notary_profiles():
    """Best-effort list of saved notarytool keychain profiles. notarytool has no
    'list profiles' command and stores them as keychain items; enumeration is
    not reliable, so this may return []. Treat absence as 'ask the user'."""
    profiles = []
    r = run(["security", "dump-keychain"])
    for m in re.finditer(r'"svce"<blob>="com\.apple\.gke\.notary\.[^"]*"', r.stdout or ""):
        pass  # service rows don't carry the profile label cleanly
    # Fallback: look for account labels referencing notary profiles, if present.
    for m in re.finditer(r'"labl"<blob>="([^"]*[Nn]otary[^"]*)"', r.stdout or ""):
        profiles.append(m.group(1))
    return sorted(set(profiles))


def resolve_signing_identity(args, *, what="DMG"):
    """Return the identity to sign with, or None to leave unsigned. Never picks
    silently: if identities exist and the user didn't choose, print them and
    exit so the caller (the skill) asks which to use."""
    if args.identity:
        return args.identity
    found = detect_devid_identity()
    if not found:
        return None  # caller decides (warn + leave unsigned, or error)
    if getattr(args, "yes", False):
        ok(f"using detected signing identity: {found[0]}")
        return found[0]
    step(f"Signing identity for the {what} — please choose (not auto-selected)")
    for i, f in enumerate(found, 1):
        print(f"  [{i}] {f}")
    print('\nRe-run with --identity "<one of the above>", or pass --yes to use the first.')
    sys.exit(3)


def app_version(app):
    plist = os.path.join(app, "Contents", "Info.plist")
    try:
        with open(plist, "rb") as f:
            d = plistlib.load(f)
        return d.get("CFBundleShortVersionString") or d.get("CFBundleVersion")
    except Exception:
        return None


def cmd_build(args):
    app = find_app(args.app)
    if not app:
        bad(f"no .app at {args.app}"); sys.exit(1)
    name = os.path.splitext(os.path.basename(app))[0]
    volname = args.volname or name
    os.makedirs(args.out, exist_ok=True)
    ver = app_version(app)
    dmg_name = f"{name}{('-' + ver) if ver and args.versioned else ''}.dmg"
    dmg_path = os.path.abspath(os.path.join(args.out, dmg_name))

    # Resolve the signing identity up front (before building anything). If more
    # than the empty case is available and the user didn't choose, this prints
    # the options and exits so the skill can ask which to use.
    ident = resolve_signing_identity(args, what="app/DMG")

    step("Pre-flight: app signing")
    info = summarize_app(app)
    if not (info["developer_id"] and info["hardened_runtime"] and info["secure_timestamp"]):
        if args.sign_app:
            if not ident:
                bad("no Developer ID Application identity found to sign with"); sys.exit(1)
            step(f"Signing app with: {ident}")
            run(["codesign", "--force", "--options", "runtime", "--timestamp",
                 "--sign", ident, app], capture=False, check=True)
            summarize_app(app)
        else:
            warn("app is not fully Developer-ID/hardened/timestamped. Re-export the "
                 "archive with Developer ID, or pass --sign-app --identity \"...\".")
            if not args.force:
                sys.exit(1)

    # Standard flow: the app inside the DMG must itself be notarized + stapled, so
    # it validates offline after a user drags it out. Enforce it here — building a
    # DMG around an un-notarized app is the usual cause of "damaged" Gatekeeper
    # errors on dragged-out apps. Waive only with an explicit flag.
    if not has_stapled_ticket(app):
        if args.allow_unstapled:
            warn("app has NO stapled ticket; packaging it anyway (--allow-unstapled). "
                 "The app copy inside the DMG will not be independently notarized.")
        else:
            bad("app has NO stapled notarization ticket. Notarize the APP first so it "
                "validates offline too, THEN build the DMG from it:")
            print(f"    notarize-app --app \"{app}\" --keychain-profile <profile>")
            print(f"    (or: --api-key AuthKey.p8 --api-key-id KEYID --api-issuer ISSUER)")
            print("  then re-run this build. To skip intentionally (DMG-only "
                  "notarization), pass --allow-unstapled.")
            sys.exit(4)

    step("Building DMG")
    staging = tempfile.mkdtemp(prefix="dmgstage_")
    try:
        shutil.copytree(app, os.path.join(staging, os.path.basename(app)), symlinks=True)
        os.symlink("/Applications", os.path.join(staging, "Applications"))
        if os.path.exists(dmg_path):
            os.remove(dmg_path)
        run(["hdiutil", "create", "-volname", volname, "-srcfolder", staging,
             "-ov", "-format", "UDZO", dmg_path], check=True)
        ok(f"created {dmg_path}")
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    step("Signing DMG")
    if not ident:
        warn("no Developer ID Application identity found — DMG left unsigned. "
             "Notarization REQUIRES a signed DMG.")
    else:
        run(["codesign", "--force", "--sign", ident, "--timestamp", dmg_path], check=True)
        ok(f"signed DMG with {ident}")

    print(f"\nNext (network — confirm with the user first):")
    print(f"  notarize --dmg \"{dmg_path}\" --keychain-profile <your-profile>")


# --------------------------------------------------------------------------- #
# notarize (shared helpers + app + DMG)
# --------------------------------------------------------------------------- #
def resolve_notary_cred(args):
    """notarytool credential args from a keychain profile or the API-key trio.
    Exits with a clear message if neither is fully provided."""
    if getattr(args, "keychain_profile", None):
        return ["--keychain-profile", args.keychain_profile]
    if getattr(args, "api_key", None) and getattr(args, "api_key_id", None) and getattr(args, "api_issuer", None):
        return ["--key", args.api_key, "--key-id", args.api_key_id, "--issuer", args.api_issuer]
    bad("provide --keychain-profile NAME (set up via `setup`) or the API key trio "
        "(--api-key AuthKey.p8 --api-key-id KEYID --api-issuer ISSUER-UUID)")
    sys.exit(1)


def notarize_submit(path, cred, *, what):
    """Submit a file (app .zip or .dmg) to the notary service and wait. On
    failure, fetch and print the notary log, then exit. Returns on success."""
    step(f"Submitting the {what} to Apple notary service (this can take minutes)")
    r = run(["xcrun", "notarytool", "submit", path, *cred, "--wait"], capture=True)
    print(r.stdout)
    if r.returncode != 0 or "status: Accepted" not in (r.stdout or ""):
        bad("notarization did not succeed.")
        sid = re.search(r"id: ([0-9a-f-]{36})", r.stdout or "")
        if sid:
            print(f"  Fetching the log for {sid.group(1)} …")
            log = run(["xcrun", "notarytool", "log", sid.group(1), *cred])
            print(log.stdout or log.stderr)
        sys.exit(1)
    ok("notarization Accepted")


def has_stapled_ticket(path):
    """True if `stapler validate` passes — i.e. a notarization ticket is stapled."""
    return run(["xcrun", "stapler", "validate", path]).returncode == 0


def cmd_notarize_app(args):
    """Notarize + staple the .app ITSELF, before it is packaged into a DMG. This
    is the standard first network step: it makes the app validate offline even
    after a user drags it out of the DMG. Run `build` afterward."""
    app = find_app(args.app)
    if not app:
        bad(f"no .app at {args.app}"); sys.exit(1)
    cred = resolve_notary_cred(args)

    step("Pre-flight: app signing (Developer ID + hardened + timestamp required)")
    info = summarize_app(app)
    if not (info["signed"] and info["developer_id"] and info["hardened_runtime"] and info["secure_timestamp"]):
        bad("app isn't fully Developer-ID/hardened/timestamped — notarization will "
            "fail. Re-export the archive with the Developer ID method first.")
        if not args.force:
            sys.exit(1)

    if has_stapled_ticket(app) and not args.force:
        ok("app already has a stapled notarization ticket — nothing to do "
           "(pass --force to re-notarize).")
        print(f"\nNext: build --app \"{app}\" --out <dir>")
        return

    step("Zipping the app for notarization")
    tmp = tempfile.mkdtemp(prefix="appnotarize_")
    zip_path = os.path.join(tmp, os.path.basename(app) + ".zip")
    try:
        run(["ditto", "-c", "-k", "--keepParent", app, zip_path], check=True)
        ok(f"created {zip_path}")
        notarize_submit(zip_path, cred, what="app")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    step("Stapling the ticket to the .app")
    run(["xcrun", "stapler", "staple", app], capture=False, check=True)
    r = run(["xcrun", "stapler", "validate", app])
    (ok if r.returncode == 0 else bad)("app stapled and validated"
                                       if r.returncode == 0 else "stapling the app failed")
    print(f"\nNext: build --app \"{app}\" --out <dir>   (the DMG will hold the notarized app)")


def cmd_notarize(args):
    dmg = os.path.abspath(args.dmg)
    if not os.path.isfile(dmg):
        bad(f"no DMG at {dmg}"); sys.exit(1)
    cred = resolve_notary_cred(args)

    notarize_submit(dmg, cred, what="DMG")

    step("Stapling the ticket to the DMG")
    run(["xcrun", "stapler", "staple", dmg], capture=False, check=True)
    ok("stapled")
    print("\nNext: verify --dmg \"%s\"" % dmg)


# --------------------------------------------------------------------------- #
# verify
# --------------------------------------------------------------------------- #
def cmd_verify(args):
    failed = False
    if args.app:
        app = find_app(args.app)
        step(f"Verifying app: {app}")
        info = summarize_app(app)
        r = run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", app])
        (ok if r.returncode == 0 else bad)("codesign --verify --deep --strict"
                                           if r.returncode == 0 else "codesign verify FAILED")
        r = run(["spctl", "-a", "-vvv", "-t", "exec", app])
        out = (r.stderr or "") + (r.stdout or "")
        if "Notarized Developer ID" in out:
            ok("Gatekeeper: accepted, Notarized Developer ID")
        elif "accepted" in out:
            warn("Gatekeeper accepted but not reported as Notarized (staple the app?)")
        else:
            bad("Gatekeeper REJECTED the app"); failed = True
        r = run(["xcrun", "stapler", "validate", app])
        (ok if r.returncode == 0 else warn)("app has a stapled ticket"
                                            if r.returncode == 0 else "app not stapled (ok if DMG is stapled)")

    if args.dmg:
        dmg = os.path.abspath(args.dmg)
        step(f"Verifying DMG: {dmg}")
        r = run(["codesign", "--verify", "--verbose=2", dmg])
        (ok if r.returncode == 0 else bad)("DMG signature valid" if r.returncode == 0 else "DMG signature INVALID")
        if r.returncode != 0:
            failed = True
        r = run(["spctl", "-a", "-vvv", "-t", "open", "--context", "context:primary-signature", dmg])
        out = (r.stderr or "") + (r.stdout or "")
        if "accepted" in out:
            ok("Gatekeeper accepts the DMG")
        else:
            bad("Gatekeeper rejects the DMG"); failed = True
        r = run(["xcrun", "stapler", "validate", dmg])
        (ok if r.returncode == 0 else bad)("DMG has a stapled notarization ticket"
                                           if r.returncode == 0 else "DMG NOT stapled")
        if r.returncode != 0:
            failed = True

    if not args.app and not args.dmg:
        bad("pass --app and/or --dmg")
        sys.exit(2)
    print()
    print("❌ verification found problems" if failed else "✅ all checks passed")
    sys.exit(1 if failed else 0)


def cmd_list(args):
    """Show available signing identities and notary credentials so the skill can
    ask the user which to use before signing/notarizing."""
    step("Developer ID Application signing identities (login keychain)")
    found = detect_devid_identity()
    if found:
        for i, f in enumerate(found, 1):
            print(f"  [{i}] {f}")
    else:
        warn("no 'Developer ID Application' certificate found — REQUIRED for "
             "direct distribution + notarization.")
        print("     Create it: Xcode → Settings → Accounts → Manage Certificates")
        print("     → + → Developer ID Application (see references/notarization.md")
        print("     for the certificate-types explanation). Note: Apple Development")
        print("     and Apple Distribution certs will NOT work for this flow.")
    other = [l for l in re.findall(r'"([^"]+)"', (run(["security", "find-identity", "-v", "-p", "codesigning"]).stdout or ""))
             if "Developer ID Application" not in l]
    if other:
        print("  (other signing certs present, NOT usable for this flow: "
              + "; ".join(sorted(set(other))) + ")")

    step("Notary credentials (keychain profiles)")
    profs = detect_notary_profiles()
    if profs:
        for p in profs:
            print(f"  • {p}")
        print("  (best-effort detection; pass the exact profile to `notarize --keychain-profile`)")
    else:
        print("  No notary profile detected (they can't be listed reliably).")
        print("  Set one up with `setup`, then use its name with --keychain-profile.")


def cmd_setup(args):
    print("""One-time notary credential setup.

STEP 1 — create an app-specific password (you do this on Apple's site):
  1. Go to https://account.apple.com  →  Sign-In & Security
  2. App-Specific Passwords  →  +  (Generate)
  3. Name it (e.g. "notarytool") and copy the password it shows ONCE
     (format: abcd-efgh-ijkl-mnop). This is NOT your Apple ID password.

STEP 2 — create the notary keychain profile with the apple-credentials skill
  (same plugin), which owns credentials:

    NOTARY_PASSWORD='abcd-efgh-ijkl-mnop' \\
      python3 <plugin>/skills/apple-credentials/scripts/apple_creds.py store-creds \\
      --profile "MyNotaryProfile" --apple-id "you@example.com" --team-id "ABCDE12345"

  From then on you just pass --keychain-profile "MyNotaryProfile" to `notarize`.

Alternative (CI): an App Store Connect API key (.p8) — pass to `notarize`:
  --api-key /path/AuthKey.p8 --api-key-id KEYID --api-issuer ISSUER-UUID

(`setup` only explains; apple_creds.py's `store-creds` is what creates the profile.)""")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("locate"); s.add_argument("path"); s.set_defaults(func=cmd_locate)

    s = sub.add_parser("list"); s.set_defaults(func=cmd_list)

    s = sub.add_parser("build")
    s.add_argument("--app", required=True, help=".app, .xcarchive, or export dir")
    s.add_argument("--out", required=True, help="output directory for the DMG")
    s.add_argument("--volname", help="DMG volume name (default: app name)")
    s.add_argument("--identity", help='"Developer ID Application: …" (if omitted, the script lists choices and stops — it never auto-picks)')
    s.add_argument("--yes", action="store_true", help="accept the first detected signing identity without asking (CI)")
    s.add_argument("--versioned", action="store_true", help="append app version to the DMG filename")
    s.add_argument("--sign-app", action="store_true", help="(re)sign the app if it isn't Developer-ID/hardened")
    s.add_argument("--force", action="store_true", help="build DMG even if app signing checks fail")
    s.add_argument("--allow-unstapled", action="store_true",
                   help="package the app even if it has no stapled notarization ticket "
                        "(skips the standard notarize-app step — DMG-only notarization)")
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("notarize-app", help="notarize + staple the .app itself (run BEFORE build)")
    s.add_argument("--app", required=True, help=".app, .xcarchive, or export dir")
    s.add_argument("--keychain-profile")
    s.add_argument("--api-key"); s.add_argument("--api-key-id"); s.add_argument("--api-issuer")
    s.add_argument("--force", action="store_true", help="re-notarize even if the app is already stapled / fails pre-flight")
    s.set_defaults(func=cmd_notarize_app)

    s = sub.add_parser("notarize")
    s.add_argument("--dmg", required=True)
    s.add_argument("--keychain-profile")
    s.add_argument("--api-key"); s.add_argument("--api-key-id"); s.add_argument("--api-issuer")
    s.set_defaults(func=cmd_notarize)

    s = sub.add_parser("verify")
    s.add_argument("--app"); s.add_argument("--dmg")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("setup"); s.set_defaults(func=cmd_setup)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
