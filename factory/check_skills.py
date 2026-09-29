#!/usr/bin/env python3
"""Does every skill still have the shape a skill is supposed to have?

    python3 factory/check_skills.py

The other checkers here ask about files: do the paths exist, do the scripts parse, do
the two languages agree. None of them looks at **what a skill is** — and a skill is the
one artefact in this repo that a model reads and obeys, so its shape is its interface.

Four things are checked, and each one is a failure this repo has actually had:

    frontmatter   `name` matches the directory, and `description` is present, folded,
                  and within budget. A description is the ONLY part of a skill that
                  sits in context in every session that enables the track, so its
                  length is a bill every session pays. Ten were over budget; the
                  largest was 2,675 characters — a skill body, loaded always.

    triggering    the description says WHEN to use the skill, and says it in both
                  languages this studio works in. Eight of 38 had Hebrew triggers,
                  which is worse than none: a Hebrew request fired some skills and
                  silently missed the rest, and a skill that does not load looks
                  exactly like a skill that decided it was not relevant.

    scope         the description says what the skill does NOT do, and the body has a
                  Boundaries section. Overlap between skills is the failure mode a
                  library this size produces on its own: three skills claimed the
                  screenshot job and two claimed the upload.

    wrapping      no hyphenated word is split across lines. In a folded YAML scalar a
                  line break becomes a space, so `aso-\\n  keywords` reaches the model
                  as "aso- keywords" — a skill name that matches nothing. Fourteen
                  descriptions carried one, invisibly, because the file looks right.

**What it deliberately does NOT judge:** whether the description is any good, whether
the workflow is correct, or whether the skill triggers in practice. None of that is
mechanical — it is measured by `claude plugin eval`, and settled by using the skill.
"""
import argparse, glob, os, re, sys, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# A description sits in context always; a body is read only when the skill fires. The
# limit is a quality bar rather than a hard one — nothing truncates — but a description
# past it has stopped describing and started explaining.
MAX_DESC = 1024
HEBREW = re.compile(r"[֐-׿]")
# States WHEN, in any of the forms these skills actually use. A description without one
# is a summary of what the skill does, which is not what the model chooses on.
WHEN = re.compile(r"\buse (this |it )?(skill )?(when|whenever|for\b)|\brun it when|"
                  r"\breach for (it|this)|\buse this whenever", re.I)
# States what the skill is NOT for. A library this size needs every skill to name its own
# edge, because the model picks between two plausible skills on these sentences alone.
# Both forms count: the direct one ("it does NOT upload") and the one that hands the job
# over by name ("creating certificates is apple-credentials' job").
NOT = re.compile(r"does ?n[o']t|do not use|never |rather than|instead of|distinct from|"
                 r"is\s+\S+'s? job|belongs to|\bowns?\b|out of scope|not this skill", re.I)


def skills():
    for p in sorted(glob.glob(os.path.join(REPO, "plugins", "*", "skills", "*", "SKILL.md"))):
        yield p, os.path.basename(os.path.dirname(p)), p.split(os.sep)[-4]


def frontmatter(text):
    """(fm_text, body) or (None, None). The trailing newline matters: without it a
    regex over the last line of a folded block silently drops it, which is how twelve
    descriptions kept a broken line through three re-wraps."""
    if not text.startswith("---\n"):
        return None, None
    end = text.find("\n---\n", 3)
    if end < 0:
        return None, None
    return text[4:end] + "\n", text[end + 5:]


def description(fm):
    """(flat_text, raw_block) — flat is what the model reads, raw is what the file holds."""
    m = re.search(r"^description:(?: >-)?\n((?:  .+\n)+)", fm, re.M)
    if m:
        return " ".join(m.group(1).split()), m.group(1)
    m = re.search(r"^description:\s*(.+)$", fm, re.M)
    return (m.group(1).strip(), None) if m else (None, None)


def headings(body):
    return [h.strip() for h in re.findall(r"^#{2,3} +(.+)$", body, re.M)]


BOUNDARY = re.compile(r"boundar|scope|what (this|it) (does not|can.t|won.t)|"
                      r"safe to|ask first|will not|out of scope|the rule for", re.I)


