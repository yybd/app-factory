#!/usr/bin/env python3
"""Apple's own search popularity, for the head terms — an optional enrichment.

    apple_ads.py status                         is a key there, and does it answer?
    apple_ads.py popularity STUDY.json --cc il  mark the study's terms Apple lists
    apple_ads.py head --cc us [--genre PRODUCTIVITY_UTILITIES] [--match WORD]

**Nothing in the method needs this.** It is used when `$KEYS_ROOT/appleads/api_key.json`
exists (an Apple Ads API key: client id, team id, key id, private key file), and the skill
says, for every number, whether it came from here or from autocomplete.

**What it gives, measured 2026-10-23** (Apple Ads Platform API v1, no campaign):
`POST /v1/insights/apps/search-term-popularity/query` returns a weekly table of real
`searchPopularity1to100` values per country and genre — **head terms only**, with a floor
around 54. A niche term is simply absent. So this does two things for a study: it puts
Apple's number on the terms Apple lists, and — because the table was read — it tells
`score.py` that every other term is below that floor (`apple_read` on the storefront).
The phrase and keyword *suggestion* endpoints returned nothing usable that day and are
not called.

Auth: an ES256 client secret signed by the `openssl` binary, exchanged for an hour's
token (cached under ~/.cache/aso-keywords, mode 600). Nothing here prints a secret.
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aso_core import CACHE, Fetched, es256_jwt, fetch, load_json, save_json, words  # noqa: E402

BASE = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"
TOKEN_CACHE = os.path.join(CACHE, "appleads_token.json")
GENRES = ("BUSINESS", "EDUCATION", "ENTERTAINMENT", "FINANCE", "FOOD_DRINK", "GAMES",
          "HEALTH_FITNESS", "LIFESTYLE", "NEW_PUBLICATION", "PHOTO_VIDEO",
          "PRODUCTIVITY_UTILITIES", "SHOPPING", "SOCIAL_NETWORKING", "SPORTS", "TRAVEL")


def key_dir():
    root = os.environ.get("KEYS_ROOT") or os.path.expanduser("~/keys")
    return os.path.join(os.path.expanduser(root), "appleads")


def config():
    """The key's identifiers, or None when there is no Apple Ads key on this machine."""
    cfg = load_json(os.path.join(key_dir(), "api_key.json"))
    if not cfg or not all(cfg.get(k) for k in ("client_id", "team_id", "key_id", "private_key")):
        return None
    pk = os.path.expanduser(cfg["private_key"])
    cfg["private_key_path"] = pk if os.path.isabs(pk) else os.path.join(key_dir(), pk)
    return cfg


def available():
    return config() is not None


def token(cfg):
    t = load_json(TOKEN_CACHE)
    if t and t.get("exp", 0) > time.time() + 60:
        return t["access_token"]
    now = int(time.time())
    secret = es256_jwt({"alg": "ES256", "kid": cfg["key_id"]},
                       {"sub": cfg["client_id"], "iss": cfg["team_id"],
                        "aud": "https://appleid.apple.com", "iat": now, "exp": now + 3600},
                       cfg["private_key_path"])
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": cfg["client_id"],
                                   "client_secret": secret, "scope": "searchadsorg"}).encode()
    r = json.loads(fetch(TOKEN_URL, {"Content-Type": "application/x-www-form-urlencoded"},
                         ttl=0, delay=0, data=body, method="POST"))
    os.makedirs(CACHE, exist_ok=True)
    save_json(TOKEN_CACHE, {"access_token": r["access_token"], "exp": time.time() + r["expires_in"]})
    os.chmod(TOKEN_CACHE, 0o600)
    return r["access_token"]


def call(method, path, body=None, account=None, ttl=0):
    cfg = config()
    if not cfg:
        raise RuntimeError(f"no Apple Ads key at {key_dir()}/api_key.json")
    h = {"Authorization": "Bearer " + token(cfg), "Content-Type": "application/json"}
    if account:
        h["X-AP-Context"] = f"adAccountId={account}"
    data = json.dumps(body).encode() if body is not None else None
    # The bearer token is not part of what is cached: the cache key is the URL and body.
    return json.loads(fetch(BASE + path, h, ttl=ttl, delay=0.5, data=data, method=method))


def account_id():
    cfg = config() or {}
    if cfg.get("ad_account_id") or os.environ.get("APPLE_ADS_ACCOUNT"):
        return str(cfg.get("ad_account_id") or os.environ["APPLE_ADS_ACCOUNT"])
    acls = call("GET", "/acls", ttl=86400)["result"]["acls"]
    return str(acls[0]["adAccount"]["id"]) if acls else None


