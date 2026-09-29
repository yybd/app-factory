# Google Play listing metadata — spec

Field list, character limits, locale codes, graphic specs, ASO notes, fastlane
supply setup, and the steps that must be done on the Play Console website.
fastlane `supply` reads and writes the tree below.

## Contents
- [Directory layout](#directory-layout)
- [Text fields & limits](#text-fields--limits)
- [Locale codes](#locale-codes)
- [Graphics](#graphics)
- [ASO on Google Play (there is no keywords field)](#aso-on-google-play-there-is-no-keywords-field)
- [fastlane supply setup](#fastlane-supply-setup)
- [Done on the Play Console website](#done-on-the-play-console-website)

## Directory layout — the `supply` shape, which is what uploads

```
fastlane/metadata/android/
└── <locale>/                      e.g. en-US, de-DE, iw-IL
    ├── title.txt                  app title
    ├── short_description.txt
    ├── full_description.txt
    ├── video.txt                  optional YouTube URL
    ├── changelogs/
    │   └── <versionCode>.txt      release notes for that build, e.g. 42.txt
    └── images/
        ├── icon.png               512×512 store icon            ← a FILE
        ├── featureGraphic.png     1024×500, required to publish ← a FILE
        ├── phoneScreenshots/      2–8
        ├── sevenInchScreenshots/  optional (7" tablet)
        ├── tenInchScreenshots/    optional (10" tablet)
        ├── tvScreenshots/         optional (Android TV)
        └── wearScreenshots/       optional (Wear OS)
```

**The two single graphics are files; only the screenshot sets are folders.** This
document said `icon/` and `featureGraphic/`, and `scaffold_metadata.py` created them
that way — so a scaffolded tree uploaded with no icon and no feature graphic, and the
validator, checking the same wrong shape, reported a *correct* tree as empty. Both are
fixed; the validator now names the folder form explicitly when it finds one.

Each locale folder is self-contained. The `changelogs/<versionCode>.txt` filename (in
the `supply` shape; `changelogs/<versionCode>/<locale>.txt` in the hub) is the integer
`versionCode` from the build (Gradle `versionCode`).

## And the hub shape, which is where the text is authored

```
<slug>/store/play/
├── metadata/<locale>/             the same four .txt files
├── changelogs/<versionCode>/      grouped by BUILD, not by locale
│   └── <locale>.txt                 (a flat <versionCode>.txt = same text everywhere)
└── iap/<product-id>/              in-app purchase text — not part of the listing
<slug>/media/play/<locale>/images/ the graphics, produced by play-store-media
```

Two deliberate differences from `supply`: **release notes transpose** (a build's
languages sit together, which is how they are written and reviewed), and **graphics
live in a separate tree** because a different skill produces them at a different time.
`sync_from_hub.sh` maps the hub onto the `supply` shape at delivery; the scaffold and
validate scripts read whichever root they are given.

## Text fields & limits
| File | Field | Limit | Notes |
|------|-------|-------|-------|
| `title.txt` | App title | **30** chars | Name shown on the listing + in search. Primary ASO field. |
| `short_description.txt` | Short description | **80** chars | Shown collapsed, above the fold — the tagline. Second ASO field. |
| `full_description.txt` | Full description | **4000** chars | The body. First ~167 chars show before "read more". Light formatting and emoji are allowed (unlike Apple). Main ASO surface. |
| `changelogs/<vc>.txt` (supply) · `changelogs/<vc>/<locale>.txt` (hub) | What's new | **500** chars | Per build. Optional but recommended. |
| `video.txt` | Promo video | — | One YouTube URL. Optional. |

Counts are Unicode characters. Don't pad to the limit — fit the message.

## Locale codes
Play uses its own language tags. Common ones:

`en-US`, `en-GB`, `de-DE`, `fr-FR`, `es-ES`, `es-419` (Latin-American Spanish),
`it-IT`, `pt-BR`, `pt-PT`, `nl-NL`, `ru-RU`, `pl-PL`, `tr-TR`, `ar`,
**`iw-IL`** (Hebrew), `ja-JP`, `ko-KR`, `zh-CN`, `zh-TW`, `hi-IN`, `id`, `th`,
`vi`.

The default/primary listing language is set in the Play Console (usually `en-US`).

> **Hebrew gotcha:** Google Play still uses **`iw-IL`** — the deprecated ISO 639
> code for Hebrew — not `he`. A folder named `he` silently won't match the
> locale. (Apple, by contrast, uses `he`.)

## Graphics
| Asset | Size | Format | Notes |
|-------|------|--------|-------|
| Icon | 512×512 | 32-bit PNG | Store icon. The launcher icon ships inside the app bundle separately. |
| Feature graphic | **1024×500** | PNG/JPEG, no alpha | **Mandatory** to publish. Sits at the top of the listing. No Apple analog. Keep text clear of the edges — it gets cropped on some surfaces and overlaid with a ▶ button when a promo video is set. |
| Phone screenshots | min side ≥320px · max side ≤3840px · max aspect 2:1 | PNG/JPEG | 2–8 required. |
| 7" / 10" tablet | same constraints | PNG/JPEG | Optional; needed to be featured on tablets. |

No iOS-snapshot-style automation exists. Capture manually, or use
`fastlane screengrab` for an instrumented app.

## ASO on Google Play (there is no keywords field)
Unlike the App Store — which has a hidden 100-character keywords field — Google
Play has **no keywords field**. Search indexes the **visible** text, primarily
the **title**, **short description**, and **full description**, weighted with
installs, ratings, and engagement. Practical guidance:

- Put the single most important search term in the **title** (within 30 chars).
- Use the **short description** (80) for the primary + one secondary term in a
  natural sentence.
- In the **full description**, cover the primary term and a handful of
  secondaries; the first ~167 chars matter most (shown above the fold).
- Mention key terms a few times across the body — but write for humans. Google's
  policy penalises keyword stuffing and repetition and can reject the listing.

This is why the skill folds ASO into the copy step instead of having a separate
keywords skill: on Play, ASO *is* the listing text.

## fastlane supply setup
`supply` is the Android equivalent of `deliver`.

- **Install** — add `fastlane` to the `Gemfile` (`bundle install`), or
  `brew install fastlane`. Ask before installing — it changes the environment.
- **Auth (only to UPLOAD, not to scaffold/validate locally)** — a Google Play
  **service-account JSON** with the Play Developer API enabled, referenced from
  the `Appfile` (`json_key_file "…"`) or `supply(json_key: "…")`.
- **Init from an existing listing** — `fastlane supply init` pulls the current
  live metadata into the tree (use this to take over an existing app).
- **Upload metadata only (no binary), dry-run first:**
  ```bash
  fastlane supply --skip_upload_apk true --skip_upload_aab true --validate_only true
  ```
  Drop `--validate_only true` to push. Use `--skip_upload_images true` /
  `--skip_upload_screenshots true` to control graphics.
- A binary (AAB) must have been uploaded at least once before some listing fields
  apply. For a brand-new app, create the app entry on the website first.

## Done on the Play Console website
fastlane can't do these — finish them on play.google.com/console:

- **Data safety** form — the Play equivalent of Apple's privacy "nutrition label".
- **Content rating** — the IARC questionnaire.
- **Pricing & distribution** — free/paid, countries.
- **App content** declarations — target audience, ads, news, data handling, etc.
- **Store settings** — category, tags, contact details.
- Creating the **app entry** itself if it doesn't exist.
