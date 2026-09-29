---
name: price-sync
description: >-
  Change a studio app's price, or reconcile prices that have drifted apart, across every
  place a price is written — prices.json, the App Store IAP, the Lemon Squeezy product,
  both profiles, store metadata, media scripts and captions, the site copy, and the
  .storekit files in the app repos. Use when the user raises or lowers a price, says a
  price is wrong or out of date, asks what an app costs, mentions the direct and store
  prices disagreeing, or after any price change in App Store Connect or Lemon Squeezy.
  Also use to audit: it reports every file whose price no longer matches. Hebrew
  triggers: "לשנות מחיר", "המחיר לא מעודכן", "כמה עולה", "לסנכרן מחירים". It reconciles
  a price everywhere it appears; it does NOT decide the price, and never changes one in
  a store.
---

# Price sync — one price, many files

A price in this studio is written in more than fifty files across four repos. Every
rise so far has reached App Store Connect and one profile and left the rest behind:
when this skill was written, three of four direct prices and five `.storekit` files
were stale, some by a year.

**`$APP_HUB/prices.json` is the source of truth.** Everything else quotes
it. When a document disagrees, the document is wrong — unless reality moved, in
which case `prices.json` is updated first and everything follows from there.

This file is the method. What running it taught — the runs behind each rule — is in
[LESSONS.md](LESSONS.md).

## Prerequisites

- **Tools:** Python 3 (stdlib) for `verify_prices.py`; `fastlane`
  (`brew install fastlane`) or spaceship only to read a live App Store price by hand.
- **Credentials:** none for the file scan. `--stores` resolves an App Store Connect
  API key through apple-track's shared credential resolver (`ASC_KEY_ID` /
  `ASC_ISSUER_ID` / `ASC_KEY_PATH`, or `credentials.json` under `$KEYS_ROOT`).
  Lemon Squeezy is a dashboard edit; no key is used.
- **Hub (`$APP_HUB`):** optional — `prices.json` is the source of truth and lives at the
  hub root when there is one; `--prices <file>` points at it anywhere else. `$SITE` and `$DEV_ROOT` locate the site pages and the `.storekit` files.
- **Other tracks:** `app-store-deliver` and `appstore-media` (apple-track); the
  `--stores` check imports apple-track's shared credential module.

## The two directions

**Reality moved** (the owner changed a price in App Store Connect or Lemon Squeezy):
update `prices.json` to match what the API reports, then propagate.

**A decision was made** (the owner wants a new price): update `prices.json`, propagate
to the documents, then tell the owner which live changes only they can make. The
Lemon Squeezy API is **read-only for products** — the price there is a dashboard
edit, always. App Store Connect prices are editable through the API but changing
what customers pay is the owner's call, not something to do while tidying files.

## Workflow

### 1. Read reality before deciding anything is wrong
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/price-sync/scripts/verify_prices.py
```
It reports, per app: `prices.json` against every price in the hub's `<slug>/`
documents, the site's pages, and the `.storekit` files in the app repos. **It does not
read a store.** `--stores` only confirms that an App Store Connect credential resolves;
the live price is read with fastlane or spaceship, by hand, when a document and the
store are suspected to differ.

Never edit a price from memory or from another document. Every price bug found so far
came from copying one file into another.

### 2. Settle `prices.json` first
It is the only file allowed to state a price on its own authority. Set `store` and
`direct`, and put in `note` **why** they differ when they do. The studio convention
is `.99` in the store and `.90` direct; a bigger gap is either deliberate — say so —
or a propagation that never happened.

### 3. Propagate, reading each occurrence
Re-run the verifier for the list, then work through it. **Do not bulk-replace.** The
same figure means different things in different lines, and the run that produced
this skill included all of these:

- the app's **store** price and its **direct** price, which differ
- a **competitor's** price in a market section
- a **historical** note — "raised from $9.99", "previously $4.99" — that must keep
  its old number to still make sense
- a **screenshot caption** describing an image that shows the old price, where the
  text and the picture have to change together or not at all

Read the line, decide which it is, and change only what claims today's price.

### 4. Media is not just text
A price in `media/apple/captions.md` or a media script usually describes a
screenshot that shows the price on screen. Changing the caption alone makes it
disagree with the image. Either recapture (`appstore-media`), or leave both and
note it — never fix half.

### 5. Store metadata needs delivering
An edited `<slug>/store/apple/metadata/**` is a hub change and nothing more until
`app-store-deliver` sends it. **If the version is `WAITING_FOR_REVIEW` or
`IN_REVIEW`, do not deliver** — it pulls the submission out of the queue. Say so and
wait.

### 6. Finish green
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/price-sync/scripts/verify_prices.py
```
Zero disagreements, or a written reason for each one that remains.

## Boundaries
- **Change what a customer pays.** Raising or lowering a live price is the owner's
  decision. Propose it, show what it would align with, and let them act.
- **Edit Lemon Squeezy.** Its API serves `GET, HEAD` on products and variants —
  verified, not assumed. Give the owner the exact values to type.
- **Guess at a price.** If neither API answers, stop and say so.

## Where a run of this lands

`places.json`, beside this file, is the same list in a form a machine can read: the five
places, how each one closes, which one must be entered rather than written from outside,
and the order. `python3 $GROVE/tools/close.py --op price-sync` prints
it and then runs the verifier, so "did every place get closed" and "do they still agree"
are one question with one answer.

## Related

- `${CLAUDE_PLUGIN_ROOT}/skills/price-sync/scripts/verify_prices.py` — the finder this
  skill drives. It ships here, and reads `prices.json` wherever that is.
- `prices.json` — the source of truth, including the competitor list the scan uses
  to avoid flagging other people's prices.
- `app-store-deliver` — sends store metadata after a price edit.
- `appstore-media` — recaptures screenshots that show a price.
