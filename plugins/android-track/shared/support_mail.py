"""Where support mail goes, and what it says — read from the hub's DATA.md, never written here.

    from support_mail import load
    sm = load()                          # {address, urls, source, warnings, …}
    sm["address"]                        # the one support address, or None
    support_url(sm, "notes-app")         # the app's page + #contact, or None
    app_subject("Notes", "1.4")      # "Notes 1.4 — Support"
    web_mailto(sm["address"], "Notes", "Support")   # mailto:…?subject=…%28web%29

**Why this file exists.** A studio found its support mail scattered: apps writing to four
addresses (one on a foreign domain), a store listing with a personal address, and hundreds
of links that sent mail with no subject, so nothing said which app a message was about.
The rule that fixed it lives in the hub's `DATA.md`, in a section whose heading begins
`### support mail`. This module is the one place the skills read it from — the address,
the per-app support-URL table — so no skill carries an address or a domain of its own.

**When DATA.md has no such section** the address falls back to the Contact email
(`email_address:` / `email:`), and a warning says the rule is not written down yet. With
no hub at all everything is None and the warning says that instead. Nothing here raises:
a missing rule is a finding, not a crash.

The same file is in apple-track/shared and android-track/shared, because each track is
installed on its own. `factory/tests/test_support_mail.py` fails when the two differ.
"""
import os
import re
from urllib.parse import quote

APP_SUBJECT = "{app} {version} — {topic}"     # from inside an app
WEB_SUBJECT = "{app} — {topic} (web)"         # from a web page

_HEADING = re.compile(r"^#{2,4}\s*support mail\b.*$", re.I | re.M)
_ADDRESS = re.compile(r"\*\*address:\*\*\s*`?([^\s`]+@[^\s`]+?)`?(?:\s|$|—|,)", re.I)
_CONTACT = re.compile(r"^\s*(?:email_address|email|contact email)\s*:\s*(\S+@\S+)\s*$", re.I | re.M)
_URL = re.compile(r"`(https?://[^`\s]+)`")


def hub_dir():
    hub = os.environ.get("APP_HUB")
    if not hub:
        root = os.environ.get("DEV_ROOT")
        hub = os.path.join(root, "app-hub") if root else None
    return hub if hub and os.path.isdir(hub) else None


def _section(text):
    m = _HEADING.search(text)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^#{1,3}\s", rest, re.M)      # the next heading of the same depth or higher
    return rest[: nxt.start()] if nxt else rest


def _slugs(cell):
    """'notes / tasks' → ['notes', 'tasks'];  'tabs (Tabs Pro)' → ['tabs']."""
    cell = re.sub(r"\([^)]*\)", "", cell).replace("`", "")
    return [s.strip() for s in cell.split("/") if s.strip()]


def _table(section):
    urls = {}
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        u = _URL.search(cells[1])
        if not u:
            continue                                   # the header row, the --- row
        for slug in _slugs(cells[0]):
            urls[slug] = u.group(1).replace("<slug>", slug)
    return urls


def parse(text, source="DATA.md"):
    out = {"address": None, "urls": {}, "has_rule": False, "source": source, "warnings": []}
    sec = _section(text)
    if sec is not None:
        out["has_rule"] = True
        m = _ADDRESS.search(sec)
        if m:
            out["address"] = m.group(1).rstrip(".,;")
        out["urls"] = _table(sec)
    if not out["address"]:
        c = _CONTACT.search(text)
        if c:
            out["address"] = c.group(1)
            out["warnings"].append(
                f"{source} has no '### support mail' rule — using the Contact email "
                f"({c.group(1)}). Write the rule down so every surface agrees.")
        else:
            out["warnings"].append(
                f"{source} names no support address — neither a '### support mail' rule "
                "nor a Contact email.")
    if sec is not None and not out["urls"]:
        out["warnings"].append(f"{source}: the support-mail rule has no per-app support-URL table.")
    return out


def load(hub=None):
    hub = hub or hub_dir()
    if not hub:
        return {"address": None, "urls": {}, "has_rule": False, "source": None,
                "warnings": ["no hub ($APP_HUB unset) — the support address and URLs are unknown; "
                             "pass them explicitly or set $APP_HUB."]}
    p = os.path.join(hub, "DATA.md")
    try:
        text = open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return {"address": None, "urls": {}, "has_rule": False, "source": p,
                "warnings": [f"{p} could not be read — the support address and URLs are unknown."]}
    return parse(text, p)


def support_url(sm, slug):
    """The app's support URL from the table, matched case-insensitively; None if it has no row."""
    if not slug:
        return None
    urls = sm.get("urls") or {}
    if slug in urls:
        return urls[slug]
    low = {k.lower(): v for k, v in urls.items()}
    return low.get(slug.lower())


def norm_url(u):
    return (u or "").strip().rstrip("/").replace("/#", "#").lower()


def matches(have, want):
    """Is `have` the support URL `want` names — or a language version of the same page?

    `https://www.example.io/he/#contact` matches `https://www.example.io/#contact`: same
    host, the same #contact, and the table's path at the end of the localized one."""
    from urllib.parse import urlparse
    if norm_url(have) == norm_url(want):
        return True
    h, w = urlparse((have or "").strip()), urlparse((want or "").strip())
    if h.netloc.lower() != w.netloc.lower() or h.fragment != w.fragment:
        return False
    hp, wp = h.path.rstrip("/"), w.path.rstrip("/")
    return hp == wp or hp.endswith(wp) and re.fullmatch(r"/[a-z]{2}(?:-[A-Za-z]{2,4})?", hp[: len(hp) - len(wp)] or "/x") is not None


def is_home(u):
    """True for a bare site root — the 'generic home page' a support URL must not be."""
    from urllib.parse import urlparse
    p = urlparse((u or "").strip())
    return bool(p.netloc) and p.path in ("", "/") and not p.fragment


def app_subject(app, version, topic="Support"):
    return APP_SUBJECT.format(app=app, version=version, topic=topic)


def web_subject(app, topic="Support"):
    return WEB_SUBJECT.format(app=app, topic=topic)


def encode(subject):
    """URL-encode a subject, parentheses included — a raw ')' ends a Markdown link."""
    return quote(subject, safe="")


def web_mailto(address, app, topic="Support"):
    return f"mailto:{address}?subject={encode(web_subject(app, topic))}"