def check_one(path, name, track):
    """[(severity, message)] — 'fail' blocks, 'note' is printed and does not."""
    out = []
    text = open(path, encoding="utf-8").read()
    fm, body = frontmatter(text)
    if fm is None:
        return [("fail", "no readable frontmatter")]

    m = re.search(r"^name:\s*(\S+)", fm, re.M)
    if not m:
        out.append(("fail", "no `name`"))
    elif m.group(1) != name:
        out.append(("fail", f"`name: {m.group(1)}` but the directory is `{name}`"))

    desc, raw = description(fm)
    if not desc:
        return out + [("fail", "no `description`")]

    if len(desc) > MAX_DESC:
        out.append(("fail", f"description is {len(desc)} chars, over the {MAX_DESC} budget"))
    if raw and re.search(r"[A-Za-z]-$", raw, re.M):
        broken = [l.strip()[-24:] for l in raw.splitlines() if re.search(r"[A-Za-z]-$", l)]
        out.append(("fail", f"a hyphenated word is split across lines — the fold turns it "
                            f"into two words: …{broken[0]}"))
    if not WHEN.search(desc):
        out.append(("fail", "the description never says WHEN to use the skill"))
    if not HEBREW.search(desc):
        out.append(("fail", "no Hebrew trigger phrase — a Hebrew request will miss this skill "
                            "while hitting its siblings"))
    if not NOT.search(desc):
        out.append(("note", "the description does not say what the skill is NOT for"))

    if not any(BOUNDARY.search(h) for h in headings(body)):
        out.append(("note", "no Boundaries section in the body"))

    # What the skill needs before it can do anything. Thirty-five of thirty-nine had
    # none, and the reader discovered that Pillow needs RAQM out of a traceback and
    # that ffmpeg was required from line 189. Four lines, in one shape, so a person
    # deciding whether to run a skill can see the cost first.
    if not any(re.match(r"prerequisite", h, re.I) for h in headings(body)):
        out.append(("fail", "no Prerequisites section — say what has to be installed, "
                            "which credentials, whether a hub is needed, and which other "
                            "track's skills it leans on"))
    else:
        # The heading may carry a parenthetical ("## Prerequisites (check first …)"),
        # so it is matched by its start rather than anchored to the end of the line.
        parts = re.split(r"^#{2,3} +[Pp]rerequisite\w*.*$", body, maxsplit=1, flags=re.M)
        block = re.split(r"^#{2,3} ", parts[1], maxsplit=1, flags=re.M)[0] if len(parts) > 1 else ""
        for want in ("Tools", "Credentials", "Hub", "Other tracks"):
            if not re.search(r"\*\*" + want, block):
                out.append(("fail", f"Prerequisites has no **{want}:** line — the four are "
                                    f"fixed so a reader can scan them across skills"))
        m = re.search(r"\*\*Hub[^*]*\*\*:?\s*(not used|optional|required)", block, re.I)
        if not m:
            out.append(("fail", "Prerequisites does not say whether the hub is "
                                "`not used` / `optional` / `required` — that word is the "
                                "one a person without a hub is looking for"))
    return out


# Documents that state how many skills or tracks there are. Every number in this repo
# has been wrong at least once — Android written as 7 when it was 8 and 8 when it was 9,
# the total as 40, 38 and 35 across six documents on one day. Where a count can be
# generated it is; these are the ones a person writes, so they are checked instead.
COUNTED_IN = ["README.md", "README.he.md", "SKILLS.md", "SKILLS.he.md",
              "plugins/README.md", "plugins/README.he.md"]
# `| `apple-track` | 16 |` in a table, and `**39 skills** …` in a sentence.
TRACK_ROW = re.compile(r"`([a-z-]+-track|factory-setup)`\s*\|\s*(\d+)")
TOTAL = re.compile(r"\*\*(\d+) (?:skills|סקילים)|"
                   r"\|\s*\*\*(?:total|סך הכול|סך הכל)\*\*\s*\|\s*\*\*(\d+)\*\*")


