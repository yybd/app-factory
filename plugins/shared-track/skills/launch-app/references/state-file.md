# The per-app state file — `$APP_HUB/<slug>/README.md`, or `<app-repo>/LAUNCH.md`

The shape below is not invented. It is a real state file from a shipped app,
generalised — written by hand during a launch that hit real friction, which is
exactly why its structure is worth keeping: it answers the question someone
actually had.

**One rule above all: `## What is blocking, in order` is the point of the file.**
Everything else is context for it. A checklist says what is done; a blocking order
says what to do now, which is the only question a session has after a gap.

---

## Template

```markdown
# <App name> — hub

**Stage:** <0a-7 and one line> · **Updated:** <YYYY-MM-DD> · by `launch-app`

- **Repo:** `$DEV_ROOT/<path>` · **Bundle / package:** `<id>`
- **Platforms:** <iOS · Android · macOS · Windows>
- **Routes:** the line the stage list is derived from. One row per route the app
  actually ships on, because they launch and close independently:
  `App Store: in review` · `Play: draft on internal` · `direct macOS: live at <url>`
  · `Windows: installer at <url>, unsigned, no updater — unmanaged by the factory`
- **Monetisation:** <free · IAP id + price, and that `prices.json` decides it>

## What exists

One line per stage that is closed. Name the artefact, not the effort:
`profile.md` ✓ · privacy page live at `<url>` ✓ · `media/apple/` 6 locales ✓

## What is blocking, in order

Numbered, and **each entry blocks the one below it**. The reader should be able to
act on entry 1 and stop reading.

1. **<the thing>** — why it blocks, and the skill that clears it.
2. …

When an entry clears, move it up to *What exists* with the same wording. Do not
delete it — the record of what was hard is what stops it being re-litigated.

## Decisions still open

Things waiting on the owner, not on work. ASO category, whether to ship both
stores together, a price. Each with the date it was raised.

## Known traps for this app

App-specific gotchas that already cost time once. Not general rules — those live
in the skills. Something like "StoreKit config must be regenerated after the IAP
id changes" belongs here only if it bit *this* app.
```

---

## Routes, and why they get their own line

The stages are derived from the routes, so the routes have to be written down where
the next session reads first. Two measured cases, both from 2026-09-09:

- **`<app>`** — App Store live since 3.9, Play still a draft on internal. Half
  closed, half blocking.
- **`<other-app>`** — notarized DMG, Sparkle appcast, Windows installer, product page
  live, and **no store listing anywhere**. Distributed for a month. A file that only
  knows about stores would call it un-launched.

## When the launch ends

The file does not end with it. It loses its blocking list and keeps everything else:

```markdown
**Live since <date>** · https://apps.apple.com/app/id<numeric id>
**Play:** draft on internal — still launching

> Launched on Apple. Further Apple versions are `prepare-app-release`; the Play
> half is still a launch. This file is now the app's standing notes.
```

*What is blocking* folds into *What exists* with its wording intact, and *Known
traps for this app* survives untouched — it is the part that stays true after the
launch is over, and the part that cost the most to learn.

---

## What must NOT go in it

**Copy.** Every word about the app comes from `profile.md`. If a description is
being drafted here, it is in the wrong file and will diverge.

**General mechanics.** "`fastlane/` is derived and `--delete` wipes it" is a rule
about the deliver skills and lives in them. Repeating it per app creates 19 copies
that age separately.

**Anything derivable.** The version, the build number, the live listing text — read
them from the project and the store. A number copied here is a number that will be
wrong, and `docs/cross-repo-session/` is about exactly that.

## Why the hub and nowhere else

It has to be readable from the app's own repo **and** from the site repo, because
the launch alternates between them. The hub is the only tree both reach by path.
Putting it in the app repo hides it from the site session; putting it in the site
repo hides it from the build session; putting it in the factory mixes an app's
state into the mechanics.
