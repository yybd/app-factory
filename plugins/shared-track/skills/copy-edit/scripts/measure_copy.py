#!/usr/bin/env python3
"""measure_copy.py — find the sentences that are likely to read badly.

Reports per sentence: length, subordinate-clause markers, em-dash asides, and
— the one a human reliably misses — pairs of ADJACENT sentences that restate each
other, measured by content-word overlap.

    python3 measure_copy.py <file-or-dir>...
    python3 measure_copy.py --max-words 25 site/i18n/en.json profile.md

Handles .md, .txt, .json (values, not keys), Xcode String Catalogs (.xcstrings —
the app's own strings, every language in one file) and a hand-authored .html page
passed by name — its visible prose only.

Every locale is measured, not only English. The locale comes from the path —
`metadata/de-DE/description.txt`, `i18n/ja.json`, `profile.he.md` — and it decides
how the text is read: clause markers are per language, and Japanese and Chinese
are measured in characters because a word count of an unspaced script is
meaningless. A language with no marker set gets the length and restatement
checks only; that is reported, so an unchecked language never reads as a clean
one.

It flags candidates. It does not judge — a long sentence that reads cleanly may
stay, and a short one that must be parsed twice must not.
"""
import argparse, glob, html, json, os, re, sys

# Subordinate-clause markers, per language. The rule they serve — at most one
# subordinate clause per sentence — is not English-specific, but the words are.
# Measuring German copy with English markers finds nothing, and nothing is
# indistinguishable from a clean bill of health.
#
# German relative pronouns (der/die/das) are also its articles, so they are left
# out: including them flags every sentence. French "qui/que" and Spanish "que"
# stay in — they are exactly as ambiguous as English "that", which the list has
# always carried, and the threshold is two markers, not one.
CLAUSE_BY_LANG = {
    "en": r"\b(which|that|because|although|though, |whereas|while|so that|"
          r"in order to|rather than|instead of|even when|even though|"
          r"unless|whenever|since)\b",
    "de": r"\b(dass|weil|obwohl|während|damit|sodass|sobald|wenn|indem|falls|"
          r"nachdem|bevor|sofern|anstatt|welche[rsnm]?)\b",
    "fr": r"\b(qui|que|qu'|dont|parce que|bien que|afin de|afin que|tandis que|"
          r"lorsque|puisque|alors que|dès que|au lieu de|même si)\b",
    "es": r"\b(que|porque|aunque|mientras|para que|ya que|cuando|puesto que|"
          r"dado que|en lugar de|si bien|cuyo|cuya)\b",
    "he": r"(?:^|\s)(?:ש|כ)?(?:כדי|מפני ש|כיוון ש|למרות ש|בזמן ש|כאשר|במקום|"
          r"אלא ש|כך ש|אף על פי ש)(?=\s|$)",
}
STOP = set("""a an the and or but of to in on for with without at by from as is are was were be been
being it its this that these those you your our we they their there here if then than so not no any
all each every into over under more most much many some such own same other another can could will
would may might must do does did have has had""".split())
HEB = re.compile(r"[֐-׿]")
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]")
# A locale as it appears in a path: an i18n stem (he, ja), a store directory
# (en-US, de-DE, zh-Hans), or Play's Hebrew (iw-IL).
LOCALE = re.compile(r"^[a-z]{2}(?:[-_][A-Za-z]{2,4})?$")
# The store fields that are prose. name/keywords/urls are neither sentences nor
# translations of each other, and comparing them reports noise.
PROSE_FIELDS = {"description.txt", "promotional_text.txt", "subtitle.txt",
                "release_notes.txt", "full_description.txt", "short_description.txt"}
# Store files that are lists, names or URLs. A keyword list has no sentences, so
# every locale reports it as one enormous one — a flag that can never be acted on.
NOT_PROSE = re.compile(r"(?:^(?:keywords|name|title|copyright|video|"
                       r"primary_category|secondary_category)|_url|_categor(?:y|ies))\.txt$")
