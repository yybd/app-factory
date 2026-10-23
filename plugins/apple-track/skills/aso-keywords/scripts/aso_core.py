#!/usr/bin/env python3
"""What every aso-keywords script shares: storefronts, the polite cached fetch, word
handling, the keyword-field unit, and ES256 signing through the openssl binary.

A module, not a command. Stdlib only — the signing goes through `openssl` because the
alternative is a pip dependency on every machine that runs a keyword study, for one
signature a day.

**Why there is a cache.** The free sources are unofficial and rate-limited: Apple's
autocomplete and the web store's search page are the same endpoints a person's browser
uses, and a study of 300 terms is 300 requests to each. Every response is kept for a day
under the cache folder, so re-running a study after changing one relevance score costs
nothing and asks Apple for nothing.
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
CALIBRATION = os.path.join(SKILL, "calibration.json")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
                     "aso-keywords")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko)"

# Storefront → the autocomplete header's numbers, and the listing locales the store
# indexes there. The locale lists are practitioner knowledge, not Apple's word (see the
# guide); the first locale is the storefront's primary one.
STOREFRONTS = {
    "us": {"front": "143441-1,29", "locales": ["en-US", "es-MX", "zh-Hans", "zh-Hant", "fr-FR",
                                                "ko", "pt-BR", "ru", "vi", "ar-SA"]},
    "il": {"front": "143491-2,29", "locales": ["he", "en-GB"]},
    "gb": {"front": "143444-2,29", "locales": ["en-GB", "en-AU"]},
    "de": {"front": "143443-4,29", "locales": ["de-DE", "en-GB"]},
    "fr": {"front": "143442-3,29", "locales": ["fr-FR", "en-GB"]},
    "ca": {"front": "143455-6,29", "locales": ["en-CA", "fr-CA"]},
    "au": {"front": "143460-27,29", "locales": ["en-AU", "en-GB"]},
}

HEBREW = re.compile(r"[֐-׿]")
WORD = re.compile(r"[\w֐-׿'’]+", re.UNICODE)
# Words Apple indexes for free or ignores — never worth a byte of the keyword field.
STOP = set("the a an and or for to of in on with your you it is are by my at app apps game games"
           " iphone ipad mac ios free".split()) | {"של", "את", "עם", "על", "או", "גם", "אפליקציה"}


class Fetched(Exception):
    """A source answered with an error. Carries the HTTP status."""

    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body[:200]}")
        self.status = status


def load_calibration():
    with open(CALIBRATION, encoding="utf-8") as f:
        return json.load(f)


def fetch(url, headers=None, ttl=86400, delay=1.0, data=None, method=None):
    """GET (or POST) with a day's cache and a pause between live requests. Returns text."""
    key = hashlib.sha256(json.dumps([url, headers, data and data.decode("utf-8", "replace")],
                                    sort_keys=True).encode()).hexdigest()
    path = os.path.join(CACHE, key[:2], key)
    if ttl and os.path.exists(path) and time.time() - os.path.getmtime(path) < ttl:
        with open(path, encoding="utf-8") as f:
            return f.read()
    h = {"User-Agent": UA}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h, data=data, method=method)
    last = getattr(fetch, "_last", 0)
    if time.time() - last < delay:
        time.sleep(delay - (time.time() - last))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise Fetched(e.code, e.read().decode("utf-8", "replace"))
    finally:
        fetch._last = time.time()
    if ttl:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def is_hebrew(text):
    return bool(HEBREW.search(text or ""))


def words(text):
    return [w.lower().strip("'’") for w in WORD.findall(text or "") if w.strip("'’")]


def stem(word):
    """A crude stem, for one purpose: two forms that Apple treats as one word should not
    both spend keyword bytes. English plurals; Hebrew plural and feminine endings."""
    w = word.lower()
    if is_hebrew(w):
        for end in ("ים", "ות"):
            if w.endswith(end) and len(w) - len(end) >= 2:
                return w[:-len(end)]
        if w[-1:] in ("ה", "ת") and len(w) >= 4:
            return w[:-1]
        return w
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and re.search(r"(ss|x|ch|sh)es$", w):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def units(text, unit="bytes"):
    """How much of a keyword field `text` uses. Apple's reference says 100 BYTES; whether
    App Store Connect counts bytes or characters for Hebrew is unverified, so the caller
    says which — and calibration.json carries the answer once someone has checked."""
    return len(text.encode("utf-8")) if unit == "bytes" else len(text)


def read_listing(metadata_root, locale):
    """{name, subtitle, keywords} for one locale of a fastlane-shaped metadata tree."""
    out = {}
    for field in ("name", "subtitle", "keywords"):
        p = os.path.join(metadata_root, locale, field + ".txt")
        try:
            with open(p, encoding="utf-8") as f:
                out[field] = f.read().strip()
        except OSError:
            out[field] = ""
    return out


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


# ---- ES256, through the openssl binary --------------------------------------------

def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def der_to_raw(der):
    """ECDSA signature: DER SEQUENCE(INTEGER r, INTEGER s) → the 64-byte r||s JWS wants."""
    i = 2 if der[1] < 0x80 else 2 + (der[1] & 0x7F)
    out = b""
    for _ in range(2):
        if der[i] != 0x02:
            raise ValueError("not a DER ECDSA signature")
        n = der[i + 1]
        out += der[i + 2:i + 2 + n].lstrip(b"\x00").rjust(32, b"\x00")
        i += 2 + n
    return out


def es256_jwt(header, payload, key_path):
    """A signed JWT. The private key is read by openssl, never by this process."""
    msg = f"{b64url(json.dumps(header).encode())}.{b64url(json.dumps(payload).encode())}"
    der = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key_path],
                         input=msg.encode(), capture_output=True, check=True).stdout
    return f"{msg}.{b64url(der_to_raw(der))}"
