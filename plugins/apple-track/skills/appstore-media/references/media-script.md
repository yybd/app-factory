# The media script (`media-script.md`) — storyboard + strategy

Phase 1's deliverable. You act as the app's **media scriptwriter**: decide how to
*sell* the app on the store, then lay out exactly what every screenshot and every
video scene shows. Save it as `media-script.md` in the media folder
(`<slug>/media/apple/media-script.md` in the hub, else the capture root). It is the
**blueprint** the XCUITest flow (Phase 3) implements and the captions / iMovie plan
(Phase 6) realize.

**Lift, don't invent.** Everything traces to the profile/README (feature ranking,
hero, differentiators, the `Pro:` line) and the house voice (`PRODUCT.md`). Every
claim must be true of the shipping app. Hero feature first.

## Template

```markdown
# Media script — <App name>

## Strategy (how we sell it)
- **Lead with:** <the one strength that opens — the hero>.
- **Uniqueness:** <what it does that the alternatives don't / do worse — honest>.
- **Monetization:** <free vs Pro — what Pro unlocks and how a shot/scene SHOWS that
  value; make the upgrade feel earned. NO paywall shot and no price anywhere>.
- **Efficiency / usefulness:** <what makes it fast / effective / worth it — the
  concrete payoff to demonstrate, not adjectives>.
- **Arc:** <the through-line: hook → value → payoff>.

## Screenshots (ordered; hero first)
| # | Screen / feature | Shows (demo data) | Headline intent | Sells (which strength) | Framing |
|---|------------------|-------------------|-----------------|------------------------|---------|
| 1 | <hero screen>    | <what's on screen>| <benefit, 3–6 w>| <strength>             | <RTL? device? background?> |
| 2 | …                | …                 | …               | …                      | … |

## App Preview video (scene-by-scene, 15–30s, real in-app footage only)
| Scene | t (s) | Shows | On-screen text | Note (pacing / transition) |
|-------|-------|-------|----------------|----------------------------|
| Hook  | 0–3   | <open on the hero value> | <short> | grab attention fast |
| Value | 3–18  | <the core flow / efficiency in action> | <short> | human-paced, real taps |
| Payoff| 18–25 | <the result / Pro value / CTA-feel> | <short> | end on the win |
```

## How the strategy guides the shots
- **Strength → shot.** Each strength in the strategy should map to at least one
  screenshot and one video beat. If a strength has no shot, either add one or cut it.
- **Monetization, shown not stated — and never priced.** Put the Pro value *on
  screen* (the feature working, the locked→unlocked moment, a `PRO` marker in a
  picker) rather than a "buy Pro" card. Three reasons, all binding: the App Store
  bans pure-marketing cards in previews; a paywall shot sells a checkout instead of
  a product; and any rendered price is wrong in ~174 storefronts and makes the shot
  expire at the next repricing. **Storyboard no shot whose screen renders a price.**
  (The IAP *reviewer* screenshot is the opposite case — it must show the price, and
  it is not part of this storyboard.)
- **Efficiency, demonstrated.** "Fast/effective" is proven by the footage (a task
  done in two taps, an export completing) — let the demo data and pacing show it.
- **Order = priority.** A scanner sees shot 1 and the first 3s of video; lead with
  the strongest, truest thing.

## Consistency downstream
- **Phase 3 (flow):** every storyboard shot/scene becomes a beat in `DemoFlowTests`,
  in this order, hitting the same screens with the same demo data.
- **Phase 6 (copy):** `captions.md` realizes each shot's *headline intent*;
  `imovie-plan.md` realizes the *video script* (scenes, timing, on-screen text).
- Update `media-script.md` first when the story changes; the flow and the copy follow it.