# A phrase a user literally types, quoted in a description. Two skills claiming the same
# one compete for the same request, and which wins is not something either of them
# decides — it is the failure mode a library this size produces on its own, and the only
# part of trigger accuracy that can be checked without running anything.
QUOTED = re.compile(r'"([^"]{4,60})"')


def competing_triggers():
    """[(phrase, [skills])] where more than one skill quotes the same trigger."""
    import collections
    claimed = collections.defaultdict(set)
    for path, name, _track in skills():
        fm, _ = frontmatter(open(path, encoding="utf-8").read())
        if not fm:
            continue
        d, _ = description(fm)
        for q in QUOTED.findall(d or ""):
            claimed[q.strip().lower()].add(name)
    return sorted((q, sorted(s)) for q, s in claimed.items() if len(s) > 1)


# The same trigger written without quotes. `apple-credentials` and
# `code-signing-provisioning` both said "asks which certificate they need or why", and
# the quoted-phrase check above saw neither, because neither quoted it. Any run of
# this many words that two descriptions share is a sentence they both claim.
SHARED_WORDS = 7
STOP = {"the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "it", "is", "this",
        "that", "when", "use", "skill", "user", "does", "not", "with", "from", "into", "by"}


TRIGGER = re.compile(r"\b(wants? to|asks?|when the user|whenever)\b")


def shared_sentences():
    """[(phrase, [two skills], is_trigger)] — one line per pair of skills that share a
    run of SHARED_WORDS words, merged into the longest shared stretch.

    A shared BOUNDARY ("does not produce store screenshots") is two skills agreeing on an
    edge, which is what the Boundaries rule asks for. A shared TRIGGER ("the user wants
    to ship a mac app outside the store") is two skills claiming one request, and that
    is the failure: `is_trigger` says which it is.
    """
    import collections, itertools
    words_of = {}
    for path, name, _track in skills():
        fm, _ = frontmatter(open(path, encoding="utf-8").read())
        if not fm:
            continue
        d, _ = description(fm)
        words_of[name] = re.findall(r"[a-z][a-z'-]+", (d or "").lower())
    runs = collections.defaultdict(set)
    for name, words in words_of.items():
        for i in range(len(words) - SHARED_WORDS + 1):
            run = tuple(words[i:i + SHARED_WORDS])
            if sum(w in STOP for w in run) > SHARED_WORDS // 2:
                continue                      # "use this skill when the user" is a form, not a claim
            if "not" in run or "n't" in " ".join(run):
                continue                      # a boundary, and boundaries are meant to agree
            runs[run].add(name)
    by_pair = collections.defaultdict(list)
    for run, names in runs.items():
        for pair in itertools.combinations(sorted(names), 2):
            by_pair[pair].append(run)
    out = []
    for pair, shared in sorted(by_pair.items()):
        # merge overlapping runs into the longest stretch, so one sentence is one line
        words = words_of[pair[0]]
        starts = sorted(i for i in range(len(words)) if tuple(words[i:i + SHARED_WORDS]) in shared)
        stretches, cur = [], [starts[0], starts[0] + SHARED_WORDS]
        for s in starts[1:]:
            if s <= cur[1]:
                cur[1] = s + SHARED_WORDS
            else:
                stretches.append(cur); cur = [s, s + SHARED_WORDS]
        stretches.append(cur)
        longest = max(stretches, key=lambda c: c[1] - c[0])
        phrase = " ".join(words[longest[0]:longest[1]])
        out.append((phrase, list(pair), bool(TRIGGER.search(phrase))))
    return out


# A script a skill tells the model to run, that is not on the disk it ships with. The
# reference checker sees paths; this sees NAMES — `snapshot.py` in web-seo was cited
# by name, described in detail, and did not exist. Every `.py` / `.rb` / `.sh` a skill
# body mentions must exist somewhere under plugins/.
SCRIPT_NAME = re.compile(r"(?<![\w/.-])([A-Za-z_][\w-]*\.(?:py|rb|sh))\b")


# Scripts a skill WRITES into the user's project, per app, and therefore does not ship:
# named here so the check can keep failing on one that is merely missing.
GENERATED = {"capture.sh", "record_video.sh"}          # appstore-media, macOS self-capture


