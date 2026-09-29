#!/usr/bin/env python3
"""Create the credentials folder the shipping skills expect — or point at an existing one.

    python3 factory/init_keys.py            # what is there, what is missing
    python3 factory/init_keys.py --create   # make the skeleton
    python3 factory/init_keys.py --point ~/vault/studio-keys

Every skill that signs or uploads needs secrets it must never find in a repo: a Play
signing keystore, a Play service account, an App Store Connect API key. They are named
in the skills as `$KEYS_ROOT/…` and nowhere as a path, so the folder can be called
anything and live anywhere — but it has to EXIST, and on a fresh machine it does not.
That gap used to surface halfway through a release, as a file-not-found on a key.

So this offers the two answers a person actually has:

    --create   I do not have one. Make the skeleton, and tell me what goes in each slot.
    --point    I have one already, somewhere else. Write that down instead.

It never writes a secret, never copies one, and never overwrites a file that exists.
What it makes is empty folders, a README describing what belongs in each, and — first,
because the whole point is that these never reach a repo — a .gitignore that refuses
everything.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from grove import scripts as _grove_scripts, MISSING as _GROVE_MISSING   # noqa: E402


class _Grove:
    """grove_repo, resolved on first use instead of at import.

    This block used to call `sys.exit()` at module level when grove was not on the
    machine. That is the right answer for a run — this script reads grove's registry
    and cannot work without it — but it is the wrong answer for `--help`, which
    exited the same way. So on a machine with only this repo, the script could not
    even say what it was for, and `check_scripts.py`'s usage check failed on it.

    Deferring costs nothing: the first attribute access happens well after argparse,
    and the message is unchanged.
    """

    _mod = None

    def __getattr__(self, name):
        if _Grove._mod is None:
            s = _grove_scripts()
            if not s:
                sys.exit("\u2717 " + _GROVE_MISSING)
            sys.path.insert(0, s)
            import grove_repo
            _Grove._mod = grove_repo
        return getattr(_Grove._mod, name)


fr = _Grove()

# What the shipping skills look for, and the skill that needs each one. Kept here rather
# than in prose so `--create` and the report can never describe different folders.
SLOTS = [
    ("android/<app>-keystore/keystore.properties",
     "play-store-ship", "the upload key for one app: storeFile, storePassword, keyAlias, keyPassword"),
    ("android/api-fastlane-supply/<service-account>.json",
     "play-store-ship · play-store-deliver", "Google Play service account, JSON, from the Play Console"),
    ("appstoreconnect/AuthKey_<KEYID>.p8",
     "app-store-deliver · ship-apple-app", "App Store Connect API key — with its key id and issuer id"),
    ("appstoreconnect/notarytool/",
     "notarize-and-distribute", "the notarisation profile or app-specific password"),
]

GITIGNORE = """# Everything here is a secret. Nothing here belongs in any repository.
*
!.gitignore
!README.md
"""

# The one file that says where each credential is. Before it, three scripts answered
# that question three ways — a folder convention, a heading grepped out of a markdown
# file in another repo, and a labelled line called `n8:` — and no developer but the one
# who wrote them had any of the three.
#
# It holds identifiers and PATHS. The keys themselves stay where they are; nothing here
# is ever read for its contents by the resolver, and nothing is ever copied into a repo.
CREDENTIALS = """{
  "_comment": "Where each credential is. Paths may be absolute, or relative to this folder. Every value here is an identifier or a path — never a secret.",

  "appstoreconnect": {
    "_where": "App Store Connect -> Users and Access -> Integrations -> App Store Connect API",
    "issuer_id": "<uuid>",
    "key_id": "<10 characters>",
    "p8": "appstoreconnect/AuthKey_<KEYID>.p8"
  },

  "notary": {
    "_where": "created by `apple_creds.py store-creds --profile <name> ...`; this is the NAME, and the credential itself lives in the login keychain",
    "keychain_profile": "<profile name>"
  },

  "googleplay": {
    "_where": "Play Console -> Setup -> API access -> service accounts",
    "service_account": "android/api-fastlane-supply/<service-account>.json",
    "keystores": {
      "_comment": "One upload key per app, by the app's name. Play refuses an AAB signed with the wrong one, and says so in terms of the certificate rather than the key you meant.",
      "<app>": "android/<app>-keystore/keystore.properties"
    }
  }
}
"""

README = """# Credentials

Referred to by every shipping skill as `$KEYS_ROOT`. Nothing in this folder is ever
committed, copied into a repo, or printed — the skills read it in place.

Where the factory looks, in order: the `KEYS_ROOT` environment variable, then
`keys_root` in grove's registry (relative to the tree's base), then `keys`
beside the other repos.

## What goes where

{slots}

## What this is not

