# shared-track

The work that is the same whichever store an app ships to: what it is called, what
it says about itself, what it costs, and the order a release happens in. Enable it
alongside a store track — and in a data repo, if you keep one.

<!-- generated:track -->
*Generated from the skills themselves by `factory/render_track_readmes.py` —
edit a skill, not this table.*

## The 7 skills

| Skill | What it is for | scripts | refs |
|---|---|---|---|
| `app-identity` | Decide an app's NAME for both stores, and own the project README as the source of truth for the name, subtitle / short description, and detected fe… | 2 | 2 |
| `app-profile` | Build an app's product profile — the one document every piece of copy about it is later derived from: store listings, site pages, campaigns. |  | 1 |
| `copy-edit` | Tighten existing product copy — App Store / Google Play listing text, marketing and product sites, README marketing sections, in-app strings, repli… | 1 |  |
| `launch-app` | Take an app from finished code to its FIRST public release, across every surface it needs: identity, profile, store or direct distribution, media,… |  | 1 |
| `prepare-app-release` | Take an app all the way to released — the cross-store orchestrator above ship-apple-app and play-store-ship. |  |  |
| `price-sync` | Change a studio app's price, or reconcile prices that have drifted apart, across every place a price is written — prices.json, the App Store IAP, t… | 1 |  |
| `store-metadata-writer` | Write an app's store listing text for BOTH stores from its profile — name-adjacent fields, descriptions, keywords, release notes, in-app purchase t… |  |  |

**What it costs.** 5,911 characters of description ≈ 1,477 tokens, in every session
that enables this track. A skill's body is read only when the skill fires; its description
is in context always.

**What it needs on the machine**, from the scripts that call it: `fastlane`, `xcodebuild`.

**Operations that declare where their work lands** (`close.py --op`): `app-profile`, `launch-app`, `price-sync`, `store-metadata-writer`.
<!-- /generated:track -->
