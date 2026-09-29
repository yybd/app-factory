---
name: prepare-app-release
description: >-
  Take an app all the way to released — the cross-store orchestrator above
  ship-apple-app and play-store-ship. Use when the user says "prepare the app for
  release/distribution", "הכן את האפליקציה להפצה", "ship this app", "release a new
  version", or asks for the whole path from a finished change to a live listing, on one
  store or both. It sequences identity, compliance, store metadata, media, the build and
  the upload, keeps the two stores consistent, and hands off the website leg explicitly
  instead of doing it silently. Run it from the app's OWN repo — that is where the build
  and the git history are. It does not author copy, capture media, or upload listings
  itself; it drives the skills that own each of those and verifies their output. This is
  an app that ALREADY SHIPS; a first launch — no profile, no listing, no privacy URL yet
  — is `launch-app`, a different order of work rather than a smaller one.
---

# Prepare an App for Release — the cross-store orchestrator

> **Conversational language:** talk to the user — questions, summaries, reports — in the `conversational language` set in the hub `DATA.md` (`$APP_HUB/DATA.md`); fall back to the language the user writes in if it is unset. This sets the *conversation* language only.

## Prerequisites

- **Tools:** none beyond Claude Code — the build, upload and validators belong to the
  skills it drives; it runs from the app repo, where `xcodebuild` / `gradlew` are.
- **Credentials:** none held here; `ship-apple-app` and `play-store-ship` own theirs.
- **Hub (`$APP_HUB`):** optional — with one, media, store metadata and the changelog
  land there in steps 3, 5 and 7 and `DATA.md` sets the conversational language;
  without one they land in the app repo's own `fastlane/` tree, which each owning
  skill selects for itself.
- **Other tracks:** `app-store-review-compliance`, `appstore-media`,
  `app-icon-generator`, `app-store-metadata`, `ship-apple-app`, `app-store-deliver`
  (apple-track); `play-store-compliance`, `play-store-media`,
  `android-icon-generator`, `play-store-metadata`, `play-store-ship`,
  `play-store-deliver` (android-track); `add-app-to-site` in the `$SITE` repo.

## Where this runs, and why it matters

**Run it from the app's own repo.** The build (`gradlew`, `xcodebuild`), the
simulator, the emulator, the binary and the git history that the release commit
lands in are all there, and none of them can move. Everything else this skill
touches is reached without moving:

| Leg | Where its files live | How it is reached |
|---|---|---|
| Code, version, build, binary, tag | the app repo | **here** — this is the cwd |
| Store metadata, changelog, media | the hub | written by path; its owning skills are global |
| The app's page on the site | $SITE, if there is one | **handed off** — see the last section |

A task that looks like it spans three repos is usually one session plus one
hand-off. Do not try to make it atomic.

## The order, and why it is this order

Each step's output is the next step's input, so running them out of order means
redoing work rather than merely doing it late.

1. **Identity** — `app-identity`. The name, subtitle / short description, and the
   README feature list. Everything downstream quotes these, so a name settled late
   invalidates metadata, media captions and the listing at once. On a first
   release this is a conversation with the user; on an update, a check that the
   README still matches what shipped.
2. **Compliance** — `app-store-review-compliance` (Apple) · `play-store-compliance`
   (Play). Before the build, because these change the project: a target API level,
   a permission, a privacy string, a demo mode. Finding them after archiving means
   archiving twice.
3. **Media** — `appstore-media` / `play-store-media`, and the icons
   (`app-icon-generator` / `android-icon-generator`) if they changed. Only when the
   UI actually changed; re-shooting an unchanged screen is waste.
4. **Version** — bump it in the project, and **read the current value from the file
   rather than from notes or memory**. Apple wants a build number higher than any
   uploaded; Play wants a versionCode higher than every code ever used. A fix that
   reports the same version name as the build it fixes leaves nobody able to tell
   which one they have. **Before the copy**, because the changelog's folder is named
   after this number — step 5 cannot write `changelogs/<versionCode>/` until this step
   has said what the versionCode is. (These two used to be the other way round.)
5. **Copy and metadata** — `store-metadata-writer` writes the per-locale text into
   the hub; `app-store-metadata` / `play-store-metadata` own and validate the files;
   `copy-edit` runs over anything customer-facing. **The changelog for THIS
   versionCode / build must exist before the upload**, not after.

   > **Media before copy, when the media is changing.** Captions and store text quote
   > the screenshots, so writing the copy first means rewriting it. This skill used to
   > have these two the other way round while `launch-app`, `store-metadata-writer` and
   > the lifecycle map all said media first — one order, stated four times, and one of
   > them disagreeing. When step 3 is skipped because nothing visual changed, the two
   > are independent and the order does not matter.
6. **Build, upload, publish** — `ship-apple-app` · `play-store-ship`. These own the
   archive/AAB, the upload and the track. Let them do it; do not hand-roll the API.
7. **Deliver the listing** — `app-store-deliver` · `play-store-deliver`, whenever
   the listing itself changed. They gate on the hub being complete — both the media
   and the per-locale text — which is the safety net for steps 3 and 5.

## Both stores at once

The two stores share the decisions and share nothing else. Keep **one** name, one
feature list, one release story; let each store's skills shape the fields, because
the shapes genuinely differ — Apple has a 30-char subtitle and a hidden keywords
field, Play has an 80-char short description and no keywords field at all.

Release them together only if that is what the user wants. There is no technical
need: they review independently and on different clocks.

## The website leg — hand off, do not reach

The app's page on the site is **not** part of this session, for two separate
reasons, and it is worth saying both:

- **Timing.** The page links to a store listing that does not exist until review
  passes — hours to days later. A page written now would point at nothing.
- **Ownership.** The site's skills (`add-app-to-site`, `translate-site`, …) load
  only inside the website repo. Writing there from here would silently bypass them,
  and the boundary guard refuses it on purpose.

So finish here, tell the user plainly what remains, and give them the exact next
step: reopen in the website repo (or `change_directory` there once the listing is
live) and run `add-app-to-site`.

## Report at the end
- The version, the store(s), the track, and what is now in review.
- **That review is a wait, not a step** — Play and Apple both review, neither
  exposes a status field worth polling, and the honest signal is the store page.
- Every repo that got a commit, and whether each was pushed.
- The website leg, still open, with its precondition.

## Boundaries

- **Not a first launch.** An app that has never shipped needs `launch-app`, which
  covers the surfaces that do not exist yet — the store record, the privacy page, the
  web presence.
- **It orchestrates; it does not author.** Copy, media, compliance fixes and the
  upload each belong to the skill named at that step.
- **It hands the website leg off explicitly** rather than doing it silently: the
  site's skills load only inside the site's own repo.

## Related skills
- `launch-app` — the same territory for an app that has never shipped, and the owner
  of the per-app state file in the hub. If this app has no live listing, it is that
  skill's job, not this one's.
- `ship-apple-app` · `play-store-ship` — the per-store shipping this drives.
- `app-store-deliver` · `play-store-deliver` — the listing send-surfaces.
- `app-identity` · `store-metadata-writer` · `copy-edit` — what is said.
- `app-store-review-compliance` · `play-store-compliance` — what would block it.
- The website repo's own skill — the handed-off leg, and only if there is a website.
