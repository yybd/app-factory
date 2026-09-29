---
name: appstore-media
description: >-
  Produce App Store screenshots and App Preview videos for iOS and macOS, from a
  scripted XCUITest demo flow that can be re-run every release. It is also the media
  SCRIPTWRITER: before any capture it writes the storyboard deciding which strengths
  each shot carries. Use when the user wants store screenshots, an app preview video, a
  demo recording, a media script or storyboard, simulator capture, fastlane snapshot
  setup, screenshot captions, an iMovie editing plan, or verification against Apple's
  required formats — including "I need screenshots for my app", "תכין צילומי מסך",
  "סרטון לאפסטור". Also for adding accessibility identifiers or a demo mode for capture.
  This skill CAPTURES from a running app. It does NOT upload, and does NOT author the
  listing text. To resize one image that already exists use
  `apple-app-store-screenshots`; `app-store-metadata` and `app-store-deliver` own the
  listing files.
---

# App Store Media Pipeline (iOS + macOS)

Produce professional, App Store-compliant screenshots and App Preview videos from a **single scripted demo flow** per app. The flow is an XCUITest that drives the app like a user; running it produces screenshots in every locale and a raw video, which scripts then convert and verify against Apple's exact specifications. The user finishes the job in iMovie (video text overlays) and a screenshot-framing tool, guided by a marketing-copy plan this skill generates.

**Language**: Write all conversation, summaries, explanations, and the working deliverables (`media-script.md`, the iMovie plan, the done-summary) in the **`conversational language`** set in the hub `DATA.md` (`$APP_HUB/DATA.md`) — fall back to the language the user writes in if it's unset. Write all code, scripts, and identifiers in English. **Distinct from the app's target locales:** the store *captions* are produced per the locales the app ships in (e.g. `he` + `en-US`), which is a separate choice — confirm which locales to produce.

## Prerequisites

- **Tools:** Xcode (`xcodebuild`, `xcrun simctl`, `xcresulttool` from Xcode 16+), macOS
  `screencapture` and `sips`, `swift` for `scripts/winframe.swift`; `ffmpeg` and
  `ffprobe` (`brew install ffmpeg`); `Pillow` with RAQM
  (`brew install libraqm && python3 -m pip install --upgrade pillow`) for
  `scripts/frameshot.py` RTL captions; `fastlane snapshot` only if already set up;
  ImageMagick's `magick` only as the suggested fix for 16-bit PNGs.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — studio flow reads `$APP_HUB/<slug>/profile.md` and
  captures into `$APP_HUB/<slug>/media/apple` via `-o`; standalone omits `-o` for a
  local folder (`scripts/capture_selfrender.sh` is a template that expects `$APP_HUB`).
- **Other tracks:** `app-profile`, `app-identity` (shared-track) are the sources of
  the screen story and captions; `store-metadata-writer` (shared-track) consumes the
  screenshots.

## Canonical media tree (one source of truth — every skill points here)

This skill **owns** the media-folder layout; `store-metadata-writer`,
`app-store-metadata`, and `app-store-deliver` consume leaf paths from it and must not
redefine it. Each app owns one media root per store in the hub: `<slug>/media/apple/`
(App Store) and `<slug>/media/play/` (Google Play). The Apple root:

```
<slug>/media/apple/
├─ media-script.md          # Phase-1 storyboard (blueprint for capture + copy)
├─ captions.md              # Phase-6 screenshot captions
├─ imovie-plan.md           # Phase-6 App Preview edit plan
├─ README.md                # generated: what's upload-ready vs raw
├─ icon-1024.png            # 1024² marketing icon (from app-profile)
├─ capture.sh · record_video.sh · demo-source.png   # capture helpers (optional)
└─ <App>/                   # <App> = the app's display name
   └─ <locale>/             # App Store Connect locale code: en-US, he, pt-BR …
      ├─ screenshots/        # ✅ upload-ready stills, exact device sizes
      ├─ app-preview/        # ✅ upload-ready App Preview video(s)
      ├─ iap/
      │  └─ review_screenshot.png   # pinned IAP reviewer screenshot (handed to app-store-metadata)
      └─ raw/                # intermediates — NOT for upload
```

