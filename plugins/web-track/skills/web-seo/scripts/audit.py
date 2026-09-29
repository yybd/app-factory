#!/usr/bin/env python3
"""The on-page technical SEO audit — everything a page can be wrong about, offline.

    python3 audit.py                    # every property in the descriptor
    python3 audit.py --errors           # only what is definitely broken
    python3 audit.py --property tools   # one property
    python3 audit.py --root <dir>       # a site with no descriptor: audit this tree

The companion to a live reading from Search Console, and the division matters:

    this        what is wrong with the pages themselves — offline, seconds, every
                finding actionable today
    live data   how Google and visitors are responding — slow, needs credentials, and
                it can only ever report what the pages already earned

A page cannot rank above what its markup allows, so this runs first: there is no point
reading impressions for a page whose title is truncated, whose description Google had
to invent, or that nothing links to.

**Every check here exists because it was found broken on a real site**, not because it
appears on a generic checklist. One run found 20 pages with no meta description, 13
descriptions cut short by an unescaped quote inside the attribute, 4 paid-product pages
with no structured data, 2 pages with zero inbound internal links (both unindexed), 3
products with two competing pages each — one pair sharing a byte-identical title — 24
canonicals pointing at URLs that redirect, and 6 titles too long to survive a result
page.

**Where the site is** comes from a descriptor rather than from this file. It was two
constants naming one machine's checkout and one studio's seven hostnames, which is what
kept this script in a private repo instead of in the skill that drives it. The shape is
in `references/site-descriptor.md`; `--root` covers a single site with no descriptor.
"""

import argparse
import collections
import glob
import html
import json
import os
import re
import sys
from urllib.parse import unquote, urljoin, urlparse

# Filled by load_descriptor() before anything runs. Module-level because the checks
# below read them directly, and threading a config object through three hundred lines of
# well-tested checks would be a far bigger change than the one this file needed.
SITE_REPO = None
PROPERTIES = {}
SKIP_DIRS = {"node_modules", ".git", ".vercel", ".claude", "content", "media", "i18n",
             "dist", "build", ".next", ".astro", "vendor"}

DESCRIPTOR = "seo-site.json"
# Set from the descriptor. Empty means "not declared", and every check that depends on a
# declaration is skipped rather than guessed — a site with no descriptor should get no
# findings it cannot act on.
declared_hosts = set()
no_trailing_slash = False
sitemap_cmd = None
# The file that carries this site's measurement snippet. Declared, never assumed: the
# check used to look for `analytics.js` by name, which is one studio's filename — and
# on any other site it reported every page as unmeasured.
analytics_src = None


def load_descriptor(root=None, explicit=None):
    """Where the site is, and which hostnames it serves.

    Looked for at `.claude/seo-site.json` in the site repo, because that is where a
    repo already keeps what its tools need to know about it. With no descriptor a
    single-site layout is assumed: the root is the tree, and the properties are
    whatever the canonicals in it turn out to say — right for most sites, and wrong
    only for a repo serving several properties out of subdirectories, which is exactly
    the case the descriptor exists for.
    """
    global SITE_REPO, PROPERTIES, SKIP_DIRS
    if explicit:
        path = os.path.expanduser(explicit)
    else:
        base = os.path.expanduser(root or os.environ.get("SITE") or ".")
        path = os.path.join(base, ".claude", DESCRIPTOR)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(path)))
        named = d.get("root")
        SITE_REPO = os.path.join(repo_dir, named) if named and not os.path.isabs(
            os.path.expanduser(named)) else os.path.expanduser(named or repo_dir)
        PROPERTIES = {k: v for k, v in (d.get("properties") or {}).items()
                      if not k.startswith("_")}
        SKIP_DIRS |= set(d.get("skip_dirs") or [])
        globals()["declared_hosts"] = set(PROPERTIES)
        globals()["no_trailing_slash"] = bool(d.get("trailing_slash") is False)
        globals()["sitemap_cmd"] = d.get("sitemap_command")
        globals()["analytics_src"] = d.get("analytics_script")
        return path
    SITE_REPO = os.path.abspath(os.path.expanduser(root or os.environ.get("SITE") or "."))
    PROPERTIES = {}                       # derived below from the canonicals found
    return None

