# aso-keywords — what running it taught

**What belongs here, and what does not.** `SKILL.md` is the method. This file is what was
**learned by running it** — facts discovered rather than designed, each dated, each with
what was expected and what happened. A lesson that changes a weight or a threshold also
changes `calibration.json`, with the same date in both.

**Data or lesson?** An outcome about one app (*"'habit tracker' did not rank for app X"*)
is data: it stays in that app's `keywords.json` and `experiments.jsonl`. An outcome that
would change how **every** app is scored (*"the autocomplete proxy over-rates two-letter
Hebrew prefixes"*) is a lesson, and goes here.

---

## 2026-10-23 — Apple Ads popularity is real, and it is only the head

*Expected* (from aso.dev and MobileAction reports): Apple's search popularity stuck at 5
since 2025-09-29, or unavailable without a campaign. *Happened*, on the Apple Ads Platform
API v1 with an account that has never run a campaign: real, varied values — US
productivity 55–90, Israel 1,070 terms over all genres, Hebrew among them. **But only head
terms**: the floor is about 54, and every niche term tried (markdown, clock, תזכורת, סידור)
is absent. So Apple's figure replaces the proxy for a handful of terms per study, and its
**absence** is information: the term is below the floor (`calibration.json` →
`apple.absent_cap`). *Cost of forgetting:* treating "not in Apple's list" as "no data"
and letting a long-tail proxy outrank a measured head term.

## 2026-10-23 — Apple Ads suggestions are not usable yet

`suggestions/phrases` with `queryType: SEARCH` returned nothing even for chatgpt and vpn,
and rejects a country filter; `suggestions/keywords` for the studio's own app answered
"App not found or access denied" — the Ads account was not linked to the developer
account's apps. Neither is called. Re-test when Apple updates the API.

## 2026-10-23 — the Mac store has no free autocomplete

`clientApplication=MacAppStore` on the hints endpoint returns terms that are not apps;
the Mac web store's suggestion API answers 401 without a token. The Mac store's **search
page** works fine. So a Mac app's popularity proxy is iOS autocomplete, labelled as such;
its ranks and difficulty are the Mac store's own.

## 2026-10-23 — the search page abbreviates rating counts

`ratingCount` on `apps.apple.com` search is a display string: `"497"`, `"2.8K"`, `"1.2M"`.
The first version parsed it as an integer, got 0 for every big app, and scored "markdown"
as easy. `serp._count` reads the suffix.

## 2026-10-23 — a Hebrew listing indexes Latin words too

The first allocator kept Latin terms out of the `he` locale. On a studio app's Israeli
listing — whose Hebrew subtitle reads "Markdown Writer — …" — that left "markdown editor"
with nowhere to go, though Israelis search it in Latin. Now a Hebrew term goes only to
`he`, and a Latin term goes anywhere, preferring a Latin locale (en-GB in Israel) when the
listing has one.

## Open: does Apple strip Hebrew prefix letters?

"בכתיבה" in a subtitle and "כתיבה" as a search: whether the store matches them (ב, ה, ו,
ל, מ, ש, כ are prefixes in Hebrew) is unknown. The allocator treats them as different
words, which spends bytes when they match and loses the term when they do not. Settle it
with a rank check on one app: a term present only with a prefix, before and after adding
the bare form.

## Open: bytes or characters for Hebrew

Unverified. The scripts count bytes. The first time a Hebrew keyword field of more than
50 letters (and at most 100) is typed into App Store Connect, record here whether it was
accepted, and set `keyword_limit_unit` in `calibration.json`.
