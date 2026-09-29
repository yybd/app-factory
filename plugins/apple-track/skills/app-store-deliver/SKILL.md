---
name: app-store-deliver
description: >-
  Send an App Store listing to App Store Connect: sync the text and media into the app
  repo, verify against what is already live, then upload metadata, screenshots, App
  Preview videos, review information and in-app purchase content over the ASC API. Use
  when the user wants the listing pushed, says "upload the metadata", "send the
  listing", "deliver to App Store Connect" ("תעלה את הליסטינג"), or after listing text
  or media changed. It pulls the live listing and refuses to overwrite work it cannot
  reproduce. It does NOT author the copy (store-metadata-writer / app-store-metadata),
  does NOT capture media (appstore-media), and does NOT build or upload the binary
  (ship-apple-app).
---

# App Store Deliver — the single send-surface (ASC API)

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

This skill is the **one place** that uploads to App Store Connect. Everything it
sends is **already authored** in the hub source of truth (`<slug>/store/apple/…`
+ `media/apple/`) by `store-metadata-writer` and its workers — this skill does not
write copy, it **syncs it down, verifies it, and delivers it** via the official
App Store Connect API. Listing fields, screenshots, release notes, and **in-app
purchases** all go up from here, together and consistently.

This is the **SEND phase**, cleanly separated from authoring:

```
authoring (→ hub):  store-metadata-writer → app-store-metadata · aso-keywords · appstore-media
                    write <slug>/store/apple/ + media/apple/   [no upload]
                              │
SEND (this skill):  app-store-deliver
                    sync_from_hub → verify (blocks if incomplete) → ASC API upload:
                    metadata + screenshots + IAP (localizations + price + review screenshot)
```

## Prerequisites

- **Tools:** `fastlane` (`gem install fastlane`) for `deliver`; `ruby` with the
  `spaceship` gem (ships with fastlane) for the helper scripts; `rsync` (system).
- **Credentials:** an App Store Connect API key, from the track's resolver
  (`shared/credentials.rb` — see *Auth* below). Never Apple-ID/session auth.
- **Hub (`$APP_HUB`):** optional — with one, the listing is authored there and synced
  down; without one, the repo's own `fastlane/` IS the source of truth and nothing is
  copied. Every script here works in both modes; pass `--repo DIR` (or run from the
  repo) to name it explicitly.
- **Other tracks:** `copy-edit` (shared-track) runs as the parity gate inside the sync;
  `store-metadata-writer` (shared-track) is where a missing field gets fixed.

## Two ways it runs
- **Standalone** — a **metadata-only / IAP-only push**: fix a description, swap a
  screenshot, update keywords, or update a Pro product — no new binary. This is the
  common case.
- **From `ship-apple-app`** — during a full release, ship triggers this skill for
  the metadata/screenshots/IAP upload portion, then handles binary + submit itself.
  This skill is **not** merged into ship — ship orchestrates, this transports.

## Auth — the track's resolver
Use the **App Store Connect API key** (token-based, official). `shared/credentials.rb`
finds the `.p8` path + Issuer ID + Key ID, asking in one order: the environment
(`$ASC_KEY_ID` / `$ASC_ISSUER_ID` / `$ASC_KEY_PATH`), then
`$KEYS_ROOT/credentials.json`, then a studio hub's `DATA.md` for an installation that
predates the JSON. Don't ask the user for them; don't use Apple-ID/session auth.

## Workflow

### 1. Sync from the hub, and verify
Pull the authored content down and confirm it's complete before any upload:
```bash
${CLAUDE_PLUGIN_ROOT}/skills/app-store-deliver/scripts/sync_from_hub.sh <slug> <version> <app-repo> \
    [--locales en-US,he,…] [--screenshot-fallback en-US] [--platform ios|osx]
```

