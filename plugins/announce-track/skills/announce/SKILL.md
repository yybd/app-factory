---
name: announce
description: >-
  Write the posts that announce a release, a launch or an article — Hacker News, Reddit,
  LinkedIn, X, Bluesky and dev.to/Medium cross-posts — from one source of truth, each
  shaped to its channel and checked against that channel's mechanical rules. Use when
  the user wants to announce or promote something they shipped, asks for a Show HN, a
  LinkedIn post, a tweet or thread, a Reddit post or a dev.to copy, or says "תכתוב פוסט",
  "הכרזה על הגרסה", "טיוטה ללינקדאין", "איפה לפרסם". It writes drafts into a git-excluded
  folder and NEVER posts, submits or creates accounts — publishing is the owner's, by
  hand. It does not write store listings (store-metadata-writer) or the article itself.
---

# Announcing something you shipped

The work is the same every time and goes wrong in the same places: a title one channel
cuts, Markdown another prints literally, a cross-post that competes with its own original
in search. This skill writes every channel's draft from **one source of truth**, then
checks the drafts mechanically before anyone pastes them.

## Prerequisites

- **Tools:** Python 3 (the checker is stdlib only). Network only for `--links`.
- **Credentials:** none. Nothing here posts, so nothing here logs in.
- **Hub (`$APP_HUB`):** optional — an app's `profile.md` there is a good source of truth.
- **Other tracks:** none. `shared-track`'s `copy-edit` is worth running on long drafts.

## Workflow

### 1. Name the source of truth, and read it

One of: a `CHANGELOG.md` section, a published article, an app's `profile.md`, a README.
**Every claim in every draft must be in that source.** Numbers are recounted from disk,
never copied from an earlier post — a count that moved since (skills, tracks, versions)
is the commonest wrong fact in an announcement. If something the post needs is not in
the source, ask; do not supply it.

### 2. Agree the plan with the owner

- **Which channels, and in what order.** See [references/channels.md](references/channels.md)
  for what each one is for. The usual order: the canonical page exists first (the blog
  post, the release notes), then the launch channel, then cross-posts days later.
- **Which accounts exist.** A channel with no account, or a brand-new one, has almost
  no reach; say so rather than writing a thread nobody will see.
- **The canonical URL** — the one page every draft points back to.

### 3. Write the drafts into a folder git does not see

Default `launch/` at the repo root. Exclude it in **`.git/info/exclude`**, not
`.gitignore`: drafts are private working files, and `.gitignore` is committed — in a
public repo it announces the folder's existence.

```bash
mkdir -p launch && grep -qx 'launch/' .git/info/exclude || echo 'launch/' >> .git/info/exclude
```

File names are how the checker knows the channel:

| file | channel |
|---|---|
| `hn-title.txt`, `hn-comment.txt` | Hacker News |
| `x-thread.txt`, `bluesky-thread.txt` | X, Bluesky — posts separated by a line holding only `---` |
| `linkedin*.md` | LinkedIn — the post, then `---`, then the first comment |
| `reddit*.md` | Reddit — first line is the title |
| `crosspost-<slug>.md` | dev.to / Medium — front matter first |
| `README.md` | what each file is, where it goes, when |

Shape each one to its channel (references/channels.md): plain text where Markdown is not
rendered, the link where the channel expects it, absolute URLs everywhere — a relative
link points nowhere once the text leaves its own site.

### 4. Check them

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/announce/scripts/check_drafts.py launch --links
```

Fix every ✗. A ⚠ is a convention, not a rule — say which ones you are keeping and why.

### 5. Hand over

Tell the owner, per file: where to paste it, which field is which, and when. Posting,
submitting and creating accounts are theirs — this skill stops at the draft.

## Boundaries

- **Never posts.** No API calls, no browser automation, no account creation. A post in
  someone's name is public and permanent; the owner sends it.
- **Never invents.** No metric, user count or quote that is not in the source.
- **Does not write the thing announced** — the article, the release notes, the store
  listing (`store-metadata-writer`) are written first, elsewhere.
- **Does not chase reach.** No vote requests, no reposting the same link to the same
  community — both are punished by the channels that matter.
