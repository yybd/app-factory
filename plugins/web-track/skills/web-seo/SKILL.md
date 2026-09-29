---
name: web-seo
description: >-
  Read how a site is doing in Google and on-site, decide what is actually wrong, and fix
  it: index coverage, impressions and queries, the conversion funnel, and the things
  that break silently — a stuck deploy, a re-enabled crawler block, a page that lost
  indexing, a sitemap that never listed a new page. Use when the user asks how the site
  or an app page is doing in search, why there is no traffic, whether pages are indexed,
  what to improve, to check the analytics or funnel, after shipping a new page, or for a
  periodic read ("איך האתר בגוגל", "למה אין תנועה"). It runs a full on-page technical
  audit and reads the live search and analytics data. It does NOT set up the measurement
  stack, and does NOT write the product's words — `copy-edit` and the profile own those.
---

# web-seo — what a site is doing in search, and what to do about it

**Where the site is, and what it is made of**, comes from `.claude/seo-site.json` in
the site's own repo — hostnames, which directory serves which property, the publish
command, and the credentials for the live half. It is optional: without one, the repo
is the site. The shape is in [references/site-descriptor.md](references/site-descriptor.md).

**A baseline is worth more than any single reading.** Search numbers only mean
something against an earlier measurement of the same thing, so the first run of this
skill on a site is a baseline, and every later one is compared to it. Keep it where the
site keeps its own notes.

Work in two passes and in this order: **audit the pages** (`audit.py` — offline,
seconds, everything actionable now), then **read Google's response** — a snapshot
of Search Console and analytics. **No client for those APIs ships here**; the
snapshot is whatever export or dashboard the site already has, and it can only
report what the pages already earned. Diagnosing from the response alone is how a markup problem gets
mistaken for a demand problem.

It does **not** set up measurement — that exists — and it does not write the
product's words: those come from `<slug>/profile.md` and are edited by
`copy-edit`. It decides *what* needs saying and where; that skill decides how it
reads.

This file is the method. What running it taught — the runs behind each rule — is in
[LESSONS.md](LESSONS.md).

## Prerequisites

- **Tools:** Python 3 for `scripts/audit.py` (standard library only, nothing to install); the site repo's own `npm run seo` and `npm run verify:deploys`; `curl` for the live checks.
- **Credentials:** Search Console and analytics credentials, only for the live reading (§3) — named by the descriptor's `search_console` / `analytics` entries (e.g. `$KEYS_ROOT/google/search-console.json`). No API client ships here; the audit needs none.
- **Hub (`$APP_HUB`):** optional — `<slug>/profile.md` is read to compare a page's title and first paragraph against the product's own words (§4); without it, compare against the page alone.
- **Other tracks:** none — `copy-edit` (shared-track) owns the wording it points at, and `add-app-to-site` is the site repo's own skill, not a factory track.

## 0. When to run this

**Monthly.** The routine read. Search moves on the scale of weeks, so a monthly
cadence is frequent enough to catch a regression and slow enough that each
reading has something new in it.

**Two weeks after anything deliberate** — new pages, a sitemap change, rewritten
titles, new internal links. Not sooner. Google learns a URL exists days before it
decides to fetch it and weeks before that shows in rankings, so a reading taken
the next morning reports the change as a failure that has simply not happened yet.
The one exception is a regression check: if a deploy might have broken something,
check the same day.