**Per-platform field overrides (universal apps).** A universal app is ONE App
Store record with BOTH an iOS and a macOS version (same bundle id), so most
listing text is shared — but a few fields read better differently per platform
(classically the **promotional text**: the Mac listing announces "Now on iPhone
and iPad", while the iOS listing should cross-promote "Also on Mac — one
Universal Purchase"). Author the platform-specific value in the hub as
`<field>.<platform>.txt` next to the canonical `<field>.txt`, e.g.
`store/apple/metadata/en-US/promotional_text.ios.txt`. Then sync **once per
platform** and deliver that platform before syncing the next:
```bash
sync_from_hub.sh <slug> <ver> <repo> --platform osx   # canonical text (.ios.txt/.osx.txt resolved/ignored)
fastlane … platform:osx …                              # deliver macOS
sync_from_hub.sh <slug> <ver> <repo> --platform ios   # overlays *.ios.txt onto the shared fields
fastlane … platform:ios …                              # deliver iOS
```
`--platform ios` overlays every `<field>.ios.txt` onto `<field>.txt` (and ignores
`.osx.txt`), and vice versa. WITHOUT `--platform`, all `*.ios.txt`/`*.osx.txt`
are excluded and you get the clean canonical set. The override is just text in the
hub — promo text is editable on a live version without resubmission, so an
iOS-only promo can also be pushed standalone via the ASC API
(`appStoreVersionLocalizations` PATCH `promotionalText`) without re-running deliver.

Screenshots are **per-locale on the App Store** (Apple doesn't share them across
locales). A locale can have authored text but no media of its own — the sync then
**warns** it would ship no screenshots. `--screenshot-fallback <loc>` reuses that
locale's stills+video for any locale lacking its own (e.g. `en-GB` reusing the
English `en-US` capture).
It mirrors `<slug>/store/apple/metadata/` → `fastlane/metadata/`, drops the
version's release notes into each locale's `release_notes.txt`, flattens the
canonical media tree (`media/apple/<App>/<locale>/{screenshots,app-preview}/`,
owned by `appstore-media`) into `fastlane/screenshots/<locale>/` — the flat layout
`deliver` requires, stills and the App Preview video together — and **verifies
every required field is present per locale**. If
anything is missing it **reports the exact locale + field, points to
`store-metadata-writer` to fill the hub, and exits non-zero — do NOT upload.**
Re-run after the hub is filled. (The repo `fastlane/` is a disposable artifact;
the hub is the truth.)

**It also runs the copy gate.** Completeness is not correctness: a locale can have
every required field and still ship a translation that lost a claim, gained one, or
was never translated — and in a language nobody here reads, that comparison is the
only thing that would notice. After the field check the sync runs
`copy-edit`'s `measure_copy.py --parity-only --fail-on-parity` over the synced
metadata and **exits non-zero** on a mismatch, naming the locale and the field.
Fix it in the hub and re-sync, or — when the difference is deliberate — re-run with
`--skip-copy-check`. Do not pass that flag to get past a finding you haven't read.



### `fastlane/` is a build directory, and this sync is its only writer

**The repo's `fastlane/` is not the source of truth and must never be treated as
one.** It is the staged, flattened, platform-filtered view that `deliver` requires,
rebuilt from the hub on every run:

```
    hub  (source of truth, in git)        staged  (derived, NOT in git)      Apple
    <slug>/store/apple/metadata/   ──┐
    <slug>/store/apple/release-notes/ ├──▶  <app-repo>/fastlane/  ──▶  deliver
    <slug>/media/apple/<App>/<loc>/ ─┘        metadata/<loc>/            ASC API
                                              screenshots/<loc>/
```

The staging step is unavoidable — the hub stores media per app and locale
(`media/apple/<App>/<loc>/screenshots/`) while `deliver` needs one flat folder per
locale, release notes have to be materialized into each locale's
`release_notes.txt` from `release-notes/<version>/`, and the platform filter runs
by pixel size. But its output is a build artifact, exactly like `target/` or
`dist/`, and the same rules apply: don't edit it, don't author into it, don't
commit it.

It runs `rsync -a --delete`, so anything authored there by another tool is
destroyed on the next run without being reported. A tool that writes listing text
writes into the hub; a repo whose listing is authored locally has no hub entry,
and the two modes are exclusive. Captures belong in the canonical media tree, not
in `fastlane/screenshots*/`, which is only that tree flattened for `deliver`.

