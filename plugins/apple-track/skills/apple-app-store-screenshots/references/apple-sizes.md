# Apple App Store Connect screenshot sizes

All sizes are in pixels.

<!-- apple-specs:begin -->
*Generated from `apple-specs.json`. Apple's source: https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications
Last checked against it: 2026-09-11. Do not edit this section by hand —
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

### App Preview videos

| Platform | Sizes |
|---|---|
| iphone | 886 × 1920 · 1920 × 886 · 1080 × 1920 · 1920 × 1080 |
| ipad | 1200 × 1600 · 1600 × 1200 |
| mac | 1920 × 1080 |

15-30 seconds, 30fps, H.264 High@4.0, and a conformant stereo AAC track — App Store Connect rejects a preview with missing or non-conformant audio.<!-- apple-specs:end -->