# Ends a chunk without ending a sentence. A single letter covers initials
# ("J. P. Smith"); the rest are the abbreviations this copy actually uses — in
# every language it ships in. German is the reason this list is not English-only:
# "macOS 14 oder neuer bzw. iOS 17" is one sentence, and read as two it reports a
# translation as having grown a claim.
ABBREV = re.compile(r"(?:^|\s)(?:[A-Za-z]|e\.g|i\.e|etc|vs|cf|approx|no|figs?|pp?|Mr|Mrs|Dr|St|Inc|Ltd|Co"
                    r"|bzw|z\.B|d\.h|ggf|inkl|evtl|usw|u\.a|ca|Nr|Abb"
                    r"|p\.ex|ex|env|p\.ej|ej|núm|art|aprox)\.$", re.I)


def family(locale):
    """The measurement family a locale belongs to.

    en-GB and en-US are one language to measure; zh-Hans and ja are one problem
    (no spaces, so no words); he and Play's iw are the same Hebrew.
    """
    base = re.split(r"[-_]", locale)[0].lower()
    if base in ("he", "iw"):
        return "he"
    if base in ("ja", "zh", "ko"):
        return "cjk"
    return base


def locale_of(path):
    """The locale a file is written in, read from its path.

    Three shapes in this studio: a store metadata directory
    (`metadata/de-DE/description.txt`), an i18n dictionary (`i18n/ja.json`, and
    release notes as `release-notes/1.2/de-DE.txt`), and a translated markdown
    twin (`profile.he.md`). Anything else is the source language.
    """
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    for d in reversed(parts[:-1]):
        if LOCALE.match(d):
            return d
    stem = parts[-1].rsplit(".", 1)[0]
    if LOCALE.match(stem):
        return stem
    if "." in stem and LOCALE.match(stem.rsplit(".", 1)[-1]):
        return stem.rsplit(".", 1)[-1]
    return "en"


def sentences(text):
    # A bullet is its own unit — without this, a run of bullets measures as one
    # enormous sentence and every real signal drowns in the artefact.
    text = re.sub(r"\s*[•·]\s*", "\n", text)
    out = []
    for block in text.split("\n"):
        block = re.sub(r"\s+", " ", block).strip()
        if not block:
            continue
        # Hebrew copy puts a directional mark (U+200E/U+200F) before Latin words,
        # so a sentence can begin with an invisible character. Without allowing for
        # it, every "…. ‏BrandName …" reads as one sentence and the parity check
        # cries wolf on text that is actually fine.
        # A sentence can open on anything: a capital, a Hebrew letter, an rsync
        # flag ("‎--bwlimit מגביל…"), a number, a markdown bold, or a lowercase
        # product name ("openrsync ships inside the app"). So split at every
        # terminator and put back only the ones that are abbreviations — the
        # closed set below — which is the case a lookahead cannot tell apart.
        # Japanese and Chinese end a sentence with 。！？ and put no space after
        # it, so those terminators split on their own with nothing following.
        parts = re.split(r"(?<=[。！？])|(?<=[.!?…])\s+[‎‏]*|(?<=[.!?])\s*$", block)
        merged = []
        for part in parts:
            if merged and ABBREV.search(merged[-1]):
                merged[-1] = merged[-1] + " " + part
            else:
                merged.append(part)
        parts = merged
        out += [p.strip() for p in parts if p and p.strip()]
    return out


def units(text):
    """Claims, for comparing two languages.

    A bullet is one claim however it is punctuated. Japanese closes a clause with
    。 where English uses a comma, so counting sentences inside a bullet reports
    idiom as drift. Prose outside a bullet list is still counted by sentence.
    """
    n = 0
    for line in re.sub(r"\s*[•·]\s*", "\n• ", text).split("\n"):
        line = line.strip()
        if not line:
            continue
        n += 1 if re.match(r"^[•·*]|^-\s", line) else len(sentences(line))
    return n