Content sitting in the repo that the hub does not have is **un-back-ported work,
not garbage**: it goes back through `store-metadata-writer` (and `appstore-media`
for captures) first. The sync enforces this before it deletes anything — a file
the hub cannot reproduce **stops** the run and names it, a field that exists in
both and differs is reported as a warning with the hub winning. Release notes are
checked against the **version being synced**: an earlier release's notes do not
make this release's reproducible. `--discard-repo-extras` deletes the repo-only
files anyway; use it when you have read what it names, not to get past the stop.

**`fastlane/` has two writers, and this one is not the only one.**
`play-store-deliver`'s sync stages the Play listing into `fastlane/metadata/android/`
— a subtree of ours, because that is the path `supply` reads by default, exactly as
`fastlane/metadata/` and `fastlane/screenshots/` are the paths `deliver` reads. This
sync owns the per-locale folders and the screenshots; it treats `metadata/android/`
as none of its business — protected from `--delete`, skipped by the guard above, not
counted as a locale, not fed to the copy gate. When that subtree is present the sync
says so by name, so its files are never mistaken for un-back-ported work. Shipping to
both stores in one session, in either order, is safe and needs no flag.

### Untrack it — and say so when it is still tracked

**Committing `fastlane/` is a defect, not a preference**, once the hub reproduces
it. It makes the repo a second copy of a listing the hub owns, and the copy is the
one that goes stale. Three failures seen in practice, all in one repo:

- Screenshot sets from an old release (`screenshots-ios/`, `screenshots-mac/`) left
  behind after the flat `screenshots/` layout replaced them, still committed,
  still showing a UI and a **pre-rename app name** two years out of date, read by
  nothing.
- A `--platform ios` sync — which correctly filters the Mac stills by pixel size —
  showing up in `git status` as *"the Mac screenshots were deleted"*. It takes a
  hub comparison to tell a scope filter from a real deletion.
- A `git diff` full of binary screenshot churn on every release, burying the one
  text change that mattered.

So the end state is: the files live on disk, the sync rewrites them, and git does
not track them.

```gitignore
# Staged App Store listing, rebuilt by app-store-deliver's sync_from_hub.sh.
# NOT the source of truth — that is the app's hub entry.
fastlane/
```

**The sync checks this itself and reports.** After a clean run — clean meaning the
hub reproduced every field, so nothing would be lost — it looks at whether the repo
still tracks `fastlane/` and prints the `git rm -r --cached` + `.gitignore` fix.
Offer it to the user; don't apply it silently, and never apply it while the run
reported missing fields or repo-only files. A repo whose listing is authored
locally (no hub entry) is the exclusive other mode — there `fastlane/` **is** the
source of truth and must stay in git. The check knows the difference because it
only runs after a successful hub sync.

Two things go with it, when they apply: delete sibling `screenshots-*` folders the
sync does not write (nothing reads them), and leave `Fastfile` / `Appfile` /
`Deliverfile` tracked if they exist — those are real repo config, not staged
output, and a repo that has none is pure build directory.

### 1a. MANDATORY — pull the live listing and diff it before uploading
**Never deliver without running this, in either mode.** What you hold locally is the
source of truth only if nobody edited the listing on the App Store Connect website
since the last deliver — and they do. A blind deliver silently reverts those edits.
```bash
LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 RUBYOPT=-EUTF-8 \
  ${CLAUDE_PLUGIN_ROOT}/skills/app-store-deliver/scripts/pull_and_diff.rb <slug> <bundle-id> <version> \
      [--platform IOS|MAC_OS] [--hub DIR | --repo DIR]
```
It compares the store against the hub when there is one, and against the app repo's
own `fastlane/` when there is not — it says which, in its first line. The hub is found
by `$APP_HUB`; the repo by `--repo`, `$APP_REPO`, or a `fastlane/` in the working
directory.

