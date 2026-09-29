---
name: app-store-reviews-responder
description: >-
  Monitor App Store / Mac App Store customer reviews and draft developer responses to
  them. Use this whenever the user wants to read, track, triage, or analyze their app's
  user reviews and ratings, find what users complain about, draft or write replies to
  reviews, or set up a routine to keep on top of new reviews ("ביקורות באפסטור", "תענה
  למשתמשים"). It fetches reviews from Apple's public feed (no credentials needed),
  summarizes ratings/themes, drafts on-guideline responses, and explains how to post
  them in App Store Connect. This is post-launch reputation work — distinct from
  app-store-metadata (listing text) and aso-keywords (discoverability).
---

# App Store Reviews Responder

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

After launch, reviews are the feedback loop and the public face of the app.
This skill helps the user stay on top of them: pull recent reviews, see the
rating trend and recurring complaints, and write professional, on-guideline
responses — so users feel heard and the listing reads well to prospects.

## Prerequisites

- **Tools:** none beyond Claude Code; `scripts/fetch_reviews.py` is stdlib Python 3
  and needs network access to Apple's public reviews RSS feed.
- **Credentials:** none to fetch; posting a reply through the App Store Connect API
  (`customerReviewResponses`) needs an API key — `apple-credentials` creates it.
- **Hub (`$APP_HUB`):** optional — only the conversational-language default in `DATA.md`.
- **Other tracks:** `copy-edit` (shared-track) for the pass over the drafts.

## Workflow

### 1. Get the app and fetch reviews
You need the app's numeric App Store ID (or its bundle id, which the script
looks up). Then fetch recent reviews from Apple's **public** feed (no auth):
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/app-store-reviews-responder/scripts/fetch_reviews.py \
  --bundle-id com.you.app --countries us,il,de
# or: --app-id 1234567890
```
It reports total/average rating, the 5★–1★ distribution, the negative/neutral
reviews (≤3★), and common terms in them. Reviews are per-country, so pass the
countries that matter (the feed only returns recent reviews, capped per
country). A new app may have none yet — that's normal.

### 2. Triage
Prioritize responses to: low-rating reviews that raise a **fixable or
clarifiable** issue (a misunderstanding, a missing-feature request you can
address, a bug you've since fixed), and reviews that misstate facts others will
read. Don't bother responding to every 5★ ("thanks!" spam adds little); focus
where a response changes the reader's impression or helps the reviewer.

### 3. Draft responses (on Apple's rules + good tone)
Draft per [references/response-guidelines.md](references/response-guidelines.md).
In short: professional and specific, thank them, address the actual point, never
include personal data, don't argue, and if you fixed the issue say so and invite
them to update. Match the review's language where you can. Present drafts to the
user to approve/edit — the public voice is theirs.

**Edit the drafts before you show them (`copy-edit`).** A reply sits on the store
page under the app's name, next to the listing, and it is read by every later
visitor — the same standard as the listing itself applies. Run the `copy-edit`
skill over the drafted replies: one idea per sentence, no point made twice, no
term of art the reviewer does not know, and none of the rhythms that make a reply
read as generated. A reply written in the reviewer's language gets the same pass in
that language; a canned-sounding response to a complaint is worse than none.

Run the **`copy-edit`** skill over `<drafts-file>`. It is in another plugin
(shared-track), so invoke it by name rather than pathing to its script.

### 4. Post (App Store Connect — authenticated)
Posting a developer response is NOT in the public feed; it's done in **App Store
Connect → your app → Ratings & Reviews → Reply**, or via the App Store Connect
API (`customerReviewResponses`, needs an API key — see the `apple-credentials`
skill). One response per review (you can edit it later). Guide the user to post,
or — only with explicit confirmation and an API key — post via the API.

### 5. (Optional) Make it a routine
If the user wants ongoing monitoring, suggest running the fetch on a schedule
(e.g. the `/loop` or `/schedule` tooling) and flagging new ≤3★ reviews to draft
replies for. Don't auto-post; keep a human in the loop.

## What's safe vs ask-first
Safe: fetching/summarizing reviews, drafting responses. Ask first: posting a
response publicly (it's outward-facing and tied to your account) — always show
the draft and get approval first.

## Boundaries

- **It does not change the app or the listing.** A review that reveals a real bug
  goes to `apple-bug-flow-review`; one that reveals a misleading listing goes to
  `app-store-metadata`.
- **Nothing is posted without the user seeing it first.** A reply is public and
  immediate, and cannot be taken back.

## Reference files
- [references/response-guidelines.md](references/response-guidelines.md) —
  Apple's rules for developer responses + tone/best practices + templates.
- [scripts/fetch_reviews.py](scripts/fetch_reviews.py) — fetch + summarize
  reviews from the public feed (read-only, no auth).