**After `add-app-to-site` ships a new page or site.** Confirm it reached the
sitemap (`npm run seo` in the site repo, after committing), that it carries the
analytics tag, and that something links to it (why: see
[LESSONS.md](LESSONS.md#a-new-page-with-no-inbound-link-produced-the-whole-baseline-finding)).

**Before any decision that leans on traffic numbers** — pricing, killing an app,
deciding a positioning did not work. This is the one that matters most here: a page
that was never crawled has not failed at anything (why: see
[LESSONS.md](LESSONS.md#low-downloads-were-never-a-pricing-signal-and-now-that-is-testable)).

**Not** daily, and not to watch a number move. Nothing here responds on that
timescale, and reading it that way produces false alarms in both directions.

## 1. Audit the pages first

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/web-seo/scripts/audit.py            # everything
python3 ${CLAUDE_PLUGIN_ROOT}/skills/web-seo/scripts/audit.py --errors   # only breakage
python3 ${CLAUDE_PLUGIN_ROOT}/skills/web-seo/scripts/audit.py --root <dir>   # no descriptor
```

It ships with this skill and reads the descriptor, so it runs on any site. Every check
in it exists because it was found broken on a real one (see
[LESSONS.md](LESSONS.md#every-check-in-the-audit-was-found-broken-on-a-real-site)).

Offline, seconds, and every finding is actionable today. **Run it before the
snapshot**, because a page cannot rank above what its markup allows: there is no
point reading impressions for a page whose title is truncated, whose description
Google had to invent, or that nothing links to.

It checks titles, descriptions, canonicals, `h1`, structured data, Open Graph,
`lang`, hreflang reciprocity, image alt text and dimensions, analytics coverage,
sitemap membership, duplicate titles and descriptions across pages, orphan pages,
**links and assets that point at nothing**, thin content, and per-property
`robots.txt`/`sitemap.xml`. Errors are broken; warnings are weaker than they
should be; notes are for awareness.

**It does not cover everything, and the gaps are deliberate.** It is a static
analysis of the repo, so it cannot see: whether a canonical URL actually returns
200 (a real error class — only `curl` or `npm run verify:deploys` catches it; why:
see [LESSONS.md](LESSONS.md#the-audit-cannot-see-a-canonical-that-redirects)), page
speed and Core Web Vitals, whether a redirect chains or loops, or whether structured
data satisfies a given `@type`'s required properties. Check those separately
rather than reading a clean audit as a clean site.

**`noindex` pages are excluded from every check and reported as notes.** That
exclusion is correct for the 404s and dangerous for anything else: a product page
marked noindex by accident would otherwise vanish from this report at the moment
someone needed telling. Read the notes.

## 2. What to do with what it finds

The audit says *what*. This says *what it is worth* — several of these are not
worth fixing in the order their counts suggest.

**Duplicate title or description.** Treat as the most serious finding, ahead of
anything cosmetic. Two pages with the same title are two pages competing for one
query, and Google keeps one. Usually the real answer is not to rewrite the title
but to admit there should be one page (why: see
[LESSONS.md](LESSONS.md#two-pages-for-one-product-compete-and-consolidating-beat-any-rewording)).

**Orphan page.** Equally serious and usually invisible. A page nothing links to
is a page Google will not fetch. Fix by linking from a page that *is* crawled — not by
adding it to the sitemap again. A sitemap is a hint; a link is a path.

**Missing description.** Real. Google writes the snippet itself from page text,
and it writes a worse one than you would.

**Description over 160 characters.** Google truncates it; there is no penalty.
So this is not "trim to 160" — it is *"do the first 155 characters stand alone
as the pitch?"* If they do, the overflow is harmless and you can leave it. Only
rewrite when the sentence that matters is the one being cut off.

**Title over 65 characters.** Same logic, but the fix is nearly always the same
edit: the `· <Studio>` suffix is what gets cut, and the distinctive word belongs
at the front. `<Distinctive name> — <what it is, in three words>` is right; the ones
that read `<App> — <long clause> · <Studio>` are wrong at the end, not the start.

**Missing structured data.** Worth it on product pages, which is what a buyer
searches for. Not worth it on a privacy policy. Never invent `aggregateRating`
to qualify for a rich result — the apps have too few ratings to carry one
honestly, and fabricating it is worse than the gap it fills.

**Missing Open Graph.** Almost all of it is on legal and privacy pages, which
nobody shares; it is cosmetic there. The one that matters is `og:image` on the
product subdomain pages, and it needs a real 1200×630 image. **Do not
point it at the square app icon** — it renders as a small box and looks like a
broken preview, which is worse than none.

**Missing alt text.** Accessibility first, search second. Fix it because the
image is unreadable to a screen reader, and describe what the screenshot shows
rather than repeating the app's name.

## 3. Take a reading

The live half needs Search Console and analytics credentials, which the descriptor
names (`search_console`, `analytics`). **This skill does not ship that client** (why:
see [LESSONS.md](LESSONS.md#why-no-search-console-client-ships-here)). What the skill
needs is the numbers, however they arrive — a script the project already has, an
export, or the Search Console UI.

What to collect, per property, against the baseline:

| | why |
|---|---|
| indexed / submitted | a page that is not indexed cannot be read at all |
| impressions and clicks, per query | impressions without clicks is a different problem from neither |
| pages that **lost** indexing since the last reading | the only finding here that is urgent |
| the conversion step this site exists for | §6 |

A 403 from Search Console has two causes that look identical and have different fixes:
the API is switched off in the Cloud project, or nobody shared the property with the
service account. Check both before assuming either.

### After a deploy that changed pages

```bash
# whatever this project uses to ping IndexNow with the changed URLs
```

Tells Bing, Yandex and Seznam to come and look. Google ignores IndexNow — its
side is the sitemap, which is already submitted and does not need resubmitting.
Do not run it on unchanged URLs; it gains nothing and the spec discourages it.

## 4. Diagnose — four states that look alike

**Read index coverage per property, never as a total.** The total hides the
shape: a studio-wide percentage can call a portfolio "38% indexed" while three whole
domains have nothing (why: see
[LESSONS.md](LESSONS.md#coverage-per-property-never-as-a-total)).

Then place each property in one of these. They are not degrees of the same
problem; they have different causes and different fixes.

| what you see | what it means | what actually helps |
|---|---|---|
| **Not indexed / unknown to Google** | Google has not fetched the page, or has never heard of it | Reachability. Internal links from pages that *are* crawled, the page's presence in a sitemap, and manual Request Indexing for a handful. Copy changes do nothing — nobody has read the page. |
| **Indexed, zero impressions** | Reachable, and competing for nothing anyone types | Relevance. What does the page claim to be about? Compare its title, `h1` and first paragraph against the words in `<slug>/profile.md` and against what people actually search. |
| **Impressions, few clicks** | Shown and not chosen | The title and meta description are the entire advert. Rewrite those before touching the page. |
| **Clicks, no `cross_property_click`** | People arrive and never discover another app | The funnel. Nothing on the page offers a next step — see §6. |

**Indexing is the floor, not the goal.** If a property reaches full indexing and
impressions stay at zero, the work moves to relevance (the standing example: see
[LESSONS.md](LESSONS.md#indexed-for-sixteen-months-and-never-once-shown)).

## 5. Find the cheapest movement first

Search Console's query report, filtered to positions 5–20 ("striking distance") —
already shown, not yet clicked. Moving position 11 to 6 costs a title and a
paragraph; ranking for a query that ranks nowhere costs a new page and months.
Read it before proposing anything new.

For each such query, check whether the page it ranks with actually targets it.
Often it ranks *despite* the copy, on a phrase the page mentions once — which
means saying it properly is a small, high-yield edit.

Watch for borrowed demand — traffic arriving on a **competitor's product name** or a
domain's previous owner. That is real traffic and it is worth keeping, but it is not
evidence that anything ranks for what the app is, and it must never be reported as
if it were (why: see
[LESSONS.md](LESSONS.md#borrowed-demand-the-traffic-was-for-a-competitors-product)).

## 6. The funnel — the reason any of this exists

Some apps are free (a free suite) so they can bring people who
may later buy a paid one. `cross_property_click` in GA4 is the only direct
evidence that works.

If sessions rise on free properties and this stays at zero, that is a **linking
and copy problem, not a traffic problem** — and the fix is on the page, not in
search (why: see [LESSONS.md](LESSONS.md#no-product-site-linked-to-any-other)).

Audience overlap is real and should be respected: link where the readers of one
property plausibly want the other. A free app's readers do not overlap commercially
with a paid developer tool — pointing them at it dilutes both. Do not propose links
just to raise a number.

## 7. How the site should be built

Recommendations to make when asked what to change structurally, or when
reviewing a new page before it ships. These are conclusions from what the
portfolio actually did, not general advice.

**One product, one page, one domain.** Before adding a page for an app that already has
one, decide which domain owns it and link to that from everywhere else. Where a
duplicate already exists, consolidate with a 301 — and do it while the pages are
still unindexed, which costs nothing, rather than after they have earned
something to lose.

**A page ships with an inbound link or it does not ship.** Being in the sitemap
is not enough — Google treats a sitemap as a suggestion and a link as a path.
When `add-app-to-site` creates a page, the same change should add the link that
reaches it.

**Nothing more than two clicks from its property's home page.** The catalogue at
`/apps` is the studio's one hub; each product site's home is its own. A page
reachable only from a footer is reachable in principle and not in practice.

**Link free apps to paid ones only where the audience genuinely overlaps.** Pure
(Markdown, writers, developers) overlaps with the tools subdomain and one product, and
that link is worth making. The free apps overlap with nothing commercial —
pointing a free app's readers at a paid developer tool helps neither, and a link nobody
follows still dilutes the page it sits on. Symmetry is not a reason.

**Say what the app is, in the words someone would type.** Titles and first paragraphs
should carry the job the app does — "Markdown editor", "App Store screenshots",
"encrypt files on your Mac" — not only the product name. A name nobody knows is
not a keyword.

**Do not build pages for search that a person would not want.** A set of privacy
policies will be a page per app and rank for nothing; they exist because the stores
require them, and that is a good enough reason to keep them
exactly as they are. Do not pad them, do not add structured data to them, and do
not count them when judging whether the site is working.

**Every new language needs reciprocal hreflang.** A page that lists an alternate
which does not list it back is ignored, and the audit checks this because it is
invisible otherwise.

## 8. Check what breaks silently

Each of these has happened or can happen, and none of them raises an error:

- **A stuck Vercel deploy.** `cd $SITE && npm run verify:deploys`. The guard is in
  each `vercel.json`; do not remove it (why: see
  [LESSONS.md](LESSONS.md#five-of-seven-vercel-projects-were-failing-on-fatal-bad-object)).
- **Cloudflare's managed robots.txt returning.** the apex domain is the one domain
  behind Cloudflare, and its AI Crawl Control setting *prepends* a block that
  disallows `GPTBot`, `ClaudeBot`, `Google-Extended` and `CCBot`, overriding the
  repo's file. Check with
  `curl -s https://<your-domain>/robots.txt | grep -i disallow`.
- **New pages missing from the sitemap.** `npm run seo` in the site repo, after
  committing the pages — `lastmod` is the git commit date, so running it first
  leaves every entry a commit stale.
- **GA4 gone quiet.** Sessions at zero across all hosts usually means the tag or
  the measurement id moved, not that nobody visited. `analytics.js` holds the id
  in one place.
- **Cross-domain measurement switched off.** A UI setting, unreachable by API,
  and nothing reports its absence — the free → paid journey just stops appearing.
- **A property's consent state.** Where consent mode is used it must stay
  `analytics_storage: denied` until a
  cookie banner exists; its published policy names consent as the legal basis and
  the site addresses EU visitors. Never flip it to raise a number.

## 9. What this cannot do

**There is no API to request indexing for ordinary pages.** Google's Indexing API
accepts only `JobPosting` and `BroadcastEvent`; using it for anything else is
against its terms and does nothing. Request Indexing is a manual action in the
Search Console UI with a quota of roughly ten a day — so it is a tool for a
handful of priority pages, never for a backlog of fifty. For a backlog the real
levers are internal links and sitemaps.

Cross-domain measurement, Custom definitions and the Cloudflare setting are all
UI-only. Say so plainly rather than appearing to have done them.

## 10. Report

Lead with the number that decides everything else — index coverage per property,
against the previous snapshot. Then impressions, then clicks, then the funnel.
Name what moved, what did not, and which of the four states each property is in.
Recommend the cheapest available action, and say what you did not do.

Do not report a percentage that averages a well-indexed domain together with one
that has nothing indexed (why: see
[LESSONS.md](LESSONS.md#coverage-per-property-never-as-a-total)).

## Boundaries

- **It reads and repairs what is measurable.** It does not set up the measurement
  stack, and it does not invent traffic: a page nobody links to and nobody searches
  for is a content problem, not an indexing one.
- **It does not write the product's words.** The profile and `copy-edit` own those.
- **It does not deploy.** It says what needs to ship and what to verify afterwards.