**Pass the version that is LIVE, not the one being prepared.** The guard reads a
version record off ASC, and a new release has none until the `deliver` below
creates it — asking for it fails outright with `version <x> not found`, which
reads like the guard is inapplicable and invites skipping it. It is not
inapplicable: the question this step asks is whether anyone edited the listing on
the website since the last deliver, and the record those edits landed on is the
live one. Diff that, then deliver the new version.
Exit 0 = the hub matches the store, proceed. Exit 2 = fields differ; it prints
store-vs-hub for each. Classification:
- `hub adds` — the store field is empty (e.g. `whatsNew` on a first version).
  Safe: delivering only adds content.
- `CONFLICT` — both sides have content and they disagree. **Stop.** The store is
  often *ahead*. Show the user each conflict, and **back-port whatever they want
  to keep INTO the hub** (`store-metadata-writer` owns the authoring) before
  delivering. Do not overwrite website edits just because the hub is "the SoT".
- `ORPHAN` — an asset is on the store and **not in the hub**. This is the
  dangerous one, and it is easy to read as harmless. The deliver below runs
  `overwrite_screenshots: true` and `overwrite_preview_videos: true`, so a run
  **deletes that asset from the live listing** — the hub does not merely fail to
  add it, it replaces the set. Back-port it (`appstore-media` owns capture) before
  delivering, or accept the deletion deliberately. Play's counterpart is
  `MISSING IN HUB`, same meaning, different word.
- `STALE` — the same asset exists on both sides at different byte sizes. **Rule
  this out before believing it: Apple re-encodes every PNG it serves, so a set
  that is pixel-perfect still reports STALE on every file.** On one release it
  fired on 18 files and all 18 were false — every live asset was identical.
  Only once re-encoding is excluded does it mean what it says: a recapture that
  never reached the store, or the store still serving the old file. The check that
  actually decides is a PIXEL comparison — download each live asset through
  `appScreenshots.imageAsset.templateUrl` (substituting `{w}` `{h}` `{f}`) and
  compare `sha1(Image.open(f).convert('RGB').tobytes())` against the hub file.
  Byte size matches nothing. Play's `pull_and_diff.sh` hashes content and has no
  such problem.

It also prints the version's `appStoreState`. If it is `WAITING_FOR_REVIEW`,
`IN_REVIEW` or `PENDING_APPLE_RELEASE`, **metadata is frozen** — uploading means
pulling the submission out of review and losing its queue position. Never do that
without explicit confirmation; say so plainly and let the user decide.

### 2. Deliver the listing metadata + screenshots (official ASC API)
Upload with `deliver` authenticated by the **API key** (official ASC API under the
hood). For a **Mac app, `platform: "osx"` is required** (default is ios):
```ruby
deliver(
  api_key: app_store_connect_api_key(key_id: "…", issuer_id: "…", key_filepath: "…"),  # AppleCredentials.asc_key
  platform: "osx",                       # REQUIRED for Mac apps
  app_identifier: "<bundle id>",
  force: true,                           # skip the HTML preview
  skip_binary_upload: true,              # metadata-only push
  overwrite_screenshots: true,
  overwrite_preview_videos: true,
  run_precheck_before_submit: false,     # not submitting here
  submit_for_review: false,
  precheck_include_in_app_purchases: false
)
```
**Run it under a UTF-8 locale — the same prefix as the guard above, and for the
same reason.** With `LANG`/`LC_ALL` unset, which is the normal state of a
non-interactive shell, Ruby opens the metadata files as US-ASCII and `deliver`
dies on the first byte that is not ASCII: `invalid byte sequence in US-ASCII`,
raised from `updating_localized_app_info?`. A single `⌘` in the release notes was
enough on one release; Hebrew or an em dash in any field is a certainty. Two
things make this worse than an ordinary failure:

- it happens **before** the upload, so nothing is half-delivered and the listing
  looks untouched — and
- **fastlane exits 0 anyway.** A caller that checks the exit code concludes the
  listing was delivered. Only reading the output shows the stack trace.

```bash
LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 RUBYOPT=-EUTF-8 fastlane deliver …
```

