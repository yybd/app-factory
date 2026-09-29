*English · [עברית](1-shared-context-repos.he.md)*

# 1 — When a repo is not private: the hub and the site

**Type:** a decision record. **Status:** decided.
**Written:** 2026-09-09 · measurements taken that day, from disk.

---

## The question

Grove's placement rule — *where a skill lives*, in its `docs/skills/` — says **global**
if it needs to load everywhere, **local** if the skill is *"tied to one tree and cannot
run anywhere else at all"*.

That criterion was written against a site repo, and behind it sat a silent assumption:
**that a project's repo contains one project.** The assumption is false for the two
central repos here.

**`app-hub` is not a project.** It is the data layer for **every** app —
`<slug>/profile.md`, `prices.json`, `DATA.md`, `<slug>/store/`, `<slug>/media/`. **A
studio site is not a private site** — it has a page for every app.

Both are **shared-context repos**. A skill that touches them does not become "local" by
touching them, and that is exactly the distinction the old criterion could not make.

---

## The measurement that settles it

**31 of the 35 skills here refer to the hub by a real path** (`$APP_HUB`, `<hub>/`)
or read one of its core files (`DATA.md`, `profile.md`, `prices.json`).

| Track | Skills depending on the hub |
|---|---|
| apple | 15 of 16 |
| android | 8 of 8 |
| shared | 6 of 6 |
| capacitor | 2 of 2 |
| design | **0 of 3** |

**And that is the whole answer.** If "depends on the hub" were a sign of locality, 31
skills would move into `app-hub` and this repo would empty out. **Depending on the hub
is the norm, not the exception** — that is where the data every app skill needs lives.

The four exceptions sharpen it: the three design skills (entirely generic, they know
nothing about apps) and `macos-direct-distribution`.

---

## The corrected criterion

The old criterion asked **which repo the skill touches**. The right question is **how
many repos one of its actions spans**:

> **Global** — one invocation touches **more than one repo**, or no particular one.
> **Local** — the skill operates **entirely inside one tree**, and cannot be invoked
> outside it.

**And the clarification this document adds:** *one tree* is not *one app*. The hub is
one tree even though it serves them all. A skill that maintains the hub's own internal
structure — its scripts, its schema, its conventions — **is local to the hub**, even
though nothing in it is private.

The test is not *"who does it serve"* but *"how many trees does it act on"*.

**Why this follows from the need:** an action on an app spreads across several repos,
and every mechanism in the environment has one home. A cross-repo skill **has no home
repo** — whichever you pick, it is absent from the others. Global is not a convenience;
it is the only place that exists for it.

---

## The decision about the hub's three skills

All three existed **both** here and in `$APP_HUB/.claude/skills/`, and so
loaded twice in a session standing there.

**All three are global.** Measured:

| Skill | What one invocation acts on | Verdict |
|---|---|---|
| `price-sync` | `<hub>/prices.json` · `<hub>/scripts/verify_prices.py` · **`.storekit` inside app repos** · both profiles · metadata · site copy · App Store IAP · an external payment service | **global** — four repos and two external services |
| `app-profile` | reads the **app's source** (an app project path, "app repo" ×4, "source project" ×3) · writes `<hub>/<slug>/profile.md` · `<hub>/<slug>/media/apple/` · reads `DATA.md` | **global** — the app repo plus the hub |
| `store-metadata-writer` | **"app repo" ×13** · `fastlane/metadata/` · reads `<hub>/<slug>/profile.md` · writes `<hub>/<slug>/store/` | **global** — the app repo plus the hub |

`price-sync` is the cleanest case: **no single repo can contain it.** Not the hub —
because it writes `.storekit` files inside app repos. Not an app repo — because it
reconciles a price across all of them at once.

**Hence: the copies in `app-hub` are redundant, and this repo is the source of
truth.** And not merely redundant — `store-metadata-writer` there was measured to have
**diverged and broken**: it referred to `~/.claude/skills/copy-edit/scripts/measure_copy.py`,
a path deleted in the migration. Grove's version uses `${CLAUDE_PLUGIN_ROOT}` and
is correct.

---

## What the criterion says about what does stay local

**Right to stay in a site repo:** `add-app-to-site` (39 references), `translate-site`
(12), `reference-page` (8). All of them operate inside the site's tree only.

**Right to stay in `app-hub`:** a skill that maintains the hub's own structure. **There
is none today** — the three that were there are not that.

### `web-seo` — checked 2026-09-09, and the criterion says: **global**

It existed in `app-hub` and in the site repo, **byte-for-byte identical** (17,955 bytes,
same sha), and was not one of the tracked skills.

**"Seven websites" sounds like seven trees, and it is not.** The hub's own README says
so explicitly: the seven domains ship from **one repo** to seven deployments. So the
correct count is **two**:

| Tree | What the skill does there |
|---|---|
| `app-hub` | runs four scripts — an audit, a snapshot, an IndexNow push, a Google auth helper (all verified present) · reads the web README and baseline · writes `2-web/snapshots/<date>` |
| the site repo | runs `npm run seo` **in the site repo** · fixes titles, canonicals, hreflang, the sitemap |

**Two trees in one invocation → global.** And it is explained from the other side too:
it hands off to `add-app-to-site` (local to the site), to `copy-edit` (a track here) and
refers to `<slug>/profile.md` (the hub) — it sits exactly on the seam between the three,
which is why it has no home in any of them.

**The state it was in was the worst of both:** neither local nor global but
**duplicated** — and both copies loaded in a session standing in either repo. That they
were identical was luck, not a mechanism; `frontend-design` and `store-metadata-writer`
show where that goes.

**The price:** a 1,255-character description ≈ **359 tokens** — from 9,029 to 9,388,
**+4.0%**.

**Which track.** `shared-track`. Its plugin description says *"Cross-store"*, but the
content is already cross-surface and not only cross-store: `prepare-app-release`
mentions the website seven times, `store-metadata-writer` four, and `app-profile` covers
site cards, app pages and product sites. **The plugin's description understates what is
in it**, and that is a correction needed anyway.

---

## What was tried and ruled out

| | Why not |
|---|---|
| **"A skill that touches the hub belongs to the hub"** | 31 of 35 touch it. The rule would have emptied this repo |
| **"A skill that serves all the apps is global"** | close, but wrong at the edge: a skill that maintains the hub's **structure** serves them all and still acts on one tree, and belongs there |
| **Keeping a copy in each repo "for convenience"** | *"it does no harm there" is not a criterion* — this repo's own rule. And it was measured to do harm: two of the copies had diverged, and one of them was broken |
| **Duplicating deliberately and syncing** | syncing between repos is exactly what staleness — measured in grove's cross-repo docs — shows does not happen |
