#!/usr/bin/env python3
"""Generate the factory dashboard as a single static HTML file.

NEVER hand-edit the output: it is overwritten. Edit this generator instead.

The data splits by what it costs to collect, and the split is the whole design:

  local   filesystem + registry + `git` — instant, free, always collected
  remote  the stores' APIs (live versions per track) — costs calls, needs
          credentials, and can fail; collected only with --remote

so the page is useful offline and honest about what it could not reach. Every
figure carries the moment it was taken, because a dashboard whose age you cannot
see is worse than no dashboard.

  build_dashboard.py                 # local only
  build_dashboard.py --remote        # also ask the stores
  build_dashboard.py -o path.html
"""
import argparse, datetime, html, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGINS = os.path.join(ROOT, "plugins")
# The guards' own helpers, so "is this project protected?" is decided in ONE place. The
# dashboard used to answer it with its own os.path.isdir and would have shown two repos
# as protected on the strength of an empty leftover directory — the same wrong answer
# the guard was giving, in a second copy of the rule.
sys.path.insert(0, os.path.join(ROOT, "factory"))
from grove import scripts as _grove_scripts, MISSING as _GROVE_MISSING   # noqa: E402
_s = _grove_scripts()
if not _s:
    # The dashboard is a view over grove's registry — which repos are protected, what
    # each session pays — and has no meaning on a machine with one repo and no
    # registry. Saying that is better than the generic message, which read as "install
    # grove" to a reader the QUICKSTART had just told did not need it.
    sys.exit("\u2717 the dashboard reads grove's registry (which repos exist, what each "
             "enables), so it needs grove.\n  It is the maintainer's view of a "
             "multi-repo tree; nothing a single repo needs is in it.\n  " + _GROVE_MISSING)
sys.path.insert(0, _s)
from grove_repo import (projects as reg_projects, apps as reg_apps, has_local_skills,  # noqa: E402
                        resolve_root, registry_path)
# The registry is grove's, and grove_repo is the one thing that knows where it sits —
# $GROVE_REGISTRY, else the checkout it finds. This used to be a hardcoded
# `factory/registry.json`, which resolves only on a machine where someone had made that
# path a symlink by hand: it is gitignored and ships with no clone, so the dashboard was
# the one script here that could not run on a fresh install.
REGISTRY = registry_path()
# History is a SOURCE, not a view: it cannot be regenerated from the tree, so unlike
# dashboard.html it is committed. Appended only when a figure actually moves.
COST_HISTORY = os.path.join(ROOT, "factory", "dashboard", "cost-history.json")
CHARS_PER_TOKEN = 3.5        # rough, and labelled as rough wherever it is shown


def sh(args, cwd=None):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def expand(p):
    """A registry root → where it is on this machine. One rule, shared with the guards."""
    return resolve_root(p) if p else p


# ---------- collectors ------------------------------------------------------

def skill_dirs():
    """Every skill in the factory, wherever the plugin layout puts it."""
    for plug in sorted(os.listdir(PLUGINS)) if os.path.isdir(PLUGINS) else []:
        sk = os.path.join(PLUGINS, plug, "skills")
        if not os.path.isdir(sk):
            continue
        for name in sorted(os.listdir(sk)):
            yield name, os.path.join(sk, name), plug


def collect_skills():
    rows = []
    for name, d, plug in skill_dirs():
        skill = os.path.join(d, "SKILL.md")
        if not os.path.isfile(skill):
            continue
        text = open(skill, encoding="utf-8").read()
        m = re.search(r"^description:\s*(?:>-)?\s*\n?((?:\s+.*\n)+)", text, re.M)
        desc = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        rows.append({
            "name": name,
            "track": plug.replace("-track", ""),
            "lines": text.count("\n") + 1,
            "scripts": len([f for f in os.listdir(os.path.join(d, "scripts"))
                            if not f.startswith((".", "__"))])
                       if os.path.isdir(os.path.join(d, "scripts")) else 0,
            "refs": len(os.listdir(os.path.join(d, "references")))
                    if os.path.isdir(os.path.join(d, "references")) else 0,
            "desc": desc[:160],
        })
    return rows


