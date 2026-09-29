#!/usr/bin/env python3
"""Where this machine's Apple credentials are — asked once, answered one way.

    from credentials import asc_key, notary_profile

Three mechanisms answered this question before, and they disagreed about almost
everything:

  * `asc_common.rb` read `$APP_HUB/DATA.md` and pulled the issuer id, key id and `.p8`
    path out of **prose**, by regex, including a line labelled `n8:` — a convention
    that exists in one studio's markdown file and nowhere else in the world.
  * `publish_aab.py` looked for exactly one `.json` in a fixed folder under `$KEYS_ROOT`.
  * `pull_and_diff.sh` grepped DATA.md for a heading and took the first path-looking
    string after it.

Any developer who is not this one has none of those. A product cannot ask them to
reproduce a heading in a markdown file.

**The order, and why it is this order:**

    1. the environment      ASC_KEY_ID / ASC_ISSUER_ID / ASC_KEY_PATH
                            CI sets variables; it does not keep a credentials file.
    2. $KEYS_ROOT/credentials.json
                            the documented answer, and what `factory/init_keys.py`
                            writes a template for.
    3. $APP_HUB/DATA.md     the studio form that predates this file. Still read, so
                            an existing setup keeps working — and reported as legacy,
                            because a fallback nobody is told about is a fallback that
                            becomes the real mechanism.

**It returns paths and identifiers, never secrets.** The `.p8` is opened by the tool
that signs with it; nothing here reads its bytes, and nothing here prints them.
"""
import json
import os

ENV_KEY_ID = "ASC_KEY_ID"
ENV_ISSUER = "ASC_ISSUER_ID"
ENV_P8 = "ASC_KEY_PATH"


class Missing(Exception):
    """No credential found. Carries what was looked for and where."""


def keys_root():
    return os.path.expanduser(os.environ.get("KEYS_ROOT") or "~/keys")


def _from_env():
    kid, iss, p8 = (os.environ.get(ENV_KEY_ID), os.environ.get(ENV_ISSUER),
                    os.environ.get(ENV_P8))
    if kid and iss and p8:
        return {"key_id": kid, "issuer_id": iss, "p8": os.path.expanduser(p8),
                "_from": "the environment"}
    return None


def _store():
    p = os.path.join(keys_root(), "credentials.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f), p
    except Exception:
        return None, p


def _from_store():
    d, p = _store()
    if not d:
        return None
    a = d.get("appstoreconnect") or {}
    if not (a.get("key_id") and a.get("issuer_id") and a.get("p8")):
        return None
    p8 = os.path.expanduser(a["p8"])
    if not os.path.isabs(p8):
        p8 = os.path.join(keys_root(), p8)         # relative to the credentials folder
    return {"key_id": a["key_id"], "issuer_id": a["issuer_id"], "p8": p8,
            "_from": p}


def _from_data_md():
    """The studio form: labelled lines in the hub's DATA.md. Kept so an existing
    installation does not break on the day this file appears."""
    import re
    hub = os.environ.get("APP_HUB")
    if not hub:
        root = os.environ.get("DEV_ROOT")
        hub = os.path.join(root, "app-hub") if root else None
    if not hub:
        return None
    p = os.path.join(hub, "DATA.md")
    try:
        # DATA.md may hold any language; without an explicit encoding Python reads it
        # as the locale's, which raises on a bare shell where LANG is unset.
        text = open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return None
    kid = re.search(r"key id:\s*(\S+)", text, re.I)
    iss = re.search(r"issuer id:\s*(\S+)", text, re.I)
    p8 = re.search(r"^\s*(?:n8|p8|key path):\s*(\S+)", text, re.I | re.M)
    if not (kid and iss and p8):
        return None
    return {"key_id": kid.group(1), "issuer_id": iss.group(1),
            "p8": os.path.expanduser(os.path.expandvars(p8.group(1))),
            "_from": p + "  (legacy: move it to credentials.json)"}


def asc_key(required=True):
    """{key_id, issuer_id, p8, _from} for App Store Connect, or raise."""
    for source in (_from_env, _from_store, _from_data_md):
        got = source()
        if got:
            return got
    if not required:
        return None
    raise Missing(
        "No App Store Connect credential found. Looked in, in order:\n"
        f"  1. ${ENV_KEY_ID} / ${ENV_ISSUER} / ${ENV_P8} in the environment\n"
        f"  2. {os.path.join(keys_root(), 'credentials.json')}  (appstoreconnect)\n"
        "  3. the hub's DATA.md, for a studio installation\n\n"
        "  python3 factory/init_keys.py --create   writes the folder and a template\n"
        "  (run it in the app-factory checkout — ~/.claude/plugins/marketplaces/app-factory\n"
        "  when the marketplace was added from GitHub).\n"
        "  The key itself comes from App Store Connect → Users and Access → Integrations.")


def notary_profile(required=False):
    """The `notarytool` keychain profile name, when one is recorded."""
    v = os.environ.get("NOTARY_PROFILE")
    if v:
        return v
    d, _ = _store()
    v = ((d or {}).get("notary") or {}).get("keychain_profile")
    if v or not required:
        return v
    raise Missing("No notary keychain profile recorded. Create one with "
                  "`apple_creds.py store-creds --profile <name> …`, then put that name "
                  "under \"notary\" in credentials.json.")


if __name__ == "__main__":
    try:
        k = asc_key()
        print(f"App Store Connect: key {k['key_id']}, issuer {k['issuer_id']}")
        print(f"  .p8: {k['p8']}  {'(present)' if os.path.isfile(k['p8']) else '(NOT FOUND)'}")
        print(f"  from: {k['_from']}")
    except Missing as e:
        print(e)
    n = notary_profile()
    print(f"Notary profile: {n or '— none recorded'}")