def last_week(today=None):
    """The last complete Sunday–Saturday week, which is what Apple reports."""
    today = today or datetime.date.today()
    sat = today - datetime.timedelta(days=(today.weekday() + 2) % 7 or 7)
    return sat - datetime.timedelta(days=6), sat


def head_terms(cc, genre=None):
    """{term: row} for one country's latest week, every genre unless one is named.
    Steps back a week at a time (up to three) while Apple has not published the latest."""
    acc = account_id()
    start, end = last_week()
    for _ in range(3):
        rows, offset = [], 0
        while True:
            filters = [{"field": "countryOrRegion", "operator": "EQUALS", "value": cc.upper()}]
            if genre:
                filters.append({"field": "genre", "operator": "EQUALS", "value": genre})
            body = {"filters": filters,
                    "timeRange": {"start": start.isoformat(), "end": end.isoformat(),
                                  "granularity": "WEEKLY_SUN_SAT"},
                    "pagination": {"offset": offset, "pageSize": 1000}}
            page = (call("POST", "/insights/apps/search-term-popularity/query", body, acc, ttl=86400)
                    .get("result") or {}).get("rows", [])
            rows += page
            if len(page) < 1000:
                break
            offset += 1000
        if rows:
            out = {}
            for r in rows:
                t = r["searchTerm"].strip().lower()
                if t not in out or r["searchPopularity1to100"] > out[t]["searchPopularity1to100"]:
                    out[t] = r
            return out, start.isoformat()
        start, end = start - datetime.timedelta(days=7), end - datetime.timedelta(days=7)
    return {}, None


def enrich(study, cc, genre, add_matching):
    table, week = head_terms(cc, genre)
    if not week:
        return 0, 0, None
    sf = study.setdefault("storefronts", {}).setdefault(cc, {})
    cands = sf.setdefault("candidates", {})
    hit = added = 0
    if add_matching:
        mine = {w for t in cands for w in words(t) if len(w) > 2}
        for term in table:
            if term not in cands and mine & set(words(term)):
                cands[term] = {"sources": ["apple-ads"]}
                added += 1
    for term, c in cands.items():
        r = table.get(term)
        if r:
            c["apple"] = {"pop": r["searchPopularity1to100"], "week": week, "genre": r.get("genre")}
            if "apple-ads" not in c.setdefault("sources", []):
                c["sources"].append("apple-ads")
            hit += 1
        else:
            c.pop("apple", None)
    sf["apple_read"] = f"Apple Ads week {week}" + (f", {genre}" if genre else "")
    return hit, added, week


def main():
    ap = argparse.ArgumentParser(description="Apple Ads search popularity (head terms) — "
                                 "optional; the method works without it.")
    ap.add_argument("action", choices=["status", "popularity", "head"])
    ap.add_argument("study", nargs="?", help="the study file, for popularity")
    ap.add_argument("--cc", default="us")
    ap.add_argument("--genre", choices=GENRES, help="one genre only (default: every genre)")
    ap.add_argument("--add-matching", action="store_true",
                    help="add Apple head terms that share a word with the study's candidates")
    ap.add_argument("--match", help="for head: only terms containing this")
    a = ap.parse_args()

    if not available():
        print(f"No Apple Ads key ({key_dir()}/api_key.json). That is fine: popularity comes "
              "from the autocomplete proxy, and score.py says so for every term.")
        sys.exit(0 if a.action == "status" else 2)
    try:
        if a.action == "status":
            acc = account_id()
            print(f"Apple Ads key found; ad account {acc or '— none visible to this key'}.")
            table, week = head_terms(a.cc, a.genre)
            vals = [r["searchPopularity1to100"] for r in table.values()]
            print(f"{a.cc.upper()} week {week or '—'}: {len(table)} head terms"
                  + (f", popularity {min(vals)}–{max(vals)}" if vals else ""))
        elif a.action == "head":
            table, week = head_terms(a.cc, a.genre)
            for t, r in sorted(table.items(), key=lambda kv: -kv[1]["searchPopularity1to100"]):
                if not a.match or a.match.lower() in t:
                    print(f"{r['searchPopularity1to100']:3}  {t}  ({r.get('genre')})")
            print(f"— week {week}")
        else:
            if not a.study:
                ap.error("popularity needs the study file")
            study = load_json(a.study)
            if not study:
                ap.error(f"{a.study} does not exist")
            hit, added, week = enrich(study, a.cc, a.genre, a.add_matching)
            save_json(a.study, study)
            print(f"Apple Ads week {week}: {hit} of the study's terms have Apple's popularity"
                  f"{f'; {added} head terms added' if added else ''}; every other term is "
                  "below Apple's head list and score.py caps it accordingly.")
    except Fetched as e:
        print(f"Apple Ads answered {e.status}: {e}. The study goes on without it.", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
