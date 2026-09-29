---
name: app-store-metadata
description: >-
  Create, organize, translate, and validate App Store / Mac App Store listing metadata
  for an Xcode project — localized text (name, subtitle, description, keywords, promo
  text, release notes, URLs), review information, categories, and screenshot file
  placement. Use whenever the user wants to write, translate, fix or validate App Store
  listing text, set up the fastlane metadata structure, or manage multi-language
  listings ("טקסט לאפסטור", "תתרגם את הליסטינג"). It scaffolds the per-locale files,
  validates against Apple's limits, and says which steps are website-only. It authors
  into a hub when there is one and the repo's fastlane/ when there is not — so it is
  the direct route for a single app, while store-metadata-writer is preferable once a
  hub holds the profile and both stores must stay consistent. It does NOT upload:
  delivery to App Store Connect is app-store-deliver's job.
---

# App Store Metadata (fastlane)

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

Getting an app listing accepted means every localized field is present, within
Apple's character limits, and consistent across languages — and that the things
that can't be set programmatically (age rating, pricing, privacy questionnaire)
get done on the website. This skill **authors and validates** that metadata; the
actual `deliver` upload to App Store Connect is the **`app-store-deliver`** skill.

Guide the user — don't just generate files. Listing copy is a product/marketing
decision; ask for the positioning and translate intent faithfully rather than
inventing claims. Confirm before installing tools.