Rules: scriptwriter deliverables + helpers live at the **apple root** (one app per
root); captured, per-locale media lives under `<App>/<locale>/…`. The capture scripts
create `<App>/<locale>/raw/`; Phase-5 conversion/organization produces `screenshots/`,
`app-preview/`, and `iap/`. `<locale>` is the store's locale code (Hebrew = `he` on
Apple, `iw-IL` on Play). One IAP reviewer screenshot covers all locales unless the
paywall is localized.

## The six phases

Work through these in order. Each phase has a reference file — read it when you reach that phase, not before.

```
Phase 0  Discover         → interview + inspect the Xcode project
Phase 1  Write the script → media-script.md: strategy + storyboard (stills + video)   (references/media-script.md)
Phase 2  Prepare the app  → demo mode, accessibility IDs, seeded data
Phase 3  Script the flow  → XCUITest demo flow executes the storyboard   (references/xcuitest-flow.md)
Phase 4  Capture          → capture_ios.sh / capture_mac.sh
Phase 5  Frame+verify     → frameshot.py, convert_preview.sh, verify_assets.py
Phase 6  Copy + editing   → captions & iMovie plan, from the script   (references/marketing-copy.md)
```

Apple's exact format requirements (resolutions, codecs, durations, content rules) live in `references/apple-specs.md`. Read it before Phase 4 and keep it in mind throughout — **capturing at the wrong size wastes an entire run**.

## Phase 0 — Discover

Before writing anything, build a picture of the app:

1. **Read the profile first (studio apps).** If this app has a studio profile at `$APP_HUB/<slug>/profile.md` (ask for the slug, or check the hub), read it — it is the source of truth and usually already holds what you'd otherwise interview for: the ranked feature list, the single hero feature, the honest differentiators, the target locales, and the house voice for captions. Lift the screen story and caption material from it and **confirm** with the user rather than asking cold. If there is no profile and this is a studio app, consider running `app-profile` first. For a standalone app, read the repo's `README.md` (written and owned by the `app-identity` skill) — its **ranked feature list** is the screen story and its identity block holds the names; lift the captions from there and **confirm**, falling back to interview only for what the README doesn't cover.
2. Inspect the project: find the `.xcodeproj`/`.xcworkspace`, list schemes (`xcodebuild -list`), determine platform(s) (iOS, macOS, or both), check whether a UI testing target already exists, and grep for existing `accessibilityIdentifier` usage and launch-argument handling.
3. Interview the user (in the `conversational language` from the hub `DATA.md`) for whatever the profile didn't already answer. You need:
   - **The story**: which 3–6 screens/features sell this app? What is the single strongest "hero" feature? Ask the user to rank them — the order becomes the screenshot order and the video storyline. *(If the profile already ranks features, lift that order and just confirm it — don't re-ask.)*
   - **Locales** to produce. Default to the app's own — the locales its listing
     already has, or the languages it ships strings for. Never assume a pair.
   - **Targets**: iOS screenshots? iOS App Preview? Mac screenshots? Mac App Preview? Marketing video for web/social too?
   - Whether the app has (or can have) a demo mode with attractive seeded data.

If neither the profile nor the user pins down the story, propose one yourself from the project inspection and let them edit it. Don't proceed to Phase 1 without an agreed screen list — everything downstream is built on it.

## Phase 1 — Write the media script (storyboard + strategy)

Before touching code, act as the app's **media scriptwriter**: turn the agreed
screen story into a written **storyboard** for both outputs, saved as
`media-script.md` in the media folder (`<slug>/media/apple/media-script.md` when
`-o` points at the hub, else the capture root). This file is the **blueprint** — the
XCUITest flow (Phase 3) executes its beats and the captions / iMovie plan (Phase 6)
are its polished derivatives. Read `references/media-script.md` for the template.

Decide and write down — **lifting from the profile/README, never inventing**:

1. **Strategy — how to sell this app.** The core strength(s) to lead with; the
   honest **uniqueness** vs the alternatives; the **monetization** story (free vs
   Pro — *show* the value of what Pro unlocks, don't bury it, but **never storyboard
   the paywall or any screen that renders a price**; see the hard rules); and the
   app's **efficiency / usefulness** (what makes it fast, effective, worth it). One
   short paragraph that sets the angle everything else follows.
2. **Screenshot storyboard** — the ordered shot list (hero first). Per shot: the
   screen/feature, the headline intent, what's on screen (the demo data to show),
   framing, and **which strength it sells**.
3. **Video script** — the App Preview as a scene-by-scene script: per scene the
   timing (seconds), what's shown, the on-screen text, pacing, and the narrative
   arc — a 15–30s story (hook → value → payoff). Real in-app footage only (see the
   hard rules).

Show the storyboard to the user and get agreement before Phase 2 — everything
downstream is built on it.

## Phase 2 — Prepare the app

Three small code changes make the difference between amateur and professional captures. Propose them as a concrete diff/PR for the user's app:

1. **Demo mode**: a `-DemoMode` launch argument that seeds realistic, attractive content (well-written sample documents, sensible dates, populated lists — never empty states or "test test 123"). Demo content must exist in every target locale; Hebrew demo content should be real, natural Hebrew. (This is a *marketing-capture* demo mode. It's distinct from the *App Review* demo path owned by the `app-store-review-compliance` skill — that one exists to let a reviewer past a login/paywall. One launch argument can serve both, but the goals differ; don't conflate them.)
2. **Accessibility identifiers** on every element the flow will touch (`.accessibilityIdentifier("newDocumentButton")`). Identifiers are language-independent, so one flow serves all locales.
3. **(Optional but recommended) `-CaptureMode`**: hides badges/timestamps that look stale, disables animations or first-run popovers, and on macOS sets a fixed window size.
4. **Bundle the demo source asset (sandboxed apps / macOS XCUITest).** A sandboxed app launched by XCUITest runs with an *isolated HOME*, so reading a demo image/file from an external path (e.g. `$DEV_ROOT/...` via `homeDirectoryForCurrentUser`) silently fails and you fall back to a placeholder. Load demo assets from `Bundle.main` and have the capture script copy the file into the built `.app/Contents/Resources` before launching. (An `open`-launched run may read the external path fine; the XCUITest-launched one won't — so bundle it.)
5. **macOS — in-app self-render capture (recommended; permission-free).** Add `-DemoScene <name>` / `-CaptureMode` / `-CaptureAll` / `-VideoSize` handling so that in capture mode the app sizes its own window and, for `-CaptureAll`, cycles every still scene in ONE launch — rendering its own window to a 2× PNG via `cacheDisplay` into the sandbox tmp (no Screen Recording, no Accessibility). The companion `capture.sh` flattens to RGB and lays the files out. See `references/macos-capture.md` for the snippet, the `capture.sh` contract, and the **hard-won gotchas**: don't wrap the SwiftUI `body` in a `ZStack` (breaks window creation — use `.overlay`); one launch for all scenes (per-scene relaunch is flaky); `${VAR}`+ASCII in shell strings (a multibyte char after `$VAR` → "unbound variable" under UTF-8); and staged manual capture + a privacy blur for interactive system sheets (Image Playground shows the user's face/name).

**macOS relaunch caveat:** `open --args` does NOT re-apply launch arguments to an already-running app — it just activates it, so a new `-DemoScene`/flag is ignored. Between scenes/runs, terminate first with `pkill -x <AppName>` then `open -n … --args …`. `osascript -e 'quit app "X"'` needs Automation permission and can silently fail — prefer `pkill`.

### Reviewer media (App Review, Guideline 2.1) — distinct from the marketing capture
For features a reviewer cannot exercise, prepare reviewer media *in addition* to the listing media:
- **IAP review screenshot (required):** App Store Connect requires a review screenshot for each in-app purchase. **This is the one place a price belongs** — the inverse of the listing rule above, and the two are easy to confuse: App Review needs to see the purchase point, customers must never see a hardcoded currency. Capture the paywall in-app; to show the real price, run under **StoreKit Testing** (scheme → Run → StoreKit Configuration = your `.storekit`).

  > **Shoot the purchase screen itself — not the limit it removes.** The tempting substitution is a frame showing what the free tier withholds (a `+N locked` badge, a greyed feature, a blurred row) on the reasoning that this is what the purchase changes. It is a listing shot, and it is the wrong asset here: a reviewer is approving a *product*, and needs to see the screen that sells it — its title, what it unlocks, the price, and the Buy/Restore buttons. A locked-state frame shows none of those. If the screenshot does not contain a price and a purchase control, it is not the right frame, however well it illustrates the feature. (Made this mistake; the developer caught it after upload.)

  If the paywall renders no price, that is StoreKit failing, not a reason to shoot something else. Two causes, both fixable: the scheme is missing its `StoreKitConfigurationFileReference` (check a sibling app's scheme — an auto-generated, unshared scheme never has one), or a demo mode that force-unlocks Pro is short-circuiting product loading for the paywall scene. Fix it and re-shoot; a paywall screenshot with a blank or errored price is worse than none. Because it carries a price, this is also the one asset a repricing invalidates — re-shoot it (one image) whenever the price changes. **Save it to the pinned path `<slug>/media/apple/<App>/<locale>/iap/review_screenshot.png`** — this is the handoff point: `app-store-metadata` copies it from here into the IAP listing's `store/apple/iap/<product-id>/review/screenshot.png` (it knows the product-id; this skill doesn't), and `app-store-deliver` uploads it. One screenshot covers all locales unless the paywall is localized.
- **Reviewer demonstration video (recommended):** for features gated behind credentials the reviewer lacks (e.g. an App Store Connect API key) or an OS/hardware requirement (Apple Intelligence, a specific macOS), record a private end-to-end demo video and attach it in App Store Connect → App Review Information → **Attachment**, with explanatory notes. Protect any secrets shown (use a dedicated/revocable key). This is a separate file from the public App Preview.
- The full App Review demo-account/notes strategy is owned by the `app-store-review-compliance` skill.

## Phase 3 — Script the demo flow

Read `references/xcuitest-flow.md` and write one `DemoFlowTests` XCUITest class for the app. Key principles (details in the reference):

- One flow serves both outputs: `snapshot()`/screenshot calls at each beat for stills, and human-paced execution (`humanPause`, slow typing) so the same run records well as video.
- Beats **implement the `media-script.md` storyboard** from Phase 1 (each storyboard shot/scene = a beat, in order).
- Locale is injected from outside (`xcodebuild -testLanguage`), never hardcoded.

Show the user the flow and a dry-run plan before capturing.

## Phase 4 — Capture

**macOS — strongly preferred: generate one `capture.sh` and offer it to the user to run in their terminal.**
Read `references/macos-capture.md`. Instead of driving the UI, the app renders its OWN
window to a PNG per demo scene, so **stills need no system permission** and a single launch
captures every scene; only the App Preview video needs Screen Recording. Author a tailored
`capture.sh` in the app's media folder and hand it to the user: `./capture.sh` (stills, no
perms) · `./capture.sh video` (App Preview). The script auto-captures what it can and
**prints exactly what to do for anything it can't** (grant Screen Recording; perform an
interactive Image Playground / share-sheet generation). This is the simplest, most reliable
macOS path — confirm it works once, and it regenerates everything next release in one command.

For iOS (simulator) and for the macOS video / window-region grab, use the bundled scripts —
don't improvise capture commands; they handle status-bar override, recording lifecycle, and output layout:

- `capture_ios.sh` — boots the right simulator, applies the clean 9:41 status bar, runs the test per locale, records video, extracts screenshot attachments from the `.xcresult`.
- `capture_mac.sh` — positions/sizes the app window, captures stills and video of just that window region. The window grab includes the title bar so it's almost never an accepted Mac size (e.g. 1440×952@2x = 2880×1904); the script auto-composes an upload-ready `<name>-2880x1800.png` (scale-to-fit + white pad, flattened to RGB — no alpha) when ffmpeg is present. It also `rm`s any prior `_raw.mov` before recording (`screencapture -v` won't overwrite, which would otherwise silently re-encode a stale take).

