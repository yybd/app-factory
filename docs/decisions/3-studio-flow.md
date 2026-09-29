*English · [עברית](3-studio-flow.he.md)*

# 3 — the studio flow, as it was actually run

**A record, not instructions.** This is one studio's full launch sequence, written while
running it: every skill in order, what each draws from, and the rules that were learned
by getting them wrong. It assumes that studio's shape — a shared **hub** repo for
profiles and listing text, a separate **site** repo, and several apps — and it names
three skills that do not ship in this marketplace (`add-app-to-site`, `reference-page`,
the campaign work), because they live in the site repo where they belong.

**What to read instead**, if you are shipping an app: [`APP-LIFECYCLE.md`](../../APP-LIFECYCLE.md)
at the root, which is the same sequence with the hub optional and only the skills that
ship here. This file is what that one was distilled from, and it is kept because the
alternative that was ruled out is usually the expensive part to rediscover.

**Dated.** It describes the state when it was written; where it disagrees with today's
code, the code is right. (See [`docs/README.md`](../README.md) on what a decision record is.)

---

One map from source to "live everywhere": the binary, the stores (App Store + Google
Play), the website and the marketing. **The source of truth for all copy is
`<slug>/profile.md` in the hub** — no text is written before the profile exists, and no
skill invents; everything is derived from the profile. Above it, the repo's `README.md`
(maintained by `app-identity`) is the source of truth for **identity** (name + feature
list + Pro), and `app-profile` draws from it. The stores' **multilingual metadata** lives
in the hub under `<slug>/store/` (its SoT), and is synced into the repo's `fastlane/`
**only at deliver time** (with validation that blocks the upload if anything is missing).

The mechanics are global · the content is in the hub · the site is in the site repo.

---

## A. Where each skill lives — and what the tags mean

**Nothing is global.** The skills live in `$APP_FACTORY/plugins/`, installed as a
marketplace, and each track is enabled **per repo** — in that repo's own
`.claude/settings.json`, written by `factory/enable.py` or by grove's registry. A repo
that enabled nothing loads nothing. The exceptions are a site repo's own skills, which
are tied to its tree and never leave it.

Who decides what sits where, and why — [`1-shared-context-repos.md`](1-shared-context-repos.md):
the test is **how many trees one action spans**, not which repo it touches.

### The tags below are not "where the skill loads"

They stayed because they are still true — after changing meaning. They say **where the
session must stand**, which is not the same thing:

| | The session stands in… | And why there |
|---|---|---|
| `[G]` | **the app's repo** | the build, the simulator, the binary, and the git the commit lands in — none of them move |
| `[H]` | no particular place | the hub is **data**, written by path from anywhere. The skills that write to it are global |
| `[B]` | **the site repo** | the site skills load only there |

**`[H]` is the only one emptied of locational meaning** — before the migration it said
"open a session in the hub", and today it says only "the output lands in the hub".

---

## B. The flow: from 0 to "live"

```
0a app-identity          repo [G]       ← README: name + features + Pro (identity SoT)
│
0b app-profile           hub  [H]       ← profile.md (drawn from the README). No media yet.
│
├─ 1  the binary         repo [G]   ┐  advance in parallel
├─ 2  privacy page       site [B]   ┘  = add-app-to-site · Phase A (no media)
│
3  media → hub           repo [G]       ← the media point (needs a build from 1)
│
4  copy → hub/store      hub  [H]       ← writes metadata to the hub (the SoT). Needs profile + media
│
5  deliver               repo [G]       ← ship invokes app-store-deliver: sync (validates! blocks) → ASC API
│
6  web presence          site [B]       = add-app-to-site · Phase B (tiers 2/3 need media)
│
7  marketing + tracking  hub  [H] / global [G]
```

