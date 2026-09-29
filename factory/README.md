# factory — the app skills' control plane

Not a skill. The parts of this repo that are not themselves skills: deployment of
the tracks, the checkers that run inside it, and the initialisers for what the shipping
skills read. The registry and the guards moved to grove; `grove.py` is how this repo
finds them.

## Every script here

Two audiences, and the split is whether grove is needed. **A person who installed the
skills** runs only the first group; everything below it is the maintainer's.

| | | needs grove |
|---|---|---|
| `enable.py` | turn tracks on for one repo (a shim — the tool ships in `plugins/factory-setup/scripts/`) | no |
| `init_keys.py` | create the credentials folder, or point at an existing one | no, with `$KEYS_ROOT` |
| `init_hub.py` | create a hub, if you want one | no, with `$APP_HUB` |
| `check_urls.py` | do the store-facing URLs resolve | no, with `$APP_HUB` |
| | | |
| `ci.py` | everything checkable without installing anything; what a push is gated on | no |
| `check_skills.py` | does every skill still have a skill's shape (`--strict` in CI) | no |
| `check_references.py` | does every path written as a path exist | no |
| `check_scripts.py` | do the scripts parse, resolve their imports, and print a usage | no |
| `check_bilingual.py` | do the two language copies of a document still agree | no |
| `check_commit_message.py` | does a commit message name a machine, a site or a product (`--install` puts it on `commit-msg`) | no |
| `render_track_readmes.py` | generate each track's README from its skills (`--check`) | no |
| `bump_version.py` | move the version in all eight places, and print the release steps | no |
| `tests/` | portability, and `init_hub` against a throwaway tree | one skips without it |
| | | |
| `deploy.py` | put this repo onto this machine: settings, cache, the commit-msg hook, verify | **yes** |
| `dashboard/build_dashboard.py` | the maintainer's view of the whole tree | **yes** |
| `grove.py` | find the grove checkout, or say it is not here | — |

## The invariant

> **A project's files may be written from outside only if the skills that own them
> are global.**

A project carrying its own `.claude/skills` has *local* owners — skills that load
only when the session's working directory is that project. Writing there from an
outside session always appears to work: the file lands, git commits, nothing
errors. It just bypasses the skill whose job that file was. The failure is silent,
which is why it needs a guard rather than a convention.

### It also decides where the skill lives

These look like two separate questions — *where do I put the skill* and *who may
write the files it owns*. They are not. The second follows from the first, and both
follow from one question that comes before them: **when does this skill need to
load?**

| when it must run | so it lives | so its files | example |
|---|---|---|---|
| during work on an app — i.e. while the session sits in the app's repo | **global, here** | may be written from any session | `store-metadata-writer` writes hub metadata while you prepare a release in `<app>` |
| only while the session sits inside its own project | **in that project** | may be written only from a session there | `add-app-to-site` builds pages inside the site's `src/` and `i18n/` |

So the test for any new skill is not *"what does it write?"* but **"which directory
is the session in when I need it?"** — and that is the distinction that is easy to
miss: **writing reaches everywhere** through an absolute path, **loading does not**.
The file will never stop you; the missing skill will, silently.

## The registry — `$GROVE/tools/registry.json`

It is grove's file, and this repo reads it rather than keeping one: which repos exist in
the tree, which tracks each loads, and — the part that matters here — the apps, with repo
path, hub slug and the bundle id / package name per store. That is what makes
`change_directory` and task-spawning reliable, and what the dashboard reads.

`deploy.py` finds it through `factory/grove.py`, which tries `$GROVE`, then a
`cross-repo-guards` checkout beside this one, then the installed plugin copy.

## The guards are grove's

Seven of them, shipped in the `grove` plugin and enabled at user scope, so they run in
every repo whether or not it is registered. Two block — a write to a path another place
declared, and `commit -a` / `add .` / `push` into a repo the session is not standing in —
and five report. Their pipelines, their fail-open rule and the reasoning behind each are
in grove, next to the code.

**What concerns this repo** is the far side of the same boundary: a skill here that
writes into another repo must name exact paths, because a sweep is refused by design.

## Ownership is per path, not per repo

A repo is not owned by its skills wholesale — specific trees are. `open_paths` in
the registry lists the subtrees inside a protected project that **no local skill
authors**, and those stay writable from outside:

```json
"<site>": { "protected": "auto", "open_paths": ["public/data/", "public/downloads/"] }
```

Without this the guard is too blunt: it would refuse a machine-fed data file in the
website repo that no site skill has ever touched, and the only way past would be to
hand over the session for a one-line write. Keep the list short and specific — every
entry is a hole in the boundary, and the default of "no exceptions" is the safe one.

Note what this does **not** need an exception for: after the hub's skills move to
the factory, `app-hub` has no `.claude/skills` at all, so `"auto"` stops protecting
it and every path in it is writable from an app session. The hub was never meant to
be permanently fenced — the fence was a symptom of its skills being in the wrong
place.

## dashboard/build_dashboard.py

One static HTML page, generated. **Never hand-edit `dashboard.html`** — it is
overwritten on every run, and it is gitignored, because a page is a view and the
repos already hold the history.

The data splits by what it costs to collect, and that split is the design:

| tier | source | cost | collected |
|---|---|---|---|
| local | the skills on disk, `registry.json`, `git` | instant, offline | always |
| remote | the stores' APIs — live version per track | API calls + credentials, can fail | only with `--remote` |

So the page is useful with no network and honest about what it could not reach.
Every figure carries the moment it was taken; a dashboard whose age you cannot see
is worse than none.

```bash
python3 $APP_FACTORY/factory/dashboard/build_dashboard.py            # local
python3 $APP_FACTORY/factory/dashboard/build_dashboard.py --remote   # + stores
```

**When to regenerate.** The local tier is cheap enough to run whenever; the honest
moments are *at the end of a factory session* (a skill changed) and *when you open
the lobby* to ask what needs attention. The remote tier costs calls per app — run
it around a release, or on a schedule, not on every glance.

The one automation worth adding is a `SessionStart` hook **scoped to the factory
project only** (`.claude/settings.json` there, not the global file), regenerating
the local tier when you open the lobby. Global would be wrong: it would fire in
every app session, where the page is not being looked at.