def collect_cost():
    """What a track costs a session that loads it, per track.

    A skill's DESCRIPTION sits in context always; its body is read only when the skill
    fires. So this counts descriptions — see docs/skills/2-global-cost.md in grove, which
    prices the two and measures the ratio.

    Counted from the repo, not from the installed copies: the question a factory
    dashboard answers is what this tree costs, and the copies may lag it.

    `claude plugin details` is the authority on the token figure and is not called
    here — it needs the plugin installed, and this collector is in the local tier that
    must stay instant, offline and free. Characters are exact; tokens are an estimate.
    """
    per = {}
    for name, d, plug in skill_dirs():
        f = os.path.join(d, "SKILL.md")
        if not os.path.isfile(f):
            continue
        text = open(f, encoding="utf-8", errors="replace").read()
        fm = re.match(r"---\s*\n(.*?)\n---\s*\n", text, re.S)
        desc = ""
        if fm:
            dm = re.search(r"^description:\s*(.*?)(?=\n[A-Za-z_-]+:|\Z)",
                           fm.group(1), re.S | re.M)
            if dm:
                desc = dm.group(1).strip()
        t = plug.replace("-track", "")
        row = per.setdefault(t, {"track": t, "skills": 0, "chars": 0})
        row["skills"] += 1
        row["chars"] += len(desc)
    rows = sorted(per.values(), key=lambda r: -r["chars"])
    total = sum(r["chars"] for r in rows) or 1
    for r in rows:
        r["tokens"] = round(r["chars"] / CHARS_PER_TOKEN)
        r["share"] = 100.0 * r["chars"] / total
    return rows


def cost_history(rows):
    """(previous entry, entries) after recording today's figure if it moved.

    The problem this answers is not the size of the number — docs/skills/3 says
    7,994 does not hurt. It is that nothing ever compares two of them, so growth is
    invisible. One stored row per change is the cheapest thing that creates a
    comparison.
    """
    total = sum(r["chars"] for r in rows)
    skills = sum(r["skills"] for r in rows)
    try:
        hist = json.load(open(COST_HISTORY))
        if not isinstance(hist, list):
            hist = []
    except Exception:
        hist = []                                   # unreadable history: start over, never crash
    prev = hist[-1] if hist else None
    today = datetime.date.today().isoformat()
    if not prev or prev.get("chars") != total or prev.get("skills") != skills:
        entry = {"date": today, "skills": skills, "chars": total,
                 "tokens": round(total / CHARS_PER_TOKEN)}
        # Same day, changed again: replace rather than accumulate rows nobody reads.
        if prev and prev.get("date") == today:
            prev = hist[-2] if len(hist) > 1 else None
            hist[-1] = entry
        else:
            hist.append(entry)
        try:
            with open(COST_HISTORY, "w", encoding="utf-8") as fh:
                json.dump(hist, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
        except Exception:
            pass                                    # a dashboard must not fail on a write
    else:
        prev = hist[-2] if len(hist) > 1 else None
    return prev, hist


def track_of(name, text):
    if name.startswith(("play-", "android-")):
        return "android"
    if name.startswith("capacitor-"):
        return "capacitor"
    if name.startswith(("app-store", "apple-", "appstore", "ship-apple", "macos-", "notarize", "code-signing")):
        return "apple"
    if name in ("app-icon-generator", "aso-keywords", "localization-i18n"):
        return "apple"
    if name in ("app-identity", "copy-edit", "prepare-app-release"):
        return "shared"
    return "other"


def git_state(root):
    if not root or not os.path.isdir(os.path.join(root, ".git")):
        return None
    branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], root) or "?"
    dirty = sh(["git", "status", "--porcelain"], root)
    ahead = sh(["git", "rev-list", "--count", "@{u}..HEAD"], root)
    behind = sh(["git", "rev-list", "--count", "HEAD..@{u}"], root)
    last = sh(["git", "log", "-1", "--format=%h %s"], root)
    return {"branch": branch,
            "dirty": len([l for l in (dirty or "").splitlines() if l.strip()]),
            "ahead": ahead if ahead is not None else "—",
            "behind": behind if behind is not None else "—",
            "last": (last or "")[:78],
            "remote": sh(["git", "remote", "get-url", "origin"], root) is not None}