> **`add-app-to-site` splits around the media (step 3):** Phase A (step 2 — the privacy
> page) runs **before** the media and **does not depend on it at all**; Phase B (step 6 —
> the site presence) runs **after** the media, and tiers 2/3 **require** `media/apple/`.
> Without media you can already do: the privacy page (Phase A) or a tier 1 card (icon plus
> a sentence, no screenshots).

**The numbered detail:**

0. **Identity + profile** —
   - **0a · `app-identity`** `[G]` — scans the code, decides the name with you (device
     display + store + subtitle), identifies the features and the Pro tier, and writes the
     repo's `README.md` (the identity SoT). Runs **first**.
   - **0b · `app-profile`** `[H]` — reads the app's code **and the README** and interviews
     you → writes `<slug>/profile.md` (the source of truth for all copy). No screenshots
     exist at this stage.
1. **The binary** — `[G]` — preparing the build in the app's repo:
   `apple-credentials` → `code-signing-provisioning` → `app-store-review-compliance` →
   `localization-i18n` → `app-icon-generator` → (`apple-hig-design-review`, optional) →
   build.
2. **The privacy page** — `[B]` — `add-app-to-site` **Phase A** (before the media — **no
   media needed**) produces the privacy URL. ⚠️ Required before submitting to the store.
3. **Store media** — `[G]` — `appstore-media` captures from the running app (reading the
   profile for screen order and captions) → `apple-app-store-screenshots` for individual
   adjustments. The output is written **to the hub**: `<slug>/media/apple/`.
4. **Store copy → hub** — `[H]` — `store-metadata-writer` reads the profile, the media and
   `DATA.md`, and drives the workers (`app-store-metadata` + `aso-keywords` +
   `play-store-metadata`) which write the multilingual metadata **to the hub**
   (`<slug>/store/{apple,play}/metadata/` — the SoT), including per-version release notes.
   They do **not** write to the repo's fastlane — that happens only at step 5.
5. **Deliver** — `[G]` — `ship-apple-app`: verifies everything is ready → build →
   **invokes `app-store-deliver`** (syncs from the hub including this version's release
   notes; **validates completeness — if data is missing it blocks and points at
   `store-metadata-writer`**; ASC API: metadata + screenshots + IAP) → uploads the binary →
   App Store Connect web steps → submit. (Alternative path: `notarize-and-distribute` for a
   direct DMG.)
6. **Web presence** — `[B]` — `add-app-to-site` **Phase B** (after the media): card / app
   page / product site + a store link. **Media gate:** tiers 2/3 need `media/apple/` (from
   3); if it is missing, run `appstore-media` first or drop to tier 1.
7. **Marketing + tracking** — `[H]`/`[G]` — campaigns and ads (in the hub) ·
   `app-store-reviews-responder` (global).

**Order and dependencies, briefly:** 0a (identity/README) then 0b (profile) — always first
· 1 and 2 in parallel after 0 · 3 needs a build (from 1) · 4 needs the profile (0) and the
media (3), and writes **to the hub** · 5 syncs from the hub (from 4), validates (blocks if
anything is missing), and requires 2 to be complete · 6 after 5 · 7 continuous.

---

## C. Each skill

For each: **what it does · draws from · invokes · depends on.** ("Invokes — none" = it
runs no other skill.)

### Step 0 — identity + profile

0. **app-identity** `[G]`
   - Does: scans the code, proposes and decides **with you** the name (device display, App
     Store, subtitle) with an ASO check, identifies the feature list and the Pro/IAP tier,
     updates the display name in the build settings, and writes the repo's `README.md`
     (identity block + feature list) — the identity SoT. Runs **first, before**
     `app-profile`.
   - Draws from: the app's code, the conversation with you, `aso-keywords`.
   - Invokes: relies on `aso-keywords` (does not run another skill directly).
   - Depends on: nothing — **the first step in the repo.**
