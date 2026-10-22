---
name: announce
description: >-
  Write the posts that announce a release, a launch or an article — Hacker News, Reddit,
  LinkedIn, X, Bluesky and dev.to/Medium cross-posts — from one source of truth, each
  shaped to its channel and checked against that channel's mechanical rules. Use when
  the user wants to announce or promote something they shipped, asks for a Show HN, a
  LinkedIn post, a tweet or thread, a Reddit post or a dev.to copy, or says "write a
  launch post", "draft a LinkedIn post", "write an X thread", "announce the release",
  "post this to LinkedIn", "where should I announce this", "תכתוב פוסט", "הכרזה על
  הגרסה", "טיוטה ללינקדאין", "איפה לפרסם". It writes drafts into the hub's campaigns
  folder (a git-excluded one when there is no hub) and hands them over; it posts only when the user asks, one confirmed post at a
  time, through a browser they are already signed in to — and never signs in or creates
  accounts. It does not write store listings (store-metadata-writer) or the article itself.
---

# Announcing something you shipped

The work is the same every time and goes wrong in the same places: a title one channel
cuts, Markdown another prints literally, a cross-post that competes with its own original
in search. This skill writes every channel's draft from **one source of truth**, then
checks the drafts mechanically before anyone pastes them.

## Prerequisites

- **Tools:** Python 3 (the checker is stdlib only). Network only for `--links`.
- **Credentials:** none. Nothing here logs in: the optional publish step works only in
  a browser where the user is already signed in to the channel.
- **Browser (optional, step 6 only):** Claude in Chrome or the desktop app's built-in
  browser pane.
- **Hub (`$APP_HUB`):** optional — where the drafts live, in `campaigns/` (see the hub
  contract, `docs/contracts/hub.md`), and an app's `profile.md` there is a good source of
  truth. Without a hub the drafts go to a git-excluded `launch/` in the repo.
- **Other tracks:** none. `shared-track`'s `copy-edit` is worth running on long drafts.

## Workflow

### 1. Name the source of truth, and read it

One of: a `CHANGELOG.md` section, a published article, an app's `profile.md`, a README.
**Every claim in every draft must be in that source.** Numbers are recounted from disk,
never copied from an earlier post — a count that moved since (skills, tracks, versions)
is the commonest wrong fact in an announcement. If something the post needs is not in
the source, ask; do not supply it.

**A feature list is made from the thing itself, not from the article.** An article
covers what it was about; the post lists what ships. Walk the repo's skill or feature
index (and, for a capability that sells, the skills behind it) and check the list in the
draft against it. On the App Factory launch the licence-key paywall — Lemon Squeezy,
Keygen or Gumroad, in `macos-direct-distribution` — was missing from every draft
because the article predated it, and the owner had to point it out.

**What the owner says about themselves comes from the owner.** What it cost them to
build, why they give it away, how long it took — ask; never write it on their behalf.

### 2. Agree the plan with the owner

- **Which channels, and in what order.** See [references/channels.md](references/channels.md)
  for what each one is for. The usual order: the canonical page exists first (the blog
  post, the release notes), then the launch channel, then cross-posts days later.
- **Which accounts exist.** A channel with no account, or a brand-new one, has almost
  no reach; say so rather than writing a thread nobody will see.
- **The canonical URL** — the one page every draft points back to.

### 3. Write the drafts where they will be kept

**With a hub (`$APP_HUB` set),** a campaign folder in it — the hub contract's
`campaigns/`. Pick the one that matches what is announced:

| announcing | folder |
|---|---|
| an app | `$APP_HUB/<slug>/campaigns/<campaign>/` |
| a project that is not an app (a tool, a library) | `$APP_HUB/<area>/<project>/campaigns/<campaign>/` |
| several projects at once | `$APP_HUB/<area>/campaigns/<campaign>/` |

`<campaign>` names what and when — `launch-2026-10`, `v0.7.0`. `<area>` is the owner's
grouping for non-app projects (`3-oss`, say): if the hub has one, use it; if not, ask
rather than invent one. Share images go in the project's `media/social/`. The hub is
private and in git, so the drafts are committed there — **in the hub's own terms, from a
session standing in the hub or as an exact-path commit**, never by sweeping it.

**Without a hub,** `launch/` at the repo root, excluded in **`.git/info/exclude`** — not
`.gitignore`, which is committed and in a public repo announces the folder's existence:

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
| `README.md` | what each file is, where it goes, when — the notes, never the status |

**A draft holds only what is pasted**, plus one status line as an HTML comment, which the
channel never sees and a hub's stats reader counts:

```
<!-- Status: draft -->
<!-- Status: scheduled 2026-10-22 08:30 -->
<!-- Status: posted 2026-10-20 · https://… -->
```

A file that goes to more than one channel names it: `<!-- Status (medium): posted … -->`.
How-tos, headings and "first comment:" labels go in the folder's `README.md`, not in the
draft — around the post they are Markdown the channel would print.

**The order a post is built in** — learned from the owner's edits to the App Factory
LinkedIn post, each of which moved the draft toward it:

1. **The reader's pain, in concrete steps.** Not "shipping is hard" but the steps
   themselves: *"Finishing an app's code is only half the way to the stores. Then come
   signing, compliance, screenshots in every language, store copy, two listings, the
   release — and again for every version."*
2. **What the thing is, end to end — as the main point.** One sentence that says it does
   the whole of what the pain listed (*"from the code to a live app, start to finish"*),
   right after the pain, before any backstory.
3. **The details** — the complete feature list (step 1), the limits, where it stops on
   purpose.
4. **The author's why, later.** The motivation (*"one big instructions file stopped
   holding at my third app"*) explains the thing; placed first, it buries what the thing
   is under the author's story.
5. **What it cost, and that it is given away** — *"building it was a big investment on
   my part, and I've released it as open source"*, in the owner's words. On LinkedIn, X
   and general subreddits only; on Hacker News and in technical communities
   (r/ClaudeCode and the like) it reads as marketing — leave it out there.
6. **An explicit invitation to take part**, last: try it, fork the repo, improve it. On
   Hacker News, *"pull requests that improve a skill are welcome"*, beside asking where
   it gets in the way.

A post written as a lesson (a technical subreddit's "three things I learned") keeps its
lesson first, as references/channels.md says; the invitation still closes it.

Shape each one to its channel (references/channels.md): plain text where Markdown is not
rendered, the link where the channel expects it, absolute URLs everywhere — a relative
link points nowhere once the text leaves its own site.

### 4. Check them

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/announce/scripts/check_drafts.py <drafts-folder> --links
```

Fix every ✗. A ⚠ is a convention, not a rule — say which ones you are keeping and why.

### 5. Hand over

Tell the owner, per file: where to paste it, which field is which, and when. Then ask how
it gets published:

- **(a) The owner pastes it** — the default. The skill stops at the draft.
- **(b) Claude posts it, in a browser the owner is signed in to.** Only on their request.
  Ask which browser — **Claude in Chrome** (their own Chrome, with their sign-ins) or the
  **built-in browser pane** of the desktop app — and load the matching browser skill
  (`chrome-browser` or `built-in-browser`) before the first browser step.

### 6. Publish — only if the user asks, and only with a yes per post

**Never sign in, type a password, create an account or accept terms for the user.** If a
channel shows a login page, a consent wall or a new-account flow, stop, ask the user to
do it themselves, and continue once they say it is done.

Per post, one at a time:

1. **Fill the composer** with the checked draft — exactly the file's text, nothing
   rewritten on the way. Attach the image if there is one (the lessons in
   [references/channels.md](references/channels.md#posting-by-browser) save time here).
2. **Show the user the final text and a screenshot** of the filled composer, and ask for
   a yes for **this** post.
3. **Post only after that explicit yes.** A yes for one post does not carry to the next,
   or to its own first comment — unless the user said so for both at once.
4. **Add the first comment** where the channel's convention puts the link there
   (LinkedIn), with its own yes as above.
5. **Verify** that the post and the comment are visible on the live page, rendered as
   intended — paragraphs, direction, link.
6. **Record** it in the draft's own status line — `<!-- Status: posted <date> · <url> -->`
   in place of `draft` or `scheduled` — and commit it, when the drafts are in the hub. The
   line in the file is the record, not the README: it is what a hub's stats reader counts,
   and a posted draft that says nothing about being posted is the one that gets posted
   twice.

If anything on the page differs from what the user approved — the composer cut the text,
an image failed, the channel asks for something new — stop and show them; do not adjust
and post.

## Boundaries

- **Posts only when asked, one confirmed post at a time.** A post in someone's name is
  public and permanent, so each one waits for the user's explicit yes on the exact text.
  Only through a browser the user is already signed in to; no API calls.
- **Never signs in or creates accounts.** No passwords, no sign-up, no accepting terms —
  a login page means the user signs in themselves.
- **Never invents.** No metric, user count or quote that is not in the source.
- **Does not write the thing announced** — the article, the release notes, the store
  listing (`store-metadata-writer`) are written first, elsewhere.
- **Does not chase reach.** No vote requests, no reposting the same link to the same
  community — both are punished by the channels that matter.
