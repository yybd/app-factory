---
name: store-metadata-writer
description: >-
  Write an app's store listing text for BOTH stores from its profile — name-adjacent
  fields, descriptions, keywords, release notes, in-app purchase text — into the one
  place the delivery skills read. Use when the user wants listing copy written or
  refreshed for a release, says "write the store text", "update the listing", "prepare
  the metadata" ("תכתוב את הטקסט לחנות", "עדכן את הליסטינג"), or when a profile changed
  and the stores have not caught up. **It needs a hub** (`$APP_HUB`) and a profile in
  it: prefer it when there is one, because it keeps the two stores consistent and hands
  each the files it owns; for a single app with no hub, go to app-store-metadata or
  play-store-metadata directly, which author in the repo's own fastlane tree. It does
  NOT upload anything (app-store-deliver / play-store-deliver do), does NOT decide the
  app's name (app-identity), and does NOT write the website.
---

# Store Listings — Profile → App Store + Google Play (cross-store)

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

One profile, two stores, consistent copy. This skill takes the app's **profile**
(the source of truth) and produces the App Store and Google Play listing metadata
from it — fitting each store's fields and limits — then hands the file mechanics
to the per-store skills. It does not invent copy, and it does not touch the
studio website (that is `add-app-to-site`).

This file is the method. What running it taught — the runs behind each rule — is in
[LESSONS.md](LESSONS.md).

## Prerequisites

- **Tools:** none beyond Claude Code — `copy-edit`'s `measure_copy.py` (Python 3, standard library) for Step 6b, and `curl` for the privacy-URL check. The per-store validators and `sync_from_hub.sh` belong to the skills they ship with.
- **Credentials:** none used here — `DATA.md` names the App Store Connect key (Issuer ID, Key ID, `.p8` path) for the deliver step; this skill only reads that it is recorded.
- **Hub (`$APP_HUB`):** required — reads `DATA.md` and `<slug>/profile.md`, consumes `<slug>/media/apple/`, and writes every listing field under `<slug>/store/apple/…` and `<slug>/store/play/…`.
- **Other tracks:** `app-store-metadata`, `aso-keywords`, `appstore-media`, `apple-app-store-screenshots` (apple-track); `play-store-metadata` (android-track). The deliver skills (`app-store-deliver`, `play-store-deliver`) and `ship-apple-app` / `play-store-ship` run later, from the hub this skill filled. `app-profile`, `app-identity` and `copy-edit` are this track's.

**Prerequisite — the profile (run `app-profile` first).** Every word about the
app lives in `$APP_HUB/<slug>/profile.md`. Its **Derived copy** section
already holds the limit-bound strings (store title, subtitle / short description,
short description for meta, tagline). Before writing any listing field, check the
profile exists:
- If it exists, read it — lift the Derived copy, don't re-invent store copy.
- If it does not exist, **run `app-profile` first**, then return. (`app-profile`
  itself lifts the names + ranked features from the app repo's `README.md`, which
  the `app-identity` skill writes — so the full chain is `app-identity` → `app-profile` →
  this skill. If the name/README isn't settled yet, that's where to start.)

**Two directories are in play — do not confuse them:**
- **The hub** (`$APP_HUB`) — the **source of truth, and now where the
  metadata itself lives.** You READ the profile + `DATA.md` here and you WRITE the
  per-locale store metadata here, under `<slug>/store/`.
- **The app's native project** — you do **not** author metadata here when there is a
  hub. Its `fastlane/metadata` is then a generated artifact, synced down at deliver time
  and git-ignored. The one listing artifact that stays in the app repo either way is its
  `README.md` — the identity block and feature list, owned by `app-identity`.

## The hub store layout (the metadata source of truth)

All listing fields, every locale, in fastlane format, live in the hub:

```
$APP_HUB/
  DATA.md                                  # studio-wide data (URLs, contact, copyright, App Store Connect .p8) — see below
  <slug>/
    profile.md                             # narrative source of truth
    store/
      apple/
        metadata/<locale>/                 # name, subtitle, description, keywords, promotional_text, *_url
        metadata/                          # root: copyright.txt (from DATA.md), primary_category.txt, …
        metadata/review_information/       # contact_* (from DATA.md), demo creds, notes
        release-notes/<version>/<locale>.txt   # "What's New", versioned
      play/
        metadata/<locale>/                 # title, short_description, full_description
        changelogs/<versionCode>/<locale>.txt   # changelog, grouped by build
    media/apple/ · media/play/             # screenshots / graphics (existing)
```

## `DATA.md` — studio-wide data (read it; don't re-author)