1. **app-profile** `[H]`
   - Does: reads the app's code as a product analyst and interviews you, then writes
     `profile.md` (a factual dossier plus reusable "derived copy"). Also creates the
     `media/apple/` folder (icon only for now — it does **not** capture media).
   - Draws from: the app's code (read-only) + **`app-identity`'s `README.md`** (names and
     feature ranking) + the interview + the hub's `PRODUCT.md` (voice).
   - Invokes: none.
   - Depends on: `app-identity` (the README) — runs after it.

### Step 1 — the binary `[G]` (runs in the app's repo)

2. **apple-credentials** — the sole owner of certificates and credentials: creation,
   `.p12`, notary profile, App Store Connect API key. Depends on nothing; **every signing
   and upload skill draws from it.**
3. **code-signing-provisioning** — explains the signing model (cert · App ID · entitlements
   · profile), diagnoses the project and decodes errors. Depends on `apple-credentials`.
4. **app-store-review-compliance** — scans against Apple's review guidelines, ranks
   findings and fixes the safe ones (usage strings, privacy manifest, IAP, account
   deletion, a reviewer demo mode). Note: the demo mode here is **the reviewer's** — a
   different thing from `appstore-media`'s marketing demo mode.
5. **localization-i18n** — localisation **inside** the app (`.strings`/`.xcstrings`):
   hardcoded strings, language completeness, RTL. Not store text.
6. **app-icon-generator** — produces a full AppIcon set for every platform from one
   1024 px image (or generates a first icon).
7. **apple-hig-design-review** (optional) — a design and accessibility review against the
   HIG, with recommendations ranked by impact.

### Steps 2 + 6 — the website `[B]` (runs from the site repo)

8. **add-app-to-site**
   - Does: puts the app on the site in two phases around the media. **Phase A** (step 2,
     **before** the media): the privacy page → the privacy URL — **no media needed.**
     **Phase B** (step 6, **after** the media): card / app page / product site.
   - Draws from: the profile in the hub + (in Phase B) `media/apple/` (reads and copies —
     it does **not** move the original).
   - Depends on: `app-profile`. **Phase B media gate:** tiers 2/3 require `media/apple/`;
     if missing, run `appstore-media` first or drop to tier 1.

### Step 3 — media `[G]` (captures in the repo, writes to the hub)

9. **appstore-media** (also **the scriptwriter**)
   - Does: first writes `media-script.md` (strategy: strengths, distinctiveness,
     monetisation, efficiency, plus a storyboard for the shots and the video) into the
     media folder; then captures screenshots and an App Preview video from a UI-test demo
     flow that realises the storyboard, converts and validates against Apple's specs, and
     produces captions and an editing plan derived from the script.
   - Draws from: the app's build (needs Xcode) + **the profile** (screen order, hero,
     differentiators, monetisation, voice).
   - Invokes: `apple-app-store-screenshots` (to adjust a single image, as needed).
   - Depends on: the build (step 1) and the profile (step 0). Writes to
     `<slug>/media/apple/` in the hub.
   - **Owns the canonical media tree** (`<App>/<locale>/{screenshots,app-preview,iap,raw}/`)
     — defined once at the top of its `SKILL.md`; the metadata and deliver skills consume
     leaf paths from it and do not redefine it.
10. **apple-app-store-screenshots** — adapts one existing image to an exact pixel size
    (padding/blur/crop). The light path when a full capture is unnecessary.

### Step 4 — store copy `[H]` (written to the hub; fastlane is synced only at deliver)

11. **store-metadata-writer** — **the bridge / orchestrator**
    - Does: reads the profile and `DATA.md`, assembles a store-neutral copy block, maps it
      to App Store against Play fields (including the keywords/subtitle differences), and
      hands the file mechanics to the workers. Writes the metadata **to the hub** (the SoT),
      including per-version release notes. It does **not** sync and does **not** upload.
    - Draws from: the profile + `media/apple/` + `DATA.md` (contact details, copyright,
      URLs) + the hub's `PRODUCT.md` (voice).
    - Invokes: `app-store-metadata` + `aso-keywords` + `play-store-metadata`.
    - Depends on: `app-profile`; the privacy URL from `add-app-to-site` Phase A. (When the
      sync at step 5 reports missing data, you come back here to fill the hub.)
