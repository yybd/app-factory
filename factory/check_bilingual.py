#!/usr/bin/env python3
"""Have the two language copies of a document drifted apart?

    python3 factory/check_bilingual.py

Every document here ships twice — `X.md` in English and `X.he.md` in Hebrew — and
**nothing keeps them together.** That is the staleness problem in its purest form: two
records of the same fact, edited in different sessions, with no moment at which anyone
compares. It has already happened twice in one day. `check_references.py` verifies the
link between them exists; it says nothing about whether they still agree.

Three kinds of finding, and they are deliberately not equal:

    FAIL    a copy has no counterpart, or the two do not point at each other.
            Mechanical, certain, and cheap to fix.
    FAIL    a `.he.md` exists and its English twin carries no language line — the
            pair is real but unreachable from one side.
    REPORT  a PROSE document with no counterpart and no language line. It may be
            deliberately English-only, so this is named, never failed on. It exists
            because the checker recognised a document only BY its language line, so a
            file without one was not merely unpaired — it was invisible, and
            `factory/README.md` sat outside the count entirely.

            **Skills are not prose and are not counted.** Everything under `plugins/`
            is read by a model, not by a person, and ships in English by policy —
            listing all 89 of them here is the noise that gets a checker skipped.
    REPORT  a number stated in one and not the other. This is where "40 skills" and
            "35 skills" lived side by side in the two READMEs.

**The numbers are reported and never failed on**, because only a person can tell a real
drift from a paragraph one side words differently. Dates are excluded outright: a
measurement dated in one copy and summarised in the other is not a disagreement, and
flagging it would be the noise that gets a checker ignored.

What it cannot do: compare meaning. Two paragraphs saying opposite things in different
languages pass here. It catches the class that is mechanical — a missing section's
numbers, a count that was updated once.
"""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SKIP = (".git", "node_modules", "__pycache__", "worktrees")
# Drafts, not documentation. They argue a case for a reader who has never seen this
# repo — a different job from telling someone how to use it — and they are Hebrew-only
# on purpose. Pairing them would be a rule about writing, not about drift.
SKIP_DIRS_REL = ("docs/articles",)

# The bilingual policy, stated rather than inferred. English is canonical for anything
# that changes with the code; Hebrew is kept for the documents a newcomer reads first.
# Everything below is English-only ON PURPOSE — so a document that is English-only and
# NOT on this list is the interesting case, and is reported as one.
#
# Why a list and not a rule: "deliberate" and "forgotten" look identical to a checker,
# and the report used to say so and leave it there. A list is someone having decided.
ENGLISH_ONLY = {
    # A policy document, written once and read by whoever is reporting something. A
    # half-translated security contact is worse than one language clearly stated.
    "SECURITY.md",
    "CHANGELOG.md",            # a release record; the audience reads English release notes
    "COMPATIBILITY.md",        # tool and version names, which are not translated anyway
    "CONTRIBUTING.md",         # for someone changing the code, and the code is English
    "THIRD_PARTY_NOTICES.md",  # licence text, which must not be paraphrased
    "TRUST.md",                # ← candidate for translation: it is read BEFORE installing
    "factory/README.md",       # the control plane, for whoever maintains it
}

SWITCH = re.compile(r"^\*(?:English|\[English\]\(([^)]+)\))\s*·\s*(?:\[עברית\]\(([^)]+)\)|עברית)\*")
# Two digits or more, not part of a word, a path, a version or a percentage.
NUM = re.compile(r"(?<![\w.\-/])\d{2,}(?![\w.\-/%])")
# A date in any of the shapes these documents use — excluded from the comparison.
DATE = re.compile(r"\d{4}[-‑/.]\d{1,2}[-‑/.]\d{1,2}|\d{1,2}[-‑/.]\d{1,2}[-‑/.]\d{4}|\b20\d\d\b")


def docs():
    for root, dirs, names in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")
                   and os.path.relpath(os.path.join(root, d), REPO) not in SKIP_DIRS_REL]
        for n in sorted(names):
            if n.endswith(".md"):
                yield os.path.join(root, n)


def switcher(path):
    """(is_switched, target) from the first two lines — the language line, if there is one."""
    try:
        with open(path, encoding="utf-8") as f:
            head = "".join(f.readline() for _ in range(2))
    except Exception:
        return False, None
    m = SWITCH.search(head)
    if not m:
        return False, None
    return True, (m.group(1) or m.group(2))


def facts(path):
    """Numbers stated in the document, with dates removed first."""
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        return set()
    return set(NUM.findall(DATE.sub(" ", text)))


def _help_only():
    """`--help` must answer, not run. These take no options, so the docstring IS the
    usage — but a script that ignores `-h` and starts a full scan instead teaches you
    that its flags are not to be trusted."""
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__.strip())
        raise SystemExit(0)


def main():
    _help_only()
    fails, notes, pairs = [], [], 0
    seen, lone = set(), []

    for p in docs():
        rel = os.path.relpath(p, REPO)
        is_he = p.endswith(".he.md")
        other = p[:-6] + ".md" if is_he else p[:-3] + ".he.md"
        switched, target = switcher(p)

        if switched and not os.path.exists(other):
            fails.append((rel, f"says it has a {'English' if is_he else 'Hebrew'} counterpart; "
                               f"{os.path.basename(other)} does not exist"))
            continue
        if not switched and os.path.exists(other):
            fails.append((rel, f"{os.path.basename(other)} exists, but this file carries no "
                               f"language line — a reader cannot get from one to the other"))
            continue
        if not switched:
            # No counterpart and no language line. Legitimate for a document that is
            # English-only on purpose, and indistinguishable from one whose translation
            # was forgotten — so it is named and counted, and never fails.
            if (not is_he and not rel.startswith("plugins" + os.sep)
                    and rel.replace(os.sep, "/") not in ENGLISH_ONLY):
                lone.append(rel)
            continue
        if target and os.path.basename(target) != os.path.basename(other):
            fails.append((rel, f"its language line points at {target}, not {os.path.basename(other)}"))
            continue

        key = tuple(sorted((p, other)))
        if key in seen:
            continue
        seen.add(key)
        pairs += 1

        en, he = (other, p) if is_he else (p, other)
        a, b = facts(en), facts(he)
        only_en, only_he = sorted(a - b, key=int), sorted(b - a, key=int)
        if only_en or only_he:
            notes.append((os.path.relpath(en, REPO), only_en, only_he))

    print(f"Checked {pairs} bilingual pairs, and {len(ENGLISH_ONLY)} documents that are "
          f"English-only by policy"
          + (f" — plus {len(lone)} that {'is' if len(lone)==1 else 'are'} not on that list.\n" if lone else ".\n"))

    for rel, why in fails:
        print(f"  ✗ {rel}\n      {why}")
    if fails:
        print()

    if lone:
        print("Prose documents in English only that the policy does not list.\n"
              "Either translate it, or add it to ENGLISH_ONLY with the reason:")
        for rel in sorted(lone):
            print(f"  · {rel}")
        print()

    if notes:
        print("Numbers stated in one copy and not the other — read, do not obey:")
        for rel, only_en, only_he in notes:
            print(f"  · {rel}")
            if only_en:
                print(f"      only in English: {', '.join(only_en)}")
            if only_he:
                print(f"      only in Hebrew:  {', '.join(only_he)}")
        print()

    if fails:
        print(f"{len(fails)} pairs are broken as pairs.")
        return 1
    print("✓ every document has its counterpart, and they point at each other.")
    if notes:
        print("  The numbers above may be fine — a section one copy states and the other")
        print("  summarises is not a disagreement. A count that moved in one is.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
