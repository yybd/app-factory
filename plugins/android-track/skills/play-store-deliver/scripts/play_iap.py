#!/usr/bin/env python3
"""Upsert and activate a Play one-time product from the hub.

Reads <hub>/<slug>/store/play/iap/<product-id>/ and runs the monetization flow:
convertRegionPrices (base price -> every region) -> oneTimeProducts.patch with
allowMissing (an upsert) -> purchaseOptions:batchUpdateStates to activate.

The old `inappproducts` resource answers 403 "Please migrate to the new publishing
API" for every app, and a 403 from a retired endpoint looks exactly like a
permissions problem. This script does not touch it.

Two traps it checks for before writing anything:
  * the product must have a listing in the app's DEFAULT listing language — which
    is whatever the Console says, not necessarily en-US;
  * convertRegionPrices answers 400 FAILED_PRECONDITION until the developer account
    has a payments profile.

  play_iap.py --package com.x.y --dir $APP_HUB/<slug>/store/play/iap/<id> --dry-run
  play_iap.py --package com.x.y --dir $APP_HUB/<slug>/store/play/iap/<id>
  play_iap.py --package com.x.y --list
"""
import argparse, importlib.util, json, os, re, sys, urllib.parse
from decimal import Decimal

# play-store-ship ships in this same plugin, so locate it relative to this file:
# one auth implementation, the same as reviews.py.
SHIP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "play-store-ship", "scripts",
                                     "publish_aab.py"))
_spec = importlib.util.spec_from_file_location("ship", SHIP)
ship = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ship)

API = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
JSON = "application/json; charset=utf-8"
TITLE_MAX, DESC_MAX = 55, 200


