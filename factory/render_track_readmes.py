#!/usr/bin/env python3
"""Write each track's README from the skills it actually contains.

    python3 factory/render_track_readmes.py            # write them
    python3 factory/render_track_readmes.py --check    # report drift, change nothing

**Generated, because every count in this repo has been wrong at least once.** Android
was written as 7 when it was 8 and as 8 when it was 9; the total was 40, 38 and 35 in
six different documents on the same day; one document listed a track that had been
deleted and another omitted one that existed. The repo's own rule is "count, do not
copy" — and a person following that rule still has to remember to re-count. A generated
file does not.

What each README says is what can be derived and nothing else: which skills the track
holds, the first sentence of each one's description, what the track costs a session that
enables it, and which external tools its scripts need. Anything that needs judgement —
why the track exists, who should enable it — is hand-written prose above the marker and
is never touched.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BEGIN = "<!-- generated:track -->"
END = "<!-- /generated:track -->"

# Binaries and packages a script calls, worth naming because they are what a new
# installation is missing. Matched against the track's scripts, not guessed.
TOOLS = {
    "fastlane": r"\bfastlane\b", "xcodebuild": r"\bxcodebuild\b", "xcrun": r"\bxcrun\b",
    "gradle": r"\bgradlew?\b", "adb": r"\badb\b", "ffmpeg": r"\bffmpeg\b",
    "ImageMagick": r"\bmagick\b", "ruby": r"\bruby\b|\.rb$", "Pillow": r"\bPIL\b|\bPillow\b",
    "openssl": r"\bopenssl\b", "keytool": r"\bkeytool\b", "security (keychain)": r"\bsecurity find|\bsecurity import",
    "sips": r"\bsips\b", "swift": r"\bswift\b", "node / npm": r"\bnpm \b|\bnpx \b",
}


def skills_in(track):
    out = []
    for p in sorted(glob.glob(os.path.join(REPO, "plugins", track, "skills", "*", "SKILL.md"))):
        t = open(p, encoding="utf-8").read()
        end = t.find("\n---\n", 3)
        fm = t[4:end] + "\n"
        m = re.search(r"^description:(?: >-)?\n((?:  .+\n)+)", fm, re.M)
        desc = " ".join(m.group(1).split()) if m else ""
        # the first sentence, which is the "what", before the triggers and the scope
        first = re.split(r"(?<=[.!?])\s+(?=[A-Z])", desc)[0] if desc else ""
        d = os.path.dirname(p)
        out.append({
            "name": os.path.basename(d),
            "what": first.rstrip(),
            "chars": len(desc),
            "scripts": len([f for f in glob.glob(os.path.join(d, "scripts", "*"))
                            if not os.path.basename(f).startswith((".", "__"))]),
            "refs": len(glob.glob(os.path.join(d, "references", "**", "*"), recursive=True)),
            "declares": os.path.isfile(os.path.join(d, "places.json")),
        })
    return out


def tools_used(track):
    text = ""
    for p in glob.glob(os.path.join(REPO, "plugins", track, "**", "*"), recursive=True):
        if p.endswith((".py", ".sh", ".rb", ".swift")) and "__pycache__" not in p:
            try:
                text += open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                pass
    return [name for name, pat in TOOLS.items() if re.search(pat, text, re.M)]


def manifest(track):
    p = os.path.join(REPO, "plugins", track, ".claude-plugin", "plugin.json")
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def render(track):
    sk = skills_in(track)
    man = manifest(track)
    total = sum(s["chars"] for s in sk)
    # The reader of a track README is deciding whether to enable it, not auditing this
    # repo's history. "Every count here has been wrong at least once" is a maintainer's
    # note, and it was printed to that reader seven times — CONTRIBUTING is where it
    # belongs.
    one = len(sk) == 1
    L = [f"*Generated from the skills themselves by `factory/render_track_readmes.py` —",
         f"edit a skill, not this table.*", "",
         f"## The {'one skill' if one else str(len(sk)) + ' skills'}", "",
         "| Skill | What it is for | scripts | refs |",
         "|---|---|---|---|"]
    for s in sk:
        what = s["what"] if len(s["what"]) <= 150 else s["what"][:147].rstrip() + "…"
        L.append(f"| `{s['name']}` | {what} | {s['scripts'] or ''} | {s['refs'] or ''} |")
    L += ["",
          f"**What it costs.** {total:,} characters of description ≈ {total // 4:,} tokens, "
          f"in every session\nthat enables this track. A skill's body is read only when the "
          f"skill fires; its description\nis in context always.", ""]
    ext = tools_used(track)
    if ext:
        L += ["**What it needs on the machine**, from the scripts that call it: "
              + ", ".join(f"`{e}`" for e in ext) + ".", ""]
    dec = [s["name"] for s in sk if s["declares"]]
    if dec:
        L += ["**Operations that declare where their work lands** (`close.py --op`): "
              + ", ".join(f"`{d}`" for d in dec) + ".", ""]
    if man.get("license") and man["license"] != "MIT":
        L += [f"**Licence: {man['license']}** — this track carries work that is not ours. "
              f"See `THIRD_PARTY_NOTICES.md`.", ""]
    return "\n".join(L).rstrip() + "\n"


HEAD = """# {track}

