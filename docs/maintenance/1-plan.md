*English · [עברית](1-plan.he.md)*

# 1 — Keeping this repo true: what is checked, when, and what is only measured

**Type:** an operating plan. **Status:** in effect 2026-09-11.

---

## What is different here

Grove's plan covers the same four cadences and the same clean-room argument; this one is
about what is peculiar to a repo whose content is **38 skills that a model reads and
follows**. Three things follow from that, and none of them is true of a guard:

1. **A skill is text, and text cannot be unit-tested.** The pipelines under
   `factory/tests/` cover the *scripts* a skill runs and the *shape* of the repo. What a
   skill instructs is checked by using it, or not at all.
2. **A skill goes stale against the world, not against the code.** An App Store field
   that was renamed, a `fastlane` flag that changed, a review rule that moved — nothing
   in this repo can notice. That is the largest maintenance surface here and it is
   entirely manual.
3. **A skill can be perfect and never load.** The failure that cost the most was a
   description that did not trigger; the code was fine.

---

## Four cadences

| when | what | who triggers it | cost |
|---|---|---|---|
| **every turn** | grove's Stop guards, in whatever repo you are standing in | automatic | milliseconds |
| **every change to `plugins/`** | `python3 factory/deploy.py` — the registry into settings, the repo into the installed copies, then verification | a person | seconds |
| **every push** | `python3 factory/ci.py` — everything that needs no installation, **and no grove** | GitHub Actions | ~20s |
| **before a submission** | `python3 factory/check_urls.py --slug <app>` | a person | seconds, and it needs the network |
| **monthly** | the list in *What no machine can check* | a person | an hour |

```bash
python3 factory/ci.py             # the gate
python3 factory/ci.py --metrics   # …and the numbers as JSON
python3 factory/ci.py --record    # …appended to factory/metrics.jsonl
```

**`ci.py` runs without grove on purpose** — a runner has this repo and nothing else — and
that is also its limit. What runs there: every path written as a filename, every script
parsed with its imports resolved, every bilingual pair, and that no skill names a machine
path. What is **skipped, loudly**: the hub pipeline, and the check that every `$ANCHOR` a
skill stands on is one a deploy actually writes. Both read grove's registry.

**Closing that gap needs a credential**, and it has not been taken: a runner could clone
grove, but a private repo needs a token stored as a secret, and the two checks it would
buy are cheap to run by hand. `deploy.py` on a real machine runs all of them, which is
where they are covered today. Worth revisiting if either repo goes public — a public
checkout needs no token.

**`check_urls` is not in CI, deliberately.** It is the only thing here that reaches the
network: slow by comparison, fails when you are offline, and a check that cries wolf on
a train is a check people learn to skip. It belongs before a submission.

---

## What is measured

`--record` appends one line to `factory/metrics.jsonl`: skills per track and in total,
how many operations declare their places, documents, bilingual pairs, python files, the
date and the commit.

**Two of those are the ones to watch:**

- **`skills_per_track`.** Every number in these documents is supposed to be counted from
  disk, and it was copied instead twice — Android written as 7 when it was 8, a total of
  40 when the column summed to 38. The series makes the drift visible instead of relying
  on someone re-counting.
- **`declared_operations`.** One skill declares where its work lands (`places.json`).
  Several more should: an operation that lands in eight places and declares none is the
  failure `close.py --op` exists to catch, and it cannot catch what was never declared.
  This number going up is the only measure of that debt being paid.

---

## What no machine can check

- **Whether a skill still matches the store.** The largest surface, and entirely manual.
  A store console rename breaks a skill silently: it still reads well, and the upload
  fails three days later.
- **Whether a skill loads when it should.** Trigger accuracy is a property of the
  description, and `skill-creator` ships the measurement for it (`run_eval.py`,
  `improve_description.py`). Building a second one would be the waste; running the
  existing one on the skills that matter has not been done.
- **Whether the copy a skill writes is good.** `copy-edit` enforces a tone; nothing
  judges the result.

**Monthly:** pick one track, open its skills against the store's current documentation,
and re-run one measurement the docs state. **After any release:** if something surprised
you, the skill that should have said so is the one to edit — while the surprise is still
in your head.
