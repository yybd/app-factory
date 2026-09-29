# Refreshing the HIG digest against the live guidelines

The curated digest ([hig-curated.md](hig-curated.md)) is fast and offline, but
Apple revises the Human Interface Guidelines with each OS cycle — sometimes
substantially (new design language, new materials, new layout metrics, new
components). This is the "hybrid" half: when accuracy matters, reconcile against
the live HIG and report drift.

## When to refresh
- The digest's `last-verified` date is more than ~90 days old.
- A new major OS was announced/released (WWDC season especially) — design
  language and components shift then.
- The user wants certainty the review reflects current Apple guidance.
- The app targets a new component/pattern you want to verify (e.g. a new
  navigation container, a new control).

## How to refresh
1. Fetch the relevant HIG pages:
   ```
   WebFetch https://developer.apple.com/design/human-interface-guidelines/
   ```
   The HIG is split into many topic pages (Accessibility, Typography, Color,
   Layout, Navigation, etc.). Fetch the overview, then the specific topic pages
   relevant to the review. Ask the fetch to return the current guidance and any
   "what's new" / platform-version notes.
2. If WebFetch returns little (the site is JS-heavy), fall back to WebSearch for
   "Apple Human Interface Guidelines <topic>" and WWDC design session notes.

## What to do with drift
- **Report it** in the review: note where current Apple guidance differs from
  the digest and how it affects this app.
- **Offer to update** [hig-curated.md](hig-curated.md): adjust the affected
  topic in place, keep the format (why / look-for / recommendation + platform
  tag), and bump `last-verified` to today. Keep it curated — practical,
  reviewable topics, not a copy of the whole HIG.
- If nothing material changed, bump `last-verified` and say so.

## Note on accessibility specifics
For concrete accessibility criteria (contrast ratios, Dynamic Type sizes,
target sizes), Apple's Accessibility HIG pages and the Accessibility Inspector
are authoritative. When in doubt about a number, verify there rather than
trusting a remembered value.
