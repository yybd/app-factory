#!/usr/bin/env python3
"""Where this machine's Google Play credentials are — asked once, answered one way.

    from credentials import service_account, upload_keystore

Two mechanisms answered this before, and they did not agree:

  * `publish_aab.py` looked for exactly one `.json` in a fixed folder under `$KEYS_ROOT`
    — and gave up when there were none or several, which is right, but it was only ever
    that one folder.
  * `pull_and_diff.sh` grepped `$APP_HUB/DATA.md` for the heading "key fastlane
    playstore" and took the first path-looking string in the three lines after it.

The second cannot be asked of anyone else: it is a heading in one studio's markdown
file. The first is nearly right and now has a name.

**The order, and why:**

    1. the environment          PLAY_SERVICE_ACCOUNT
                                CI sets variables; it does not keep a credentials file.
    2. $KEYS_ROOT/credentials.json      the documented answer.
    3. $KEYS_ROOT/android/api-fastlane-supply/*.json
                                the folder convention, when it holds exactly ONE file.
                                None or several is not an answer: the filename is issued
                                by the Play Console and differs per studio, so guessing
                                which account to publish under is the one mistake that
                                cannot be undone.
    4. $APP_HUB/DATA.md         the studio form that predates this file. Reported as
                                legacy — a fallback nobody is told about becomes the
                                real mechanism.

It returns paths. It never opens the service account, and never prints its contents.
"""
import glob
import json
import os
import re
import sys

ENV_SA = "PLAY_SERVICE_ACCOUNT"


class Missing(Exception):
    """No credential found. Carries what was looked for and where."""


def keys_root():
    return os.path.expanduser(os.environ.get("KEYS_ROOT") or "~/keys")


def _store():
    p = os.path.join(keys_root(), "credentials.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f), p
    except Exception:
        return None, p


def _abs(path):
    p = os.path.expanduser(path)
    return p if os.path.isabs(p) else os.path.join(keys_root(), p)


def service_account(required=True):
    """(path, where_it_came_from) for the Play service-account JSON."""
    v = os.environ.get(ENV_SA)
    if v:
        return _abs(v), "the environment"

    d, store_path = _store()
    sa = ((d or {}).get("googleplay") or {}).get("service_account")
    if sa:
        return _abs(sa), store_path

    folder = os.path.join(keys_root(), "android", "api-fastlane-supply")
    found = sorted(glob.glob(os.path.join(folder, "*.json")))
    if len(found) == 1:
        return found[0], folder
    several = len(found) > 1

    hub = os.environ.get("APP_HUB") or (
        os.path.join(os.environ["DEV_ROOT"], "app-hub") if os.environ.get("DEV_ROOT") else None)
    if hub:
        p = os.path.join(hub, "DATA.md")
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            text = ""
        m = re.search(r"key fastlane playstore.{0,200}?(\S+\.json)", text, re.I | re.S)
        if m:
            return (os.path.expanduser(os.path.expandvars(m.group(1))),
                    p + "  (legacy: move it to credentials.json)")

    if not required:
        return None, None
    extra = (f"\n  {len(found)} .json files are in {folder}; which account to publish "
             f"under is not a guess this should make. Name one in credentials.json."
             if several else "")
    raise Missing(
        "No Google Play service account found. Looked in, in order:\n"
        f"  1. ${ENV_SA} in the environment\n"
        f"  2. {os.path.join(keys_root(), 'credentials.json')}  (googleplay.service_account)\n"
        f"  3. {folder}/*.json, when there is exactly one\n"
        "  4. the hub's DATA.md, for a studio installation\n" + extra + "\n\n"
        "  python3 factory/init_keys.py --create   writes the folder and a template\n"
        "  (run it in the app-factory checkout — ~/.claude/plugins/marketplaces/app-factory\n"
        "  when the marketplace was added from GitHub).\n"
        "  The account itself comes from the Play Console → Setup → API access.")


def upload_keystore(app=None, required=False):
    """The upload keystore's `keystore.properties`, when one is recorded.

    Per app, because a studio signs each app with its own upload key — and Play
    refuses an AAB signed with the wrong one, with a message about the certificate
    rather than about the key you meant to use.
    """
    v = os.environ.get("ANDROID_KEYSTORE_PROPERTIES")
    if v:
        return _abs(v)
    d, _ = _store()
    ks = ((d or {}).get("googleplay") or {}).get("keystores") or {}
    got = ks.get(app) if app else None
    if not got and len(ks) == 1 and not app:
        got = next(iter(ks.values()))
    if got:
        return _abs(got)
    if app:
        guess = os.path.join(keys_root(), "android", f"{app}-keystore", "keystore.properties")
        if os.path.isfile(guess):
            return guess
    if required:
        raise Missing(
            f"No upload keystore recorded{' for ' + app if app else ''}. Put its path "
            f"under googleplay.keystores in {os.path.join(keys_root(), 'credentials.json')}, "
            f"or set $ANDROID_KEYSTORE_PROPERTIES.")
    return None


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Where this machine's Play credentials are.")
    ap.add_argument("--path", action="store_true",
                    help="print the service account's path alone, for a shell script")
    ap.add_argument("--keystore", metavar="APP",
                    help="print the upload keystore's keystore.properties path alone, for one app")
    a = ap.parse_args()
    if a.keystore:
        # The form play-store-ship's build step calls. It existed as a function and not
        # as a flag, so the skill invoked something that returned "unrecognized
        # arguments" — a step a checker that only parses `--help` cannot see.
        try:
            print(upload_keystore(a.keystore, required=True))
            return 0
        except Missing as e:
            print(e, file=sys.stderr)
            return 1
    try:
        p, src = service_account()
    except Missing as e:
        print(e, file=sys.stderr)
        return 1
    if a.path:
        # stdout is the path and nothing else: a caller does `key="$(… --path)"`.
        print(p)
        return 0 if os.path.isfile(p) else 1
    print(f"Play service account: {p}")
    print(f"  {'present' if os.path.isfile(p) else 'NOT FOUND'}  ·  from: {src}")
    k = upload_keystore()
    print(f"Upload keystore: {k or '— none recorded'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
