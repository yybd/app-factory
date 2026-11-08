#!/usr/bin/env python3
"""Set the Play listing's contact email and website — from the hub's DATA.md.

    play_contact.py --package com.x.y --slug <hub-slug> --dry-run   # show, change nothing
    play_contact.py --package com.x.y --slug <hub-slug>             # set, then commit
    play_contact.py --package com.x.y --check                       # read what Play has

`fastlane supply` never sets these: they are store-listing *contact details*, a field
of the app (`edits.details`), not of any locale. That is how one app went out with a
personal address and two with none — nothing in the listing flow ever wrote them.

**Where the values come from.** The hub's `DATA.md`, section `### support mail`:
  contact email   = the support address
  contact website = the app's support URL (its page + #contact) from that section's table
No section: the Contact email (`email_address:`), with a warning. `--email` and
`--website` override both, for a repo with no hub.

**It refuses to publish without an email.** Play requires one before an app can be
published, and an empty field here is the exact failure this exists for — so no email
from DATA.md and none given is a stop, not a skip. A missing website is a warning.

An edit that is never committed changes nothing, which is what makes --dry-run safe:
it opens an edit, reads the current details, prints the change, and deletes the edit.
"""
import argparse, importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHIP = os.path.normpath(os.path.join(HERE, "..", "..", "play-store-ship", "scripts",
                                     "publish_aab.py"))
_spec = importlib.util.spec_from_file_location("ship", SHIP)
ship = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ship)

sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "shared")))
import support_mail  # noqa: E402

API = ship.API
JSON = "application/json; charset=utf-8"


def wanted(slug, email=None, website=None):
    """(email, website, notes) — the values to set, and what was assumed to get them."""
    sm = support_mail.load()
    notes = list(sm.get("warnings", []))
    email = email or sm.get("address")
    if not website:
        website = support_mail.support_url(sm, slug)
        if not website:
            notes.append(f"no support-URL row for '{slug or '?'}' in DATA.md's support-mail "
                         "table — the contact website is left as it is. Add the row.")
    return email, website, notes


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--package", required=True)
    p.add_argument("--slug", help="the app's hub slug (selects its support URL)")
    p.add_argument("--email", help="override the contact email")
    p.add_argument("--website", help="override the contact website")
    p.add_argument("--key", default=ship.default_key(),
                   help=f"service-account JSON (default: the one in {ship.DEFAULT_KEY_DIR})")
    p.add_argument("--dry-run", action="store_true", help="show the change, write nothing")
    p.add_argument("--check", action="store_true",
                   help="print what Play has now and compare it with DATA.md; write nothing")
    a = p.parse_args()

    email, website, notes = wanted(a.slug, a.email, a.website)
    for n in notes:
        print(f"! {n}")
    if not email and not a.check:
        sys.exit("✗ no contact email: DATA.md has no '### support mail' address and no Contact "
                 "email, and --email was not given. Play requires one before the app can be "
                 "published — nothing was written.")

    if not a.key:
        p.error(f"no service account found in {ship.DEFAULT_KEY_DIR} — pass --key")
    tok = ship.token(a.key)

    def call(url, method="GET", body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        return ship.call(tok, url, method, data, JSON if data is not None else None)

    eid = call(f"{API}/{a.package}/edits", "POST", {})["id"]
    ship.CLEANUP.update({"tok": tok, "pkg": a.package, "eid": eid})
    have = call(f"{API}/{a.package}/edits/{eid}/details")
    cur_email, cur_web = have.get("contactEmail") or "", have.get("contactWebsite") or ""
    print(f"Play now:  email={cur_email or '(none)'}  website={cur_web or '(none)'}")
    print(f"DATA.md:   email={email or '(none)'}  website={website or '(unchanged)'}")

    change = {}
    if email and cur_email.lower() != email.lower():
        change["contactEmail"] = email
    if website and support_mail.norm_url(cur_web) != support_mail.norm_url(website):
        change["contactWebsite"] = website

    if a.check or a.dry_run or not change:
        ship.discard_edit()
        if not change:
            print("✓ already matches — nothing to set.")
        else:
            print(("would set: " if a.dry_run else "differs: ") + json.dumps(change))
            if a.check:
                sys.exit(1)
        return

    call(f"{API}/{a.package}/edits/{eid}/details", "PATCH", change)
    call(f"{API}/{a.package}/edits/{eid}:commit", "POST")
    ship.CLEANUP.pop("eid", None)
    print("✓ committed: " + json.dumps(change))


if __name__ == "__main__":
    main()
