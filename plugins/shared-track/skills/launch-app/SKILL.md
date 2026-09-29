---
name: launch-app
description: >-
  Take an app from finished code to its FIRST public release, across every surface it
  needs: identity, profile, store or direct distribution, media, listing, privacy page
  and web presence. Use when the user is launching something new — "launch my app",
  "publish it for the first time", "what's left before release" ("תשיק את האפליקציה",
  "מה נשאר לפני השחרור") — or wants to know where a launch in progress stands. It keeps
  the launch's state in one file so a launch spanning days and repos can be picked up
  where it stopped, and it sequences the other skills rather than doing their work. For
  a SUBSEQUENT release of an app already live, use `prepare-app-release` instead.
---

# Launch an App — zero to live, across three repos

> **Conversational language:** talk to the user in the `conversational language` set
> in the hub `DATA.md` (`$APP_HUB/DATA.md`).

## Prerequisites

- **Tools:** none beyond Claude Code — every stage runs another skill's tooling.
- **Credentials:** none held here; the shipping skills it sequences own theirs.
- **Hub (`$APP_HUB`):** optional — the state file is `$APP_HUB/<slug>/README.md` with a
  hub and `<app-repo>/LAUNCH.md` without one, read on every run and written at every
  stage boundary. A hub also holds `<slug>/profile.md`, which decides the routes.
- **Other tracks:** `appstore-media`, `ship-apple-app`, `macos-direct-distribution`,
  `notarize-and-distribute` (apple-track); `play-store-media`, `play-store-ship`
  (android-track); `web-seo` (web-track); the `$SITE` repo's own skill for stages
  2 and 6.

## This is not `prepare-app-release`, and the difference is the order

| | starts from | ends at |
|---|---|---|
| **`launch-app`** (this) | an app that has **never shipped** — no profile, no listing, no page | first version live, listed, on the site |
| `prepare-app-release` | an app that **already ships** | version N+1 live |

They are not the same work at a different size. A first launch has to settle the
name before anything quotes it, produce a privacy URL before the store will accept
a submission, and create a listing that does not exist yet. An update inherits all
three. **If the app has a live listing, stop and use `prepare-app-release`.**

## Start by reading the state file — always

```
$APP_HUB/<slug>/README.md        # with a hub
<app-repo>/LAUNCH.md             # without one
```

**Where it sits does not matter; that it exists does.** A hub is the right home when
several apps share one, because a launch crosses repos and the hub is the tree both
reach. With one app there is no hub and no second repo, and the file belongs beside
the code.

**This is the first thing to do, on every run, including the first one.** A launch
crosses three repos and cannot finish in one session; the state file is the only
thing that carries it across the gaps. If it does not exist, create it from
`references/state-file.md` before doing any other work.

**It answers one question: what is the next unblocked step.** Not "what is done" —
a checklist tells you *what*, a blocking order tells you *what now*, and after two
days in a different repo that is the only question you actually have.

### What belongs in it, and what does not

| | |
|---|---|
| `<slug>/profile.md` | what the app **is** — the source of truth for every word written about it. Stable. |
| `<slug>/README.md` | where the launch **stands** — blockers, gaps, decisions still open. Volatile. |

**The test: if it changes when you ship, it does not belong in the profile.** Status
has been leaking into `profile.md` — "Waiting on the next App Store version record",
"TODO, the only media still missing" — and that is the leak this file closes.

### You write it, not the user

Measured 2026-09-09: **19 apps in the hub, one README.** The one that exists was
written by hand during a launch that hit real friction, and no one wrote the other
eighteen. A state file that depends on human discipline becomes eighteen empty files
and one stale one, which is worse than none — see the cross-repo docs in grove.

So: **update it as each stage closes, in the same session that closed it.** Not at
the end, not "when there is something to report". A stage that closed and was not
recorded is a stage that will be redone.

## Decide the routes before the stages — the stages come from them

**Read the `Distribution` line in `<slug>/profile.md` and settle which routes this
app ships on.** The stage list is derived from that answer; there is no fixed
sequence.

**Read that line — do not scan the file for store URLs.** `app-profile` positions
each app against its real competitors, so a profile is full of other people's store
links. One real profile carried three of them, while its own
Distribution line said *"Not on the Mac App Store"*. A keyword sweep over the
document reports two store routes that do not exist; the sentence that names the
app's own distribution is the only thing that answers this.

Four routes exist, and an app is usually on more than one:

| route | ends at | owned by |
|---|---|---|
| **App Store** | a released version | `ship-apple-app` → `app-store-deliver` |
| **Google Play** | a released version | `play-store-ship` → `play-store-deliver` |
| **direct download (macOS)** | a notarized DMG at its URL + a Sparkle appcast | `macos-direct-distribution` → `notarize-and-distribute` |
| **direct download (Windows)** | an installer at its URL | **nothing in the factory covers this — say so** |

### Common to every route

| | stage | session stands in | skill |
|---|---|---|---|
| 0a | identity — name, features, Pro, the repo README | **app repo** | `app-identity` |
| 0b | profile — the copy source of truth | anywhere | `app-profile` |
| 1 | the binary — credentials, signing, compliance, icon, build | **app repo** | apple/android track |
| 3 | media — captured from the running app, written to the hub | **app repo** | `appstore-media` · `play-store-media` |
| 6 | site presence — card, page or product site | **$SITE**, if there is one | that repo's own skill |
| 7 | marketing and tracking | anywhere | `web-seo` · reviews responders |

### Store routes add these

| | stage | session stands in | skill |
|---|---|---|---|
| 2 | the privacy URL **the store demands** — any host that resolves | **$SITE**, or anywhere | that repo's own skill Phase A |
| 4 | store copy → hub | anywhere | `store-metadata-writer` |
| 5 | ship — build, deliver, upload | **app repo** | `ship-apple-app` · `play-store-ship` |