Not an index of the values. The studio-level notes — which account, which vendor
number, which bundle id — belong in the hub's `DATA.md`. This folder holds the FILES.
"""


def report(root):
    print(f"Credentials folder: {short(root)}")
    if not os.path.isdir(root):
        print("  ✗ does not exist.\n")
        print("  Create it:            python3 factory/init_keys.py --create")
        print("  Or point at one:      python3 factory/init_keys.py --point <path>")
        return 1
    missing = []
    for slot, who, _what in SLOTS:
        head = slot.split("/")[0]
        if not os.path.isdir(os.path.join(root, head)):
            missing.append((head, who))
    has_creds = os.path.isfile(os.path.join(root, "credentials.json"))
    if not missing and has_creds:
        print("  ✓ it is there, with every folder the skills look for, and a credentials.json.")
        return 0
    if not has_creds:
        print("  Missing: credentials.json — the one file that says where each credential is.")
        print("      Without it the skills fall back to a folder convention and to the hub's")
        print("      DATA.md, both of which still work and neither of which is documented")
        print("      anywhere a new installation would find.")
    if not missing:
        print("\n  To fill in:  python3 factory/init_keys.py --create")
        return 0
    print("  ✓ it is there. Missing from it:")
    for head, who in sorted(set(missing)):
        print(f"      {head}/   ({who})")
    print("\n  To fill in:  python3 factory/init_keys.py --create")
    return 0                                    # missing slots are not a failure


def create(root):
    made = []
    os.makedirs(root, exist_ok=True)
    gi = os.path.join(root, ".gitignore")
    if not os.path.exists(gi):                  # first, before anything can be put here
        open(gi, "w", encoding="utf-8").write(GITIGNORE)
        made.append(".gitignore")
    for slot, _who, _what in SLOTS:
        d = os.path.join(root, os.path.dirname(slot))
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
            made.append(os.path.relpath(d, root) + "/")
    cj = os.path.join(root, "credentials.json")
    if not os.path.exists(cj):
        open(cj, "w", encoding="utf-8").write(CREDENTIALS)
        made.append("credentials.json")
    rd = os.path.join(root, "README.md")
    if not os.path.exists(rd):
        slots = "\n".join(f"- `{s}`\n  {w} — *{who}*" for s, who, w in SLOTS)
        open(rd, "w", encoding="utf-8").write(README.format(slots=slots))
        made.append("README.md")
    print(f"Credentials folder: {short(root)}")
    if made:
        for m in made:
            print(f"  + {m}")
    else:
        print("  Everything was already there. Nothing was touched.")
    print("\nThe secrets themselves go in by hand. The skills read them in place and copy them into no repo.")
    return 0


def point(path):
    """Write the location into the registry — the one place that names it."""
    target = os.path.realpath(os.path.expanduser(path))
    if not os.path.isdir(target):
        print(f"✗ {short(target)} is not an existing directory. Create it first, or use --create instead.")
        return 2
    if not _grove_scripts():
        print(f"Without grove there is no registry to record {short(target)} in.")
        print("Point the skills at it with the variable instead — in your shell, or in")
        print("~/.claude/settings.json under `env`:")
        print(f'    "KEYS_ROOT": "{target}"')
        return 0
    reg_path = fr.registry_path()
    with open(reg_path, encoding="utf-8") as f:
        reg = json.load(f)
    base = fr.dev_base()
    value = os.path.relpath(target, base) if base and target.startswith(base + os.sep) else target
    if reg.get("keys_root") == value:
        print(f"The registry already points at {short(target)}.")
        return 0
    reg["keys_root"] = value
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"The registry now points at {short(target)}  (written as \"{value}\")")
    print("Run  python3 factory/deploy.py  so $KEYS_ROOT is updated in the environment too.")
    return 0


def short(p):
    home = os.path.expanduser("~")
    return "~" + p[len(home):] if p.startswith(home + os.sep) else p


def main():
    ap = argparse.ArgumentParser(description="The credentials folder the shipping skills expect.")
    ap.add_argument("--create", action="store_true", help="make the skeleton where the registry says")
    ap.add_argument("--point", metavar="PATH", help="use an existing folder instead, and record it")
    a = ap.parse_args()
    if a.point:
        return point(a.point)
    # The environment first, grove after. $KEYS_ROOT is the contract every resolver in
    # the tracks reads; a person who set it has answered the question this script asks
    # the registry, and QUICKSTART tells them to set it — so failing here for want of
    # grove was failing the reader who did exactly what the page said.
    root = os.environ.get("KEYS_ROOT")
    root = os.path.expanduser(root) if root else fr.keys_root()
    if not root:
        print("✗ could not work out where the tree sits, and so neither where the keys are.")
        return 2
    return create(root) if a.create else report(root)


if __name__ == "__main__":
    sys.exit(main())