{blurb}

{BEGIN}
{body}{END}
"""

# The one sentence per track that cannot be derived: why it exists as a separate track.
BLURB = {
 "apple-track": "Everything Apple: the App Store and the Mac App Store, plus direct macOS\ndistribution outside them. Enable it in a repo that builds an Apple app.",
 "android-track": "Google Play, and getting an Android build onto a device to look at. Enable it in a\nrepo that builds an Android app.",
 "shared-track": "The work that is the same whichever store an app ships to: what it is called, what\nit says about itself, what it costs, and the order a release happens in. Enable it\nalongside a store track — and in a data repo, if you keep one.",
 "web-track": "A website and whether anyone finds it: what a page should contain before anyone\nstyles it, an audit of the result, and the search and analytics read on what is\nlive. Enable it in a site repo.",
 "capacitor-track": "Capacitor apps specifically — a web app in a native shell, where the strings live\nin JavaScript and the bugs live in the seam between the two. Enable it alongside\nthe Apple and Android tracks, not instead of them.",
 "factory-setup": "On everywhere, and one job: say when a repo looks like an app and no\ntrack is enabled in it. That failure is silent otherwise — a repo nobody set up\nlooks exactly like one where the skills decided they were not relevant.",
 "design-track": "Visual craft for any HTML interface. Deliberately generic: a Capacitor app's UI is\nHTML and CSS as much as a marketing page is, so this is not part of web-track.",
}


def main():
    ap = argparse.ArgumentParser(description="Generate each track's README from its skills.")
    ap.add_argument("--check", action="store_true", help="report drift, change nothing")
    a = ap.parse_args()

    tracks = sorted(os.path.basename(os.path.dirname(os.path.dirname(p)))
                    for p in glob.glob(os.path.join(REPO, "plugins", "*", ".claude-plugin", "plugin.json")))
    stale, ok = [], 0
    for track in tracks:
        p = os.path.join(REPO, "plugins", track, "README.md")
        body = render(track)
        if os.path.isfile(p):
            old = open(p, encoding="utf-8").read()
            m = re.search(re.escape(BEGIN) + r"\n(.*?)" + re.escape(END), old, re.S)
            if m and m.group(1) == body:
                ok += 1
                continue
            new = (old[:m.start(1)] + body + old[m.end(1):]) if m else \
                HEAD.format(track=track, blurb=BLURB.get(track, ""), BEGIN=BEGIN, body=body, END=END)
        else:
            new = HEAD.format(track=track, blurb=BLURB.get(track, ""), BEGIN=BEGIN, body=body, END=END)
        stale.append(track)
        if not a.check:
            open(p, "w", encoding="utf-8").write(new)

    for t in stale:
        print(f"  {'✗' if a.check else '→'} plugins/{t}/README.md")
    print()
    if a.check and stale:
        print(f"{len(stale)} track READMEs are out of date with the skills on disk.\n"
              f"  python3 factory/render_track_readmes.py")
        return 1
    print(f"✓ {ok + len(stale)} track READMEs match the skills on disk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
