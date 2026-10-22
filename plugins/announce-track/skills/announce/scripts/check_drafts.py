#!/usr/bin/env python3
"""Check announcement drafts against the mechanical rules of the channel they are for.

    python3 check_drafts.py <drafts-dir>
    python3 check_drafts.py <drafts-dir> --links     # also fetch every URL (network)

A draft's channel is read from its file name — the convention the announce skill writes:

    hn-title.txt        one line, the Show HN / Ask HN title
    hn-comment.txt      the first comment, plain text
    x-thread.txt        posts separated by a line holding only ---
    bluesky-thread.txt  same shape
    linkedin*.md        a post, with its first comment after a line holding only ---
                        (no Markdown: LinkedIn shows it as typed)
    reddit*.md          a post: the first line is the title
    crosspost-*.md      a dev.to / Medium copy, front matter first

What is checked is only what a channel enforces or silently breaks — a title HN cuts,
Markdown HN prints as literal characters, a front matter dev.to does not see because a
comment came first. Whether the words are any good is not mechanical and is not checked.

Exit 1 when any draft breaks a rule; warnings alone exit 0.
"""
import argparse, glob, os, re, sys, unicodedata, urllib.request

LIMITS = {"x": 280, "bluesky": 300}
HN_TITLE = 80
DEVTO_TAGS = 4
URL = re.compile(r"https?://[^\s)\]>\"']+")
MD_MARKS = re.compile(r"`|^\s*>|^\s*#{1,6}\s|\*\*|\[[^\]]+\]\([^)]+\)", re.M)

failures, warnings = [], []


def fail(path, msg):
    failures.append(f"{os.path.basename(path)}: {msg}")


def warn(path, msg):
    warnings.append(f"{os.path.basename(path)}: {msg}")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


COMMENT = re.compile(r"<!--[\s\S]*?-->\n?")
STATUS = re.compile(r"^(?:> |<!-- )Status(?: \([^)]+\))?: (posted|scheduled|draft)\b", re.M)


def pasted(path):
    """The text that is pasted: the file without its <!-- --> comments. A draft carries its
    own status line as a comment (`<!-- Status: posted 2026-10-20 · <url> -->`, the form a
    hub's stats reader counts); the channel never sees it, so no check should either."""
    return COMMENT.sub("", read(path)).strip("\n")


def check_status(path):
    if path.endswith(".md") and not STATUS.search(read(path)):
        warn(path, "no `<!-- Status: draft -->` line — a hub's stats reader lists it as untracked")


# X's weighted count (twitter-text v3): a character in these ranges counts 1, any other 2.
# Latin, Hebrew, Arabic and most scripts are under 4352; of general punctuation only the
# spaces, dashes and quotes are light — "•", "…" and "→" count 2, as do CJK and emoji.
X_LIGHT = ((0x0000, 0x10FF), (0x2000, 0x200D), (0x2010, 0x201F), (0x2032, 0x2037))
# What joins a code point to the emoji before it: variation selectors, skin tones, the
# keycap, tag characters, and the zero-width joiner with the code point after it.
EMOJI_TAIL = re.compile("[︎️⃣\U0001F3FB-\U0001F3FF\U000E0020-\U000E007F]|‍.")
REGIONAL = re.compile("[\U0001F1E6-\U0001F1FF]{2}")


def x_weight(ch):
    o = ord(ch)
    return 1 if any(a <= o <= b for a, b in X_LIGHT) else 2


def x_length(text):
    """What X counts, not what len() counts: every URL is 23 characters whatever its real
    length, a character outside the light ranges counts 2, and an emoji counts 2 however
    many code points build it (a flag, a skin tone, a ZWJ family). Text is NFC first, as
    X normalises it."""
    text = unicodedata.normalize("NFC", URL.sub("x" * 23, text))
    text = REGIONAL.sub("\U0001F1E6", text)
    n, i = 0, 0
    while i < len(text):
        j = i + 1
        while (m := EMOJI_TAIL.match(text, j)):
            j = m.end()
        n += 2 if j - i > 1 else x_weight(text[i])
        i = j
    return n


def check_hn_title(path):
    t = pasted(path).strip()
    if "\n" in t:
        fail(path, "a title is one line")
    if len(t) > HN_TITLE:
        fail(path, f"{len(t)} characters — HN cuts titles at {HN_TITLE}")
    if not re.match(r"(Show|Ask|Tell) HN: ", t):
        warn(path, "no 'Show HN: ' prefix — fine for a plain link, wrong for a launch")