def drift(n_src, n_tr, fam):
    """Whether two unit counts are far enough apart to mean a content difference.

    Fewer units in the translation always matters: something is missing. More
    units usually matters too — a claim was added — except in Japanese and
    Chinese, which idiomatically close a clause where English uses a comma, so a
    small gain there is punctuation rather than content. The direction that can
    lose a claim is checked in every language.
    """
    if n_tr < n_src:
        return True
    return n_tr > n_src + 2 if fam == "cjk" else n_tr > n_src


def content_words(s, fam="en"):
    # An unspaced script has no words to compare: \w+ swallows a whole Japanese
    # sentence as one token, and every pair then overlaps either fully or not at
    # all. Character bigrams are the unit that actually repeats.
    if fam == "cjk":
        chars = re.sub(r"[\s、。！？，,·・「」『』（）()]", "", s)
        return {chars[i:i + 2] for i in range(len(chars) - 1)}
    ws = re.findall(r"[\w֐-׿'-]+", s.lower())
    return {w for w in ws if w not in STOP and len(w) > 2}


def length(s, fam):
    if fam == "cjk":
        return len(re.sub(r"\s", "", s)), "c"
    return len(re.findall(r"[\w֐-׿'-]+", s)), "w"


RHYTHM = []          # (label, paragraph-preview, sentence lengths)


def rhythm(label, text, locale="en"):
    """Flag a prose paragraph whose sentences are all the same length.

    Every other check here looks for a sentence that is too long. This one looks for the
    opposite failure: a paragraph that has been edited until nothing varies. People write
    unevenly — a long thought, then a short one — so a run of sentences that all land
    within a couple of words of each other is the signature of an over-corrected pass,
    not of careful writing. Nothing else in this script can see it.
    """
    fam = family(locale)
    for para in re.split(r"\n\s*\n", text):
        lines = [l.strip() for l in para.splitlines() if l.strip()]
        if not lines:
            continue
        # Bullet lists and headings are uniform by design — measuring them would flag
        # every well-formed list in the file.
        listish = sum(1 for l in lines
                      if l.startswith(("•", "-", "*", "‣")) or re.match(r"\d+[.)]\s", l))
        if listish > len(lines) / 2:
            continue
        if len(lines) == 1 and len(lines[0]) < 45 and lines[0] == lines[0].upper():
            continue
        ns = [length(x, fam)[0] for x in sentences(" ".join(lines))]
        ns = [n for n in ns if n >= 3]
        if len(ns) < 4:
            continue
        mean = sum(ns) / len(ns)
        if mean <= 0:
            continue
        spread = max(ns) - min(ns)
        cv = (sum((n - mean) ** 2 for n in ns) / len(ns)) ** 0.5 / mean
        # Length variance is only half of it. The other half — and the half that catches an
        # over-corrected pass — is punctuation: a writer subordinates. Prose that runs for
        # several sentences without a single dash, colon or semicolon has had every aside
        # flattened into its own sentence, which is exactly what "split the long ones"
        # produces when it is applied without judgement.
        joined = " ".join(lines)
        asides = sum(joined.count(c) for c in ("—", ":", ";"))
        if len(ns) >= 5 and asides == 0:
            RHYTHM.append((f"{label} [{locale}]" if locale != "en" else label,
                           joined[:110] + "  ← no dash, colon or semicolon anywhere", ns))
            continue
        if cv < 0.22 or spread <= 4:
            RHYTHM.append((f"{label} [{locale}]" if locale != "en" else label,
                           " ".join(lines)[:110], ns))