# Titles are truncated by Google around 580px, which is roughly 60 characters;
# 65 is where it becomes reliably visible. Descriptions get ~155-160.
TITLE_MAX, TITLE_MIN = 65, 15
DESC_MAX, DESC_MIN = 160, 70

ERROR, WARN, INFO = "ERROR", "WARN", "INFO"


def meta(html_text, attr, name):
    """Read a meta tag's content.

    Two traps, both of which produced confident wrong answers before they were
    fixed. The tag may span several LINES — the homepage writes it that way, and
    a single-line pattern reports the two most important pages on the main domain
    as having no description at all. And the closing quote must be the SAME quote
    that opened: `content="…the app's…"` with a `["\']` character class on both
    ends stops at the apostrophe, so a perfectly good 205-character description
    reads as 38 and gets reported as thin."""
    q = r'(?P<q>["\'])'
    m = re.search(
        rf'<meta[^>]*\b{attr}=["\']{re.escape(name)}["\'][^>]*?\bcontent={q}(.*?)(?P=q)',
        html_text, re.I | re.S)
    if not m:
        m = re.search(
            rf'<meta[^>]*?\bcontent={q}(.*?)(?P=q)[^>]*\b{attr}=["\']{re.escape(name)}["\']',
            html_text, re.I | re.S)
    return html.unescape(re.sub(r"\s+", " ", m.group(2)).strip()) if m else None


def load_pages():
    pages, noindexed = {}, []
    for dp, dn, fn in os.walk(SITE_REPO):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if not f.endswith(".html") or f == "_template.html":
                continue
            path = os.path.join(dp, f)
            s = open(path, encoding="utf-8", errors="replace").read()
            # A noindex page (the 404) is deliberately not part of the site's
            # search surface: it has no canonical, belongs in no sitemap, and
            # every check below would be a false positive on it.
            if re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex', s, re.I):
                noindexed.append(os.path.relpath(path, SITE_REPO))
                continue
            can = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', s, re.I)
            if not can:
                continue
            t = re.search(r"<title[^>]*>(.*?)</title>", s, re.I | re.S)
            body = re.search(r"<body.*?</body>", s, re.I | re.S)
            # Comments carry example markup — one page documented an unlinked badge
            # as <a href="…"> inside a comment — and scanning them reports authored
            # prose as a broken link. Strip before looking at anything.
            body_clean = re.sub(r"<!--.*?-->", " ", body.group(0), flags=re.S) if body else ""
            pages[can.group(1).strip()] = {
                "file": os.path.relpath(path, SITE_REPO),
                "html": s,
                "body": body_clean,
                "path": path,
                "title": html.unescape(re.sub(r"\s+", " ", t.group(1)).strip()) if t else None,
                "desc": meta(s, "name", "description"),
                "og_title": meta(s, "property", "og:title"),
                "og_desc": meta(s, "property", "og:description"),
                "og_image": meta(s, "property", "og:image"),
                "lang": (re.search(r"<html[^>]+lang=[\"']([^\"']+)[\"']", s, re.I) or [None, None])[1],
                "h1": len(re.findall(r"<h1[\s>]", s, re.I)),
                "ldjson": re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S),
                "alternates": re.findall(
                    r'<link[^>]+rel=["\']alternate["\'][^>]+hreflang=["\']([^"\']+)["\'][^>]+href=["\']([^"\']+)["\']', s, re.I),
                "analytics": bool(analytics_src and re.search(
                r'<script[^>]+src="[^"]*' + re.escape(analytics_src) + '"', s)),
            }
    return pages, noindexed