All the scripts named in this skill live in `${CLAUDE_PLUGIN_ROOT}/skills/appstore-media/scripts/`;
the commands below give the full path, because a session's working directory is the
project, never the skill.

Both scripts print usage with `-h`. Output lands under the `-o` root (default `./AppStoreMedia`) as `<root>/<AppName>/<locale>/raw/`.

**Studio apps — write straight into the hub.** Point `-o` at the app's hub media folder so capture lands in the source of truth the downstream skills read, with no separate "collect" step:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/appstore-media/scripts/capture_ios.sh \
  -s MyApp -p MyApp.xcodeproj -t MyAppUITests/DemoFlowTests \
  -l <the app's locales> -o $APP_HUB/<slug>/media/apple
```

The hub **stores and consumes** media; capture runs here in the app repo, because it needs the build. For a standalone app, omit `-o` and the default local folder is fine.

If `fastlane` is already set up in the project, prefer `fastlane snapshot` for the stills and use the script only for video.

## Phase 5 — Convert and verify

Raw captures are almost never at Apple's accepted sizes (e.g. a 6.9" simulator records at 1320×2868 but App Previews must be **886×1920**). Run:

- `convert_preview.sh` — scales/encodes video to the exact accepted resolution, 30fps, H.264 High@4.0, ~10–12 Mbps, with a valid stereo AAC track (App Store Connect rejects previews with missing/non-conformant audio). Also enforces the 15–30s window and warns if trimming is needed.
- `verify_assets.py` — checks every file in the output tree against the spec tables and prints a pass/fail report. Run this **before** telling the user the assets are ready.

Requires `ffmpeg` (`brew install ffmpeg`) — the scripts check and say so.

## Phase 6 — Marketing copy and the editing plan

Read `references/marketing-copy.md`, then produce two deliverables (in the conversational language) at the **apple media root** next to `media-script.md` (`<slug>/media/apple/captions.md` and `imovie-plan.md` when `-o` points at the hub — see the canonical media tree above, not under `<App>/`). **Both derive from the `media-script.md` storyboard (Phase 1)** — the captions realize the per-shot headline intent, and the iMovie plan realizes the video script's scenes/timing:

1. **`captions.md`** — for each screenshot, a recommended caption in every locale the app ships in (benefit-first, 3–6 words), with placement guidance. The captions are consumed by `frameshot.py`, which does the framing — do not hand the user settings for an external tool.
2. **`imovie-plan.md`** — a timestamped editing plan for the App Preview: which clip segment goes where, what on-screen text to add at which second, transition and pacing notes, and exact iMovie export settings. The plan must respect Apple's content rules (real app footage only — overlay captions are fine, device frames/hands/marketing montages are not).

**Lift, don't invent.** When a profile exists, the captions come from its **Derived copy** and the differentiators it lists, in the hub's `PRODUCT.md` voice — not a freshly invented set of marketing lines. The screenshot order follows the Phase 1 storyboard (itself from the Phase 0 ranking / profile). Every claim must be true of the shipping app. These deliverables are where you guide the user on **what text to add and where** — specific to *their* app, never generic.

## Framing — always the script, never by hand

`frameshot.py` turns a raw capture into the store-ready image: exact canvas, device
frame, caption band, PNG without alpha. **Use it for every framed screenshot.** Framing by
hand, or in a separate design tool, is what makes a set drift between shots, between locales
and between releases — and a set that drifts reads as a listing nobody maintains.

```bash
frameshot="${CLAUDE_PLUGIN_ROOT}/skills/appstore-media/scripts/frameshot.py"