def measure(label, text, limits, out, locale="en"):
    max_words, max_chars = limits
    fam_file = family(locale)
    prev = None
    for s in sentences(text):
        # The path names the locale, but a file can still hold another script —
        # a Hebrew line in an untagged .md, a Japanese string in a shared JSON.
        # Read the sentence itself when the path claimed the source language.
        fam = fam_file
        if fam == "en":
            fam = "he" if HEB.search(s) else "cjk" if CJK.search(s) else "en"
        flags = []
        n, unit = length(s, fam)
        if n > (max_chars if fam == "cjk" else max_words):
            flags.append(f"{n}{unit}")
        marker = CLAUSE_BY_LANG.get(fam)
        if marker:
            c = len(re.findall(marker, s, re.I))
            if c > 1:
                flags.append(f"{c} clauses")
        if fam != "cjk" and s.count("—") > 1:
            flags.append(f"{s.count('—')} dashes")
        if prev is not None:
            a, b = content_words(prev, fam), content_words(s, fam)
            if a and b:
                overlap = len(a & b) / min(len(a), len(b))
                if overlap >= 0.5 and min(len(a), len(b)) >= 4:
                    flags.append(f"restates previous ({overlap:.0%})")
        if flags:
            out.append((f"{label} [{locale}]" if locale != "en" else label, s, flags))
        prev = s


def xcstrings(path):
    """(source language, {locale: {key: text}}) from an Xcode String Catalog.

    A catalog holds every language of the app's own UI in one file, so the locale
    cannot come from the path — it is the key each value sits under. A key with no
    localization for the source language is its own source text, which is how Xcode
    stores an untranslated string.
    """
    d = json.load(open(path, encoding="utf-8"))
    src = d.get("sourceLanguage") or "en"
    out = {}

    def value(unit):
        if "stringUnit" in unit:
            return unit["stringUnit"].get("value", "")
        for kind in ("plural", "device"):
            if kind in unit.get("variations", {}):
                return " ".join(value(v) for v in unit["variations"][kind].values())
        return ""

    for key, entry in (d.get("strings") or {}).items():
        locs = entry.get("localizations") or {}
        for lang, unit in locs.items():
            v = value(unit)
            if v:
                out.setdefault(lang, {})[key] = v
        if src not in locs and key.strip():
            out.setdefault(src, {})[key] = key
    return src, out


def twins(paths):
    """Source file → its translations, for the two file-per-language shapes.

    `i18n/en.json` beside `i18n/de.json`; `profile.md` beside `profile.he.md`.
    """
    pairs = {}
    for p in paths:
        for f in walk(p):
            d, base = os.path.dirname(f) or ".", os.path.basename(f)
            if base == "en.json":
                for g in sorted(os.listdir(d)):
                    stem = g[:-5]
                    if g.endswith(".json") and g != base and LOCALE.match(stem):
                        pairs.setdefault(f, {})[stem] = os.path.join(d, g)
            elif base.endswith(".md") and not LOCALE.match(base[:-3].rsplit(".", 1)[-1]):
                for g in sorted(glob.glob(f[:-3] + ".*.md")):
                    loc = os.path.basename(g)[:-3].rsplit(".", 1)[-1]
                    if LOCALE.match(loc):
                        pairs.setdefault(f, {})[loc] = g
    return pairs


def locale_groups(paths):
    """Store strings that exist once per locale, grouped by the string.

    Two shapes in the hub: `metadata/<locale>/<field>.txt` (both stores) and
    `release-notes/<version>/<locale>.txt`. Both are the same listing sentence
    written in several languages, which is what makes them comparable.
    """
    groups = {}
    for p in paths:
        # Only a directory is walked. Given a single file, walking its parent
        # would drag in every sibling tree — pointing at one String Catalog in a
        # repo root would compare the whole repo.
        if not os.path.isdir(p):
            continue
        for root, dirs, files in os.walk(p):
            for d in sorted(dirs):
                if not LOCALE.match(d):
                    continue
                for f in sorted(os.listdir(os.path.join(root, d))):
                    if f in PROSE_FIELDS:
                        groups.setdefault((root, f), {})[d] = os.path.join(root, d, f)
            for f in sorted(files):
                stem, ext = os.path.splitext(f)
                if ext == ".txt" and LOCALE.match(stem):
                    groups.setdefault((root, "release notes"), {})[stem] = os.path.join(root, f)
    return groups


