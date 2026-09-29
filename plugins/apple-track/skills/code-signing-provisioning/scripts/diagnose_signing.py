#!/usr/bin/env python3
"""
diagnose_signing.py — one-shot Apple code-signing diagnostic.

Gathers (and cross-checks) everything that usually causes signing/provisioning
errors, so you don't chase them one at a time:
  - the project's signing build settings per target/config (auto vs manual,
    team, identity, profile specifier)
  - signing identities in the keychain, grouped by certificate TYPE
  - installed provisioning profiles, decoded (name, team, App ID, dev vs
    distribution, EXPIRY, embedded certs)
  - cross-checks: expired profiles, team-id consistency

Usage:
    python3 diagnose_signing.py <project-root> [--json]

Read it as evidence; confirm against the actual error before concluding.
macOS only (uses `security`). Stdlib otherwise.
"""

import argparse
import glob
import json
import os
import plistlib
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

CERT_TYPES = cert_types()

PROFILE_DIRS = [
    os.path.expanduser("~/Library/MobileDevice/Provisioning Profiles"),
    os.path.expanduser("~/Library/Developer/Xcode/UserData/Provisioning Profiles"),
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def list_identities():
    r = run(["security", "find-identity", "-v", "-p", "codesigning"])
    names = re.findall(r'\d+\)\s+[0-9A-F]+\s+"([^"]+)"', r.stdout or "")
    grouped = {}
    for n in names:
        label = next((desc for pref, desc in CERT_TYPES if n.startswith(pref)), "other / unknown")
        team = re.search(r"\(([A-Z0-9]{10})\)", n)
        grouped.setdefault(label, []).append({"name": n, "team": team.group(1) if team else None})
    return grouped, names


def decode_profile(path):
    r = run(["security", "cms", "-D", "-i", path])
    try:
        d = plistlib.loads((r.stdout or "").encode("utf-8", "ignore"))
    except Exception:
        return None
    ent = d.get("Entitlements", {}) or {}
    get_task_allow = ent.get("get-task-allow", False)
    has_devices = bool(d.get("ProvisionedDevices"))
    # classify
    if get_task_allow and has_devices:
        kind = "development"
    elif has_devices:
        kind = "ad-hoc"
    else:
        kind = "distribution (App Store / Developer ID / enterprise)"
    return {
        "file": os.path.basename(path),
        "name": d.get("Name"),
        "team": (d.get("TeamIdentifier") or [None])[0],
        "app_id": ent.get("application-identifier"),
        "platform": d.get("Platform"),
        "kind": kind,
        "expires": str(d.get("ExpirationDate")),
        "num_certs": len(d.get("DeveloperCertificates") or []),
    }


def list_profiles():
    out = []
    for d in PROFILE_DIRS:
        if not os.path.isdir(d):
            continue
        for f in glob.glob(os.path.join(d, "*.mobileprovision")) + glob.glob(os.path.join(d, "*.provisionprofile")):
            info = decode_profile(f)
            if info:
                out.append(info)
    return out


def signing_build_settings(root):
    pbx = glob.glob(os.path.join(root, "*.xcodeproj", "project.pbxproj"))
    pbx += glob.glob(os.path.join(root, "**", "*.xcodeproj", "project.pbxproj"), recursive=True)
    text = ""
    for p in set(pbx):
        try:
            with open(p, "r", errors="ignore") as fh:
                text += fh.read()
        except OSError:
            pass
    keys = ["CODE_SIGN_STYLE", "DEVELOPMENT_TEAM", "CODE_SIGN_IDENTITY",
            "PROVISIONING_PROFILE_SPECIFIER", "PRODUCT_BUNDLE_IDENTIFIER",
            "ENABLE_HARDENED_RUNTIME", "CODE_SIGN_ENTITLEMENTS"]
    settings = {}
    for k in keys:
        vals = sorted(set(re.findall(rf"{k} = ([^;]+);", text)))
        if vals:
            settings[k] = [v.strip().strip('"') for v in vals]
    return settings, bool(pbx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    settings, found = signing_build_settings(root)
    identities, ident_names = list_identities()
    profiles = list_profiles()

    # cross-checks
    teams = set()
    for grp in identities.values():
        for c in grp:
            if c["team"]:
                teams.add(c["team"])
    expired = [p for p in profiles if p["expires"] and p["expires"] < "2026-06-02"]

    report = {
        "project_root": root,
        "signing_build_settings": settings,
        "identities_by_type": identities,
        "provisioning_profiles": profiles,
        "checks": {
            "distinct_teams_in_keychain": sorted(teams),
            "expired_profiles": [p["name"] for p in expired],
        },
    }

    if args.json:
        print(json.dumps(report, indent=2, default=str)); return

    print(f"=== Code-signing diagnostic: {root} ===\n")
    print("▶ Signing build settings" + ("" if found else "  (no .xcodeproj found)"))
    for k, v in settings.items():
        print(f"   {k} = {', '.join(v)}")
    if "CODE_SIGN_STYLE" in settings and "Automatic" in settings["CODE_SIGN_STYLE"]:
        print("   → automatic signing: Xcode creates/renews certs & profiles on demand.")

    print("\n▶ Signing identities in keychain (by type)")
    if not identities:
        print("   ⚠️  none found")
    for label, certs in identities.items():
        for c in certs:
            print(f"   • [{label}] {c['name']}")

    print("\n▶ Provisioning profiles installed")
    if not profiles:
        print("   (none — fine for a pure Developer-ID DMG flow or automatic signing)")
    for p in sorted(profiles, key=lambda x: x["name"] or ""):
        print(f"   • {p['name']}  [{p['kind']}]  team={p['team']}  app={p['app_id']}  expires={p['expires'][:10]}")

    print("\n▶ Cross-checks")
    ts = report["checks"]["distinct_teams_in_keychain"]
    if len(ts) > 1:
        print(f"   ⚠️  multiple team IDs in keychain: {', '.join(ts)} — make sure distribution uses one consistent team.")
    else:
        print(f"   ✅ single team: {ts[0] if ts else 'n/a'}")
    if expired:
        print(f"   ⚠️  expired profiles: {', '.join(p['name'] for p in expired)} — regenerate.")
    else:
        print("   ✅ no expired profiles detected")
    print("\nWhich cert for which goal, and creating one → the apple-credentials skill")


if __name__ == "__main__":
    main()
