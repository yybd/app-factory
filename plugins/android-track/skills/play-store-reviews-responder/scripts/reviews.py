#!/usr/bin/env python3
"""List and reply to Google Play reviews via the Play Developer API.

`reviews.list` only returns reviews from about the last WEEK, and only those
that carry text — an empty result means "nothing in the window", not "no
reviews". Older ones are in the Console's CSV exports.

  reviews.py --package com.x.y --list
  reviews.py --package com.x.y --reply <reviewId> --text "…"
"""
import argparse, importlib.util, os, sys, json, urllib.parse

# play-store-ship ships in this same plugin, so locate it relative to this file:
# an absolute path breaks the moment the plugin is installed anywhere else, and the
# install path is pinned to a commit sha.
SHIP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "play-store-ship", "scripts",
                                     "publish_aab.py"))
_spec = importlib.util.spec_from_file_location("ship", SHIP)
ship = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ship)          # reuse token() / call() — one auth implementation

API = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--package", required=True)
    # publish_aab resolves the service account through default_key(), which returns None
    # when the credentials folder holds none or several — the filename is issued by the
    # Play Console and differs per studio, so it cannot be written here. This used to
    # read `ship.DEFAULT_KEY`, a name that module never defined: the AttributeError fired
    # at argparse construction, so `--help` itself raised and the skill could not be used
    # at all. `check_scripts.py` did not see it, because parsing and importing both
    # succeed — only running the file fails.
    p.add_argument("--key", default=ship.default_key(),
                   help=f"service-account JSON (default: the one in {ship.DEFAULT_KEY_DIR})")
    p.add_argument("--list", action="store_true")
    p.add_argument("--reply", metavar="REVIEW_ID")
    p.add_argument("--text")
    p.add_argument("--translation-language", help="also fetch reviews translated to this locale")
    a = p.parse_args()
    if not a.key:
        p.error(f"no service account found in {ship.DEFAULT_KEY_DIR} — pass --key, or run "
                f"`python3 factory/init_keys.py --create` in the app-factory checkout "
                f"and put the JSON there")

    tok = ship.token(a.key)

    if a.reply:
        if not a.text:
            sys.exit("--reply needs --text")
        if len(a.text) > 350:
            sys.exit(f"reply is {len(a.text)} characters; Play allows 350")
        body = json.dumps({"replyText": a.text}, ensure_ascii=False).encode("utf-8")
        r = ship.call(tok, f"{API}/{a.package}/reviews/{a.reply}:reply", "POST", body,
                      "application/json; charset=utf-8")
        print("replied:", r.get("result", {}).get("lastEdited", "ok"))
        return

    url = f"{API}/{a.package}/reviews"
    if a.translation_language:
        url += "?" + urllib.parse.urlencode({"translationLanguage": a.translation_language})
    reviews = ship.call(tok, url).get("reviews", [])
    if not reviews:
        print("no reviews in the API window (about the last week, text reviews only).\n"
              "Older reviews: Play Console → Download reports → Reviews.")
        return
    for rv in reviews:
        c = rv["comments"][0]["userComment"]
        stars = "★" * int(c.get("starRating", 0)) + "☆" * (5 - int(c.get("starRating", 0)))
        print(f'\n{stars}  {rv.get("authorName") or "—"}   id={rv["reviewId"]}')
        print(f'   {c.get("appVersionName","?")} · {c.get("device","?")} · {c.get("reviewerLanguage","?")}')
        print(f'   {(c.get("text") or "").strip()}')
        for cm in rv["comments"][1:]:
            if "developerComment" in cm:
                print(f'   ↳ already replied: {cm["developerComment"]["text"][:120]}')
    print(f"\n{len(reviews)} review(s). Draft replies, show the user, and post only "
          "what they approve — a reply is public and immediate.")


if __name__ == "__main__":
    main()