def collect_projects(reg):
    out = []
    for name, p in reg_projects(reg):
        root = expand(p.get("root"))
        has_local = has_local_skills(root) if root else False
        # Ownership stopped being a property of the repo on 2026-09-10: a place declares
        # the paths it owns in its own .claude/owns.json, and undeclared is open. So what
        # is worth showing is whether it declared, not a flag in the registry.
        claims = 0
        if root:
            try:
                with open(os.path.join(root, ".claude", "owns.json"), encoding="utf-8") as f:
                    claims = len(json.load(f).get("claims") or [])
            except Exception:
                claims = 0
        out.append({"name": name, "root": p.get("root"), "role": p.get("role", ""),
                    "claims": claims, "local_skills": has_local, "git": git_state(root)})
    return out


def collect_apps(reg, remote=False):
    out = []
    for name, a in reg_apps(reg):
        repo = expand(a.get("repo"))
        row = {"name": name, "repo": a.get("repo"), "hub": a.get("hub_slug"),
               "git": git_state(repo) if repo else None,
               "local_version": local_version(repo) if repo else None,
               "platforms": a.get("platforms") or {}, "store": {}}
        if remote:
            pkg = (row["platforms"].get("android") or {}).get("package")
            if pkg:
                row["store"]["play"] = play_tracks(pkg)
        out.append(row)
    return out


def local_version(repo):
    g = os.path.join(repo, "Capacitor", "android", "app", "build.gradle")
    if os.path.isfile(g):
        t = open(g, encoding="utf-8").read()
        c = re.search(r"versionCode\s+(\d+)", t)
        n = re.search(r'versionName\s+"([^"]+)"', t)
        if c and n:
            return f'{n.group(1)} (vc{c.group(1)})'
    return None


def play_tracks(pkg):
    """Live track state. Reuses play-store-ship's auth so there is one implementation."""
    try:
        import importlib.util
        p = os.path.join(PLUGINS, "android-track", "skills", "play-store-ship", "scripts", "publish_aab.py")
        spec = importlib.util.spec_from_file_location("ship", p)
        ship = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ship)
        # default_key() returns None when the credentials folder holds none or several
        # service accounts. `ship.DEFAULT_KEY` was a name that module never defined, so
        # --remote answered with an AttributeError string in the store column for every
        # app — a dashboard reporting its own bug as the stores' state.
        key = ship.default_key()
        if not key:
            return {"error": f"no single service account in {ship.DEFAULT_KEY_DIR}"}
        tok = ship.token(key)
        eid = ship.call(tok, f"{ship.API}/{pkg}/edits", "POST", b"")["id"]
        tracks = ship.call(tok, f"{ship.API}/{pkg}/edits/{eid}/tracks").get("tracks", [])
        ship.call(tok, f"{ship.API}/{pkg}/edits/{eid}", "DELETE")
        return {t["track"]: [f'{r.get("name")} vc{",".join(r.get("versionCodes",[]))} {r.get("status")}'
                             for r in t.get("releases", [])] for t in tracks}
    except SystemExit as e:
        return {"error": str(e)[:120]}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"[:120]}


# ---------- rendering -------------------------------------------------------

CSS = """
:root{--bg:#fcfbf6;--ink:#3c3830;--soft:#8c8472;--line:#e6e0d2;--gold:#a8862f;
--ok:#3f7d4f;--warn:#b4762a;--bad:#a33b32;--card:#fffdf8}
@media(prefers-color-scheme:dark){:root{--bg:#1a1815;--ink:#e8e2d5;--soft:#9c9483;
--line:#332f28;--card:#211e1a}}
*{box-sizing:border-box}body{margin:0;padding:2rem 1.25rem 4rem;background:var(--bg);
color:var(--ink);font:15px/1.55 ui-sans-serif,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 .2rem}h2{font-size:1.05rem;margin:2.4rem 0 .6rem;
color:var(--gold);letter-spacing:.02em}
.stamp{color:var(--soft);font-size:.82rem;margin-bottom:.4rem}
.note{color:var(--soft);font-size:.85rem;margin:.3rem 0 .9rem}
table{width:100%;border-collapse:collapse;background:var(--card);
border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:start;padding:.5rem .7rem;border-bottom:1px solid var(--line);
font-size:.87rem;vertical-align:top}
th{background:rgba(0,0,0,.03);font-weight:600;color:var(--soft);font-size:.78rem;
text-transform:uppercase;letter-spacing:.04em}
tr:last-child td{border-bottom:0}
code{font:.82rem ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--soft)}
.pill{display:inline-block;padding:.08rem .45rem;border-radius:99px;font-size:.74rem;
border:1px solid var(--line)}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}
.desc{color:var(--soft);font-size:.8rem}
.scroll{overflow-x:auto}
.bar{height:.42rem;border-radius:99px;background:var(--gold);opacity:.65;min-width:2px;margin-inline-start:0}
.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.big{font-size:1.6rem;font-weight:600;font-variant-numeric:tabular-nums}
.delta{font-size:.85rem}
"""


