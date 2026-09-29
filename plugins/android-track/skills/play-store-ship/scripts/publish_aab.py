#!/usr/bin/env python3
"""Upload an AAB to Google Play and publish it to a track.

The whole edit lifecycle in one place: create edit -> upload bundle -> PUT track
-> commit -> re-read the tracks and prove what landed.

Two traps this exists to avoid:
  * bundles upload to the /upload/ host path, not the ordinary one (posting an
    AAB to the plain path makes the API try to parse the zip as JSON);
  * `edits/<id>:commit` 404s through curl because the colon does not survive the
    shell, while urllib sends it fine. Everything here is urllib.

An edit that is never committed changes nothing, which is what makes --dry-run a
real rehearsal: it uploads, stages the track, then deletes the edit. The
versionCode stays free to upload again.

  publish_aab.py --package com.x.y --status
  publish_aab.py --package com.x.y --aab app-release.aab --track production \
                 --name 1.2.3 --notes-dir .../changelogs/7 --dry-run
  publish_aab.py --package com.x.y --aab app-release.aab --track alpha --draft
"""
import argparse, base64, json, os, subprocess, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request

API = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
UPLOAD = "https://androidpublisher.googleapis.com/upload/androidpublisher/v3/applications"
# Where the credential comes from is ONE question, and it had two answers that did not
# agree: this file looked for exactly one .json in a folder under $KEYS_ROOT, while the
# Play diff script grepped a heading out of the hub's DATA.md. The second cannot be
# asked of anyone else — it is a heading in one studio's markdown file.
# `shared/credentials.py` asks in the documented order and reports which source answered.
_SHARED = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "..", "..", "shared"))
sys.path.insert(0, _SHARED)
import credentials as _creds                                  # noqa: E402

DEFAULT_KEY_DIR = os.path.join(_creds.keys_root(), "android", "api-fastlane-supply")


def default_key():
    """The service account this machine should publish under, or None.

    None is a real answer and not a failure: the filename is issued by the Play Console
    and differs per studio, so with none or several present the right move is to say so
    and let --key decide, never to guess which account a release goes out under.
    """
    path, _src = _creds.service_account(required=False)
    return path


def token(key_path):
    """Mint an access token from the service-account JSON (RS256 JWT via openssl)."""
    sa = json.load(open(key_path))
    b64 = lambda d: base64.urlsafe_b64encode(d).rstrip(b"=")
    now = int(time.time())
    head = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claim = b64(json.dumps({
        "iss": sa["client_email"],
        "scope": "https://www.googleapis.com/auth/androidpublisher",
        "aud": "https://oauth2.googleapis.com/token",
        "exp": now + 3600, "iat": now}).encode())
    signing_input = head + b"." + claim
    kf = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    kf.write(sa["private_key"].encode()); kf.close()
    try:
        sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", kf.name, "-binary"],
                             input=signing_input, capture_output=True, check=True).stdout
    finally:
        os.unlink(kf.name)
    jwt = signing_input + b"." + b64(sig)
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt.decode()}).encode()
    return json.load(urllib.request.urlopen(
        "https://oauth2.googleapis.com/token", data=body))["access_token"]


CLEANUP = {}          # {"tok":…, "pkg":…, "eid":…} — the edit to drop if we die


def discard_edit():
    """An abandoned edit is harmless but untidy; drop it on the way out."""
    c = CLEANUP.pop("eid", None)
    if c:
        try:
            call(CLEANUP["tok"], f'{API}/{CLEANUP["pkg"]}/edits/{c}', "DELETE")
            sys.stdout.flush()
            print(f"(edit {c} discarded)")
        except SystemExit:
            pass


def call(tok, url, method="GET", data=None, ctype=None):
    headers = {"Authorization": "Bearer " + tok}
    if ctype:
        headers["Content-Type"] = ctype
    headers["Content-Length"] = "0" if data is None else str(len(data))
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        raw = urllib.request.urlopen(req).read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:800]
        if "FAILED_PRECONDITION" in detail and "/edits/" in url:
            detail += ("\n\nFAILED_PRECONDITION on beta/production while alpha accepts "
                       "writes is the production-access gate, not a credentials problem.")
        if "has already been used" in detail:
            detail += ("\n\nThat versionCode is spent. A code is burned by a COMMITTED "
                       "edit and can never be reused; only an edit that was deleted "
                       "before commit leaves it free. Bump versionCode and rebuild.")
        if "status draft may be created on draft app" in detail:
            detail += ("\n\nThe app has never been published (a draft app): until the "
                       "Console's app-content forms are complete, only a DRAFT release "
                       "can be created. Rerun with --draft, then roll it out from the "
                       "Console once the forms are done.")
        msg = f"HTTP {e.code} on {method} {url}\n{detail}"
        if method != "DELETE":
            discard_edit()
        sys.exit(msg)
    return json.loads(raw) if raw.strip() else {}


