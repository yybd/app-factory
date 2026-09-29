# What these skills will do to your repos, your machine and your store listings

A skill is instructions a model reads and acts on. Installing this marketplace does not
grant it anything Claude Code would not otherwise do — every file write, command and
network call still goes through the same permission model. What it changes is **what
gets proposed**, and that is worth reading before you enable a track.

This document is the honest list. Where something here is uncomfortable, that is the
point: you should know it before it happens rather than after.

---

## The short version

| | |
|---|---|
| Writes files in your app repo | **Yes** — and one directory it will delete from |
| Writes files in other repos | Only where you point it, and it says so first |
| Reads your credentials | **Yes**, in place. Never copies, prints or commits them |
| Uploads to App Store Connect / Google Play | **Yes**, at the end of skills whose whole job that is |
| Submits an app for review | **No.** It prepares; a person presses it |
| Publishes a reply to a public review | Drafts it; posts only what you approve |
| Changes a price | **Never.** It reports disagreements and gives you the values |
| Commits | Where a skill says it will, in that repo's own terms |
| Pushes | **Never**, unless you ask in that moment |

---

## Deletes — the one to know about

`fastlane/` **in your app repo is treated as disposable** by the delivery skills. Their
sync runs `rsync --delete` into it, so anything authored there by hand and not present
in the source it syncs from is removed.

That is deliberate: in the studio flow the listing is authored once somewhere else and
mirrored in, so the repo's copy is a build artefact. **The sync will not silently
destroy work it cannot reproduce** — it stops, names the file, and tells you to put it
back in the source first. `--discard-repo-extras` overrides that, and exists so
discarding is a decision rather than an accident.

If you author your listing directly in `fastlane/`, run the delivery skills in
standalone mode, where nothing is copied and nothing is deleted. They detect that on
their own when there is no hub.

Nothing else here deletes. No skill removes a store listing, a build, a screenshot set
already uploaded, or a git object.

---

## What reaches the network

| Skill | What it sends | What it can change |
|---|---|---|
| `app-store-deliver` | listing text, screenshots, previews, review information, in-app purchase content | the **draft** version of your App Store listing |
| `play-store-deliver` | listing text, graphics, in-app products | your Play listing |
| `play-store-ship` | the AAB you built | a release on the track you name |
| `ship-apple-app` | the archive | a build in App Store Connect |
| `notarize-and-distribute` | your app, to Apple's notary service | nothing but the notarisation ticket |
| both reviews responders | a reply you approved | a public reply under a review |
| `aso-keywords`, `app-identity` | a search query to the public store search API | nothing |
| `web-seo` | requests to your own pages | nothing |
| `web-design-guidelines` | a request for a public rules document | nothing |

Everything else is offline.

**A store upload lands in a draft, not in front of customers.** Submitting for review,
and releasing after approval, are steps a person takes in the console. That line is
where the skills stop on purpose: an upload can be replaced, and a submission cannot be
unmade.

---

## Credentials

Secrets live in one folder outside every repo — `$KEYS_ROOT` — which
`factory/init_keys.py` creates with a `.gitignore` that refuses everything before
anything can be put in it.

- Skills read those files **in place** and hand the path to the tool that needs it.
- Nothing prints a key, a password, a token or a `.p8`'s contents.
- Nothing copies a credential into a repo, and nothing commits one.
- `credentials.json` holds **identifiers and paths only** — never a secret itself.
- A notary credential is stored by `notarytool` in your login keychain, by name. The
  skills use the name.

**What this does not protect against:** a credential you paste into a chat, a key
committed before you installed any of this, or a machine someone else has. None of that
is in this project's power to fix.

---

## Git

Skills commit where they say they will, in the repo the change belongs to, with a
message written in that repo's terms. Five operations declare every place their work
lands, so `close.py --op <name>` can list them.

**No skill pushes.** A push publishes a whole branch, including commits that have
nothing to do with the work in front of you — and it cannot be undone. Where a skill
would otherwise be "done", it says what remains to be pushed and stops.

---

## Writing into a repo the session is not standing in

Several skills read from one repo and write into another — a profile written from an
app's source into a data repo, listing text mirrored into a build repo. Each one names
the exact paths it writes.

This is worth knowing because a session sees one `git status`. Work left in another repo
is not missing; it is **invisible**. The skills that do this declare their places for
exactly that reason, and grove — a separate, optional marketplace — adds guards that
refuse a write into a repo the session is not in unless it was declared.

---

## What no skill here does

- Change what a customer pays. `price-sync` finds disagreements and gives you the
  values; setting a price is the owner's decision and is made in the store.
- Submit for review, or release an approved build.
- Remove an app, a listing, a build or a review.
- Read your browser, your mail, or anything outside the repos you point it at.
- Send your code, your data or your credentials anywhere except the store APIs listed
  above, and then only what that API is for.

---

## If you want less than this

Every track is separate and enabled per repo. Nothing obliges you to install the ones
that upload: the audit, compliance, copy, icon, localisation and design skills change
only files in front of you and reach nothing. `factory/enable.py --tracks …` takes
exactly the list you give it.
