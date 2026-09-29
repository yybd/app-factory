#!/usr/bin/env python3
"""Audit the UI strings of a Capacitor/web app that keeps them in JS and HTML.

These apps have no .strings, no .xcstrings and no populated strings.xml — the
user-facing text lives in per-language object literals ({ he: …, en: … }) and in
sibling HTML spans (<span class="lbl-he">…</span><span class="lbl-en">…</span>).
Nothing validates them, and the usual lookup

    return e[lang] || e.he

means a MISSING translation is not an error: the reader is quietly shown the
fallback language instead. That is the failure this scans for.

  scan_web_strings.py app/           # or any dir; --langs he,en to change the set
"""
import argparse, os, re, sys

# No default language pair. The project's own languages are discovered from its
# translation tables, and `--langs` overrides. A hardcoded ["he", "en"] audited every
# other app against two languages it does not have.
DEFAULT_LANGS = []
# A "hardcoded string" is one written in a script this app does not treat as
# translatable text. Which script that is depends on the app — this was a Hebrew regex,
# so every non-Hebrew app got a clean report from a check that never looked at anything.
# The block is derived from the languages found, and NON_LATIN covers the common case
# where the source language is not the one written in ASCII.
NON_LATIN = re.compile(r"[^\x00-\x7F]")


def discover_langs(root):
    """The language codes this project's own translation tables use.

    A table is written `{ he: '…', en: '…' }` or `{ "fr": "…" }`, so the keys that
    recur as two-letter codes across the JavaScript ARE the app's languages. Reading
    them beats assuming a pair: a hardcoded ["he", "en"] audited every other app
    against two languages it does not have, and reported nothing.
    """
    seen = {}
    # …and its value is a string literal. `{ id: 1, on: true }` has two-letter keys
    # and is not a translation; `{ he: 'שלום', en: 'Hello' }` is.
    key = re.compile(r"[{,]\s*[\"']?([a-z]{2}(?:-[A-Z]{2})?)[\"']?\s*:\s*[\"'`]")
    for f in js_files(root):
        try:
            src = open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        # A translation table holds SEVERAL languages in one object: `{ he: …, en: … }`.
        # So a code counts only when another code sits in the same braces. Counting
        # every `xx:` that recurred made `id:`, `on:` and `to:` languages in any
        # ordinary JavaScript file — three `id:` keys is nothing — and every real table
        # was then reported as missing its "id" translation.
        for obj in re.finditer(r"\{([^{}]*)\}", src):
            codes = set(key.findall("{" + obj.group(1)))
            if len(codes) < 2:
                continue
            for c in codes:
                seen[c] = seen.get(c, 0) + 1
    return sorted(k for k, n in seen.items() if n >= 3)


def js_files(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "vendor", ".git", "www")]
        for f in files:
            if f.endswith((".js", ".mjs")):
                yield os.path.join(base, f)


def html_files(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "vendor", ".git", "www")]
        for f in files:
            if f.endswith((".html", ".htm")):
                yield os.path.join(base, f)


def enclosing_object(src, at):
    """The {...} literal containing position `at`, as (start, end) or None."""
    depth, start = 0, None
    i = at
    while i >= 0:                       # walk back to the opening brace
        c = src[i]
        if c == "}":
            depth += 1
        elif c == "{":
            if depth == 0:
                start = i
                break
            depth -= 1
        i -= 1
    if start is None:
        return None
    depth, j = 0, start
    while j < len(src):                 # then forward to its match
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return start, j + 1
        j += 1
    return None


def audit_js(path, langs, findings):
    src = open(path, encoding="utf-8").read()
    seen = set()
    for m in re.finditer(r"\b(%s)\s*:" % langs[0], src):
        obj = enclosing_object(src, m.start())
        if not obj or obj in seen:
            continue
        seen.add(obj)
        start, end = obj
        body = src[start:end]
        line = src.count("\n", 0, start) + 1
        present = [l for l in langs if re.search(r"\b%s\s*:" % l, body)]
        missing = [l for l in langs if l not in present]
        if missing:
            snippet = re.sub(r"\s+", " ", body)[:70]
            findings.append((path, line, "missing " + "/".join(missing), snippet))
            continue
        vals = {}
        for l in langs:                 # compare only simple single-quoted values
            v = re.search(r"\b%s\s*:\s*'([^'\\]*)'" % l, body)
            if v:
                vals[l] = v.group(1)
        if len(vals) == len(langs) and len(set(vals.values())) == 1 and vals[langs[0]].strip():
            findings.append((path, line, "identical across languages",
                             re.sub(r"\s+", " ", body)[:70]))


