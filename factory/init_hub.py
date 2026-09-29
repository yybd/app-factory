#!/usr/bin/env python3
"""Create the hub the shipping skills read from — or point at an existing one.

    python3 factory/init_hub.py            # what is there, what is missing
    python3 factory/init_hub.py --create   # make the skeleton
    python3 factory/init_hub.py --app <slug>   # add one app's folders to an existing hub

**32 of the 39 skills can read `$APP_HUB`.** They need a profile to write copy from, studio
facts they should not have to ask for, and somewhere to put store metadata and media. On a
fresh installation none of that exists, and the skills fail one by one at the step each of
them guards — which is the worst place to discover a missing folder.

What this makes is a skeleton and the documents that explain it: `DATA.md` and
`PRODUCT.md` as templates with the fields named, and a per-app tree. **It writes no
content it could not know** — every field is left as a placeholder for a person to fill,
because a studio's contact details and voice are not derivable.

The full contract — what each file must contain and who reads it — is in
`docs/contracts/hub.md`. This script creates what that document describes.

Never overwrites a file that exists. A hub that is already set up is only reported on.
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

# What the skills look for at the hub root, and what depends on each. Kept here rather
# than in prose so the report and `--create` can never describe different things.
ROOT_FILES = [
    ("DATA.md", "studio-wide facts: contact, copyright, default URLs, API key paths",
     "app-store-metadata · store-metadata-writer · both deliver skills"),
    ("PRODUCT.md", "the product voice every copy skill holds to", "copy-edit · every copy skill"),
]
ROOT_OPTIONAL = [
    ("prices.json", "every app's price in one file", "price-sync"),
]
# One app's tree. `store/` and `media/` are written by the skills; the folders are made
# here so the first run has somewhere to land rather than failing on a missing parent.
APP_TREE = [
    "store/apple/metadata",
    "store/apple/metadata/review_information",
    # Read by app-store-deliver's sync_from_hub.sh, which looks for
    # release-notes/<version>/<locale>.txt and stops when it is not there. It was in
    # no APP_TREE and in no contract — so the first release in a hub this script had
    # created failed on a folder this script was supposed to have made.
    "store/apple/release-notes",
    "store/apple/iap",
    "store/play/metadata",
    "store/play/changelogs",
    "store/play/iap",
    "media/apple",
    "media/play",
]

DATA_MD = """# DATA — studio-wide facts

Read by the shipping skills instead of asking you. Fill each field once; every app uses
these unless its own profile overrides them.

**The secrets themselves are not here.** This file holds identifiers and paths only — the
key files live under `$KEYS_ROOT`, which is not a git directory.

## Contact (App Store review information)

- name: <a person the reviewer can reach>
- email_address: <email>
- phone number: <+country number>

## Copyright

- `<year> <Studio Name>`

## Default URLs

`{app-slug}` is substituted per app.

- marketing: `https://<your-site>/apps/{app-slug}/`
- support: `https://<your-site>/support/`
- privacy: `https://<your-site>/privacy-policy/{app-slug}/`

## App Store Connect API key

- issuer id: <uuid>
- key id: <10 characters>
- p8 path: `$KEYS_ROOT/appstoreconnect/AuthKey_<KEYID>.p8`

## Google Play service account

- json path: `$KEYS_ROOT/android/api-fastlane-supply/<service-account>.json`

## Conversational language (optional)

- conversational language: <leave unset to answer in whatever language you write in>
"""

PRODUCT_MD = """# PRODUCT — the voice

How everything this studio ships sounds. Every skill that writes customer-facing text
reads this, and `copy-edit` enforces it.

## What we sound like

<two or three sentences. Concrete, not adjectives.>

## Always

- <a habit worth keeping — e.g. "say what the app does before why it is good">

## Never

- <a word or move that is banned here, and why>

## Words we use / words we avoid

| Use | Avoid | Why |
|---|---|---|
| <word> | <word> | <the reason> |
"""

HUB_README = """# The hub

The data layer for every app: profiles, store listings in every language, media, prices.
Not code, and not a website.

Its structure is a contract the factory's skills rely on — see `docs/contracts/hub.md`
in the factory. `python3 factory/init_hub.py` reports whether this hub satisfies it.

```
DATA.md         studio-wide facts
PRODUCT.md      the voice
prices.json     every app's price          [price-sync]
<slug>/         one directory per app
  profile.md    THE source of truth for all copy
  store/        listings — written by the skills, not by hand
  media/        screenshots and previews
```
"""

PROFILE_STUB = """# {slug}