12. **app-store-metadata** (worker — **writes and validates only, no upload**) — the
    mechanics of the App Store listing files: scaffold, fill, validate limits **in the
    hub**, **and the IAP/Pro metadata** (`store/apple/iap/<product-id>/`: per-locale
    display name, description, price, review notes and a reviewer screenshot). **It does
    not upload** — that is `app-store-deliver`.
13. **aso-keywords** (worker) — optimises the indexed fields (name / subtitle / 100-char
    keywords) with no waste or duplication, across locales. Hands its file edits to
    `app-store-metadata`.
14. **play-store-metadata** (worker — **writes and validates only, no upload**) — the Play
    equivalent, writing and validating **in the hub** (changelogs per versionCode). ASO
    there works through the visible text; there is no keywords field.

### Step 4½ — Deliver `[G]` (the only shipping surface; runs in the repo, pulls from the hub)

14a. **app-store-deliver** — the only shipping surface to App Store Connect.
     **`pull_and_diff.rb` (mandatory: pulls the live listing and compares; a `CONFLICT`
     stops and back-ports into the hub)** then `sync_from_hub.sh` (hub → `fastlane/`,
     **validates completeness and blocks if anything is missing**) → uploads metadata,
     screenshots and **IAP** through the official ASC API. Runs on its own (a metadata/IAP
     push) or from inside `ship-apple-app`.
14b. **play-store-deliver** — the Play equivalent. **`pull_and_diff.sh` (mandatory:
     compares text and image sets by content hash; `MISSING IN HUB` means supply will
     delete live media)** then `sync_from_hub.sh` → `fastlane supply`.

> ⚠️ **A new version record in ASC does not inherit the promotional text.**
> `POST /v1/appStoreVersions` copies the description, keywords and support URLs from the
> previous version — and leaves `promotionalText` **empty in every locale**, with no
> warning. The listing looks complete in the console until you look at that field itself.
> After creating any version record, by hand or through the API, push
> `promotional_text.txt` from the hub again and verify every field comes back non-empty.
> Caught on a live app after the record already looked ready to submit.

> ⚠️ **In Play, `completed` on a track does not mean "submitted for review".** The API
> shows a release as `completed` even while it sits under **Changes not yet submitted for
> review** in the publishing overview, waiting for a click. No endpoint distinguishes the
> two, so after any `commit` through the API, open the publishing overview and confirm the
> change appears under **Changes in review** and not above it.
>
> Observed on a live app: production and 176 countries did enter review, while the open
> testing release of the same build stayed waiting to be submitted — two tracks, one
> build, two different states, and from the API both looked identical.

### Step 5 — shipping the binary `[G]` (runs in the app's repo)

15. **ship-apple-app** — the **final** step: verifies everything already exists (signing,
    compliance, metadata in the hub, screenshots, an app record) → build → **invokes
    `app-store-deliver` at upload time** → uploads the binary → the web steps → submit. **It
    produces no content.** If something is missing it **points at the owning skill** and
    re-verifies.
16. **notarize-and-distribute** (alternative path) — macOS outside the App Store: DMG →
    Developer ID signature → notarization → staple → Gatekeeper verification.

### Step 7 — marketing + tracking

17. **app-store-reviews-responder** `[G]` — pulls reviews from the public feed, summarises
    ratings and complaints, and drafts replies. Reading reviews needs no auth; posting a
    reply does.
