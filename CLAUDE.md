*English · [עברית](CLAUDE.he.md)*

# Factory rules

Loaded **in addition to** `~/.claude/CLAUDE.md`, not instead of it. On this machine that
file points at grove's own global rules rather than at anything here; on a
machine without grove it is whatever the user wrote. Either way the global rules apply,
and what follows adds to them.

**Grove is the other half of the maintainer's setup, and it is optional for everyone
else.** The guards, the registry, the anchors and `close.py` live in the
`cross-repo-guards` repo and install as their own marketplace. This repo is the app
skills: what builds, describes and ships an app. Anything below about crossing a repo
boundary is grove's, and is named here only because it applies while you work in this
one — a person who installed the skills alone runs none of it.

## The tools in this repo

`factory/README.md` indexes every script and says which need grove. The four that come
up constantly: **`factory/ci.py`** (everything checkable without installing — run it
before saying anything is done), **`factory/deploy.py`** (this machine's copies; needs
grove), **`factory/enable.py`** (tracks for one repo; a shim for
`plugins/factory-setup/scripts/enable.py`, which is the file that ships), and
**`factory/bump_version.py`** (the version, in all eight places, plus the release steps).

## What is written by hand and what is generated

`factory/dashboard/dashboard.html` is **generated, not edited.** It is overwritten on
every run and it is gitignored. Change `build_dashboard.py` instead.

## Counts and numbers

**Count, do not copy.** Every number in these documents — how many skills, how many in
each track — is recounted from disk before it is written. A number copied from an
earlier document was wrong twice (Android recorded as 7 instead of 8, the total as 27
instead of 28), because it was duplicated without being checked.

## Deciding where a skill belongs

**Decide against the files, not against the title.** Before deciding whether a skill is
shared, separate, global or local — read it and count how much of its content is tied to
one particular repo. `add-app-to-site` sounded like a thin bridge and turned out to be
the deepest worker (455 lines, 28 references); `frontend-design` sounded like a site
skill and turned out to be entirely generic (0).

**"It does no harm there" is not a criterion.** The criterion is where the skill needs
to **load**.

## Migrations

**Verify before deleting.** In any skill migration — install and verify the destination
first, and only then delete the source. Temporary duplication is confusing; deleting
early leaves you with nothing.

## Deployment

**A commit is not a deployment.** Skills and hooks live inside a plugin, and a plugin is
a **copy** in `~/.claude/plugins/cache`. Between "I committed it" and "it is running"
there are two steps nobody takes for you, and one of them is opening a new session. On
2026-09-09 this happened twice in one hour: a guard was fixed, committed, reported as
fixed — and the machine went on running the broken code.

**After any change under `plugins/` or to grove's registry (`$GROVE/tools/registry.json`):**

```bash
python3 factory/deploy.py
```

It syncs the settings files from the registry, refreshes the installed copies,
installs the `commit-msg` hook, and verifies. `--check` answers "is everything in
place?" without changing anything. The equivalent inside a session is `/grove:deploy`.

The hook is there because `core.hooksPath` is per-clone git config and is never
committed: a fresh checkout has the commit-message check off and nothing says so.

**Commit before deploying.** `claude plugin update` copies the **working tree** and tags
it with HEAD, so deploying uncommitted work puts bytes in the cache that are in no
commit — and from that moment `update` cannot fix the copy, only a reinstall can.
`deploy.py` refuses to do it.

**And never report "fixed" on the strength of a commit.** The report comes after the
deployment, and with the sentence that it takes effect **in the next session**.

## Closing across places

**A session sees one `git status`.** What you left open anywhere else is not missing —
it is **invisible**, which is how "done" gets said over a clean status while the rest
sits open. The answer lives in grove:

```bash
python3 $GROVE/tools/close.py
```

It reports every place the session touched, stages only paths the session actually
wrote, and `--commit -m "…"` closes each in its own terms. It commits; it does not push.
**`--op <name>`** is the form that catches a place that should have been written and was
not — and the operations that declare their places are declared by skills **here**, in
`plugins/*/skills/*/places.json`.

## Staleness

**A record is written correctly, the world moves, and the record does not.** What
invalidated it sits somewhere else, so nobody looks. Measured: seven memories pointing
at paths that had vanished, and one migration that broke 39 references across two repos
— one of them inside an `import`, so the skill did not load at all.

**Most staleness cannot be detected mechanically** — *"the price is 9.99"* looks fine
even when it is wrong, and only asking the store settles it. **A path is the exception:**
either it is there or it is not.

```bash
python3 factory/check_references.py
```

It also runs inside `deploy.py`. It checks **only paths written as filenames** — not
prose, not numbers, not claims. The first version checked anything with a slash in it
and found 258 items, most of them `svh/dvh` and `next/font`. **A checker that reports
noise is a checker nobody runs.**

**The scripts the skills run are checked too** — `factory/check_scripts.py`, inside
`deploy.py`: that they parse, and that every import they name exists here. **Static
analysis only, nothing is executed** — these scripts sign artifacts and upload builds,
and a checker that runs them to see whether they work is a checker that ships something
by accident. Without it, a fault in one surfaces halfway through a release.

**And two language copies of one document drift apart** — `factory/check_bilingual.py`,
inside `deploy.py`. Nothing keeps `X.md` and `X.he.md` together; they are edited in
different sessions with no moment at which anyone compares. A missing counterpart is a
failure; a **number stated in one and not the other** is reported and never failed on,
because only a person can tell a real drift from a paragraph one side words differently.
Its first run found two READMEs saying 40 skills and 35.

## The guards

**They are grove's, and they are on while you work here.** `honor_ownership` refuses a
write to a path a place declared in its own `.claude/owns.json`; `scope_foreign_commits`
refuses `commit -a`, `add .` and `push` into a repo this session is not standing in, and
hands back that repo's `git status` when it allows a foreign write. The rest report.

What that means for this repo: **a skill that writes into another repo must name exact
paths**, and a skill that owns files should say so in that repo's `owns.json`. The full
account, the pipelines, and what the guards cannot see are in grove.