def phantom_scripts():
    """[(skill, name)] for a script named in a SKILL.md that exists nowhere shipped."""
    on_disk = {os.path.basename(p) for p in glob.glob(
        os.path.join(REPO, "plugins", "**", "*.*"), recursive=True)} | GENERATED
    out = []
    for path, name, _track in skills():
        _, body = frontmatter(open(path, encoding="utf-8").read())
        for n in sorted(set(SCRIPT_NAME.findall(body or ""))):
            if n not in on_disk:
                out.append((name, n))
    return out


def counts_in_documents():
    """[(file, what, claimed, actual)] where a written count disagrees with disk."""
    import collections
    per = collections.Counter(
        p.split(os.sep)[-4] for p in glob.glob(
            os.path.join(REPO, "plugins", "*", "skills", "*", "SKILL.md")))
    total = sum(per.values())
    out = []
    for rel in COUNTED_IN:
        p = os.path.join(REPO, rel)
        if not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8").read()
        for track, claimed in TRACK_ROW.findall(text):
            if track in per and int(claimed) != per[track]:
                out.append((rel, track, int(claimed), per[track]))
        for groups in TOTAL.findall(text):
            claimed = next((g for g in groups if g), None)
            if claimed and int(claimed) != total:
                out.append((rel, "total", int(claimed), total))
    return out


def main():
    ap = argparse.ArgumentParser(description="Does every skill still have a skill's shape?")
    ap.add_argument("--strict", action="store_true", help="treat notes as failures too")
    a = ap.parse_args()

    fails, notes, total, per_track = [], [], 0, {}
    n = 0
    for path, name, track in skills():
        n += 1
        rel = os.path.relpath(path, REPO)
        fm, _ = frontmatter(open(path, encoding="utf-8").read())
        d, _ = description(fm) if fm else (None, None)
        total += len(d or "")
        per_track[track] = per_track.get(track, 0) + len(d or "")
        for sev, msg in check_one(path, name, track):
            (fails if sev == "fail" or a.strict else notes).append((rel, msg))

    # Collected before anything is printed: a note added after the report has been
    # written is a note nobody sees, which is how this check passed its own test.
    for phrase, names in competing_triggers():
        (fails if a.strict else notes).append(
            ("two skills", f'both quote the trigger "{phrase}": {", ".join(names)} — '
                           f'which one fires is not something either of them decides'))
    for phrase, names, is_trigger in shared_sentences():
        (fails if (a.strict and is_trigger) else notes).append(
            ("two skills", f'share the {"TRIGGER" if is_trigger else "sentence"} '
                           f'"…{phrase}…": {", ".join(names)} — '
                           + ("one request, two claimants: one of them must hand over"
                              if is_trigger else "wording copied between siblings; harmless "
                              "unless it is a claim")))
    for name, script in phantom_scripts():
        fails.append((name, f"names `{script}`, and no such file ships anywhere in plugins/"))

    print(f"Checked {n} skills.")
    widest = max(per_track, key=lambda t: per_track[t]) if per_track else "?"
    print(f"Descriptions: {total:,} characters ≈ {total // 4:,} tokens, "
          f"the bill a repo pays for every track it loads.")
    print(f"  largest track: {widest} at {per_track.get(widest, 0):,} "
          f"({100 * per_track.get(widest, 0) // max(total, 1)}%)")
    print()

    for rel, msg in notes:
        print(f"  · {rel}\n      {msg}")
    if notes:
        print()
    miscounts = counts_in_documents()
    for rel, what, claimed, actual in miscounts:
        fails.append((rel, f"says {what} is {claimed}; there are {actual} on disk"))

    if not fails:
        print(f"✓ every skill has a name that matches, a description within budget that says "
              f"when to use it\n  in both languages, and no fold that breaks a word. "
              f"Every written count matches disk.")
        return 0
    for rel, msg in fails:
        print(f"  ✗ {rel}\n      {msg}")
    print(f"\n{len(fails)} skills whose shape would cost a session something — "
          f"a description that never loads its skill,\nor one that loads it everywhere.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
