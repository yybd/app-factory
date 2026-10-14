# Apple App Store Connect screenshot sizes

All sizes are in pixels.

<!-- apple-specs:begin -->
*Generated from `apple-specs.json`. Apple's source: https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications
Last checked against it: 2026-10-14. Do not edit this section by hand —
edit the JSON and run `render_specs.py`.*

PNG or JPG, RGB, no alpha. App Store Connect rejects any dimension not listed here exactly.

### iphone

| Family | Portrait sizes | Devices |
|---|---|---|
| 6.9" | 1320 × 2868 · 1290 × 2796 · 1260 × 2736 | iPhone Air, 17 Pro Max, 16 Pro Max, 16 Plus, 15 Pro Max, 15 Plus, 14 Pro Max |
| 6.5" | 1284 × 2778 · 1242 × 2688 | iPhone 14 Plus, 13 Pro Max, 12 Pro Max, 11 Pro Max, 11, XS Max, XR |
| 6.1" / 6.3" | 1206 × 2622 · 1179 × 2556 | iPhone 16, 15, 14 Pro, 13 Pro, 13, 12 Pro, 12, 11 Pro, XS, X |
| 5.5" | 1242 × 2208 | iPhone 8 Plus, 7 Plus, 6s Plus |
| 4.7" | 750 × 1334 | iPhone SE 2nd/3rd gen, 8, 7, 6s |
| 4" | 640 × 1136 | iPhone SE 1st gen |

### iphone_duo

| Family | Portrait sizes | Devices |
|---|---|---|
| Duo outer | 1398 × 2034 | iPhone Duo, outer display |
| Duo inner | 2007 × 2853 | iPhone Duo, inner display |

### ipad

| Family | Portrait sizes | Devices |
|---|---|---|
| 13" | 2064 × 2752 · 2048 × 2732 | iPad Pro 13", iPad Pro 12.9" |
| 12.9" / 11" / 10.5" | 1668 × 2420 · 1668 × 2224 | iPad Pro 11", iPad Air 13"/11", iPad 11"/10.9", iPad mini |
| 9.7" | 1536 × 2048 · 768 × 1024 | older iPad |

### mac

| Family | Portrait sizes | Devices |
|---|---|---|
| 16:10 | 1280 × 800 · 1440 × 900 · 2560 × 1600 · 2880 × 1800 | any Mac |

### appletv

| Family | Portrait sizes | Devices |
|---|---|---|
| tvOS | 1920 × 1080 · 3840 × 2160 | Apple TV |

### visionpro

| Family | Portrait sizes | Devices |
|---|---|---|
| visionOS | 3840 × 2160 | Apple Vision Pro |

### watch

| Family | Portrait sizes | Devices |
|---|---|---|
| Ultra 3 | 422 × 514 | Apple Watch Ultra 3 |
| Ultra 2 / Ultra | 410 × 502 | Apple Watch Ultra 2, Ultra |
| Series 11 / 10 | 416 × 496 | Apple Watch Series 11, 10 |
| Series 9 / 8 / 7 | 396 × 484 | Apple Watch Series 9, 8, 7 |
| Series 6 / 5 / 4 / SE | 368 × 448 | Apple Watch Series 6, 5, 4, SE 3, SE |
| Series 3 | 312 × 390 | Apple Watch Series 3 |

**Landscape is the transpose of every size above**, and is accepted wherever
the portrait one is.

For Apple Watch the SAME size must be used across every localization.

iPhone Duo has two displays. In App Store Connect both sizes go into ONE set (placement group IPHONE_DUO_PROFILE, up to 10 stills, inner and outer mixed) — confirmed against the live reference data 2026-10-14. Optional today; Apple: "Starting in April 2027, screenshots will be required for any app using the iOS 27.1 SDK or later." fastlane deliver does not know the Duo display type, so these go up through the App Asset Library API (app-store-deliver/scripts/upload_library_assets.rb), never through the deliver staging folder.

### App Preview videos

| Platform | Sizes |
|---|---|
| iphone | 886 × 1920 · 1920 × 886 · 1080 × 1920 · 1920 × 1080 |
| ipad | 1200 × 1600 · 1600 × 1200 |
| mac | 1920 × 1080 |

15-30 seconds, 30fps, H.264 High@4.0, and a conformant stereo AAC track — App Store Connect rejects a preview with missing or non-conformant audio.

iPhone Duo App Previews use the ordinary iPhone preview sizes (886 x 1920 / 1920 x 886); there is no Duo-specific video size.

### Creative assets — product page header and search results

*Source: https://developer.apple.com/help/app-store-connect/reference/app-information/creative-assets-specifications — checked 2026-10-14.*

| Placement | Kind | Ratio | Size | Formats | Video |
|---|---|---|---|---|---|
| product page header | image | 21:9 | 3840 × 1646 | png, jpg, jpeg |  |
| product page header | image | 16:9 | 5244 × 2950 | png |  |
| product page header | video | 21:9 | 3840 × 1646 | mov, m4v, mp4 | 30/60 fps, 5–30 s |
| search results | image | 3:2 | 1920 × 1280 – 3840 × 2560 | png, jpg, jpeg |  |
| search results | image | 16:9 | 5244 × 2950 | png |  |
| search results | video | 3:2 | 1920 × 1280 – 3840 × 2560 | mov, m4v, mp4 | 30/60 fps, 5–30 s |

Optional. Shown on iOS / iPadOS 27 and later. No alpha, no transparency. Videos loop; header video is muted by default and the viewer may unmute, search video is always muted. Reviewed by App Review, on their own (no app version needed) or with a version.

A 16:9 PNG at exactly 5244 x 2950 is accepted by BOTH placements, so one file can serve as header and search asset (the 'Use header asset in search results' option).<!-- apple-specs:end -->
