# The App Asset Library — creative assets and iPhone Duo over the ASC API

Read this before sending a product page **header**, a **search results** asset, or
**iPhone Duo** screenshots. `fastlane deliver` sends none of the three (fastlane
2.240 has no Asset Library support and no Duo display type), so they go through
[`scripts/upload_library_assets.rb`](../scripts/upload_library_assets.rb).

Apple's documentation — the source for everything below that is not marked *measured*:
- API: https://developer.apple.com/documentation/appstoreconnectapi/app-asset-library
  (rendered by JavaScript; the readable JSON is under
  `developer.apple.com/tutorials/data/documentation/appstoreconnectapi/<page>.json`)
- Help: https://developer.apple.com/help/app-store-connect/manage-app-information/manage-your-app-store-assets
- Sizes: `shared/apple-specs.json` → `creative_assets` and `iphone_duo`

Checked: 2026-10-14, including one read-only run against a live library.

## The model in four nouns

| Noun | What it is |
|---|---|
| **Library** | One per app: `GET /v1/apps/{id}/assetLibrary`. Every asset relates to it. |
| **Asset** | `appAssetLibraryImages` / `appAssetLibraryVideos`. Uploaded once, immutable after commit. Its **category** is fixed at reservation: `CREATIVE_ASSETS` (header, search, event art) or `APP_SCREENSHOTS_AND_PREVIEWS`. A wrong category cannot be fixed — upload again. |
| **Placement** | `appAssetLibraryPlacements`: one asset × one surface × a `placementType` × a `placementGroup`. Immutable — to change one, delete and recreate, then reorder. |
| **Reference data** | `GET /v1/appAssetLibraryRefData`: every spec, group, placement type and limit. **Read at runtime, never copied** — Apple adds devices to it without an API version change. |

Surfaces a placement can attach to: `appStoreVersionLocalization`,
`appCustomProductPageLocalization` (CPP), `appStoreVersionExperimentTreatmentLocalization`
(PPO), `appEventLocalization`.

## What the live reference data says (*measured* 2026-10-14)

- **Header and search results: one asset per localization each**, in a single group
  `DEFAULT_PROFILE` whose platform is `ANY` — the same asset serves iPhone and iPad.
  The same limit of 1 holds on version pages, CPPs and PPO treatments.
- **iPhone Duo: one group, `IPHONE_DUO_PROFILE`**, which accepts both displays (inner
  and outer, portrait and landscape) in one set of up to 10.
- **Group platforms are store names**, not version platforms: `IPHONE_APP_STORE`,
  `IPAD_APP_STORE`, `MAC_APP_STORE`, `ANY` … A filter that compares them to `IOS`
  matches nothing. (The script's first run planned zero placements for this reason.)
- **A range spec is a box.** The 3:2 search spec spans widths and heights, and a 21:9
  header at 3840 wide fits inside the box — so a spec must also be matched on its
  `aspectRatio` before trusting it. The exact specs are labelled with ratios rounded
  far past 1% (Duo inner is filed under a ratio it is not), so the ratio check applies
  to range specs only.
- The universal 16:9 spec (`5244×2950`, PNG) lists both `PRODUCT_PAGE_HEADER_ASSET` and
  `APP_STORE_SEARCH_RESULTS_ASSET` in `compatiblePlacementTypes`.
- The listing's existing screenshots already appear as placements on the version
  localization — the library holds what `deliver` uploaded through the old set API.

## The upload, in Apple's order

```
GET   /v1/apps/{id}/assetLibrary                    → library id (stable for the app's life)
GET   /v1/appAssetLibraryRefData                    → specs, groups, types, limits
POST  /v1/appAssetLibraryImages                     {fileName, fileSize, category, referenceName?}
                                                     + relationships.appAssetLibrary
PUT   <uploadOperations[].url>                      bytes[offset, length]; NO JWT on these URLs
PATCH /v1/appAssetLibraryImages/{id}                {uploaded: true}   ← nothing else; a checksum is rejected
GET   /v1/appAssetLibraryImages/{id}                poll: AWAITING_UPLOAD → UPLOAD_COMPLETE → PREPARE_FOR_SUBMISSION
POST  /v1/appAssetLibraryPlacements                 {placementType, placementGroup} + image|video + one surface
POST  /v1/appAssetLibraryPlacementOrderingRequests  order within one group (screenshots only)
```

Videos are the same with `appAssetLibraryVideos`, plus an optional
`previewFrameTimeCode`. The preview frame belongs to the video, not the placement —
changing it changes every placement — and it cannot be edited once the asset is approved.

**Never send `specId`.** Apple matches the file to a spec during processing and reports
it back. Compare it with the spec you meant: a file that matched a different spec is
accepted by different groups.

## Review: with a version, or on its own

Placements travel through App Review **with their parent** — submit the version (or
CPP, or PPO test) as usual and each placement follows it to `PARENT_APPROVED`.

An asset can also be **submitted on its own**, ahead of any version:
`POST /v1/reviewSubmissions` → `POST /v1/reviewSubmissionItems` with the
`appAssetLibraryImage` / `appAssetLibraryVideo` relationship (both are in Apple's
schema for review items) → `PATCH … {submitted: true}`. The help page: standalone
submissions "are reviewed against your app's latest version."

**That is the only road onto a live version.** A version that is already approved
accepts a placement only of an asset that is itself `APPROVED`. So for an app that is
already on the store:

1. `upload_library_assets.rb … --submit` — uploads, tries the placement (fails on the
   approved version, and says so), and sends the assets to review on their own.
2. After approval, run the **same command again** without `--submit`. It finds the
   asset by `referenceName` + byte size, uploads nothing, and places it.

For a version still in `PREPARE_FOR_SUBMISSION`, one run places the assets and they go
to review with the version.

## Gotchas

- **Delete in reverse order.** An asset that still has placements cannot be deleted
  (`STATE_ERROR.ASSET_HAS_PLACEMENTS`). Placements first, then the asset — the opposite
  of the old set API, where deleting a set took its screenshots with it.
- **Archive only what is approved.** `archived: true` on an asset still in
  `PREPARE_FOR_SUBMISSION` is a 409.
- **Placing on a frozen parent fails** — an approved CPP version, a version in review.
  The script refuses up front for a version that is `WAITING_FOR_REVIEW`, `IN_REVIEW`
  or `PENDING_APPLE_RELEASE`.
- **A running PPO test blocks placement on the version** (reported by a third party,
  not yet seen here). Stop the test or place on the treatment instead.
- **The set-based endpoints are deprecated** (`appScreenshotSets`, `appScreenshots`,
  `appPreviewSets`, `appPreviews` and their CPP / event counterparts). They still work
  and `deliver` still uses them. Nothing here migrates the existing listing — but when
  `deliver` stops working for screenshots, this script is the replacement already
  written, and `--kind screenshot` sends any still the reference data accepts.
- **Role:** Account Holder, Admin or App Manager for the API; Marketing can also use the
  website's Asset Library.
- **Shown on iOS / iPadOS 27 and later only.** Older systems keep the screenshot-led
  listing, so the creative assets add to it and never replace it.
