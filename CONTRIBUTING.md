# Contributing

The unusual thing about this repo is that most of its content is **text a model reads
and obeys**. A skill cannot be unit-tested: the pipelines cover the scripts a skill
runs and the shape of the repo, and what a skill *instructs* is checked by using it, or
not at all. Everything below follows from that.

## The gate

```bash
python3 factory/ci.py
```

Everything that needs no installation: the checkers, the tests, the manifests. It runs
without grove and without a hub — a clean checkout gets an answer. It is what CI runs,
and a change that does not pass it is not ready.

After changing anything under `plugins/` or the registry:

```bash
python3 factory/deploy.py
```

**A commit is not a deployment.** A plugin is a *copy* in `~/.claude/plugins/cache`, and
between "I committed it" and "it is running" there are two steps nothing performs for
you — one of them is opening a new session. Never report something as fixed on the
strength of a commit.

**Commit before deploying.** `claude plugin update` copies the working tree and labels
it with HEAD, so deploying uncommitted work puts bytes in the cache under a commit that
does not contain them — and `update` can then never repair that copy. `deploy.py`
refuses to do it.

## Adding a skill

Decide **where it belongs** first, and decide it against the files rather than the
title: read the skill and count how much of it is tied to one particular repo. The test
is not "what does it write" but **"which directory is the session in when I need it?"**
— writing reaches everywhere through an absolute path; loading does not.

Then:

1. `plugins/<track>/skills/<name>/SKILL.md`, with `name` matching the directory.
2. A description that says **what**, **when** (with trigger phrases in both languages)
   and **what it is not for**, within 1024 characters. It is the only part of a skill
   that sits in context in every session that enables the track, so its length is a
   bill every session pays.
3. A `## Boundaries` section naming what the skill does not do and which skill does.
4. Scripts as `${CLAUDE_PLUGIN_ROOT}/skills/<name>/scripts/<file>` — a session's working
   directory is the project, never the skill's own.
5. `python3 factory/render_track_readmes.py` to regenerate the track's README.
6. If the skill's work lands in more than one place, a `places.json` declaring them.
   `close.py --op` can only report on an operation that declared itself.

`python3 factory/check_skills.py --strict` states all of this and fails on it. It also
refuses two skills that quote the same trigger phrase, because which one fires is then
not something either of them decides.

## On measuring whether a skill triggers

The one thing that matters most about a skill — does it load when it should — is the one
thing none of this measures. `claude plugin eval` is the tool for it, and it is early
access: it is not in this CLI, so no eval suite here could be run, and an unrunnable
suite is worse than none. When it becomes available, the cases worth writing first are
the ones where a skill has already failed to trigger: a request phrased in Hebrew, and a
request that two skills could both plausibly answer.

Until then the mechanical half is what exists — a description that says *when*, in both
languages, with a negative scope, and no phrase claimed twice — and the rest is settled
by using the skill and noticing when it did not come.

## The rules that came from real failures

**Count, do not copy.** Every number in these documents is recounted from disk before
it is written. A copied one was wrong repeatedly — Android as 7 when it was 8, the total
as 40, 38 and 35 in six documents on one day. Where a number can be generated, it is.

**A checker that reports noise is a checker nobody runs.** The first reference checker
flagged 258 things, most of which were not paths. A check that depends on a declaration
is skipped when there is no declaration, never guessed.

**A sweep must verify it comes back empty**, not count what it fixed. "Zero fingerprints
remain" was recorded while eleven were still in shipped text. That is why the sweep is
now a test.

**No skill names a path on any particular machine.** `$APP_HUB`, `$KEYS_ROOT`, `$SITE`
are real variables. A skill is copied to the next machine verbatim and read as
instruction, so `~/Developer/app-hub` inside one is a lie told to whoever installs it.

**Do not execute a script to check it.** These sign artefacts and upload builds. The
checkers parse, resolve imports, and run `--help` — which exits inside `parse_args()`,
before any of the script's own work.

## What a skill has to contain

Beyond the frontmatter, `check_skills.py --strict` requires two sections and fails
without them:

- **`## Prerequisites`** — four lines in this order and this shape, so a reader can
  scan them across skills: `**Tools:**` with install commands, `**Credentials:**` and
  how they are found, **`**Hub (`$APP_HUB`):**`** saying `not used` / `optional` /
  `required`, and `**Other tracks:**` naming skills from other plugins it leans on.
  Derive each from the skill's own text and its scripts; a tool the skill never runs
  does not belong there.
- **`## Boundaries`** — what the skill does not do, and which skill does it instead.

## Documentation

English is canonical for anything that changes with the code. Hebrew is kept for
`README`, `HOW-IT-WORKS` and `QUICKSTART`, and a translation says which commit it
matches. `factory/check_bilingual.py` fails on a broken pair and *reports* a number
stated in one copy and not the other — only a person can tell a real drift from a
paragraph one side words differently.

## Releasing

**A version is the only thing that reaches a user.** `claude plugin update` compares
versions, not content: a change shipped without a bump is a change nobody receives, and
between releases the cache stays on the old bytes however many times it is "updated".
Measured on 2026-09-11 — six tracks answering "already at the latest version" over
copies a byte comparison called stale.

The version sits in eight files (seven `plugin.json` and `marketplace.json`) and they
have to agree; `ci.py` fails when they do not.

```bash
python3 factory/bump_version.py --check    # what it is, and whether the files agree
python3 factory/bump_version.py patch      # or minor / major / an exact 0.3.0
```

It writes the number and prints the rest, which it deliberately does not do: rename
`## Unreleased` in `CHANGELOG.md` to the new version and open a fresh one, run
`factory/ci.py`, commit, **tag** `v<version>` (the tag is how a release is found later),
push both, then `factory/deploy.py` for this machine's own copies.

**One version for all seven tracks.** They are not independent — a delivery script runs
`shared-track`'s copy measurer, `price-sync` reads `apple-track`'s credential resolver —
so per-track versions would need a compatibility matrix, and an unmaintained
compatibility matrix is worse than no version at all.

## Commits

One logical change, one commit, in the repo it belongs to. The message says what was
wrong and why it mattered, not what the diff already shows. **Push only when asked** —
a push publishes a whole branch, not your last commit.

## What is not wanted

- A number typed into a document that a script could generate.
- A second copy of a table that already exists somewhere.
- A fallback nobody is told about. It becomes the real mechanism.
- A skill that overlaps another without saying which one wins.