def esc(x):
    return html.escape(str(x)) if x is not None else ""


def render(skills, cost, prev, projects, apps, remote, out):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    tracks = {}
    for s in skills:
        tracks.setdefault(s["track"], []).append(s)

    p = [f"<!doctype html><html dir=rtl lang=he><meta charset=utf-8>"
         f"<title>App factory — dashboard</title>",
         f"<style>{CSS}</style><div class=wrap>",
         "<h1>App factory — dashboard</h1>",
         f"<div class=stamp>generated {esc(now)} · "
         f"{'including live store data' if remote else 'local data only — run with --remote for store data'}</div>",
         "<div class=note>This file is generated. Do not edit it — edit "
         "<code>factory/dashboard/build_dashboard.py</code>.</div>"]

    # Cost goes above the skill inventory on purpose: the inventory says what exists,
    # this says what it charges for existing, and the second is the one nobody asks.
    # NOT "every session": since the split these tracks are opt-in per repo — only grove
    # is on everywhere. This is the bill a repo pays for the tracks the registry gave it.
    tot_c = sum(r["chars"] for r in cost)
    tot_t = round(tot_c / CHARS_PER_TOKEN)
    tot_s = sum(r["skills"] for r in cost)
    p.append("<h2>Fixed cost — what a repo pays for the tracks it loads</h2>")
    p.append(f"<div class=big><span dir=ltr>≈ {tot_t:,}</span> tokens</div>")
    if prev:
        d_t = tot_t - prev.get("tokens", 0)
        d_s = tot_s - prev.get("skills", 0)
        pct = (100.0 * d_t / prev["tokens"]) if prev.get("tokens") else 0.0
        cls = "warn" if d_t > 0 else ("ok" if d_t < 0 else "desc")
        verb = "up" if d_t > 0 else ("down" if d_t < 0 else "unchanged")
        p.append(f"<div class='delta {cls}'>{verb} by <span dir=ltr>{abs(d_t):,}</span> tokens · "
                 f"<span dir=ltr>{abs(pct):.0f}%</span> · "
                 f"<span dir=ltr>{abs(d_s)}</span> skills — since "
                 f"<span dir=ltr>{esc(prev['date'])}</span></div>")
    else:
        p.append("<div class='delta desc'>No earlier measurement to compare with — "
                 "this is the first one recorded.</div>")
    p.append("<div class=note>Every skill's description sits in context always; the body is read only "
             "when it runs — hence this count. The characters are exact, the tokens an estimate "
             f"(chars/{CHARS_PER_TOKEN}); <code>claude plugin details</code> is the authority "
             "for the exact number. Counted from the repo, not from the installed copies, which may lag. "
             "A track loads only where the registry enables it; the total below is a repo "
             "that carries all of them. "
             "Background: <code>docs/skills/2-global-cost.md</code>, in grove.</div>")
    p.append("<div class=scroll><table><tr><th>track</th><th>skills</th>"
             "<th>description chars</th><th>≈ tokens</th><th>share</th><th></th></tr>")
    for r in cost:
        p.append(f"<tr><td><span class=pill>{esc(r['track'])}</span></td>"
                 f"<td class=num dir=ltr>{r['skills']}</td>"
                 f"<td class=num dir=ltr>{r['chars']:,}</td>"
                 f"<td class=num dir=ltr>{r['tokens']:,}</td>"
                 f"<td class=num dir=ltr>{r['share']:.0f}%</td>"
                 f"<td style='width:34%'><div class=bar style='width:{r['share']:.0f}%'></div></td></tr>")
    p.append(f"<tr><td><b>total</b></td><td class=num dir=ltr><b>{tot_s}</b></td>"
             f"<td class=num dir=ltr><b>{tot_c:,}</b></td>"
             f"<td class=num dir=ltr><b>{tot_t:,}</b></td>"
             f"<td></td><td></td></tr>")
    p.append("</table></div>")

    p.append(f"<h2>Skills — {len(skills)}</h2>")
    p.append("<div class=scroll><table><tr><th>track</th><th>skill</th><th>lines</th>"
             "<th>scripts</th><th>sources</th><th>description</th></tr>")
    # Derived, not listed. A hardcoded tuple here silently dropped every design-track
    # skill from this table while the heading above kept counting them — the table said
    # 32 and the heading said 36 on 2026-09-09, and adding web-track widened the gap.
    # Known tracks keep their reading order; anything new appears rather than vanishing.
    order = [t for t in ("shared", "apple", "android", "capacitor", "web", "design") if t in tracks]
    for t in order + sorted(set(tracks) - set(order)):
        for s in tracks.get(t, []):
            p.append(f"<tr><td><span class=pill>{esc(t)}</span></td>"
                     f"<td><code>{esc(s['name'])}</code></td><td>{s['lines']}</td>"
                     f"<td>{s['scripts'] or ''}</td><td>{s['refs'] or ''}</td>"
                     f"<td class=desc>{esc(s['desc'])}</td></tr>")
    p.append("</table></div>")

    p.append("<h2>Projects</h2>")
    p.append("<div class=scroll><table><tr><th>project</th><th>role</th><th>claims</th>"
             "<th>git</th><th>last commit</th></tr>")
    for x in projects:
        g = x["git"]
        prot = (f"<span class=warn>{x['claims']} claims</span>" if x["claims"]
                else "<span class=ok>no claims</span>")
        p.append(f"<tr><td><code>{esc(x['root'])}</code></td><td class=desc>{esc(x['role'])}</td>"
                 f"<td>{prot}</td><td>{git_cell(g)}</td>"
                 f"<td class=desc>{esc(g['last']) if g else ''}</td></tr>")
    p.append("</table></div>")

    p.append("<h2>Apps</h2>")
    p.append("<div class=scroll><table><tr><th>app</th><th>version in repo</th>"
             "<th>git</th><th>stores</th></tr>")
    for a in apps:
        stores = []
        for plat, meta in (a["platforms"] or {}).items():
            ident = meta.get("package") or meta.get("bundle_id") or ""
            stores.append(f"<div class=desc>{esc(plat)}: <code>{esc(ident)}</code></div>")
        play = (a["store"] or {}).get("play")
        if play and "error" in play:
            stores.append(f"<div class=bad>Play: {esc(play['error'])}</div>")
        elif play:
            for tname, rels in play.items():
                stores.append(f"<div class=desc><b>{esc(tname)}</b>: {esc('; '.join(rels))}</div>")
        p.append(f"<tr><td><code>{esc(a['repo'] or a['name'])}</code></td>"
                 f"<td>{esc(a['local_version'] or '—')}</td>"
                 f"<td>{git_cell(a['git'])}</td><td>{''.join(stores)}</td></tr>")
    p.append("</table></div></div>")

    open(out, "w", encoding="utf-8").write("\n".join(p))