> **Where the listing copy comes from.** This skill owns the file mechanics —
> scaffolding, field placement, and character-limit validation — not the wording,
> and not the upload (that's `app-store-deliver`). In the **studio flow** the copy is
> lifted from the app's profile (`$APP_HUB/<slug>/profile.md`) by the
> `store-metadata-writer` skill, which drives this one; so when a profile exists,
> take the copy from there (or let `store-metadata-writer` orchestrate) instead of
> re-authoring it here. Standalone (no profile), the app's `README.md` — written and
> owned by the `app-identity` skill — is the source of truth: take the **App name** and
> **Subtitle** from its identity block and base the **description** on its ranked
> feature list, rather than re-authoring. Only if there's no README either, write the
> fields with the user as below. Either way, never fabricate claims.

## Prerequisites

- **Tools:** `fastlane` (`brew install fastlane` or `gem install fastlane`, see
  `references/fastlane-setup.md`) for `deliver init` / `snapshot`; `ffmpeg`
  (`brew install ffmpeg`) only for the review-screenshot one-liner; Python 3, stdlib.
- **Credentials:** none for authoring and validation; `fastlane deliver init` (pulling
  the current listing) signs in to App Store Connect — the key is `apple-credentials`'.
- **Hub (`$APP_HUB`):** optional — studio flow authors into
  `$APP_HUB/<slug>/store/apple/metadata/` and reads URLs from `DATA.md`; standalone
  authors into the repo's `fastlane/metadata/`.
- **Other tracks:** `store-metadata-writer` and `app-identity` (shared-track) supply
  the listing copy this skill places.

## Where the canonical metadata lives (hub vs repo)

- **studio (hub) flow — the source of truth is the hub:**
  `$APP_HUB/<slug>/store/apple/metadata/<locale>/…`. Scaffold, write, and
  validate **there**. Review-info **contact**, `copyright.txt`, and the default
  **URLs** come from a studio hub's `DATA.md` when there is one — read them, don't ask. The app repo keeps
  only its `README.md` (identity + features, owned by `app-identity`); the per-locale
  metadata lives in the hub.
- **Standalone flow (no hub)** — author directly in the app repo's
  `fastlane/metadata/<locale>/…`, taking name/subtitle/description from the repo's
  `README.md` (owned by `app-identity`).

This skill **authors + validates** the content; it does **not** upload. The delivery
to App Store Connect — sync hub → `fastlane/`, the official-ASC-API upload of
metadata + screenshots + **IAP** — is the **`app-store-deliver`** skill. Hand off to
it once the content is authored and validated.

## Workflow

### 1. Check fastlane
Detect whether fastlane is set up:
- `fastlane/` directory with a `Fastfile` and/or `metadata/`,
- `fastlane` in the `Gemfile`, or `which fastlane` / `bundle exec fastlane`.

If missing, guide installation (ask first — it changes the environment). See
[references/fastlane-setup.md](references/fastlane-setup.md) for the install and
`deliver` init steps. Prefer Bundler (`Gemfile` + `bundle install`) so the
version is pinned.

### 2. Understand the listing shape
- **Platform** — iOS vs macOS. This drives screenshots (iOS supports a capture
  script; macOS does not — see step 5) and the screenshot sizes.
- **One app or several targets** — a single project can ship multiple apps from
  one `fastlane/` folder, each with its own `metadata/<app>/` path and `deliver`
  lane (detect this; don't assume one app).

### 2a. Ask which languages — ALWAYS ask, never assume
Language choice is the user's decision and shapes everything downstream (how
many files, how much copy to write/translate, screenshot locales). So:

1. First detect what already exists — list the locale folders currently under
   `metadata/` so the user sees the starting point.
2. Then ASK explicitly, two things:
   - **Single language or multiple?** Don't default to multi-language — a
     one-locale listing is a legitimate and common choice; more locales means
     more copy to maintain and translate.
   - **Which specific languages?** Have them name the App Store languages they
     want (e.g. English (U.S.), German, Spanish, Hebrew). Offer the ones already
     present as the default to keep, and confirm any to add or remove.
3. Map each chosen language to its App Store locale code (`en-US`, `en-GB`,
   `de-DE`, `es-ES`, `fr-FR`, `ja`, `zh-Hans`, `he`, …). The full list and the
   primary-language rule are in [references/metadata-spec.md](references/metadata-spec.md).

Use the AskUserQuestion tool for this when available — it's exactly the kind of
branching decision (single vs multi, and which set) that the user should drive.
Only proceed to scaffolding once the language set is confirmed.

### 3. Ask: text only, or text + screenshots
This changes the work substantially, so ask up front:
- **Text only** — fastest; just the localized `.txt` fields + review info.
- **Text + screenshots** — also prepare/upload screenshots (step 5).

### 4. Create / update the metadata files
Scaffold the per-locale structure (won't overwrite existing content):
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/app-store-metadata/scripts/scaffold_metadata.py <metadata-root> --locales en-US,de-DE,he
```
`<metadata-root>` is the **hub** store path
`$APP_HUB/<slug>/store/apple/metadata` in the studio flow (the source of
truth), or the repo's `fastlane/metadata` when standalone. Validate at the same path.

Then fill the fields. In the studio flow the wording comes from the
profile (via `store-metadata-writer`); standalone, take **App name** / **Subtitle**
from the app's `README.md` (the `app-identity` skill's source of truth) and base the
description on its feature list — or write the base language with the user if
there's no README — then translate to the others, keeping each field within its
limit (the translated string, not the source, must fit). **Never hardcode a price**
in the description, promotional text, or release notes — storefront prices vary and a
written number goes stale; say "one-time purchase, not a subscription" without the
number, and let the price live only in the IAP/pricing config. The 100-char **keywords**
field is
an ASO decision owned by the `aso-keywords` skill — this skill just stores and
validates it. Field list, limits, and which files are per-locale vs shared are in
[references/metadata-spec.md](references/metadata-spec.md).

### 4b. Lead with the pain, and show how it is solved

A description that opens by naming the product and listing its features tells the reader
what it *is* and leaves them to work out whether they need it. State the problem instead,
in the reader's own terms, and then the mechanism that removes it.

**Name the work being saved, not the benefit.** "The difference between a saved paragraph
and a finished reply" is a claim about a difference; the reader still has to infer what the
difference is. "What costs time is going back to their message for the name, the order
number, the date — and typing each one in by hand" is the same point, and the reader
recognises themselves in it because it describes what they actually do.

**Where it goes differs by surface, and this is the part that gets missed:**

| Surface | Budget | Where the pain goes |
|---|---|---|
| **App Store** | ~170 characters are visible before "more" | Inside those 170. One clause says what the app is, the pain starts immediately after. If the whole preview is spent on the product, the pain is not in the listing as far as most readers are concerned. |
| **Product site / app page** | No budget | Develop it: the reader arrived deliberately. A short paragraph, then **show it** — the input beside the output — rather than describing it a third way. |

Check the preview literally: `head -c 170 description.txt`. Whatever falls outside it is
read by a small minority.

**Do not repeat a claim in the opening that a later section already owns.** If a sync
section exists, the opening does not need "on all your devices"; the space is better spent
on the pain. Cutting a duplicate is not cutting a claim.

### 5. Screenshots (only if chosen)
Media lives in the **canonical media tree** owned by `appstore-media`
(`<slug>/media/apple/<App>/<locale>/{screenshots,app-preview,iap,raw}/`) — read leaf
paths from it, don't redefine the layout. Three skills divide this work: for a full,
repeatable **capture** (a scripted XCUITest demo flow producing stills + App Preview
videos across locales) hand off to the `appstore-media` skill; for a one-off **conform**
of an existing image to an exact size use `apple-app-store-screenshots`. Both write into
the canonical media tree, and `app-store-deliver` stages from it and uploads.

**This skill does not organise them.** It used to say it did — moving the files into
`store/apple/` — and nothing reads media from there: the delivery sync looks only under
`media/apple/`. Anything "organised" into the store tree was work that disappeared.
- **iOS** — you can automate with `fastlane snapshot` (UI-test driven capture
  across devices/locales) and `frameit` for framing. See
  [references/screenshots.md](references/screenshots.md).
- **macOS** — there is NO snapshot automation; screenshots are captured manually
  at the required pixel sizes. Guide the manual capture, then use the
  `apple-app-store-screenshots` skill to conform any image to the exact App
  Store dimensions. Sizes and steps are in
  [references/screenshots.md](references/screenshots.md).

### 5b. In-App Purchases (Pro) — author the IAP metadata into the hub
If the app has a paid/Pro tier, **this skill authors the IAP listing metadata**
(the deliver skill only syncs + uploads — it never writes this). The README/profile
`Pro:` line names the product id and what it unlocks; the `.storekit` config /
StoreKit code give the type + price. Write each product into the hub:

```
<slug>/store/apple/iap/<product-id>/
  product.txt            # reference name · type (non-consumable / auto-renewable …)
  price.txt              # price point / tier
  <locale>/display_name.txt   # ≤30, per locale
  <locale>/description.txt    # ≤45, per locale  ← short. The .storekit / StoreKit
                              #   description is almost always longer than 45 chars;
                              #   rewrite it to fit, don't copy it through.
  review/notes.txt            # notes for App Review
  review/screenshot.png       # required reviewer screenshot — copied from media (see below)
```

Lift the per-locale copy from the profile/README like all other store copy — never
invent. **Place the reviewer screenshot** by copying it from the pinned capture path
`appstore-media` writes — `media/apple/<App>/<locale>/iap/review_screenshot.png`
(fall back to the single image in that `iap/` folder if it's named otherwise) — into
`review/screenshot.png`. This step owns the copy because it knows the product-id and
the `store/iap` tree; if the source isn't there, the IAP capture hasn't run — flag it
(don't fabricate the file). `app-store-deliver` uploads it later via the ASC API.

#### IAP field limits — verified 2026-08-23
Source: [App Store Connect Help — In-app purchase information](https://developer.apple.com/help/app-store-connect/reference/in-app-purchases-and-subscriptions/in-app-purchase-information).

| Field | Limit |
|---|---|
| Reference Name | **≤64** — internal only, but it is the name that shows in **Sales & Trends** reports. Make it self-identifying across a multi-app account: `<App> Pro`, not `Pro` or a bare feature name. |
| Product ID | **≤100**, letters/numbers/hyphens/periods/underscores only, and **permanent — it cannot be edited or reused after the product is saved**. It must match the id in the StoreKit code and the `.storekit` file exactly; a mismatch fails the purchase silently. |
| Display Name | **2–30** per locale |
| Description | **≤45** per locale — easy to miss. The `.storekit` / marketing description is almost always longer; rewrite to fit, never copy it through. |
| Review Notes | **≤4000** |

#### The reviewer screenshot has a size spec — this is the one people get wrong
It is **not** a free-form crop. Apple requires JPG/PNG matching **one of the app
screenshot specifications the app itself supports**, and **no alpha channel /
transparency**. Practically:

- **Mac app** → `2880×1800` (also 1280×800, 1440×900, 2560×1600 — all 16:10)
- **iPhone** → `1320×2868` (6.9") or `1284×2778` (6.5")
- **iPad** → `2064×2752` (13")

If the paywall is a small centred sheet, don't ship the tight crop — crop it, then
scale-to-fit and pad to a legal size, which also flattens the alpha:
```bash
ffmpeg -y -i raw.png -vf "crop=W:H:X:Y,scale=2880:1800:force_original_aspect_ratio=decrease,pad=2880:1800:(ow-iw)/2:(oh-ih)/2:white,format=rgb24" review_screenshot.png
```

**One screenshot covers every platform.** With Universal Purchase there is a single
shared IAP record across the Mac, iPhone and iPad apps, so there is one screenshot
field — no per-platform variants. Pick a size from any platform the app supports.

Validate display name (≤30), description (≤45), and that `review/screenshot.png`
exists at a legal size with no alpha (a product can't be submitted without it).

### 6. Validate against Apple's requirements
Always validate before uploading — over-limit fields and missing required files
are the common metadata rejections/errors:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/app-store-metadata/scripts/validate_metadata.py <project-root-or-metadata-root>
```
It checks character limits, required fields per locale, URL fields, and
cross-locale completeness, and prints a report. Fix every error it flags.

The validator checks URL *format*, not reachability. Separately confirm the
**privacy URL actually resolves** before upload — a dead privacy page fails App
Review. Verify with a browser User-Agent: a `403` / anti-bot block is **not** proof
of absence, so check the real status with `curl -A '<browser UA>' -I <url>` and
confirm the page title rather than trusting a soft 200.

### 7. Hand off to `app-store-deliver` (this skill does not upload)
Authoring ends at validation. **Uploading is a separate skill** — once the hub
content is written and the validator is clean, hand off to **`app-store-deliver`**,
the single send-surface: it syncs the hub tree down into `fastlane/`, re-verifies
completeness (blocking on any missing field), and uploads the metadata +
screenshots + **IAP** to App Store Connect via the official ASC API (auth from the
track's resolver — `shared/credentials.rb`). Tell the user that's the next step; don't run `deliver` from here.

The website-only leftovers (age rating, pricing display, App Privacy nutrition
label, export compliance, creating the app record) are listed in
[references/metadata-spec.md](references/metadata-spec.md#done-on-the-app-store-connect-website)
and are completed during `app-store-deliver` / `ship-apple-app`.

## Boundaries

- **It authors and validates; it does not upload.** `app-store-deliver` is the single
  send-surface, and gates on what this skill produced.
- **It does not capture or organise media.** `appstore-media` writes the canonical
  media tree; `apple-app-store-screenshots` conforms a single image.
- **It does not choose keywords** (`aso-keywords`) or the app's name
  (`app-identity`) — it owns the files those decisions land in.

## What's safe to do vs ask first
Safe: scaffolding the folder structure, drafting/cleaning field text within
limits, validating, fixing over-limit strings (with the user's wording).
Ask first: installing fastlane/gems, overwriting existing human-written copy.
(Uploading is `app-store-deliver`'s concern, not this skill's.)

## Reference files
- [references/metadata-spec.md](references/metadata-spec.md) — field list,
  character limits, per-locale vs shared, locale codes, and the website-only
  steps.
- [references/screenshots.md](references/screenshots.md) — iOS snapshot vs macOS
  manual capture, required sizes, and the screenshots skill handoff.
- [references/fastlane-setup.md](references/fastlane-setup.md) — install,
  `deliver` setup, multi-app lanes, and upload commands.
- [scripts/scaffold_metadata.py](scripts/scaffold_metadata.py) — create the
  per-locale file tree (non-destructive).
- [scripts/validate_metadata.py](scripts/validate_metadata.py) — validate
  against Apple's limits and required fields.

(The hub→repo sync + the `deliver` upload now live in the `app-store-deliver` skill.)