18. **web-seo** `[H]` — reads how the sites are performing in search and on-site,
    **diagnoses what is actually broken**, and fixes the mechanical part. Its value is not
    running the script but distinguishing four faults that produce identical numbers: *not
    indexed* (nobody read it — changing the text is pointless) · *indexed with zero
    impressions* (reachable, competing for nothing) · *impressions without clicks* (the
    title and description are the whole advert) · *clicks without onward engagement* (they
    arrive and discover nothing further — a funnel problem, not a traffic problem). It reads
    coverage **per property rather than as an average**, because an average would report
    "38% indexed" and hide three entirely empty domains.
19. **reference-page** `[B]` — builds a **reference page**: a free, complete, maintained
    answer to a question the product's buyers already search for, on the product's own
    domain, written to be linked to. **It is the opposite of a product page:** a page that
    reads as an advert does not get cited, and being cited is the entire reason it exists.
    **The test before writing:** would the page be useful even if the product did not
    exist? If not, stop.
20. **campaigns/ + ads/** `[H]` — the marketing areas in the hub, derived from the same
    `profile.md` and in the same voice.

---

## D. The golden rules

1. **`app-identity` then `app-profile` — first.** The `README.md` (identity: name +
   features + Pro) is written in the repo and feeds the profile; no copy before the profile
   exists in the hub.
2. **Never invent.** Every field traces back to the profile or to an explicit answer.
   Missing? Update the profile first, then derive again.
3. **The privacy page before submitting to the store.** `add-app-to-site` Phase A produces
   the privacy URL the store demands — **it runs early, with no dependency on the media.**
4. **The media is born at step 3** (`appstore-media`, in the app's repo) and is written to
   the hub (which stores and consumes, and does not capture). **Phase B of
   `add-app-to-site` depends on it** — before the media you can do only the privacy page or
   a tier 1 card.
5. **Each environment and its skills:** profile / store copy / marketing → from the
   **hub** · the website → from the **site repo** · binary / capture / workers → from the
   **app's repo**.
6. **Voice in two layers:** the hub's `PRODUCT.md` is the product voice (the master,
   default everywhere). The site's `PRODUCT.md` inherits from it and overrides only
   site-specific presentation.

   **6a. The standard and its enforcement are two files.** `PRODUCT.md` is the standard;
   `copy-edit` is the pass that applies it to existing text, **in every language**. Every
   skill that writes customer-facing text runs it before delivery. `measure_copy.py`
   measures each locale by its own rules (clause markers per language, characters rather
   than words for Japanese and Chinese) and compares every translation to the English claim
   by claim.

   **6b. The copy gate blocks shipping.** Both deliver skills' `sync_from_hub.sh` runs the
   check over the synced metadata and **exits non-zero** if a translation is missing,
   identical to the English (untranslated), or carries a different number of claims. Fix in
   the hub and sync again; if the difference is deliberate, `--skip-copy-check`. **In a
   language nobody here reads, that comparison is the only check that exists.**
7. **Metadata: the SoT is in the hub; uploading is done by a single deliver skill.** The
   multilingual metadata, screenshots, release notes (per version) and IAP live in
   `<slug>/store/`. The repo's `fastlane/` is derived and synced **only at deliver time**
   by `app-store-deliver` / `play-store-deliver`: `sync_from_hub` **validates completeness
   and blocks the upload if data is missing** — at which point you return to
   `store-metadata-writer` to fill the hub. The metadata skills write and validate only.

   **7a. "Pull and compare" before every push — a mandatory step.** The hub is the source
   of truth **only if nobody edited in the console since the last deliver** — and in
   practice people do. So after the sync and before any upload, run the guard that pulls the
   **live** listing and compares it to the hub.

   Three outcomes: `in sync` = continue · `hub adds` = the field is empty in the store and
   the deliver only adds — safe · **`CONFLICT` / `MISSING IN HUB` = stop.** In that case the
   store is usually **ahead** of the hub: show the user every conflict, and **back-port what
   they want to keep into the hub** before shipping. Do not overwrite edits made on the
   console merely because "the hub is the SoT".

   **The two dangers this step prevents — and each belongs to one store only.**

   - **Media deletion — in both stores, under two names.** The upload overwrites sets:
     `supply` in Play, and the overwrite flags in Apple's `deliver`. An asset that exists in
     the store and not in the hub **will be deleted from the live listing**. The guard
     reports it — as `MISSING IN HUB` in Play and as `ORPHAN` in Apple. **Different name,
     same state, same danger.**
   - **Frozen metadata — Apple only.** If the version is waiting for review, in review, or
     pending release, uploading requires pulling the submission out of the queue and losing
     its place, and therefore requires explicit approval. **Play has no equivalent** — its
     API exposes no review-status field at all, so there is no queue position to lose.

   **7b. Every surface has one writer.** The repo's `fastlane/` has a single writer:
   `sync_from_hub.sh`, at deliver time. Any other tool writing there is attaching content
   into a derived directory, and that content **will be deleted** on the next run — the sync
   uses `rsync -a --delete`.
   - **A tool that attaches listing text writes to the hub**, never to the repo's
     `fastlane/`.
   - **Screenshots and video** are written to the canonical media tree.
     `fastlane/screenshots*/` is a flattening of it into the format `deliver` requires, not
     a place to store captures.
   - **Content that is in `fastlane/` and not in the hub is neither rubbish nor a source of
     truth — it is work that was never returned.** Return it to the hub, run `copy-edit`
     over it, and only then sync. Delete only after a copy exists in the hub.
   - **`fastlane/` enters `.gitignore` only once that condition holds** — when everything in
     it can be restored from the hub. Until then, ignoring it removes the only copy from
     version control.
   - **The rule applies in the other direction too:** before the sync overwrites
     `fastlane/`, if there is a field there that the hub does not have — stop, exactly as
     with a `CONFLICT`. "The hub is the SoT" is not a licence to delete text written
     somewhere else. **The gate enforces this**: the sync compares what is already in the
     repo against the hub, **blocks** on a file the hub cannot restore, and warns about a
     field that exists in both and differs.
   - **Release notes per platform:** a universal app may need different wording for Mac and
     for iPhone. The archive supports `release-notes/<ver>/<locale>.<platform>.txt` beside
     `<locale>.txt`.

   And in the same spirit — **do not assume the store is empty.** A listing can be live on
   an internal or alpha track while the hub still thinks Play has not started, and a version
   can be submitted rather than in preparation. Check against the API, not against memory.
8. **`DATA.md` (at the hub root) = studio-wide data:** contact details (review info),
   copyright, default URLs, the path to the `.p8` (plus issuer and key id), and the
   **conversational language** (the language every skill talks to the user in). Draw from
   it; do not invent and do not ask.
   **The keys themselves are not there and never in any repo** — they are all under
   `$KEYS_ROOT`, which is not a git directory. `DATA.md` holds only **identifiers and
   paths**; the secret itself is read from `$KEYS_ROOT` at the moment of use.

> **IAP/Pro — covered by `app-store-deliver`:** IAP product metadata (per-locale display
> name, description, price and **a reviewer screenshot**) is uploaded through the official
> ASC API, written to the hub under `<slug>/store/apple/iap/<product-id>/` by
> `app-store-metadata` (orchestrated by `store-metadata-writer`), and `app-store-deliver`
> only syncs and uploads. **Google Play:** managed products and subscriptions are written to
> the hub by `play-store-metadata` and uploaded by `play-store-deliver` through the Play
> Developer API.

---

## Appendix — the site-building skills (a separate `[B]` flow)

These are not part of launching an app — they are for building web pages and sites
(including product sites):

1. **page-builder** — what, and in what order (section order, hero, CTA, i18n).
2. **frontend-design** — how it looks (typography, colour, momentum).
3. **web-design-guidelines** — what to check before delivery (accessibility, performance,
   UX).

---

*Which skill owns which topic, and the Apple/Android parity map: [`SKILLS.md`](../../SKILLS.md) at the
factory root. This file is documentation only.*