def git_cell(g):
    if not g:
        return "<span class=desc>—</span>"
    bits = [f"<code>{esc(g['branch'])}</code>"]
    if not g["remote"]:
        bits.append("<span class=warn>no remote</span>")
    if g["ahead"] not in ("0", "—"):
        bits.append(f"<span class=warn>{esc(g['ahead'])} unpushed</span>")
    if g["behind"] not in ("0", "—"):
        bits.append(f"<span class=warn>{esc(g['behind'])} behind</span>")
    if g["dirty"]:
        bits.append(f"<span class=warn>{g['dirty']} changes</span>")
    if len(bits) == 1:
        bits.append("<span class=ok>clean</span>")
    return " ".join(bits)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--remote", action="store_true", help="also query the stores")
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "factory", "dashboard", "dashboard.html"))
    a = ap.parse_args()
    if not REGISTRY:
        sys.exit("✗ " + _GROVE_MISSING)
    try:
        reg = json.load(open(REGISTRY, encoding="utf-8"))
    except Exception as e:
        sys.exit(f"cannot read {REGISTRY}: {e}")
    skills = collect_skills()
    cost = collect_cost()
    prev, _ = cost_history(cost)
    render(skills, cost, prev, collect_projects(reg), collect_apps(reg, a.remote),
           a.remote, a.out)
    tot = sum(r["chars"] for r in cost)
    print(f"{a.out}\n{len(skills)} skills · ~{round(tot / CHARS_PER_TOKEN):,} tokens of descriptions · "
          f"{'with' if a.remote else 'without'} store data")


if __name__ == "__main__":
    main()
