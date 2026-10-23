#!/usr/bin/env python3
"""Search impressions and page views per app, from App Store Connect's Analytics Reports.

    asc_analytics.py status  --app-id 123     is a report requested, and what exists
    asc_analytics.py request --app-id 123     ask Apple to start the ONGOING report (once)
    asc_analytics.py search  --app-id 123 [--days 28] [--json]

The free feedback signal, for every developer: the "App Store Discovery and Engagement"
report counts impressions and product-page views by **source type**, and one source type
is App Store search. That is how a review tells "the ranks moved and nobody saw it" from
"more people found us by searching". **It has no per-term data** — Apple keeps none in
App Store Connect — so per-term evidence is the rank snapshots, and this is the total.

**`request` is a write to the developer's account**, and the data starts accumulating only
from it: Apple builds the report from that day on, with a lag of a few days. It needs a
key with the Admin role the first time. The skill asks the owner before running it.

Credentials: the apple-track resolver (`shared/credentials.py`: the environment, then
`$KEYS_ROOT/credentials.json`), or `--key-json` / `--key-id/--issuer/--p8` for a different key — the
key that reads sales reports is not always the one fastlane uses. The `.p8` is read by
openssl only.
"""
import argparse
import csv
import datetime
import gzip
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "..", "shared")))
from aso_core import es256_jwt  # noqa: E402

API = "https://api.appstoreconnect.apple.com/v1"
REPORT = "App Store Discovery and Engagement"


