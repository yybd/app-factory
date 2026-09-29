---
name: play-store-deliver
description: >-
  The single send-surface to Google Play — sync the app's Play listing metadata,
  graphics, changelogs, AND in-app products / subscriptions from the hub source of
  truth, verify completeness, and upload them (the listing via fastlane supply, the
  in-app products via the Google Play Developer API). Use this whenever the user wants
  to push / deliver / upload Google Play listing text or graphics, publish a
  metadata-only change to a Play listing, update a changelog, or create / update a Play
  in-app product or subscription ("תעלה לפליי", "עדכן את הליסטינג בפליי"). It does NOT
  author content (that's play-store-metadata / store-metadata-writer, which write into
  the hub) and it does NOT build the APK/AAB — this skill only TRANSPORTS
  already-authored hub content to Google Play. Run it standalone for a metadata-only
  push, or as the Play half of a cross-store release. Authenticates with the Google Play
  service-account JSON the track's resolver finds. The App Store counterpart is
  app-store-deliver.
---

# Play Store Deliver — the single Google Play send-surface (supply)

> **Conversational language:** talk to the user — questions, summaries, reports — in **the language the user writes in** — unless a `conversational language` is set in the hub `DATA.md` (`$APP_HUB/DATA.md`), which overrides it. This sets the *conversation* language only — content/deliverables follow the app's target locales.

The Google Play counterpart of `app-store-deliver`. Everything it sends is
**already authored** in the hub (`<slug>/store/play/…` + `media/play/`) by
`store-metadata-writer` / `play-store-metadata`. This skill **syncs it down,
verifies it, and delivers it** via `fastlane supply` (the Google Play Developer
API). It is the **one place** that uploads to Google Play.

This is the **SEND phase**, separate from authoring:

```
authoring (→ hub):  store-metadata-writer → play-store-metadata
                    write <slug>/store/play/ + media/play/   [no upload]
                              │
SEND (this skill):  play-store-deliver
                    sync_from_hub → verify (blocks if incomplete) → supply
```

## Two ways it runs
- **Standalone** — a metadata-only push (title / short / full description / graphics
  / changelog), no new AAB.
- **As the Play half of a release** — alongside the binary upload, which is
  `play-store-ship`'s job (build, sign, upload the AAB), not this skill's.

## Prerequisites

- **Tools:** `fastlane` (`gem install fastlane`) for `supply`; `python3` (stdlib) for
  the diff; `rsync` (system).
- **Credentials:** a Play service-account JSON with listing rights, from the track's
  resolver (`shared/credentials.py` — see *Auth* below).
- **Hub (`$APP_HUB`):** optional — with one, the listing is authored there and mirrored
  into `fastlane/metadata/android/`; without one, that tree IS the source of truth and
  nothing is copied. Both scripts work in both modes (`--repo DIR`).
- **Other tracks:** `store-metadata-writer` (shared-track) authors the text;
  `copy-edit` (shared-track) is the parity gate.

## Auth — the track's resolver
Use the **Google Play service-account JSON** that `shared/credentials.py` resolves —
`$PLAY_SERVICE_ACCOUNT`, then `$KEYS_ROOT/credentials.json`, then the folder
convention, then a studio hub's `DATA.md` for an installation that predates the JSON.
If none of them has it, that is the prerequisite — stop and ask the user to add it
(create a service account in Google Cloud, grant it in the Play Console, download the
JSON, record its path under `googleplay` in `$KEYS_ROOT/credentials.json`).

## Workflow

### 1. Sync from the hub, and verify
```bash
${CLAUDE_PLUGIN_ROOT}/skills/play-store-deliver/scripts/sync_from_hub.sh <slug> <versionCode> <app-repo> [--locales en-US,iw-IL,…]
```
Mirrors `<slug>/store/play/metadata/` → `fastlane/metadata/android/`, drops the
`changelogs/<versionCode>/<locale>.txt` into each locale's `changelogs/<versionCode>.txt`, mirrors `media/play/` graphics, and **verifies every
required field is present per locale** (`title` / `short_description` /
`full_description`). On a miss it **reports the exact locale + field, points to
`store-metadata-writer` to fill the hub, and exits non-zero — do NOT run `supply`.**

