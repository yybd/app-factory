# Marketing copy + editing plan

This phase turns raw, spec-compliant captures into a product page that converts. Two deliverables: `captions.md` (the on-screen captions, **per the app's target locale** — e.g. Hebrew + English) and `imovie-plan.md` (the editing plan, written in the **`conversational language`** from the hub `DATA.md`).

> **Source of truth: the profile.** For a studio app the caption material — the hero feature, the ranked features, the honest differentiators (one-time purchase, local-first/privacy, offline, language support) — already lives in `$APP_HUB/<slug>/profile.md` (its **Derived copy** + advantages), in the hub's `PRODUCT.md` voice. Lift from there and tighten to caption length; don't invent a parallel set of claims. The guidance below is *how* to shape that material into captions, not license to make up new ones.

## Part 1 — Screenshot captions (`captions.md`)

### How to write a caption

- **Benefit first, feature second.** "Write without distractions" beats "Markdown editor". The screenshot shows the feature; the caption says why the user should care.
- **3–6 words.** Captions are read in under a second while scrolling the store.
- One idea per screenshot. If a caption needs an "and also", split it into two screenshots.
- Verbs in imperative or present ("Syncs to every device", "Works offline too") — not marketing adjectives ("amazing", "innovative").
- Every claim must be true of the shipping app (App Review checks).
- **Never put a price in a caption** — not "Only $4.99", not "$4.99 one-time". One caption set serves every storefront, so a currency amount is wrong in ~174 of them, and it expires the moment you reprice. Say the *shape* of the deal instead, which is true everywhere and never expires: "One-time purchase, no subscription". Same rule as the hard rule on shooting the paywall — see `SKILL.md`.
- English variants follow the same rules; write them separately, never machine-translate the Hebrew word-for-word.

### Screenshot order = sales pitch order

1. **Screenshot 1–2 do ~70% of the work** — they show in search results before anyone taps. Put the hero feature and the core value proposition here. If there's an App Preview, it occupies slot 1 and screenshot 1 becomes the poster-adjacent hero.
2. Screenshots 3–5: the supporting features, in the Phase 0 ranking order.
3. Last screenshot: trust/closing argument — privacy, one-time purchase ("One-time purchase, no subscription"), offline, language support. For this user's apps, one-time purchase and local-first/privacy are recurring honest differentiators — use them when true.

### Template for captions.md (one block per screenshot)

```
## 02_Editor — the editing screen
Caption (en): Clean writing, no distractions
Caption (en): Distraction-free writing
Placement: caption on top, device centred below
Design notes: quiet gradient background; in an RTL locale, right-align the caption
```

### Framing-tool guidance

- Tools: `fastlane frameit` (config-file driven, free) or AppScreens/AppMockUp (visual). Output must be exactly the accepted size — these tools handle that, but verify with `verify_assets.py` anyway.
- **Hebrew sets**: right-align captions, RTL text direction, and check punctuation doesn't flip. Use a Hebrew-capable font (SF Hebrew/Heebo/Assistant). Build the he set and en set as two separate exports, not one set with swapped text.
- Keep background style, font, and device angle identical across the whole set — consistency reads as professionalism.

## Part 2 — The App Preview editing plan (`imovie-plan.md`)

The raw video from Phase 3 is one continuous take. The plan tells the user exactly how to cut it in iMovie and which text to overlay when. Build it by watching the beat timing from the test run (the capture script logs beat timestamps) or estimating from the flow's `humanPause` budget.

### Story structure for 15–30 seconds

| Segment | Duration | Content | Overlay text |
|---|---|---|---|
| Hook | 0–3s | Hero screen, mid-action (not app launch!) | App's one-liner, e.g. "A clean Markdown editor for long-form writing" |
| Beat 2–4 | ~5s each | One feature per beat, real interaction | 2–4 word feature caption per beat |
| Close | last 2–3s | Most attractive screen, at rest | Call to action or app name |

- **Second 5 is the default poster frame** — make sure the frame at 0:05 is gorgeous, or instruct the user to set a custom poster frame in App Store Connect.
- Cut dead time between beats (mouse travel, loading) — jump cuts between beats are normal and expected in previews.
- No intro logo card, no outro marketing card — open and close on real UI (App Review rule).

### Text overlays in iMovie

- iMovie: select clip → Titles → use "Lower" or "Standard" minimal styles; avoid animated/cheesy presets.
- Hebrew overlays: type directly; verify RTL renders correctly in preview, right-align. Keep overlays ≤4 words, displayed ≥2s.
- One overlay at a time, never stacked.
- Localize: the he preview gets Hebrew overlays over the he-locale footage; the en preview gets English overlays over en-US footage. Two separate iMovie projects.

### Audio

- Default: no music → `convert_preview.sh` injects the required silent stereo AAC track automatically.
- If adding music in iMovie: royalty-free only (iMovie's built-in soundtracks are licensed for this), keep volume low, no voiceover unless localized per locale.

### Export settings from iMovie

File → Share → File: Resolution 1080p (Mac/landscape) or highest available, Quality High, Compress Better Quality → then **always run the export back through `convert_preview.sh`** to hit the exact accepted resolution and audio spec, and `verify_assets.py` before upload. iMovie's "App Preview" project type (iOS) exports at compliant sizes directly — still verify.

### Writing the plan for *this* app

Don't emit the generic table — fill it with the user's actual beats, actual timestamps from the run, and captions consistent with `captions.md` (same wording for the same feature; the store page should feel like one voice). End `imovie-plan.md` with a short checklist in the conversational language: cut list → overlays → export → convert script → verify script → upload.

## Part 3 — Marketing video (outside the App Store)

If the user also wants a website/social version: the same raw footage goes into CursorClip/Cap/Screen Studio where zoom effects, backgrounds, and device frames ARE welcome. Note this in the summary, but keep its outputs out of the `AppStoreMedia` tree (different rules, don't mix).