def is_name_list(v):
    """A separator-joined list of product names — the same string in every language.

    "AppOne · AppTwo · AppThree" is not an untranslated string; brand names
    stay in Latin by policy. Without this the identical-text check reports the
    house rule as a defect.
    """
    parts = [x for x in re.split(r"\s*[·•|/]\s*", v.strip()) if x]
    return len(parts) > 1 and not re.search(r"[.!?…。]", v) and all(len(x.split()) <= 4 for x in parts)


def source_locale(locales):
    for c in ("en-US", "en", "en-GB", "en-AU"):
        if c in locales:
            return c
    return sorted(locales)[0]


def rel(path):
    """A path the reader can act on: enough of it to name the file's owner."""
    p = os.path.relpath(path, os.getcwd())
    return p if not p.startswith("..") else os.sep.join(path.split(os.sep)[-4:])


def read(path):
    return open(path, encoding="utf-8", errors="replace").read().strip()


WARNINGS = []


def warn(line):
    """A parity finding: printed, and counted so a delivery gate can act on it."""
    WARNINGS.append(line)
    print(line)


def parity(paths):
    """Compare the English source with every translation, unit by unit.

    Same claims, same order, one sentence to one sentence. The reason is review,
    not symmetry: a drift is a claim that exists in one language and not the
    other, and on a language nobody on this side reads, this comparison is the
    only thing looking. When the versions drift, a defect can sit in the English
    where nobody is reading closely — which is how a string once shipped opening
    "Keep it somewhere safe" with nothing for "it" to refer to.
    """
    pairs, groups = twins(paths), locale_groups(paths)
    if not pairs and not groups:
        return
    print("\n=== translation parity ===")

    for en_f, others in sorted(pairs.items()):
        if en_f.endswith(".json"):
            en = json.load(open(en_f, encoding="utf-8"))
            for loc, g in sorted(others.items()):
                tr = json.load(open(g, encoding="utf-8"))
                bad, missing, same = [], [], []
                for k, v in en.items():
                    # A long value is not necessarily prose: a URL has no
                    # sentences and is identical in every language by design.
                    if not isinstance(v, str) or v.lstrip().startswith("<") or len(v) < 40:
                        continue
                    if re.match(r"^\s*(?:https?://|/|[\w.-]+$)", v) or " " not in v.strip():
                        continue
                    if k not in tr:
                        missing.append(k)
                        continue
                    if tr[k].strip() == v.strip() and family(loc) != "en" and not is_name_list(v):
                        same.append(k)
                    na, nb = units(v), units(tr[k])
                    if drift(na, nb, family(loc)):
                        bad.append((k, na, nb))
                print(f"  {rel(en_f)} ↔ {loc}.json")
                for k in missing:
                    warn(f"    ⚠️  {k}: missing in {loc}")
                for k in same:
                    warn(f"    ⚠️  {k}: identical to the English — untranslated")
                for k, na, nb in bad:
                    warn(f"    ⚠️  {k}: en has {na} claim(s), {loc} has {nb} — "
                          "one carries content the other does not")
                if not bad and not missing and not same:
                    print("    ✅ every string matches claim for claim")
        else:
            # Markdown twin (profile.md / profile.he.md). Sections are the unit:
            # a heading present in one and not the other, or a section that grew
            # in one language, is where the two documents have drifted apart.
            # Structure, not sentence counts. Hebrew prose is legitimately more
            # compact, so comparing lengths on a profile cries wolf. What actually
            # signals a missing claim is a section or a bullet present in one
            # document and absent from the other.
            def structure(path):
                out, cur, heads = [], None, []
                for line in open(path, encoding="utf-8"):
                    if line.startswith("## "):
                        heads.append(line.strip()[3:])
                        out.append(0)
                        cur = len(out) - 1
                    elif cur is not None and (line.startswith("- **") or line.startswith("### ")):
                        out[cur] += 1
                return heads, out

            (ha, ba) = structure(en_f)
            for loc, g in sorted(others.items()):
                (hb, bb) = structure(g)
                print(f"  {rel(en_f)} ↔ {os.path.basename(g)}")
                if len(ha) != len(hb):
                    warn(f"    ⚠️  {len(ha)} section(s) in English, {len(hb)} in {loc} — "
                          "the documents no longer have the same shape")
                    continue
                gaps = [(i, ba[i], bb[i]) for i in range(len(ba)) if ba[i] != bb[i]]
                for i, na, nb in gaps:
                    warn(f"    ⚠️  \"{ha[i][:44]}\": {na} item(s) in English, {nb} in {loc}")
                if not gaps:
                    print("    ✅ same sections, same items in each")

    # A same-language variant (en-GB beside en-US) legitimately repeats the
    # source wherever no spelling differs; only another language repeating the
    # English is an untranslated string.
    for (root, field), by_locale in sorted(groups.items()):
        if len(by_locale) < 2:
            continue
        src = source_locale(set(by_locale))
        base = read(by_locale[src])
        n_src = units(base)
        label = rel(root)
        print(f"  {label}/ — {field} ({src} → {len(by_locale) - 1} translation(s))")
        clean = True
        for loc in sorted(set(by_locale) - {src}):
            text = read(by_locale[loc])
            n = units(text)
            if not text:
                warn(f"    ⚠️  {loc}: empty")
            elif text == base and family(loc) != family(src) and not is_name_list(text):
                warn(f"    ⚠️  {loc}: identical to {src} — untranslated")
            elif drift(n_src, n, family(loc)):
                warn(f"    ⚠️  {loc}: {src} has {n_src} claim(s), {loc} has {n} — "
                      "one carries content the other does not")
            else:
                continue
            clean = False
        if clean:
            print("    ✅ every translation matches claim for claim")