*Written by `app-profile`, which reads the app's source and interviews you. This stub
exists so the folder is not empty — run the skill to replace it.*

- **Slug:** {slug}
- **Last updated:** <date>
- **Project:** <path to the app's repo>

## What it is

<one paragraph a stranger would understand>
"""


def short(p):
    home = os.path.expanduser("~")
    return "~" + p[len(home):] if p.startswith(home + os.sep) else p


def apps_in(root):
    """Slugs already present — a directory with a profile.md, or one the registry names."""
    out = set()
    try:
        for n in os.listdir(root):
            if os.path.isfile(os.path.join(root, n, "profile.md")):
                out.add(n)
    except Exception:
        pass
    return sorted(out)


def report(root):
    print(f"Hub: {short(root)}")
    if not os.path.isdir(root):
        print("  ✗ does not exist.\n")
        print("  Create it:            python3 factory/init_hub.py --create")
        print("  Or point at one:      edit `app-hub` in $GROVE/tools/registry.json")
        print("\n  32 of the 39 skills can read it — and every one works without it.")
        return 1
    missing = [(f, why) for f, why, _ in ROOT_FILES if not os.path.exists(os.path.join(root, f))]
    apps = apps_in(root)
    if not missing and apps:
        print(f"  ✓ set up, with {len(apps)} app{'s' if len(apps) != 1 else ''}: {', '.join(apps[:6])}"
              + (" …" if len(apps) > 6 else ""))
        return 0
    if missing:
        print("  Missing at the root:")
        for f, why in missing:
            print(f"      {f:14} {why}")
    if not apps:
        print("  No app has a profile.md yet — `app-profile` writes the first one,")
        print("  or `python3 factory/init_hub.py --app <slug>` makes the folders.")
    print("\n  To fill in:  python3 factory/init_hub.py --create")
    return 0                                    # an incomplete hub is not a failure


def make_app(root, slug):
    made = []
    for d in APP_TREE:
        p = os.path.join(root, slug, d)
        if not os.path.isdir(p):
            os.makedirs(p, exist_ok=True)
            made.append(os.path.join(slug, d) + "/")
    prof = os.path.join(root, slug, "profile.md")
    if not os.path.exists(prof):
        open(prof, "w", encoding="utf-8").write(PROFILE_STUB.format(slug=slug))
        made.append(os.path.join(slug, "profile.md"))
    return made


def create(root, slug=None):
    made = []
    os.makedirs(root, exist_ok=True)
    for name, body in (("DATA.md", DATA_MD), ("PRODUCT.md", PRODUCT_MD),
                       ("README.md", HUB_README)):
        p = os.path.join(root, name)
        if not os.path.exists(p):
            open(p, "w", encoding="utf-8").write(body)
            made.append(name)
    if slug:
        made += make_app(root, slug)
    print(f"Hub: {short(root)}")
    if made:
        for m in made:
            print(f"  + {m}")
    else:
        print("  Everything was already there. Nothing was touched.")
    print("\nFill in DATA.md and PRODUCT.md by hand — the contact details and the voice are")
    print("the two things no skill can derive. Everything else the skills write for you.")
    print("The contract: docs/contracts/hub.md")
    return 0


def hub_root():
    """$APP_HUB, else $DEV_ROOT/app-hub, else where grove's registry says.

    `app-hub` is the name the skills assume. The environment is read first because it
    is the contract the skills themselves read (`docs/contracts/hub.md`), and because
    a machine with only this repo has no registry — QUICKSTART's "you do not need
    grove" was false at exactly this line.
    """
    env = os.environ.get("APP_HUB")
    if env:
        return os.path.expanduser(env)
    base = os.environ.get("DEV_ROOT")
    if base:
        return os.path.join(os.path.expanduser(base), "app-hub")
    if not _grove_scripts():
        return None
    try:
        with open(fr.registry_path(), encoding="utf-8") as f:
            reg = json.load(f)
    except Exception:
        reg = {}
    entry = (reg.get("projects") or {}).get("app-hub")
    named = entry.get("root") if isinstance(entry, dict) else None
    return fr.resolve_root(named or "app-hub")


def main():
    ap = argparse.ArgumentParser(description="The hub the shipping skills read from.")
    ap.add_argument("--create", action="store_true", help="make the skeleton where the registry says")
    ap.add_argument("--app", metavar="SLUG", help="also make one app's folders")
    a = ap.parse_args()
    root = hub_root()
    if not root:
        print("✗ could not work out where the tree sits, and so neither where the hub is.")
        return 2
    if a.create or a.app:
        return create(root, a.app)
    return report(root)


if __name__ == "__main__":
    sys.exit(main())