**It also runs the copy gate.** Completeness is not correctness: a locale can have
every required field and still ship a translation that lost a claim, gained one, or
was never translated — and in a language nobody here reads, that comparison is the
only thing that would notice. After the field check the sync runs `copy-edit`'s
`measure_copy.py --parity-only --fail-on-parity` over the synced metadata and
**exits non-zero** on a mismatch, naming the locale and the field. Fix it in the hub
and re-sync, or — when the difference is deliberate — re-run with
`--skip-copy-check`. Do not pass that flag to get past a finding you haven't read.


### `fastlane/metadata/android/` has one writer: this sync

It runs `rsync -a --delete`, so anything authored there by another tool is
destroyed on the next run without being reported. A tool that writes listing text
writes into the hub; a repo whose listing is authored locally has no hub entry,
and the two modes are exclusive. Captures belong in the canonical media tree, not
in `fastlane/screenshots*/`, which is only that tree flattened for `deliver`.

Content sitting in the repo that the hub does not have is **un-back-ported work,
not garbage**: it goes back through `store-metadata-writer` (and `play-store-media`
for graphics — `appstore-media` is Apple's and produces nothing Play accepts) first. The sync enforces this before it deletes anything — a file
the hub cannot reproduce **stops** the run and names it, a field that exists in
both and differs is reported as a warning with the hub winning. Changelogs are checked against the **versionCode being synced**: an
earlier release's changelog does not make this one's reproducible. `--discard-repo-extras` deletes the repo-only
files anyway; use it when you have read what it names, not to get past the stop.

**`fastlane/` has two writers, and this one is not the only one.**
`app-store-deliver`'s sync stages the App Store listing into `fastlane/metadata/<locale>/`
and `fastlane/screenshots/`, one level above this skill's `fastlane/metadata/android/`.
Our `--delete` is scoped to the android subtree and the script refuses to run if that
destination is ever widened — one level up would silently delete the entire App Store
listing on every run. Shipping to both stores in one session, in either order, is safe
and needs no flag.

Only once that holds is `fastlane/` safe to add to `.gitignore` — until then,
ignoring it takes the only copy of that text out of version control.

### 1a. MANDATORY — pull the live listing and diff it before uploading
**Never supply without running this, in either mode.** What you hold locally is the
source of truth only if nobody edited the listing in the Play Console since the last
supply — and they do. `supply` **overwrites the image sets it is given**, so a blind
run can wipe screenshots the owner uploaded by hand. The script compares Play against
the hub when there is one and against `fastlane/metadata/android/` when there is not,
and says which in its first line (`--hub DIR` / `--repo DIR` to be explicit).
```bash
LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
  ${CLAUDE_PLUGIN_ROOT}/skills/play-store-deliver/scripts/pull_and_diff.sh <slug> <package-name>
```
It downloads the live listing (`fastlane supply init` into a temp dir) and
compares text per locale plus every image set by **content hash** (`supply`
renames downloads to `<n>_<locale>.png`, so filenames prove nothing).

Exit 0 = the hub matches Play, proceed. Exit 2 = items differ. Classification:
- `hub adds` — the field is empty on Play. Safe.
- `CONFLICT` / `MISSING IN HUB` — Play has content the hub does not, or they
  disagree. **Stop.** Play is often *ahead*. Show the user, and **back-port what
  they want to keep INTO the hub** (`store-metadata-writer` owns the authoring)
  before supplying. `MISSING IN HUB` on an image set is the dangerous one: a
  supply run would delete those images from the live listing.

Also check the track state before assuming nothing is published — a listing can
already be live on `internal`/`alpha` while the hub still thinks Play is unstarted:
```bash
fastlane run google_play_track_version_codes package_name:<pkg> json_key:<key> track:internal
```

### 2. Deliver with supply
```bash
fastlane supply --json_key "$(python3 ${CLAUDE_PLUGIN_ROOT}/shared/credentials.py --path)" \
  --package_name <com.example.app> --skip_upload_apk true --skip_upload_aab true --validate_only true
```
Then the real run (drop `--validate_only`). Control graphics with
`--skip_upload_images` / `--skip_upload_screenshots`. Choose the track at upload.

### 3. Deliver in-app products / subscriptions (Play Developer API)
`supply` doesn't manage in-app products — deliver them via the **Google Play
Developer API** (AndroidPublisher v3), authenticated with the same service-account
key. The IAP content is **authored by `play-store-metadata`** into the hub (this
skill only reads + uploads). For each **one-time product** under
`<slug>/store/play/iap/<product-id>/`, run the script — `--dry-run` first:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/play-store-deliver/scripts/play_iap.py \
  --package <pkg> --dir $APP_HUB/<slug>/store/play/iap/<product-id> --dry-run
```

It converts the base price to every region (`convertRegionPrices`), upserts the
product (`monetization.onetimeproducts`), and activates its purchase option. The old
`inappproducts` resource answers **403 "Please migrate to the new publishing API"**
for every app — a retired endpoint, not a permissions problem. The script stops
before writing if the hub lacks a listing in the app's **default** listing language
(not necessarily en-US) or a price. **Subscriptions**
(`monetization.subscriptions`) are not scripted yet. The flow, the traps, and the
subscription notes are in [references/play-iap.md](references/play-iap.md). Skip if
the app has no Play in-app products.

### 4. Hand off the Play-Console-only leftovers
`supply` / the API can't do these — tell the user: the **Data safety** form,
**content rating (IARC)**, **pricing & countries**, app-content declarations,
creating the app entry, and any tax/compliance or subscription settings that
finalize only in the **Play Console**.

## Two modes: with a hub, and without one

**With a hub** (a studio with more than one app): the listing text and media are authored
once in `$APP_HUB/<slug>/`, and the sync mirrors them into this repo's `fastlane/metadata/android/` before
the upload. The hub is the source of truth and the repo's copy is disposable.

**Without one**: `fastlane/metadata/android/` IS the source of truth, you author there, and the sync copies
nothing. Pass `--standalone`, or simply have no `$APP_HUB` — an unreachable hub selects
this mode on its own and says so.

**The verification runs either way**, and that is the half that matters: a missing
locale, an over-limit field or release notes for the wrong version stop the upload
before anything reaches the store. Only the copying is conditional.

## Boundaries
- **Outward-facing — confirm before upload.** Don't author content here; fix it in
  the hub (`store-metadata-writer`) and re-sync.
- Standalone (no hub) Android-only apps author + deliver in the repo's own
  `fastlane/` directly; the hub-sync step is then a no-op.

## Reference files
- [scripts/pull_and_diff.sh](scripts/pull_and_diff.sh) — **mandatory pre-upload guard**:
  pulls the live Play listing and diffs text plus every image set by content hash
  (`hub adds` = safe, `CONFLICT`/`MISSING IN HUB` = stop; supply overwrites media).
- [scripts/sync_from_hub.sh](scripts/sync_from_hub.sh) — mirror the hub Play store
  tree + changelog + graphics into `fastlane/metadata/android/`, and verify.
- [scripts/play_iap.py](scripts/play_iap.py) — upsert + activate one Play one-time
  product from the hub (`monetization.onetimeproducts`); `--dry-run`, `--list`.
- [references/play-iap.md](references/play-iap.md) — deliver in-app products /
  subscriptions via the Play Developer API (AndroidPublisher v3): hub layout, the
  three-call flow, and its traps.

## Related skills
- `play-store-metadata` — **authors** the Play files into the hub (+ validates);
  this skill delivers them. (It no longer uploads.)
- `store-metadata-writer` — orchestrates the cross-store authoring into the hub.
- `app-store-deliver` — the App Store counterpart (ASC API).