def catalog_parity(catalogs):
    """A String Catalog's own languages, against its source language.

    Only the strings long enough to carry more than one claim: a button label that
    is one word in every language says nothing about drift, and reporting it buries
    the alert message that lost a sentence.
    """
    for path, src, by_locale in catalogs:
        base = by_locale.get(src, {})
        prose = {k: v for k, v in base.items() if len(v) >= 40}
        if not prose or len(by_locale) < 2:
            continue
        print(f"\n=== {rel(path)} — {src} → {len(by_locale) - 1} language(s) ===")
        for lang in sorted(set(by_locale) - {src}):
            tr = by_locale[lang]
            bad = [(k, units(v), units(tr[k])) for k, v in prose.items()
                   if k in tr and drift(units(v), units(tr[k]), family(lang))]
            missing = [k for k in prose if k not in tr]
            same = [k for k, v in prose.items()
                    if k in tr and tr[k].strip() == v.strip() and family(lang) != family(src)]
            for k in missing:
                warn(f"    ⚠️  {lang}: \"{k[:56]}\" missing")
            for k in same:
                warn(f"    ⚠️  {lang}: \"{k[:56]}\" identical to the {src} — untranslated")
            for k, na, nb in bad:
                warn(f"    ⚠️  {lang}: \"{k[:44]}\" — {src} has {na} claim(s), {lang} has {nb}")
            if not (bad or missing or same):
                print(f"    ✅ {lang}: every string matches claim for claim")