class Asc:
    def __init__(self, key_id, issuer, p8):
        self.key_id, self.issuer, self.p8, self._tok = key_id, issuer, p8, None

    def token(self):
        if not self._tok or self._tok[1] < time.time() + 60:
            now = int(time.time())
            jwt = es256_jwt({"alg": "ES256", "kid": self.key_id, "typ": "JWT"},
                            {"iss": self.issuer, "iat": now, "exp": now + 1200,
                             "aud": "appstoreconnect-v1"}, self.p8)
            self._tok = (jwt, now + 1200)
        return self._tok[0]

    def call(self, method, url, body=None):
        url = url if url.startswith("http") else API + url
        req = urllib.request.Request(url, method=method,
                                     data=json.dumps(body).encode() if body else None,
                                     headers={"Authorization": "Bearer " + self.token(),
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            raise SystemExit(f"App Store Connect answered {e.code} on {method} {url}:\n{text[:600]}"
                             + ("\n(a 403 usually means this key's role cannot read analytics —"
                                " try another key with --key-json)" if e.code == 403 else ""))

    def pages(self, url):
        while url:
            d = self.call("GET", url)
            yield from d.get("data", [])
            url = (d.get("links") or {}).get("next")


def client(a):
    if a.key_json:
        k = json.load(open(os.path.expanduser(a.key_json), encoding="utf-8"))
        p8 = k.get("key_filepath") or k.get("p8") or ""
        p8 = p8 if os.path.isabs(p8) else os.path.join(os.path.dirname(os.path.expanduser(a.key_json)), p8)
        return Asc(k["key_id"], k["issuer_id"], os.path.normpath(p8))
    if a.key_id and a.issuer and a.p8:
        return Asc(a.key_id, a.issuer, os.path.expanduser(a.p8))
    from credentials import asc_key
    k = asc_key()
    return Asc(k["key_id"], k["issuer_id"], k["p8"])


def requests_of(asc, app_id):
    return list(asc.pages(f"/apps/{app_id}/analyticsReportRequests"))


def ongoing(asc, app_id):
    return next((r for r in requests_of(asc, app_id)
                 if r["attributes"].get("accessType") == "ONGOING"
                 and not r["attributes"].get("stoppedDueToInactivity")), None)


def engagement_reports(asc, req_id):
    return [r for r in asc.pages(f"/analyticsReportRequests/{req_id}/reports"
                                 "?filter[category]=APP_STORE_ENGAGEMENT")
            if r["attributes"].get("name", "").startswith(REPORT)]


def rows(asc, report_id, since, granularity="DAILY"):
    """Every row of the report's instances on or after `since` (ISO date)."""
    out = []
    for inst in asc.pages(f"/analyticsReports/{report_id}/instances?filter[granularity]={granularity}"):
        if inst["attributes"].get("processingDate", "") < since:
            continue
        for seg in asc.pages(f"/analyticsReportInstances/{inst['id']}/segments"):
            raw = urllib.request.urlopen(seg["attributes"]["url"], timeout=120).read()
            text = gzip.decompress(raw).decode("utf-8") if raw[:2] == b"\x1f\x8b" else raw.decode("utf-8")
            out += list(csv.DictReader(io.StringIO(text), delimiter="\t"))
    return out


def col(row, *names):
    low = {k.lower(): v for k, v in row.items()}
    for n in names:
        if n in low:
            return low[n]
    return ""


def search_totals(rs):
    """{territory: {event: count}} for rows whose source type is App Store search."""
    out = {}
    for r in rs:
        if "search" not in col(r, "source type").lower():
            continue
        terr = col(r, "territory") or "?"
        event = col(r, "event") or "?"
        try:
            n = int(float(col(r, "counts", "count") or 0))
        except ValueError:
            n = 0
        out.setdefault(terr, {}).setdefault(event, 0)
        out[terr][event] += n
    return out


def search(asc, app_id, days):
    req = ongoing(asc, app_id)
    if not req:
        return {"error": "no ONGOING report requested for this app — `request` starts one"}
    reps = engagement_reports(asc, req["id"])
    if not reps:
        return {"error": "the request exists, Apple has not produced the report yet (a few days)"}
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    rep = next((r for r in reps if "Standard" in r["attributes"]["name"]), reps[0])
    rs = rows(asc, rep["id"], since)
    if rs and not col(rs[0], "source type"):
        return {"error": f"the report has no 'Source Type' column — its columns are {list(rs[0])}"}
    return {"since": since, "report": rep["attributes"]["name"], "rows": len(rs),
            "search": search_totals(rs)}


def main():
    ap = argparse.ArgumentParser(description="App Store search impressions and page views "
                                 "per app (Analytics Reports API).")
    ap.add_argument("action", choices=["status", "request", "search"])
    ap.add_argument("--app-id", required=True, help="the app's Apple id")
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--key-json", help="a fastlane-style api_key.json (key_id, issuer_id, key_filepath)")
    ap.add_argument("--key-id")
    ap.add_argument("--issuer")
    ap.add_argument("--p8")
    a = ap.parse_args()
    asc = client(a)

    if a.action == "status":
        reqs = requests_of(asc, a.app_id)
        if not reqs:
            print("No analytics report requested for this app. `request` starts one (needs an "
                  "Admin key the first time; data accumulates from that day on).")
        for r in reqs:
            at = r["attributes"]
            print(f"request {r['id']}: {at.get('accessType')}"
                  f"{' — STOPPED for inactivity' if at.get('stoppedDueToInactivity') else ''}")
            for rep in engagement_reports(asc, r["id"]):
                print(f"  report: {rep['attributes']['name']}")
    elif a.action == "request":
        if ongoing(asc, a.app_id):
            print("An ONGOING request already exists — nothing to do.")
            return
        d = asc.call("POST", "/analyticsReportRequests", {"data": {
            "type": "analyticsReportRequests", "attributes": {"accessType": "ONGOING"},
            "relationships": {"app": {"data": {"type": "apps", "id": str(a.app_id)}}}}})
        print(f"Requested: {d['data']['id']}. Apple produces the first reports in a few days.")
    else:
        res = search(asc, a.app_id, a.days)
        if a.json:
            print(json.dumps(res, indent=1, ensure_ascii=False))
        elif "error" in res:
            print(res["error"])
        else:
            print(f"{res['report']} since {res['since']} ({res['rows']} rows), App Store search:")
            for terr, ev in sorted(res["search"].items()):
                print(f"  {terr}: " + ", ".join(f"{k} {v}" for k, v in sorted(ev.items())))


if __name__ == "__main__":
    main()
