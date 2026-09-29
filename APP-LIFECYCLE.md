*English · [עברית](APP-LIFECYCLE.he.md)*

# App lifecycle — from an app that exists to an app that ships

Which skill runs when, and what each one needs before it can. Every skill named here
ships in this marketplace; nothing below assumes a second repo, a shared data store, or
more than one app.

**Two shapes, one sequence.** A single app keeps everything in its own repo: the
listing text and media live in `fastlane/`, which is the layout Apple's `deliver` and
Google's `supply` read. A studio with several apps keeps them in one **hub** repo
instead, so the copy is written and reviewed in one place. The steps are identical; only
where the files land differs, and each skill selects the mode itself — an unreachable
`$APP_HUB` is not an error, it is the first shape.

The full studio version of this sequence, with the site repo and the campaign work, is
the record in [`docs/decisions/3-studio-flow.md`](docs/decisions/3-studio-flow.md).

---

## Before anything: which tracks this repo loads

**Nothing is global.** A track is enabled in the repo's own `.claude/settings.json`,
which is what keeps App Store skills out of a website. A repo that enabled nothing loads
nothing, and looks exactly like a repo where the skills decided they were not relevant.

```bash
python3 $AF/factory/enable.py --yes
```

[QUICKSTART.md](QUICKSTART.md) is the install, and where `$AF` gets its value.
`factory-setup` is the skill that fixes this when a store skill you expected is missing.

---

## The sequence

```
0  identity            app-identity          the name, the feature list, the Pro tier
│                      app-profile           one dossier every later skill quotes
│
1  the binary          credentials → signing → compliance → i18n → icon → build
│
2  the privacy URL     required before any store will accept a submission
│
3  media               appstore-media · play-store-media      needs a build from 1
│
4  version             the build number / versionCode, read from the project file
│
5  copy                store-metadata-writer → the per-store metadata skills
│
6  deliver listing     app-store-deliver · play-store-deliver   pull-and-diff first
│
7  ship the binary     ship-apple-app · play-store-ship
│
8  after               reviews-responder · price-sync · aso-keywords
```

**A first launch is not an update.** `launch-app` sequences the whole of the above for
an app that has never shipped — it has to settle a name before anything quotes it and
produce a privacy URL before a store will take a submission. `prepare-app-release` is
the same map for version N+1, which inherits all three. If the app has a live listing,
it is the second one.

---

## What each step needs

**0 · Identity, then the profile.** `app-identity` reads the code, decides the name with
you (device display, store name, subtitle), ranks the features, and writes the repo's
`README.md` — the source of truth for identity. `app-profile` then writes one dossier
(`profile.md`) that every copy skill quotes: no skill invents a claim, and a field that
is wrong gets fixed there rather than in the listing.

**1 · The binary.** In the app's repo, in this order: `apple-credentials` /
`android-credentials` (the one owner of certificates and keys) → `code-signing-provisioning`
→ `app-store-review-compliance` / `play-store-compliance` → `localization-i18n` /
`capacitor-localization` → `app-icon-generator` / `android-icon-generator` → build.
Compliance runs **before** the build, because its findings change the project — a target
API level, a permission, a privacy string — and finding them after archiving means
archiving twice.

**2 · The privacy URL.** Both stores refuse a submission without one, and it needs no
media, so it can be done at any point before step 6. What the stores actually require of
it is one URL that resolves: [`docs/contracts/site.md`](docs/contracts/site.md).

**3 · Media.** `appstore-media` captures from the running app and frames the shots;
`play-store-media` does the Play formats, including the 1024×500 feature graphic that
Play requires before a listing can go live. Both read the profile for screen order and
emphasis, so they come after step 0 and after a build from step 1.

**4 · Version.** Bump it in the project and **read the current value from the file**,
never from notes. Apple wants a build number higher than any uploaded; Play wants a
versionCode higher than every code ever used. This comes before the copy because the
changelog folder is named after the number.

**5 · Copy.** `store-metadata-writer` reads the profile and drives the per-store skills
(`app-store-metadata`, `aso-keywords`, `play-store-metadata`), which own the files and
their limits. `copy-edit` runs over anything a customer will read, and compares every
translation to the English claim by claim — in a language nobody on the team reads, that
comparison is the only check there is.

**Media before copy, when the media is changing**, because captions and store text quote
the screenshots. When nothing visual changed, the two are independent.

**6 · Deliver the listing.** One skill per store, and they are the only things here that
upload metadata. Each begins with a mandatory guard: pull the **live** listing and diff
it against what you hold, because the console can be edited between releases and a blind
upload silently reverts those edits — or deletes media, since both stores overwrite the
image sets they are given. Three outcomes: in sync, "adds" (the store field is empty,
safe), and **conflict — stop and back-port**.

**7 · Ship the binary.** `ship-apple-app` and `play-store-ship` verify that everything
above is present, then archive or build the AAB, upload, and publish to a track. They
verify; they do not author. A missing field sends you back to step 5.

**8 · After.** `app-store-reviews-responder` / `play-store-reviews-responder` for what
users write, `price-sync` when a price changes anywhere, `aso-keywords` when the listing
stops being found.

---

## The rules that cost something to relearn

1. **Never invent a field.** Every word traces to the profile or to an explicit answer.
   Missing? Fix the profile, then derive again.
2. **One writer per surface.** The repo's `fastlane/` is written by the deliver sync and
   by nothing else, and the sync runs `rsync --delete` — anything another tool wrote
   there is destroyed on the next run without being reported.
3. **Text in `fastlane/` that the hub cannot reproduce is unreturned work, not
   garbage.** The sync stops on it and names it rather than deleting it. (With no hub
   the question does not arise: that tree *is* the source of truth, and nothing is
   copied over it.)
4. **Pull and diff before every upload.** See step 6. This is the step that is skipped
   when someone is in a hurry, and the one that costs a live listing.
5. **Apple freezes metadata in review.** Waiting for review, in review, or pending
   release means an upload pulls the submission out of the queue and loses its place —
   so it needs explicit approval. Play has no equivalent; its API exposes no such state.
6. **Credentials are read where they sit and copied nowhere.** They live under
   `$KEYS_ROOT`, outside every repo, and each track's resolver asks in a documented
   order: [`docs/contracts/keys.md`](docs/contracts/keys.md).
7. **A commit is not a release.** What reaches a user is a version: see
   [CONTRIBUTING.md](CONTRIBUTING.md#releasing).

---

*Which skill owns which topic, what each is NOT for, and the Apple/Android parity map:
[`SKILLS.md`](SKILLS.md).*