def html_text(raw):
    """The prose a visitor reads: no head, no scripts, no tags, no entities.

    Without this an .html file measures its own <meta> and <link> tags as
    sentences — every one of them "restating" the line above — and the body copy,
    which is the whole point, never gets looked at.
    """
    raw = re.sub(r"(?is)<head\b.*?</head>|<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->", " ", raw)
    # Block boundaries have to become line breaks before the tags go, or two
    # neighbouring paragraphs merge into one very long "sentence".
    raw = re.sub(r"(?i)</(p|li|h[1-6]|div|section|figcaption|td|th|blockquote)>", "\n", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return "\n".join(l.strip() for l in raw.splitlines() if l.strip())


def walk(path):
    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for f in sorted(files):
                if f.endswith((".md", ".txt", ".json", ".xcstrings")):
                    yield os.path.join(root, f)
    else:
        yield path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--max-words", type=int, default=25)
    ap.add_argument("--max-chars", type=int, default=60,
                    help="sentence ceiling for Japanese/Chinese, counted in characters")
    ap.add_argument("--no-parity", action="store_true",
                    help="skip the sentence-for-sentence comparison against the English")
    ap.add_argument("--parity-only", action="store_true",
                    help="report only the comparison against the English, not sentence craft")
    ap.add_argument("--fail-on-parity", action="store_true",
                    help="exit non-zero when a translation is missing, untranslated or "
                         "carries a different number of claims — for a delivery gate")
    a = ap.parse_args()

    out, seen_locales, catalogs = [], {}, []
    limits = (a.max_words, a.max_chars)
    n_files = 0
    for p in a.paths:
        for f in walk(p):
            if NOT_PROSE.search(os.path.basename(f)):
                continue
            n_files += 1
            loc = locale_of(f)
            seen_locales[family(loc)] = seen_locales.get(family(loc), 0) + 1
            if f.endswith(".xcstrings"):
                src, by_locale = xcstrings(f)
                for lang, strings in sorted(by_locale.items()):
                    seen_locales[family(lang)] = seen_locales.get(family(lang), 0) + 1
                    for k, v in strings.items():
                        measure(f"{os.path.basename(f)}:{k[:40]}", v, limits, out, lang)
                catalogs.append((f, src, by_locale))
                continue
            raw = open(f, encoding="utf-8", errors="replace").read()
            if f.endswith(".json"):
                try:
                    for k, v in json.loads(raw).items():
                        if isinstance(v, str) and not v.lstrip().startswith("<"):
                            measure(f"{os.path.basename(f)}:{k}", v, limits, out, loc)
                    continue
                except json.JSONDecodeError:
                    pass
            if f.endswith((".html", ".htm")):
                if "GENERATED" in raw[:400]:
                    # Baked from an i18n dictionary — measure the dictionary, or
                    # every flag is reported twice and fixed in the wrong file.
                    print(f"  skipping {f} (generated; measure its i18n/ instead)")
                    continue
                body = html_text(raw)
            else:
                body = "\n".join(l for l in raw.splitlines()
                                 if not l.startswith(("#", "|", "```", "    ", "\t", ">")))
            measure(os.path.basename(f), body, limits, out, loc)
            rhythm(os.path.basename(f), body, loc)

    if not a.parity_only:
        for label, s, flags in out:
            print(f"\n[{', '.join(flags)}]  {label}")
            print(f"  {s[:200]}{'…' if len(s) > 200 else ''}")
        print(f"\n{len(out)} candidate(s) across {n_files} file(s). "
              f"Judge each — the flag is a spotlight, not a verdict.")
        if RHYTHM:
            print("\n=== uniform rhythm (over-editing, not clumsiness) ===")
            for label, preview, ns in RHYTHM:
                print(f"  {label}: sentence lengths {ns}")
                print(f"    {preview}…")
            print("  A paragraph where nothing varies reads written-by-rule. Restore one "
                  "long sentence or one short one — do not split anything further.")
        # Say which languages went through with no clause check, so "nothing found"
        # in a language is never mistaken for "nothing there".
        unchecked = sorted(f for f in seen_locales if f not in CLAUSE_BY_LANG and f != "cjk")
        if unchecked:
            print(f"Length and restatement only (no clause markers for): {', '.join(unchecked)}.")
    if not a.no_parity:
        parity(a.paths)
        catalog_parity(catalogs)
    # The gate a delivery script calls: a missing, untranslated or drifted
    # translation is a content defect, and it ships publicly if nothing stops it.
    if a.fail_on_parity and WARNINGS:
        print(f"\n✗ {len(WARNINGS)} translation finding(s) — not matching the English source.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