### Direct download replaces 4 and 5 entirely

There is no listing to write and nothing to submit. Instead: set up the direct
target and Sparkle once (`macos-direct-distribution`), then package, sign, notarize,
staple and verify each release (`notarize-and-distribute`), and publish the artefact
and appcast where the download link points.

**Stage 6 stops being the tail and becomes the release itself.** On a store route
the site page follows a listing that already exists; on a direct route the page *is*
the distribution — the download link, and every constraint that has to sit beside it.

**Windows is a real gap.** The factory has no skill for it. If the app ships a
Windows installer, say plainly that this part is unmanaged, and record in the state
file what it needs. A measured case: an unsigned NSIS build, so SmartScreen warns on
first run, and no auto-updater at all because Sparkle is macOS-only.

## Order that is not negotiable — and what it depends on

- **0a before 0b before everything, on every route.** The name settles first,
  because every later field quotes it. A name changed at stage 4 invalidates
  metadata, captions and the listing at once.
- **2 before 5 — on store routes only.** App Store Connect will not accept a
  submission without a privacy URL. Phase A needs no media, so run it early and in
  parallel with the binary. **On a direct route this constraint does not exist**;
  the privacy page is still wanted, but it is part of stage 6 and gates nothing.
- **3 before 4, and before 6 at tier 2/3.** Copy quotes the screenshots; the site's
  richer tiers embed them. Tier 1 (a catalog card) does not need media. On a direct
  route, 3 gates 6 and therefore gates the release.

**Three of these force a session move**, and they alternate: app repo → site → app
repo → site. That is not a flaw to route around — it is the cross-repo problem grove documents, the
problem this whole factory is built on. Do not try to make it atomic.

## At every hand-off, do three things

1. **Write the state file** — the stage that closed, and what is now the first
   blocker.
2. **Say plainly what remains and where it has to happen** — the repo, and the skill
   to run there.
3. **Do not reach into the other repo.** The site's skills load only inside it, and
   the boundary guard refuses the write on purpose. A path written from outside
   bypasses the skill that owns it.

## Stage 8 — the exit, and it is a real stage

**When the first version is live, this skill is finished with the app and must say
so in the file.** A launch that ends without being closed leaves a document
declaring blockers that no longer block, forever — the exact failure this file was
built to prevent, rebuilt inside it.

*Measured on one app, 2026-09-09.* It had been live on the App Store since 3.9.
Its state file still opened with a numbered blocking list from 1.9, and **five of
its six entries were already cleared**: the profile it called unwritten was 23 KB,
the four locales it called empty were full, the category it called unset was
`GRAPHICS_AND_DESIGN`, and the media it called missing was 41 files. The one entry
that was accurate was the one the owner had kept appending to. **Lists rot from the
top, because work happens at the bottom and nobody renumbers.**

### On entry, check this per route — not once

"Is it live?" has a different answer for each route, and asking it only about a
store listing gets the direct-download case wrong.

| route | live means |
|---|---|
| App Store · Play | a released version on the listing |
| direct download | a **notarized artefact published at its URL**, and an appcast pointing at it |

*A measured case.* An app distributed for about a month —
notarized DMG, Sparkle appcast, NSIS installer, product page live — and has **no
store listing at all**. A check that looks only for a listing would have declared
it un-launched and started it at stage 0a.

If every route it ships on is live, **stop** and hand over to
`prepare-app-release`. If some are, close those and carry the rest.

### When the first version goes live, do all four

1. **Fold the whole blocking list into *What exists*,** keeping each entry's
   wording. Do not delete it; the record of what was hard is what stops it being
   re-litigated. Anything genuinely still open becomes *Decisions still open* or
   moves to the next version's work — it is no longer a launch blocker, because
   there is no longer a launch.
2. **Write the fact in the header:** `**Live since <date>** · <store URL>` per
   store. This is the flag the entry check above reads.
3. **Say the handover in the file, not only to the user:**
   `> Launched. Further versions are `prepare-app-release`; this file is now the
   app's standing notes, not a launch.`
4. **Keep the traps.** *Known traps for this app* survives the transition intact —
   it is the part that stays true, and the part that cost the most to learn.

**Routes launch separately.** iOS live while Play is still a draft is normal —
That measured app is in exactly that state. So is one that has been downloadable for a
month and was never submitted anywhere. Close each route as it
lands, keep the others blocking, and say which is which. The file is closed only
when the last route is live.

## Report at the end of every session

- The stage just closed, and the first blocker now.
- Every repo that got a commit, and whether each was pushed.
- The next session's repo and first command — literally, so it can be pasted.
- **Review is a wait, not a step.** Neither store exposes a status field worth
  polling; the honest signal is the store page.

## Boundaries

- **First release only.** A subsequent version of an app already live is
  `prepare-app-release`'s; the two differ in what has to be created versus updated.
- **It sequences; it does not do.** Every stage is another skill's work. When this
  skill starts writing listing copy or capturing screenshots itself, it is in the
  wrong place.
- **It does not push or publish on its own.** A store submission and a site deploy
  are the owner's decisions, and it stops and says what remains.

## Related
- `prepare-app-release` — the same territory for an app that already ships.
- `app-identity` · `app-profile` — stages 0a/0b, and everything downstream quotes them.
- A website repo's own skill — stages 2 and 6, and only if the studio has one.
- `appstore-media` · `store-metadata-writer` — stages 3 and 4.
- `ship-apple-app` · `play-store-ship` — stage 5.
- `APP-LIFECYCLE.md` (factory root) — the map, with the rules that cost something to
  relearn.