The hub-root `DATA.md` holds the values shared by every app — pull from it rather
than asking or inventing:
- **Contact** (review information): name, `email_address`, `phone number`.
- **Copyright** (e.g. `2026 <Studio Name>`) → Apple `copyright.txt`.
- **Default URLs**: marketing / support / privacy (with `{app-slug}` substituted).
- **App Store Connect API key**: Issuer ID, Key ID, and the **`.p8` path** — used by
  the deliver/upload step. (Play key: when present.)
- **`conversational language`**: the language every skill talks to the user in
  (questions, summaries, reports).

## Data flow — the hub is the SoT; fastlane syncs down at deliver

The metadata is produced and kept in the hub. fastlane never authors it; the
per-store **deliver/supply skill syncs the hub tree down into the app repo's
`fastlane/` and then uploads — every time it runs**, and the **user** runs that
outward-facing step (why: see
[LESSONS.md](LESSONS.md#the-listing-moved-to-the-hub-so-the-app-repos-copy-could-not-drift)).

```
 the hub  (SOURCE OF TRUTH — written + kept here)       app repo (generated at deliver)
 ──────────────────────────────────────────────        ───────────────────────────────
 <slug>/profile.md ─READ→ store-metadata-writer (you)
                              │ write per-locale fields
                              ▼
 <slug>/store/apple/metadata/<locale>/…  ──sync──▶  fastlane/metadata/…           ─deliver→ App Store
 <slug>/store/play/metadata/<locale>/…   ──sync──▶  fastlane/metadata/android/…   ─supply→  Play
 <slug>/store/apple/release-notes/<ver>/ ──sync──▶  fastlane/metadata/<locale>/release_notes.txt
        ▲ DATA.md (contact, copyright, URLs, .p8 path)
```

**The sync and the upload are not part of this step.** This skill and the workers it
drives only fill the hub; the deliver skills sync and upload, later, when a person asks
for it. The profile's `Project:` field names the local app repo the
sync later targets.

> **This skill is the fix when a deliver-time sync reports "missing data".**
> `sync_from_hub.sh` verifies the hub is complete before upload; on failure it names
> the locale + field and points back **here**. Fill those fields in the hub
> (`<slug>/store/…`), then re-run the sync.

**Two hard rules, before anything else:**

1. **Never fabricate.** Every field traces to the profile or an explicit answer
   from the owner. The long description is *assembled* from profile sections, not
   invented. A claim you can't ground is an Open question, not a guess.
2. **House voice exactly (the hub's `PRODUCT.md`, the master product voice).** Factual, direct, specific; state the
   feature then the concrete benefit; name the real mechanism. Banned: *powerful,
   seamless, effortless, intuitive, revolutionary, cutting-edge, supercharge*,
   exclamation marks, superlatives. Cut empty intensifiers (*deep, smart, clean,
   fast, simple*) when the mechanism is already named. Section/feature lines name
   the content, never exhort.

---

## Step 1 — Inputs

Ask the user (use `AskUserQuestion` if not given):

- **Slug** — which profile to read (`$APP_HUB/<slug>/`). Metadata is
  **written under `<slug>/store/`** in the hub, not in the app repo.
- **App's native project path** — the **sync target at deliver time** (not where
  metadata is authored) and the source of technical facts (the `versionCode` /
  build number, the bundle / application id).
- **`DATA.md` (hub root)** — read it for **contact** (name/email/phone), **copyright**,
  **default URLs**, and the **App Store Connect `.p8` path** + Issuer/Key ID. Don't
  ask the user for these or invent them.
- **Which stores** — App Store, Google Play, or both.
- **Which locales, per store** — **English is the primary/default** (the studio default).
  Store listings *may* be multi-locale even though a studio website may be English-only;
  translating approved copy is fine, inventing is not. Map each language to its
  store locale code — and mind the **Hebrew gotcha**: App Store uses `he`, Google
  Play uses `iw-IL`.
- **Release notes** — "What's new" is per release and is **not** in the profile.
  Ask for this release's notes (or record a TODO); don't invent them. Store them in
  the hub **by version**: `<slug>/store/apple/release-notes/<version>/<locale>.txt`
  and Play `<slug>/store/play/changelogs/<versionCode>/<locale>.txt` — grouped by
  build, one folder per versionCode, which is the folder `play-store-ship` hands to
  `publish_aab.py --notes-dir`. A flat `<versionCode>.txt` is not that shape.
  **A universal app can need different notes per platform** — the Mac release
  talks about the menu bar, the iOS one about the keyboard. Write the shared text
  as `<locale>.txt` and the variant beside it as `<locale>.<platform>.txt`
  (`he.osx.txt`), the same convention as the `<field>.<platform>.txt` overrides.
  The deliver sync applies the variant only when given `--platform`; without it,
  the shared text ships. **Never author release notes in the app repo's `fastlane/`**
  — that tree is rebuilt from here on every send (why: see
  [LESSONS.md](LESSONS.md#release-notes-written-in-the-app-repos-fastlane-vanish-without-a-report)).
  **Don't assume the release is the app's first.** Check the app's existing store
  status first — if an earlier version is already live, write **update-style** notes
  ("what changed"), never launch copy (why: see
  [LESSONS.md](LESSONS.md#the-release-is-not-the-apps-first)).

## Step 2 — Build the store-neutral copy block (from the profile)

Read the profile's **Derived copy** and body, and assemble the canonical strings
ONCE — store-neutral — so both stores stay in sync. Map each to its profile source:

| Canonical string | From the profile |
|------------------|------------------|
| App name / store title | the app repo's `README.md` **identity block** (`App Store name`) — NOT the profile, which deliberately does not carry it |
| Subtitle | the same README identity block (`Subtitle`) |
| Short value line | Derived **one-liner** |
| Promo line | Derived **short description** / **hero tagline** |
| Long description | *assembled here* from **What it is** + **Key features** + **Advantages / differentiators**, in house voice |
| Play short description | Derived **"Google Play short description"** (≤80) |
| Keyword set (primary + secondaries) | the app's own vocabulary in **Key features** / **Positioning** — real terms, not invented |
| Privacy URL | from `DATA.md` — **it must resolve**, wherever it is hosted |
| Support / marketing URL | from `DATA.md`, or the app's own product page |

> **The Privacy URL must exist before you submit — a dead privacy URL fails App
> Review.** If the studio has a website repo (`$SITE`), that repo's own skill produces
> the page; otherwise host it anywhere that resolves. Confirm the page is live before
> the URL goes into the listing, with a browser User-Agent — a 403 is **not** proof of
> absence: `curl -A '<browser UA>' -I <url>`, and confirm the page title, not just a
> soft 200 (why: see [LESSONS.md](LESSONS.md#a-403-on-the-privacy-url-is-not-proof-of-absence)).

If the profile is missing a string you need (e.g. the Play short description),
**add it to the profile first** — keep the source of truth complete — then lift it.

## Step 3 — Map to each store's fields (the heart)

Fit the canonical block to each store. Don't just truncate one store's string to
fit the other — write each field to use its own room.

| Canonical | App Store | Google Play |
|-----------|-----------|-------------|
| App name | name **≤30** | title **≤30** |
| Short value line | subtitle **≤30** | short_description **≤80** |
| Promo line | promotional text **≤170** | folds into the top of full_description |
| Long description | description **≤4000** | full_description **≤4000** |
| Keywords | keywords field **≤100** (hidden, comma-separated) | **none** — woven into title + short + full description |
| Release notes | what's new **≤4000** | changelogs/`<versionCode>`/`<locale>`.txt **≤500** |
| In-app purchase | IAP display name **≤30**, description **≤45** | managed product name **≤55**, description **≤200** |
| Privacy | privacy URL field | Data safety form (on the website) |

Divergences to handle deliberately:
- **Keywords.** Apple has a hidden 100-char field; Play has none. The same keyword
  intent goes into Play's visible text — hand it to `play-store-metadata`'s ASO step.
- **Subtitle (30) vs short description (80).** Same message, different room. Write
  the 80 to use its space; write the 30 to be tightest. Don't reuse one verbatim.
- **Release notes (Apple 4000 vs Play 500).** Write the short one, expand for Apple.
- **Never hardcode a price** in description / promotional text / release notes —
  storefront prices vary and a written number goes stale (why: see
  [LESSONS.md](LESSONS.md#a-written-price-goes-stale)). The price lives only in the
  IAP/pricing config; in free text say "one-time purchase, not a subscription" without
  the number.

## Step 4 — Hand off the mechanics to the per-store skills

Pass the mapped copy to the skills that own the file layout + validation. Don't
re-implement scaffolding or validation here — those skills own it, and each writes
into the **hub store tree** (`<slug>/store/…`), not the app repo:

- **App Store** → `app-store-metadata` (scaffold `<slug>/store/apple/metadata/<locale>/`,
  write the fields, validate Apple's limits) **+** `aso-keywords` (the 100-char
  keywords field). **If the app has a Pro/IAP tier**, `app-store-metadata` also authors
  the IAP listing into `<slug>/store/apple/iap/<product-id>/` in this canonical layout
  (the one `app-store-deliver` reads field-for-field — don't improvise paths; on the
  45-char description see
  [LESSONS.md](LESSONS.md#the-storekit-description-is-almost-always-longer-than-45)):
  ```
  <slug>/store/apple/iap/<product-id>/
    product.txt                  # product_id, reference_name, type, cleared_for_sale
    price.txt                    # price point / tier, cleared-for-sale
    <locale>/display_name.txt    # ≤30
    <locale>/description.txt     # ≤45  ← rewrite the .storekit description to fit; don't copy it
    review/notes.txt
    review/screenshot.png        # REQUIRED reviewer screenshot
  ```
  The **reviewer screenshot** is captured by `appstore-media` to the pinned path
  `media/apple/<App>/<locale>/iap/review_screenshot.png`; `app-store-metadata` copies it
  from there into `review/screenshot.png` (it knows the product-id). `app-store-deliver`
  reads it from `review/screenshot.png`, and an IAP can't be submitted without it.
- **Google Play** → `play-store-metadata` (scaffold
  `<slug>/store/play/metadata/<locale>/`, write the fields, validate, fold the
  keyword set into the description text; author Play in-app products into
  `<slug>/store/play/iap/` when present).

## Step 5 — Screenshots (per-store sizes)

The Apple App Store-format media lives in `$APP_HUB/<slug>/media/apple/`,
in the **canonical media tree** owned and defined by `appstore-media` (`<App>/<locale>/{screenshots,app-preview,iap,raw}/`,
with scriptwriter docs at the apple root) — consume leaf paths from it, don't redefine it.
**This skill consumes it — it does not capture.** The capture runs in the **app's repo**
(`appstore-media` drives an XCUITest demo flow; `apple-app-store-screenshots` conforms a
single image), and `appstore-media` writes its output **directly** into `media/apple/` here in the hub. If that
folder is empty, produce the media in the app repo first (via `ship-apple-app` phase 5,
or directly), then return.
- **App Store** → device sizes, sourced from `media/apple/`.
- **Google Play** → the feature graphic **1024×500** (mandatory) + phone/tablet are
  **non-Apple formats**; they live in a sibling `$APP_HUB/<slug>/media/play/`
  folder (added when you produce Play assets), via `play-store-metadata`'s graphics step.

## Step 6 — Cross-store consistency pass

Before handing back, verify the two listings agree where they should:
- same app name, same value-line *meaning*, same privacy URL, same screenshot
  story, aligned version + release notes;
- intentional differences (subtitle vs short-description wording, keyword
  placement) are fine — **different value propositions are a bug**; reconcile to
  the profile.

Run each store skill's validator and fix every error before reporting done.

## Step 6b — Edit before you ship it (`copy-edit`) — REQUIRED

Draft copy is not finished copy. Run **`copy-edit`** over the fields you just
wrote, before Step 7:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/copy-edit/scripts/measure_copy.py <slug>/store/
```

It catches what writing a listing reliably produces and re-reading it reliably misses
(why: see
[LESSONS.md](LESSONS.md#what-a-listing-draft-reliably-produces-and-re-reading-reliably-misses)).
`PRODUCT.md` holds the rules; the skill is the pass that applies them. Do it **before**
delivering, not after: tightening changes lengths, so re-run the store validator
afterwards.

## Step 7 — What stays on the store websites (one checklist)

fastlane can't do these. Give the user a single consolidated list:
- **App Store Connect:** age rating, pricing & availability, the App Privacy
  "nutrition label", export compliance, creating the app record.
- **Play Console:** the Data safety form, content rating (IARC), pricing &
  countries, app-content declarations, creating the app entry.

## Step 8 — Hand off

Tell the user:
- **where the metadata lives** — the hub's `<slug>/store/…` (the source of truth);
  the app repo's `fastlane/metadata/…` is only a synced copy created at deliver time;
- **what was lifted vs composed** — the limit-bound strings came from the profile;
  the long description and release notes were assembled/collected here;
- **Open questions / missing strings** — and that the fix is to update the profile
  first, then re-derive. If you had to write a reusable string the profile lacked
  (e.g. the Play short description), **add it back to the profile's Derived copy**
  so next time it is lifted, not rewritten.

Do not upload or publish — uploading is owned by the **deliver skills**
(`app-store-deliver` / `play-store-deliver`), is outward-facing, and is the user's
call. Your job ends when the hub (`<slug>/store/`) is complete and validated.

> **Sibling skills, no overlap.** `add-app-to-site` = the app's presence on
> **the studio website, if there is one** (catalogue card, app page, product site, privacy page).
> `store-metadata-writer` = the app's presence on the **App Store + Google Play**
> (listing metadata). Both read the same profile; neither invents copy.

## Boundaries

- **It writes the hub's copy; it does not send it.** `app-store-deliver` and
  `play-store-deliver` upload, and gate on what this skill produced.
- **It does not decide the name** (`app-identity`), capture media (`appstore-media`,
  `play-store-media`), or touch the website.
- **It does not re-implement the per-store skills.** Field limits, scaffolding and
  validation belong to `app-store-metadata` and `play-store-metadata`; this skill
  keeps the two stores saying the same thing.