def check_hn_comment(path):
    t = pasted(path)
    if MD_MARKS.search(t):
        fail(path, "Markdown marks (backticks, >, #, **, [..](..)) — HN shows them as typed")
    if not URL.search(t):
        warn(path, "no link in the first comment — the write-up usually belongs here")


def check_thread(path, channel):
    posts = [p.strip() for p in re.split(r"^---\s*$", pasted(path), flags=re.M) if p.strip()]
    if not posts:
        fail(path, "empty")
    limit = LIMITS[channel]
    for i, p in enumerate(posts, 1):
        n = x_length(p) if channel == "x" else len(p)
        if n > limit:
            fail(path, f"post {i} is {n} characters — {channel} allows {limit}")


def check_linkedin(path):
    parts = re.split(r"^---\s*$", pasted(path), flags=re.M)
    body = parts[0]
    if URL.search(body) and len(parts) == 1:
        warn(path, "the link is in the post body; the convention is the first comment, after a --- line")
    if MD_MARKS.search(pasted(path)):
        fail(path, "Markdown marks (backticks, >, #, **, [..](..)) — LinkedIn shows them as typed")
    for p in parts[1:]:
        if p.strip().startswith("@"):
            warn(path, "a comment starts with an @mention — in a right-to-left LinkedIn UI it flips the comment; put it last")


def check_reddit(path):
    lines = pasted(path).strip().split("\n")
    if not lines or not lines[0].strip():
        fail(path, "the first line is the title, and it is empty")
    elif len(lines[0]) > 300:
        fail(path, f"title is {len(lines[0])} characters — Reddit allows 300")


def check_crosspost(path):
    t = read(path)
    if not t.startswith("---\n"):
        fail(path, "front matter must be the very first thing — dev.to ignores it otherwise")
        return
    m = re.match(r"---\n([\s\S]*?)\n---\n", t)
    if not m:
        fail(path, "front matter is not closed with ---")
        return
    fm = m.group(1)
    if not re.search(r"^canonical_url:\s*https?://", fm, re.M):
        fail(path, "no canonical_url — search engines would see a duplicate, not a copy")
    if not re.search(r"^published:\s*false\s*$", fm, re.M):
        warn(path, "published is not false — pasting it publishes at once")
    tags = re.search(r"^tags:\s*(.*)$", fm, re.M)
    if tags and len([x for x in tags.group(1).split(",") if x.strip()]) > DEVTO_TAGS:
        fail(path, f"more than {DEVTO_TAGS} tags — dev.to rejects the post")
    if re.search(r"\]\((?!https?://|#)", t[m.end():]):
        fail(path, "a relative link — it points nowhere once the text is off its own site")


CHECKS = [
    ("hn-title.txt", check_hn_title),
    ("hn-comment.txt", check_hn_comment),
    ("x-thread.txt", lambda p: check_thread(p, "x")),
    ("bluesky-thread.txt", lambda p: check_thread(p, "bluesky")),
    ("linkedin*.md", check_linkedin),
    ("reddit*.md", check_reddit),
    ("crosspost-*.md", check_crosspost),
]


def check_links(paths):
    seen = set()
    for path in paths:
        for u in URL.findall(read(path)):
            u = u.rstrip(".,;:")
            if u in seen:
                continue
            seen.add(u)
            try:
                req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "check_drafts"})
                code = urllib.request.urlopen(req, timeout=15).status
            except urllib.error.HTTPError as e:
                code = e.code
            except Exception as e:
                code = str(e)[:40]
            if code != 200:
                fail(path, f"{u} answers {code}")


def main():
    ap = argparse.ArgumentParser(description="Check announcement drafts against each channel's rules.")
    ap.add_argument("dir", help="the drafts directory")
    ap.add_argument("--links", action="store_true", help="also fetch every URL (network)")
    a = ap.parse_args()
    if not os.path.isdir(a.dir):
        sys.exit(f"check_drafts: no such directory: {a.dir}")
    checked = []
    for pattern, fn in CHECKS:
        for path in sorted(glob.glob(os.path.join(a.dir, pattern))):
            fn(path)
            check_status(path)
            checked.append(path)
    if a.links:
        check_links(checked)
    print(f"{len(checked)} draft(s) checked in {a.dir}")
    for w in warnings:
        print(f"  ⚠ {w}")
    for f in failures:
        print(f"  ✗ {f}")
    if not checked:
        print("  nothing matched — see --help for the file names this reads")
    elif not failures:
        print("  ✓ every draft fits its channel's rules")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