**Never pipe that output through `tail`.** `deliver` ends with fastlane's own
"a new version is available" banner, so the last lines of a *failed* run look
exactly like the last lines of a clean one — the crash, and the per-field
`Loading …` trace that proves the upload happened, are both above the cut.
Redirect to a log and grep it, then confirm against ASC.

**Push text and media in two passes** — more robust against the screenshot upload
flakiness (see Gotchas): first `skip_screenshots: true` (text lands cleanly), then
`skip_metadata: true` (media). After the media pass, verify on ASC and **dedup**
with `${CLAUDE_PLUGIN_ROOT}/skills/app-store-deliver/scripts/dedup_screenshots.rb`.

> **No `verify_only` for a metadata-only push** — it crashes when there's no binary
> (`Digest::MD5.hexdigest(nil)`). Instead validate field lengths yourself (name ≤30,
> subtitle ≤30, keywords ≤100, promo ≤170, description/notes ≤4000) and run the real
> upload (it correctly skips the binary).

**App Preview video:** `deliver` does **not** upload it (it processes only stills).
Upload it separately with `${CLAUDE_PLUGIN_ROOT}/skills/app-store-deliver/scripts/upload_app_preview.rb`
(`DESKTOP` preview type
for Mac) — the sync already places the video in `fastlane/screenshots/<locale>/`.

### 3. Deliver the App Review content (contact, notes, and the ATTACHMENT)
What App Review reads before it opens the app. `deliver` pushes the contact and
notes fields, but it **cannot upload the attachment** — there is no Spaceship model
for it — so a demo video recorded for a reviewer has no route to ASC without:
```bash
ruby ${CLAUDE_PLUGIN_ROOT}/skills/app-store-deliver/scripts/upload_review_content.rb \
    <bundle-id> <version> --slug <slug> --platform MAC_OS   # --dry-run first
```
It reads the contact/demo/notes fields from
`<slug>/store/apple/metadata/review_information/` and attaches the first
`<slug>/media/apple/review/*.{mp4,mov,pdf}` (or `--attachment PATH`), then polls
delivery to `COMPLETE`. `--force` replaces an attachment already there;
`--no-attachment` pushes text only. It refuses to write while the version is
`WAITING_FOR_REVIEW` / `IN_REVIEW` / `PENDING_APPLE_RELEASE`.