def call(tok, url, method="GET", body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    try:
        return ship.call(tok, url, method, data, JSON if data is not None else None)
    except SystemExit as e:
        msg = str(e.code)
        if "convertRegionPrices" in url and "FAILED_PRECONDITION" in msg:
            msg += ("\n\nconvertRegionPrices refuses until the developer account has a "
                    "payments profile (Console → Settings → Payments profile). Nothing "
                    "was written.")
        if "inappproducts" in url or "migrate to the new publishing API" in msg:
            msg += "\n\nThat is the retired inappproducts path — use oneTimeProducts."
        sys.exit(msg)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().strip()


def base_price(d):
    """(amount, currency) from price.txt, else from a `price:` line in product.txt.

    Only the first `<amount> <CURRENCY>` is read; the rest of the line is free prose.
    Never guessed: no price in the hub is a stop.
    """
    for name, pat in (("price.txt", r"^(?:price:\s*)?([0-9]+(?:\.[0-9]+)?)\s+([A-Z]{3})\b"),
                      ("product.txt", r"^price:\s*([0-9]+(?:\.[0-9]+)?)\s+([A-Z]{3})\b")):
        f = os.path.join(d, name)
        if os.path.exists(f):
            m = re.search(pat, read(f), re.M)
            if m:
                return Decimal(m.group(1)), m.group(2)
    sys.exit(f"no base price in {d} — expected price.txt `6.99 USD`, or a "
             f"`price: 6.99 USD` line in product.txt. Author it with play-store-metadata.")


def listings(d):
    """One listing per <locale>/ folder: name.txt (or title.txt) + description.txt."""
    out, errors = [], []
    for loc in sorted(os.listdir(d)):
        ld = os.path.join(d, loc)
        if not os.path.isdir(ld):
            continue
        tf = next((os.path.join(ld, n) for n in ("name.txt", "title.txt")
                   if os.path.exists(os.path.join(ld, n))), None)
        df = os.path.join(ld, "description.txt")
        if not tf or not os.path.exists(df):
            errors.append(f"{loc}: needs name.txt (or title.txt) and description.txt")
            continue
        title, desc = read(tf), read(df)
        if not title or len(title) > TITLE_MAX:
            errors.append(f"{loc}: title is {len(title)} chars (1–{TITLE_MAX})")
        if not desc or len(desc) > DESC_MAX:
            errors.append(f"{loc}: description is {len(desc)} chars (1–{DESC_MAX})")
        out.append({"languageCode": loc, "title": title, "description": desc})
    if errors:
        sys.exit("hub listings are not ready:\n  " + "\n  ".join(errors))
    if not out:
        sys.exit(f"no <locale>/ listing folders in {d}")
    return out


def default_language(tok, pkg):
    """The app's default listing language, read from an edit that is then dropped."""
    eid = call(tok, f"{API}/{pkg}/edits", "POST", {})["id"]
    try:
        return call(tok, f"{API}/{pkg}/edits/{eid}/details").get("defaultLanguage")
    finally:
        call(tok, f"{API}/{pkg}/edits/{eid}", "DELETE")


def money(amount, currency):
    units = int(amount)
    return {"currencyCode": currency, "units": str(units),
            "nanos": int((amount - units) * 1_000_000_000)}


def show(product):
    print(f'  {product.get("productId")}  listings: '
          f'{", ".join(l["languageCode"] for l in product.get("listings", []))}')
    for o in product.get("purchaseOptions", []):
        n = len(o.get("regionalPricingAndAvailabilityConfigs", []))
        print(f'    option {o.get("purchaseOptionId")}: {o.get("state")}  ({n} regions)')


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--package", required=True)
    p.add_argument("--key", default=ship.default_key(),
                   help=f"service-account JSON (default: the one in {ship.DEFAULT_KEY_DIR})")
    p.add_argument("--dir", help="<hub>/<slug>/store/play/iap/<product-id>/")
    p.add_argument("--product-id", help="default: the folder's name")
    p.add_argument("--option-id", default="buy",
                   help="purchase option id (default: buy)")
    p.add_argument("--list", action="store_true", help="list the app's one-time products")
    p.add_argument("--no-activate", action="store_true",
                   help="write the product but leave the purchase option inactive")
    p.add_argument("--dry-run", action="store_true",
                   help="validate, convert prices, print the body — write nothing")
    a = p.parse_args()
    if not a.key:
        p.error(f"no service account found in {ship.DEFAULT_KEY_DIR} — pass --key")
    tok = ship.token(a.key)

    if a.list:
        for prod in call(tok, f"{API}/{a.package}/oneTimeProducts").get("oneTimeProducts", []):
            show(prod)
        return
    if not a.dir:
        p.error("--dir is required (or --list)")

    d = os.path.abspath(a.dir)
    pid = a.product_id or os.path.basename(d.rstrip("/"))
    amount, currency = base_price(d)
    lst = listings(d)

    lang = default_language(tok, a.package)
    if lang and lang not in {l["languageCode"] for l in lst}:
        sys.exit(f"the app's default listing language is {lang} and the hub has no "
                 f"{lang}/ folder for {pid}. Play refuses a product without it — "
                 f"author {lang}/ with play-store-metadata.")
    print(f"{pid}: {amount} {currency} base, listings {', '.join(l['languageCode'] for l in lst)}"
          f" (default {lang})")

    conv = call(tok, f"{API}/{a.package}/pricing:convertRegionPrices", "POST",
                {"price": money(amount, currency)})
    version = conv["regionVersion"]["version"]
    regions = [{"regionCode": code, "price": r["price"], "availability": "AVAILABLE"}
               for code, r in sorted(conv.get("convertedRegionPrices", {}).items())]
    print(f"converted to {len(regions)} regions (regions version {version})")

    body = {"packageName": a.package, "productId": pid, "listings": lst,
            "purchaseOptions": [{
                "purchaseOptionId": a.option_id,
                "buyOption": {"legacyCompatible": True, "multiQuantityEnabled": False},
                "regionalPricingAndAvailabilityConfigs": regions}]}
    if a.dry_run:
        preview = dict(body, purchaseOptions=[dict(body["purchaseOptions"][0],
                       regionalPricingAndAvailabilityConfigs=regions[:3] + ["…"])])
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        print("dry run — nothing written")
        return

    q = urllib.parse.urlencode({"allowMissing": "true",
                                "updateMask": "listings,purchaseOptions",
                                "regionsVersion.version": version})
    prod = call(tok, f"{API}/{a.package}/oneTimeProducts/{pid}?{q}", "PATCH", body)
    print("upserted")

    opt = next((o for o in prod.get("purchaseOptions", [])
                if o.get("purchaseOptionId") == a.option_id), {})
    if a.no_activate:
        print("left inactive (--no-activate)")
    elif opt.get("state") == "ACTIVE":
        print(f"option {a.option_id} already active")
    else:
        r = call(tok, f"{API}/{a.package}/oneTimeProducts/{pid}/purchaseOptions:batchUpdateStates",
                 "POST", {"requests": [{"activatePurchaseOptionRequest": {
                     "packageName": a.package, "productId": pid,
                     "purchaseOptionId": a.option_id}}]})
        prod = (r.get("oneTimeProducts") or [prod])[0]
        print(f"activated option {a.option_id}")

    print("now:")
    show(prod)


if __name__ == "__main__":
    main()
