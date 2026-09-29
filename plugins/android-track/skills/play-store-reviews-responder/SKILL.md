---
name: play-store-reviews-responder
description: >-
  Read Google Play user reviews and write and post replies to them, through the Play
  Developer API. Use when the user wants to see what reviewers are saying on Play, asks
  about ratings or new reviews, wants to answer a review, reply to a complaint or a bug
  report left as a review, or wants a pass over everything unanswered ("תגובות בפליי",
  "תענה לביקורות"). It fetches reviews with the service account, drafts replies in the
  reviewer's own language, and posts them only after the user approves each one. The
  Apple counterpart is app-store-reviews-responder. It reads and answers reviews; it
  does NOT change the listing or fix the bugs they report.
---

# Play Reviews — read and reply

> **Conversational language:** talk to the user — questions, summaries, reports — in the `conversational language` set in the hub `DATA.md` (`$APP_HUB/DATA.md`); fall back to the language the user writes in if it is unset. **Replies to reviewers are written in the reviewer's language, not the conversational one.**

Play, unlike the App Store, exposes reviews and replies over the same
`androidpublisher` API the releases use — so this is scriptable end to end.

## Prerequisites

- **Tools:** `python3` (stdlib only) and `openssl` on `PATH` — `reviews.py` borrows
  `publish_aab.py`'s JWT signing; nothing to install.
- **Credentials:** a Play service-account JSON with reply-to-reviews rights, resolved by
  `shared/credentials.py` (env → `$KEYS_ROOT/credentials.json` → folder), or `--key`.
- **Hub (`$APP_HUB`):** optional — the conversational language, and a legacy credential
  fallback read from `DATA.md`.
- **Other tracks:** `copy-edit` (shared-track) over a batch of drafted replies;
  `capacitor-bug-flow-review` (capacitor-track) for bugs reported in reviews.

## Read
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/play-store-reviews-responder/scripts/reviews.py --package <pkg> --list
```

**The window is narrow, and this is the thing to know before promising a report:**
`reviews.list` returns only reviews from roughly the **last week**, and only those
with text — a bare star rating never appears. Anything older lives in the Console
and in the CSV exports under *Download reports → Reviews*. An empty result therefore
means "nothing in the window", never "nobody has reviewed the app".

Each review carries the star rating, the text, the app version and the device, and
any reply already sent. A review can be edited by its author, which resets it.

## Reply
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/play-store-reviews-responder/scripts/reviews.py \
  --package <pkg> --reply <reviewId> --text "…"
```
- One reply per review; posting again **replaces** the previous reply.
- 350 characters maximum.
- The reply is public, under the developer name, and is emailed to the reviewer.

## How to write the reply
- **In the reviewer's language.** A Hebrew review answered in English reads as a form
  letter. Match their language and register.
- Lead with the specific thing they said, not with thanks. "The share-button fix shipped in
  1.2.3" is worth more than a paragraph of appreciation.
- If it is a bug: say whether it is fixed, in which version, or that you are looking
  at it — and nothing vaguer than that.
- If it is a feature request: say yes, no, or not now. Never imply a commitment the
  user has not made.
- Never argue with a rating, never ask them to change it, never mention competitors,
  never publish anything about the reviewer.
- No personal data in a reply — it is a public page.

## Boundaries
**Never post without showing the user the exact text and getting an explicit yes**,
per review. A reply is public, immediate, and attributed to them. Draft, show,
wait — and when several are pending, show them as a batch and let the user approve
or edit each.

## Triage a batch
Sort by what the reviews are actually saying, not by star count: a repeated crash
report is worth more than ten one-liners. Group into *bugs* (hand to
`capacitor-bug-flow-review` for a Capacitor app, else straight to the repo), *feature
requests* (record them, don't promise), *misunderstandings* (usually a sign the
listing or onboarding is unclear — hand to `play-store-metadata`), and *noise*.

## Related skills
- `play-store-metadata` — when reviews reveal the listing is misleading.
- `play-store-ship` — when the answer is "fixed in the next release".
- `copy-edit` — run it over a batch of drafted replies before posting.
- `app-store-reviews-responder` — the Apple counterpart.
