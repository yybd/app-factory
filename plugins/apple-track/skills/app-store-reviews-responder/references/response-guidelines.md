# Developer responses to reviews — rules & best practices

last-verified: 2026-06-03
source: Apple — Ratings, Reviews, and Responses; App Store Connect Help

## Apple's rules (what you must/can do)
- You can respond to **any** customer review of your app; the response is public,
  shown under the review.
- **One response per review** — but you can **edit/update** it anytime.
- The reviewer is notified when you respond and can update their review.
- Keep it professional and relevant; standard App Store content rules apply
  (no offensive content, no spam).
- **Never include personal/sensitive data** (don't echo emails, order numbers,
  names) — it's public.
- Don't use responses for marketing other products or off-topic promotion.

## Tone & content that actually helps
- **Thank them**, then address the **specific** point — generic replies read as
  canned and help no one.
- **Acknowledge** the problem honestly; don't be defensive or argue, even with
  an unfair review. Future readers judge you by how you respond.
- If it's **a misunderstanding**, clarify briefly and point to where/how (a menu,
  a setting), not "you're wrong."
- If it's **a real bug/missing feature**: say whether it's fixed/planned, and if
  fixed in a version, invite them to update and re-review.
- **Offer a real support channel** for back-and-forth (your support email/URL) so
  the public thread stays short.
- Keep it **short** (2–4 sentences) and in the **reviewer's language** when you
  can.

## When to respond (triage)
- ✅ Low ratings with a fixable/clarifiable issue, factual errors others will
  read, recurring themes (respond to a few representative ones).
- ➖ Generic 5★ praise — optional; a brief thanks is fine but low-value.
- ❌ Don't argue, don't respond angrily, don't respond to obvious troll/abuse
  beyond a calm one-liner (or report it to Apple if it violates rules).

## Templates (adapt — never paste verbatim)
**Fixed bug:**
> Thanks for the report, and sorry for the trouble. This was fixed in version
> X.Y — updating should resolve it. If anything still looks off, reach us at
> <support> and we'll help right away.

**Misunderstanding / how-to:**
> Thanks for trying [App]! You can actually do that from [menu/setting] — here's
> how: [one line]. Happy to walk you through it at <support> if it's unclear.

**Feature request:**
> Appreciate the feedback — [feature] is something we're considering. We've noted
> your request; if you'd like to share more about your use case, <support> is the
> best place.

**Unfair / inaccurate (stay calm):**
> Thanks for the feedback. To clarify, [factual correction in one sentence]. If
> you ran into a specific problem we'd genuinely like to help — <support>.

## Posting
App Store Connect → your app → **Ratings & Reviews** → pick the review → **Reply**.
Or via the App Store Connect API (`customerReviewResponses`) with an API key
(see the `apple-credentials` skill). Always get the user's approval on the draft
before it goes public.