def show_tracks(tok, pkg, eid):
    for t in call(tok, f"{API}/{pkg}/edits/{eid}/tracks").get("tracks", []):
        for rel in t.get("releases", []):
            frac = rel.get("userFraction")
            roll = f"  rollout={frac}" if frac else ""
            print(f'  {t["track"]:10} {str(rel.get("name")):12} '
                  f'vc={rel.get("versionCodes")} {rel.get("status")}{roll}')


def read_notes(notes_dir):
    """Each <locale>.txt in the dir becomes one releaseNotes entry."""
    notes = [{"language": fn[:-4],
              "text": open(os.path.join(notes_dir, fn), encoding="utf-8").read().strip()}
             for fn in sorted(os.listdir(notes_dir)) if fn.endswith(".txt")]
    if not notes:
        sys.exit(f"no <locale>.txt changelogs in {notes_dir}")
    return notes


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--package", required=True)
    p.add_argument("--key", default=default_key(),
                   help=f"service-account JSON (default: the one in {DEFAULT_KEY_DIR})")
    p.add_argument("--status", action="store_true", help="read the tracks and exit")
    p.add_argument("--aab")
    p.add_argument("--track", default="internal")
    p.add_argument("--name", help="release name shown in the Console (e.g. 1.2.3)")
    p.add_argument("--notes-dir", help="dir of <locale>.txt release notes")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--rollout", type=float,
                      help="staged fraction 0<f<1; omit for a full rollout")
    mode.add_argument("--draft", action="store_true",
                      help="create the release as a draft — the only status a never-"
                           "published app accepts; rolled out later from the Console")
    p.add_argument("--dry-run", action="store_true",
                   help="upload and stage, then delete the edit — changes nothing")
    a = p.parse_args()
    if not a.key:
        p.error(f"no service account found in {DEFAULT_KEY_DIR} — pass --key, or run "
                f"`python3 factory/init_keys.py --create` in the app-factory checkout "
                f"and put the JSON there")

    tok = token(a.key)

    if a.status or not a.aab:
        eid = call(tok, f"{API}/{a.package}/edits", "POST", b"")["id"]
        print(f"tracks for {a.package}:")
        show_tracks(tok, a.package, eid)
        call(tok, f"{API}/{a.package}/edits/{eid}", "DELETE")
        if not a.aab and not a.status:
            sys.exit("\n--aab is required to publish")
        return

    if not os.path.exists(a.aab):
        sys.exit(f"no such file: {a.aab}")
    notes = read_notes(a.notes_dir) if a.notes_dir else None
    if a.rollout is not None and not (0 < a.rollout < 1):
        sys.exit("--rollout must be strictly between 0 and 1")

    eid = call(tok, f"{API}/{a.package}/edits", "POST", b"")["id"]
    CLEANUP.update(tok=tok, pkg=a.package, eid=eid)
    print(f"edit {eid}{'  (DRY RUN — will be deleted)' if a.dry_run else ''}")

    with open(a.aab, "rb") as fh:
        blob = fh.read()
    up = call(tok, f"{UPLOAD}/{a.package}/edits/{eid}/bundles?uploadType=media",
              "POST", blob, "application/octet-stream")
    vc = str(up["versionCode"])
    print(f"uploaded versionCode {vc}  sha1 {up['sha1'][:12]}  ({len(blob)//1024} kb)")

    release = {"versionCodes": [vc], "name": a.name or vc}
    if notes:
        release["releaseNotes"] = notes
        print("release notes:", ", ".join(n["language"] for n in notes))
    if a.draft:
        release["status"] = "draft"
    elif a.rollout is not None:
        release["status"], release["userFraction"] = "inProgress", a.rollout
    else:
        release["status"] = "completed"

    body = json.dumps({"track": a.track, "releases": [release]},
                      ensure_ascii=False).encode("utf-8")
    call(tok, f"{API}/{a.package}/edits/{eid}/tracks/{a.track}", "PUT", body,
         "application/json; charset=utf-8")
    print(f"staged on {a.track}: {release['name']} ({release['status']})")

    if a.dry_run:
        discard_edit()
        print("dry run — edit deleted, nothing published, versionCode still free")
        return

    call(tok, f"{API}/{a.package}/edits/{eid}:commit", "POST", b"")
    CLEANUP.pop("eid", None)          # committed: there is nothing left to discard
    print("committed — " + ("draft created; nothing is live until it is rolled out "
                            "in the Console" if a.draft else "published"))

    eid2 = call(tok, f"{API}/{a.package}/edits", "POST", b"")["id"]
    print("tracks now:")
    show_tracks(tok, a.package, eid2)
    call(tok, f"{API}/{a.package}/edits/{eid2}", "DELETE")
    print("\nGoogle reviews every production release; the API has no review-status "
          "field.\nWatch the Console, or the version served on the public listing.")


if __name__ == "__main__":
    main()