# one shot
"$frameshot" --preset iphone69 --in raw/fill.png \
  --caption "Your reply fills itself from their message" --out out/en-US/02_fill.png

# Hebrew — --rtl does real bidi through Pillow's RAQM, not a reversed string
"$frameshot" --preset iphone69 --rtl --in raw/search.png \
  --caption "חיפוש מהיר"   # an RTL caption, to show --rtl --out out/he/02_search.png

# the whole set from a manifest (same keys as the flags)
"$frameshot" --manifest shots.json

# the cross-device shot — wide capture first, phone second
"$frameshot" --preset iphone69 --composite raw/mac.png raw/phone.png \\
  --caption "Write it on your Mac. Use it on your phone." --out out/en-US/03_sync.png
```

- `--preset` — `iphone69` (1320×2868), `ipad13` (2064×2752). These two are all App Store
  Connect needs; it scales them down to every smaller size in the family. `iphone65` exists
  only for a listing that skips the 6.9" set.
- `--composite WIDE PHONE` — two captures in one frame: a Mac window behind, a phone
  overlapping its lower-right. Use it for the cross-device claim, which two separate
  screenshots only imply. In a manifest, pass `"in": ["mac.png", "phone.png"]`.
- `--bleed 0.3` — enlarges the device and runs its lower part off the bottom edge. Use it
  when the captured screen does not fill, so the shot is not mostly empty.
- `--rtl` — required for Hebrew and Arabic. The script refuses if Pillow lacks RAQM, rather
  than silently writing the caption backwards.
- The script errors when a caption wraps past three lines. That is a caption that is too
  long for a store thumbnail, not a layout problem to work around.

## Hard rules (violating these gets the submission rejected)

- App Preview = real, in-app footage only. No device frames, no hands, no lifestyle shots, no pure-marketing intro/outro cards. Short text overlays on top of footage are acceptable.
- Exact accepted resolutions only — see `references/apple-specs.md`. "Close" is rejected.
- 15–30 seconds, ≤30fps, ≤500MB per preview.
- Screenshots may be marketing-styled (frames, backgrounds, captions) but must truthfully depict the app, and must be exact-size.
- Every claim in captions must be true of the shipping app.
- **No prices in listing media — not in a screenshot, not in an App Preview, not in a caption.** Never shoot the paywall or any screen that renders a price, and never write a price into caption text. One screenshot set serves **every storefront**: a hardcoded `$4.99` is wrong in all ~174 non-US stores (the German buyer reads `$4.99` while the store charges `5,99 €`), which is inaccurate metadata and reads as misleading pricing. It also makes the set disposable — every price change would force a re-shoot of assets that have nothing to do with price. **Sell Pro without the number:** shoot the unlocked feature working, the locked-content state (blurred/badged), or the `PRO` marker in the picker. Those carry the monetization story and survive any repricing. The single exception is the **IAP reviewer screenshot** (Phase 2), which must show the real price — it is an App Review artifact and never appears in the listing.
- Specs occasionally change. If an upload is rejected on size or the user reports a mismatch, re-check Apple's live pages (linked at the top of `references/apple-specs.md`) before debugging anything else.

## Definition of done

- `media-script.md` (the storyboard + strategy) exists in the media folder and was agreed before capture.
- `verify_assets.py` passes for every locale and device class the user targeted.
- **No listing asset shows a price** — check the shot list and the captions, not just the files; `verify_assets.py` checks sizes and formats, it cannot see a price. The IAP reviewer screenshot is the deliberate exception.
- The user has `captions.md` (per target locale) + `imovie-plan.md` (in the conversational language), both consistent with `media-script.md`.
- Summarize for the user (in the `conversational language` from the hub `DATA.md`): what was produced, where it is, the remaining manual steps (iMovie pass, framing tool pass, upload to App Store Connect), and the one-command way to regenerate everything next release.

## Boundaries

- **It captures; it does not upload.** `app-store-deliver` sends what lands here.
- **It does not author the listing text.** Captions belong to the media and are
  written here; the description, keywords and release notes are
  `store-metadata-writer`'s and `app-store-metadata`'s.
- **To resize one image that already exists**, use `apple-app-store-screenshots` —
  this skill is the pipeline, not a converter.

## Related skills (where this fits)
This skill is **step 3 — media** in the app lifecycle. It runs in the app repo (it needs the build), reads the profile, and writes the media into the hub at `<slug>/media/apple/` when there is one, or the local media folder when there is not.

**Upstream** (source of truth — read from the hub):
- `app-profile` `[hub]` — writes `<slug>/profile.md`: the ranked feature list / hero / differentiators / voice this skill lifts the **media script**, screen story, and captions from (Phases 0, 1 & 6). Run it first if no profile exists.

**Downstream** (consume the media this skill writes — they read it, they don't capture):
- `store-metadata-writer` `[hub]` — uses the screenshots when assembling the App Store + Google Play listings.
- A website repo's own skill `[$SITE]` — uses the media for cards / app pages / product sites.
- `app-store-metadata` — organizes the localized listing, places the screenshots into `fastlane/metadata/`, validates limits, uploads via `deliver`.

**Siblings:**
- `apple-app-store-screenshots` — the lightweight "just resize this one image to an exact size" path, for when a full demo-flow capture is overkill.
- `app-store-review-compliance` — owns the *App Review* demo path (see Phase 1), distinct from this skill's marketing-capture demo mode.
- `ship-apple-app` — the final submission step (stage 5): it **verifies** the media exists at the right sizes, then builds / uploads / submits. It does not produce media — this skill does.