**When an attachment earns its place:** a feature the reviewer cannot reach
(credentials they lack, hardware/OS they don't have) — or a setup flow unusual
enough to invite a rejection, which is what a sandboxed app that installs a helper
script and then asks for Automation looks like. Thirty seconds of screen recording
answers the question the review notes can only assert. Protect anything secret in
frame; a recording is full-screen because the permission dialogs are system windows
outside the app, so crop the terminal and Dock out afterwards.

### 4. Deliver the in-app purchases (Pro / IAP)
`deliver` does **not** manage IAPs, and there is **no ConnectAPI IAP model** —
`provision_iap.rb` (below) drives the raw ASC endpoints with the token client.
The IAP content is **authored by `app-store-metadata`** into the hub (this skill
only reads + uploads it). For each product under `<slug>/store/apple/iap/<product-id>/`:
create-or-find the product, set the per-locale **display name + description**, the
**review note**, the **price** / cleared-for-sale, and the **required reviewer
screenshot** — but **read the IAP's relationships first**: price and screenshot are
often already set in ASC, so skip what's done. Setting localization + review note +
price + screenshot flips state to `READY_TO_SUBMIT`; it ships **attached to the next
app-version submission** (don't submit it standalone). The full endpoint map, the
working recipe, and the hub layout are in
[references/iap-and-asc-api.md](references/iap-and-asc-api.md). Skip this step if the
app has no IAP (the README/profile `Pro:` line tells you).

**One script does the whole product** — create-or-find, every locale, review note,
price, availability, reviewer screenshot — and reports "already set" per step:
```bash
ruby ${CLAUDE_PLUGIN_ROOT}/skills/app-store-deliver/scripts/provision_iap.rb \
    <slug> <product-id> <bundle-id>            # --dry-run first
```
It owns the whole lifecycle in one idempotent pass — **create → localizations (every
locale dir in the hub) → review note → price → availability → reviewer screenshot** —
and reports "already set" per step instead of rewriting, so it is safe to re-run
after a partial failure. `--mirror-from <other-product-id>` copies a sibling
product's territory set rather than every territory Apple lists; `--territory`,
`--type`, `--no-price`, `--no-screenshot`, `--locales` narrow it. Price comes from
the hub `price.txt` (first `NN.NN` found), matched against the product's own price
points — price-point ids are per-product, so a sibling's id is not reusable.

Setting localizations + review note + price + screenshot flips the state to
`READY_TO_SUBMIT`.

### 5. Hand off the website-only leftovers
Tell the user what the API can't set: age-rating questionnaire, pricing &
availability display, the App Privacy nutrition label, export compliance, and
creating the app record if missing — then submit is `ship-apple-app`'s job.

## Gotchas (hard-won, verified against fastlane 2.234)
- **Mac needs `platform: "osx"`** — deliver defaults to ios; without this it targets
  the wrong (or no) version.
- **A universal app must deliver its screenshots per platform.** One bundle id on
  macOS + iOS means one media folder holding `mac_*`, `iphone_*` and `ipad_*` side by
  side, while `deliver` uploads one platform per run from one flat folder — so the
  unfiltered set offers Mac stills to the iOS listing, where they are not a valid
  size. `sync_from_hub.sh --platform ios|osx` now keeps only that platform's stills,
  discriminating by **pixel size** (the Mac App Store accepts exactly 1280×800,
  1440×900, 2560×1600 and 2880×1800; everything else is iOS) rather than by filename,
  which no skill guarantees. It reports what it held back. Run the sync + deliver once
  per platform.
- **The asset-delivery poll returns transient `500`s.** After a reserve→upload→commit
  the commit lands and the *poll* blows up, which reads as a failed upload and is not
  one — seen on an IAP screenshot that was in fact `COMPLETE`. The upload scripts now
  retry the poll instead of aborting; check the resource's `assetDeliveryState` before
  believing any upload error raised after the bytes went up.
- **Screenshot upload is flaky** — the ASC API can return `500` on deliver's
  post-upload verification, which triggers retries that leave **duplicate
  screenshots** in a set. Always verify the set after a media push and run
  `${CLAUDE_PLUGIN_ROOT}/skills/app-store-deliver/scripts/dedup_screenshots.rb`
  (keeps one of each fileName, reorders).
- **`verify_only` crashes** with no binary (`Digest::MD5.hexdigest(nil)`). Don't use
  it for metadata-only; validate lengths + run the real upload (it skips the binary).
- **App Preview videos are NOT uploaded by deliver** — it silently processes only
  stills. Use `${CLAUDE_PLUGIN_ROOT}/skills/app-store-deliver/scripts/upload_app_preview.rb`
  (reserve→upload→commit + poll).
- **deliver never removes locales** — a locale present in ASC but absent from the hub
  (e.g. a stale one from a rename) **persists** and would ship its old copy. To drop
  it, delete the `appStoreVersionLocalization` (and the `appInfoLocalization` for the
  name/subtitle) via the API. Mirroring the hub does not clean it up.
- **The app NAME/subtitle live on the editable `appInfo`** (not the version). A live
  version keeps showing its approved name; check the `PREPARE_FOR_SUBMISSION` appInfo,
  not `appInfos.first`.
- **IAP single resource is `v2/inAppPurchases/{id}`**; sub-resources only resolve via
  the resource's `relationships.*.links.related` URLs. See the IAP reference.

## Two modes: with a hub, and without one

**With a hub** (a studio with more than one app): the listing text and media are authored
once in `$APP_HUB/<slug>/`, and the sync mirrors them into this repo's `fastlane/` before
the upload. The hub is the source of truth and the repo's copy is disposable.

**Without one**: `fastlane/` IS the source of truth, you author there, and the sync copies
nothing. Pass `--standalone`, or simply have no `$APP_HUB` — an unreachable hub selects
this mode on its own and says so. The Ruby helpers read the same two modes through
`ASC.tree` and take `--repo DIR`; their standalone paths are `fastlane/metadata/<locale>/`,
`fastlane/metadata/review_information/`, `fastlane/review/*.{mp4,mov,pdf}`,
`fastlane/iap/<product-id>/<locale>/` and `fastlane/screenshots/<locale>/`.

**The verification runs either way**, and that is the half that matters: a missing
locale, an over-limit field or release notes for the wrong version stop the upload
before anything reaches the store. Only the copying is conditional.

## Boundaries
- **Outward-facing — confirm before every upload/submit.** Uploading is the user's
  call; show what will change and ask first.
- **Never author content here.** If a field is wrong or missing, fix it in the hub
  (`store-metadata-writer`) and re-sync — don't hand-edit `fastlane/` or invent copy.
- Standalone (no hub) apps author + deliver in the repo's own `fastlane/` directly;
  this skill's hub-sync step is then a no-op — but **1a is not**: the live diff runs in
  both modes, because the website can be edited whichever way the text is authored.

## Reference files
- [scripts/pull_and_diff.rb](scripts/pull_and_diff.rb) — **mandatory pre-upload guard**:
  pulls the live ASC listing, reports `appStoreState`, and diffs every field against
  the hub (`hub adds` = safe, `CONFLICT` = stop and back-port). It also diffs the
  **media by byte size**: `STALE` = the store holds an older asset under an unchanged
  filename (the shape the App Preview gap took — `deliver` never uploads previews, so
  a recaptured clip can sit on disk while ASC serves the old one), `ORPHAN` = an asset
  on the store the hub cannot reproduce (a renamed scene leaves its predecessor
  behind), `NOT SENT` = a still the hub holds that never reached this locale. It
  cannot see an asset that is stale in the hub *and* the store — that needs a look at
  the asset itself.
- [references/iap-and-asc-api.md](references/iap-and-asc-api.md) — IAP upload via the
  raw ASC API (token client): the endpoint map, the per-locale localizations, review
  note, pricing + screenshot, the hub layout, and a working recipe.
- [scripts/sync_from_hub.sh](scripts/sync_from_hub.sh) — mirror the hub store tree +
  version release notes, flatten the canonical media tree (stills + App Preview video)
  into `fastlane/screenshots/<locale>/`, and verify completeness.
- [scripts/asc_common.rb](scripts/asc_common.rb) — shared token auth (key from the
  track's resolver) + raw `get/post/patch/delete` client, and `ASC.tree`, which decides
  whether the listing comes from a hub or from the repo's own `fastlane/`.
- [scripts/upload_app_preview.rb](scripts/upload_app_preview.rb) — upload an App
  Preview video (deliver can't); `DESKTOP` for Mac, polls processing, sets poster frame.
- [scripts/dedup_screenshots.rb](scripts/dedup_screenshots.rb) — remove duplicate
  screenshots and fix ordering after a flaky deliver run (`--dry-run` to inspect).
- [scripts/upload_review_content.rb](scripts/upload_review_content.rb) — App Review
  Information: contact, demo account, notes, and the **attachment** (demo video/PDF)
  that `deliver` cannot upload.
- [scripts/provision_iap.rb](scripts/provision_iap.rb) — create-or-update an IAP end
  to end in every locale: create, localizations, review note, price, availability,
  reviewer screenshot. Idempotent — safe to re-run after a partial failure.

## Related skills
- `app-store-metadata` — **authors** the listing files into the hub (+ validates
  limits); this skill delivers them. (It no longer uploads.)
- `store-metadata-writer` — orchestrates the authoring (incl. IAP) into the hub.
- `aso-keywords` — the keyword field content (authored upstream).
- `ship-apple-app` — triggers this skill for the metadata/IAP upload during a full
  release; owns the binary + submit.
- `play-store-deliver` — the Google Play counterpart (`supply`).