def audit_html(path, langs, findings):
    """Only ONE direction is a bug, and it must be checked as SIBLINGHOOD.

    The swap pattern is `<span class="lbl-he">…</span><span class="lbl-en">…</span>`:
    in English `body.lang-en .lbl-he {display:none}` hides the Hebrew and the
    sibling replaces it. A lbl-he with no lbl-en sibling therefore does not fall
    back — it DISAPPEARS, leaving an empty label in English.

    A bare lbl-en is not the mirror of that: it is the deliberate *stacked*
    pattern, an English subtitle under Hebrew text, shown on purpose.

    Proximity is not good enough here: the next element's own lbl-en sits a few
    dozen characters away and would mask a genuinely broken pair. The replacement
    must be the IMMEDIATELY following element.
    """
    src = open(path, encoding="utf-8").read()
    primary, secondary = langs[0], langs[1]
    pat = re.compile(r'<span[^>]*\blbl-%s\b[^>]*>.*?</span>\s*' % primary, re.S)
    nxt = re.compile(r'<span[^>]*\blbl-%s\b' % secondary, re.I)
    for m in pat.finditer(src):
        following = src[m.end():m.end() + 120]
        if not nxt.match(following):
            line = src.count("\n", 0, m.start()) + 1
            findings.append((path, line,
                             f"lbl-{primary} with no lbl-{secondary} sibling — vanishes in {secondary}",
                             re.sub(r"\s+", " ", m.group(0))[:70]))


def audit_hardcoded(path, langs, findings):
    """String literals in the app's own script that sit outside a language pair."""
    src = open(path, encoding="utf-8").read()
    pairs = []
    for m in re.finditer(r"\b(%s)\s*:" % "|".join(langs), src):
        o = enclosing_object(src, m.start())
        if o:
            pairs.append(o)
    for m in re.finditer(r"'([^'\\\n]*)'", src):
        if not NON_LATIN.search(m.group(1)) or len(m.group(1).strip()) < 2:
            continue
        if any(s <= m.start() < e for s, e in pairs):
            continue
        line = src.count("\n", 0, m.start()) + 1
        findings.append((path, line, "hardcoded — not in a language pair", m.group(1)[:60]))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("root", nargs="?", default="app")
    p.add_argument("--langs", default=",".join(DEFAULT_LANGS))
    p.add_argument("--no-hardcoded", action="store_true",
                   help="skip the heuristic hardcoded-text scan")
    a = p.parse_args()
    langs = [l.strip() for l in a.langs.split(",") if l.strip()]
    if not langs:
        langs = discover_langs(a.root)
        if not langs:
            sys.exit(f"✗ no language tables found under {a.root}. Pass --langs xx,yy, or "
                     f"point at the directory that holds the app's JavaScript.")
        print(f"languages discovered from the project: {', '.join(langs)}")
    if len(langs) < 2:
        sys.exit("--langs needs at least two languages")
    if not os.path.isdir(a.root):
        sys.exit(f"no such directory: {a.root}")

    findings = []
    for f in js_files(a.root):
        audit_js(f, langs, findings)
        if not a.no_hardcoded:
            audit_hardcoded(f, langs, findings)
    for f in html_files(a.root):
        audit_html(f, langs, findings)

    if not findings:
        print(f"no findings across {langs} — every pair carries every language")
        return 0
    order = {"missing": 0, "lbl-": 1, "identical": 2, "hardcoded": 3}
    findings.sort(key=lambda f: (next((v for k, v in order.items() if f[2].startswith(k)), 9),
                                 f[0], f[1]))
    width = max(len(k) for _, _, k, _ in findings)
    for path, line, kind, snippet in findings:
        print(f"{os.path.relpath(path)}:{line}  {kind.ljust(width)}  {snippet}")
    print(f"\n{len(findings)} finding(s). 'missing' is the one that ships a wrong "
          f"language silently — the lookup falls back instead of failing.\n"
          f"'hardcoded' is a heuristic: judge each, some are deliberate.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
