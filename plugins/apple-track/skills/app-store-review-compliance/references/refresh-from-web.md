# Refreshing the curated digest against the live guidelines

The curated digest ([guidelines-curated.md](guidelines-curated.md)) is fast and
works offline, but Apple revises the guidelines several times a year. This is the
"hybrid" half: when accuracy matters, reconcile the digest against the live
document and report any drift.

## When to refresh
- The digest's `last-verified` date is more than ~60 days old.
- The user explicitly wants to be sure it's current ("is this up to date with
  Apple's latest rules?").
- The app is in a fast-moving area Apple keeps tightening: privacy/tracking,
  AI/generative content, crypto/NFT, kids, health, fintech, loot boxes.
- A submission is high-stakes (first launch, big client) and you want certainty.

## How to refresh
1. Fetch the live guidelines:
   ```
   WebFetch https://developer.apple.com/app-store/review/guidelines/
   ```
   Prompt it to return the section numbers/titles and any "Updated <date>" note
   near the top, plus the text of the sections relevant to this app (privacy,
   IAP, login, completeness, plus anything matching the app's domain).
2. If WebFetch is unavailable or the page is JS-heavy and returns little, fall
   back to WebSearch for "App Store Review Guidelines <section number>" and
   Apple developer news/"What's New" posts about guideline changes.
3. Compare against the digest:
   - New or renumbered sections the digest lacks.
   - Tightened wording (e.g. new mandatory flows, new required-reason API
     categories, expanded ATT scope).
   - Anything in the app's specific domain.

## What to do with drift
- **Report it** in the audit output: note which rules changed and how it affects
  this app. Don't quietly rely on a digest you now know is partly stale.
- **Offer to update** [guidelines-curated.md](guidelines-curated.md): add/adjust
  the affected items in place, keep the format (rule + number + detect + fix +
  severity + platform tag), and bump `last-verified` to today. Keep the digest
  curated — only the rejection-prone, detectable items; don't paste the whole
  document.
- If nothing changed materially, just bump `last-verified` and say so.

## Note on the Required-Reason API list
Apple maintains the authoritative Required-Reason API categories and approved
reason codes in its developer documentation (search "Describing use of
required reason API"). When refreshing privacy-manifest rules, verify the
category list and reason codes there, since new categories get added.