def sitemap_urls():
    out = set()
    for f in [os.path.join(SITE_REPO, "sitemap.xml")] + sorted(
            glob.glob(os.path.join(SITE_REPO, "sites", "*", "sitemap.xml"))):
        if os.path.exists(f):
            out |= set(re.findall(r"<loc>([^<]+)</loc>", open(f, encoding="utf-8").read()))
    return out


def prop_of(url):
    return urlparse(url).netloc


def norm(u):
    p = urlparse(u)
    return f"{p.scheme}://{p.netloc}{p.path.rstrip('/') or '/'}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--errors", action="store_true", help="only definite breakage")
    ap.add_argument("--property", help="limit to one host substring")
    ap.add_argument("--root", help="the site's tree, when there is no descriptor")
    ap.add_argument("--descriptor", help="an explicit seo-site.json")
    args = ap.parse_args()

    found = load_descriptor(args.root, args.descriptor)
    if not os.path.isdir(SITE_REPO):
        sys.exit(f"✗ no site tree at {SITE_REPO}. Pass --root <dir>, set $SITE, or put a "
                 f"{DESCRIPTOR} in the repo's .claude/ — see references/site-descriptor.md.")
    print(f"site: {SITE_REPO}")
    print(f"  {'descriptor: ' + found if found else 'no descriptor — one site, properties read from the canonicals'}")

    pages, noindexed = load_pages()

    if not PROPERTIES:
        # No descriptor: every host a canonical names is a property, and the whole tree
        # is its root. Right for a single site; a repo serving several properties out of
        # subdirectories needs the descriptor to say which folder is which.
        for u in pages:
            PROPERTIES.setdefault(prop_of(u), ".")
    if args.property:
        pages = {u: v for u, v in pages.items() if args.property in prop_of(u)}
    smap = sitemap_urls()
    if args.property:
        # Filter the sitemap set too, or every OTHER property's URLs read as
        # "in a sitemap but no page claims it" — 74 false errors from a flag
        # whose whole purpose is to narrow the output.
        smap = {u for u in smap if args.property in prop_of(u)}
    findings = []          # (severity, category, url, detail)

    def add(sev, cat, url, detail):
        findings.append((sev, cat, url, detail))

    # ---- link graph: orphans and reachability -----------------------------
    by_norm = {norm(u): u for u in pages}
    inbound = collections.Counter()
    for u, v in pages.items():
        for href in re.findall(r'href="([^"]+)"', v["body"]):
            if href.startswith(("mailto:", "tel:", "#", "javascript:")):
                continue
            target = norm(urljoin(u, href))
            if target in by_norm and by_norm[target] != u:
                inbound[by_norm[target]] += 1

    # ---- per page ---------------------------------------------------------
    for u, v in sorted(pages.items()):
        # title
        if not v["title"]:
            add(ERROR, "title", u, "no <title>")
        elif len(v["title"]) > TITLE_MAX:
            add(WARN, "title", u, f'{len(v["title"])} chars — truncated in results: "{v["title"][:70]}…"')
        elif len(v["title"]) < TITLE_MIN:
            add(WARN, "title", u, f'only {len(v["title"])} chars: "{v["title"]}"')

        # description
        if not v["desc"]:
            add(ERROR, "description", u, "no meta description — Google writes the snippet itself")
        elif len(v["desc"]) < DESC_MIN:
            add(WARN, "description", u, f'{len(v["desc"])} chars, thin: "{v["desc"][:60]}…"')
        elif len(v["desc"]) > DESC_MAX:
            add(WARN, "description", u, f'{len(v["desc"])} chars — truncated')
        if v["desc"] and v["desc"].rstrip().endswith(("(", '"', ",")):
            add(ERROR, "description", u, f'ends mid-sentence — likely an unescaped quote: "{v["desc"][-40:]}"')

        # canonical hygiene
        if declared_hosts and prop_of(u) not in declared_hosts:
            add(ERROR, "canonical", u, f"canonical host {prop_of(u)} is not a declared property")
        if no_trailing_slash and u.rstrip("/") != u and u.count("/") > 3:
            add(ERROR, "canonical", u,
                "trailing slash, but this property is declared trailing_slash:false — it 308-redirects")

        # structure
        if v["h1"] == 0:
            add(WARN, "heading", u, "no <h1>")
        elif v["h1"] > 1:
            add(WARN, "heading", u, f'{v["h1"]} <h1> elements — there should be one')
        if not v["lang"]:
            add(WARN, "lang", u, "no lang attribute on <html>")

        # structured data
        if not v["ldjson"]:
            add(WARN, "json-ld", u, "no structured data")
        for block in v["ldjson"]:
            try:
                d = json.loads(block)
            except json.JSONDecodeError as e:
                add(ERROR, "json-ld", u, f"invalid JSON: {e}")
                continue
            if "@type" not in d:
                add(ERROR, "json-ld", u, "JSON-LD without @type")

        # social preview
        for k, label in (("og_title", "og:title"), ("og_desc", "og:description"), ("og_image", "og:image")):
            if not v[k]:
                add(WARN, "open-graph", u, f"no {label}")

        # measurement
        if analytics_src and not v["analytics"]:
            add(ERROR, "analytics", u,
                f"no {analytics_src} — this page is unmeasured")

        # Links and assets that point nowhere. Offline, but decisive: the file
        # either exists in the repo or the deployed page 404s. This is how the
        # shared 404 page shipped with a favicon that 404'd on three domains —
        # each property uses different icon filenames, and nothing checked.
        root = "." if not v["file"].startswith("sites/") else "sites/" + v["file"].split("/")[1]
        here = os.path.dirname(os.path.join(SITE_REPO, v["file"]))
        rootdir = os.path.join(SITE_REPO, root)

        def resolve(ref):
            ref = unquote(ref.split("#")[0].split("?")[0])
            if not ref:
                return None
            base = rootdir if ref.startswith("/") else here
            return os.path.normpath(os.path.join(base, ref.lstrip("/")))

        broken = []
        for href in re.findall(r'href="([^"]+)"', v["body"]):
            if href.startswith(("http", "mailto:", "tel:", "#", "javascript:", "data:")):
                continue
            t = resolve(href)
            if t and not (os.path.isfile(t) or os.path.isfile(t + ".html")
                          or os.path.isfile(os.path.join(t, "index.html"))):
                broken.append(href)
        if broken:
            add(ERROR, "broken-link", u, f"link(s) to nothing: {', '.join(sorted(set(broken))[:4])}")

        missing = []
        for ref in re.findall(r'(?:src|href)="([^"]+\.(?:png|jpe?g|webp|svg|css|js|mp4|ico))"', v["html"]):
            if ref.startswith(("http", "data:")):
                continue
            t = resolve(ref)
            if t and not os.path.isfile(t):
                missing.append(ref)
        if missing:
            add(ERROR, "missing-asset", u, f"referenced but not in the repo: {', '.join(sorted(set(missing))[:4])}")

        # Thin content. A page Google has fetched still has to say enough to
        # match a query; under ~120 words in <main> it rarely does.
        words = len(re.sub(r"<[^>]+>", " ", v["body"]).split())
        if words < 120:
            add(WARN, "thin-content", u, f"{words} words in <main>")

        # sitemap membership
        if u not in smap:
            add(ERROR, "sitemap", u, "canonical is not in any sitemap — regenerate the sitemap")

        # reachability
        if inbound[u] == 0:
            add(ERROR, "orphan", u, "no internal link anywhere points at this page")
        elif inbound[u] == 1:
            add(INFO, "weak-link", u, "only one inbound internal link")

        # Images. Tags with no src are JavaScript placeholders — the lightbox
        # fills them on click — so they render nothing, shift no layout, and
        # need no dimensions. Counting them produced 26 findings and not one
        # real defect, which is the kind of noise that gets an audit ignored.
        imgs = [i for i in re.findall(r"<img[^>]*>", v["body"], re.I) if re.search(r"\bsrc=", i, re.I)]
        noalt = [i for i in imgs if not re.search(r'\balt=', i, re.I)]
        if noalt:
            add(WARN, "alt-text", u, f"{len(noalt)} of {len(imgs)} <img> without an alt attribute")
        nodim = [i for i in imgs if not (re.search(r"\bwidth=", i, re.I) and re.search(r"\bheight=", i, re.I))]
        if nodim:
            add(WARN, "layout-shift", u,
                f"{len(nodim)} of {len(imgs)} <img> without width and height — the page reflows as they load")

    # ---- cross-page duplication ------------------------------------------
    for field, cat in (("title", "duplicate-title"), ("desc", "duplicate-description")):
        seen = collections.defaultdict(list)
        for u, v in pages.items():
            if v[field]:
                seen[v[field]].append(u)
        for value, urls in seen.items():
            if len(urls) > 1:
                add(ERROR, cat, urls[0],
                    f'shared by {len(urls)} pages, which then compete for the same query: '
                    + ", ".join(urls[1:]) + f' — "{value[:60]}…"')

    # ---- hreflang reciprocity --------------------------------------------
    for u, v in pages.items():
        for lang, href in v["alternates"]:
            if lang == "x-default":
                continue
            t = by_norm.get(norm(href))
            if t is None:
                add(ERROR, "hreflang", u, f"points at {href}, which is not a page in this repo")
            elif not any(norm(h) == norm(u) for _, h in pages[t]["alternates"]):
                add(ERROR, "hreflang", u, f"{href} does not point back — hreflang must be reciprocal")

    # ---- site-level -------------------------------------------------------
    for host, folder in PROPERTIES.items():
        base = os.path.join(SITE_REPO, folder)
        for f, cat in (("robots.txt", "robots"), ("sitemap.xml", "sitemap")):
            if not os.path.exists(os.path.join(base, f)):
                add(ERROR, cat, f"https://{host}/",
                    f"no {f}" + (f" — run `{sitemap_cmd}`" if sitemap_cmd else ""))
        r = os.path.join(base, "robots.txt")
        if os.path.exists(r) and "Sitemap:" not in open(r, encoding="utf-8").read():
            add(WARN, "robots", f"https://{host}/", "robots.txt does not point at the sitemap")

    # Every noindex page is reported, not silently skipped. Skipping is right —
    # the 404 has no canonical and every check would misfire on it — but a
    # product page marked noindex by accident would then disappear from this
    # report at exactly the moment someone needed to be told.
    for rel in noindexed:
        add(INFO, "noindex", rel, "excluded from indexing and from every check below — intended for 404 pages only")

    orphan_sitemap = smap - set(pages)
    for u in sorted(orphan_sitemap):
        add(ERROR, "sitemap", u, "in a sitemap but no page claims it as its canonical")

    # ---- report -----------------------------------------------------------
    order = {ERROR: 0, WARN: 1, INFO: 2}
    if args.errors:
        findings = [f for f in findings if f[0] == ERROR]
    findings.sort(key=lambda f: (order[f[0]], f[1], f[2]))

    counts = collections.Counter(f[0] for f in findings)
    print(f"{len(pages)} pages across {len(set(prop_of(u) for u in pages))} properties")
    print(f"{counts[ERROR]} errors · {counts[WARN]} warnings · {counts[INFO]} notes\n")

    by_cat = collections.defaultdict(list)
    for sev, cat, url, detail in findings:
        by_cat[(order[sev], sev, cat)].append((url, detail))

    for (_, sev, cat), items in sorted(by_cat.items()):
        print(f"── {sev}  {cat}  ({len(items)})")
        for url, detail in items[:25]:
            print(f"   {url}\n     {detail}")
        if len(items) > 25:
            print(f"   … and {len(items) - 25} more")
        print()

    return 1 if counts[ERROR] else 0


if __name__ == "__main__":
    sys.exit(main())
