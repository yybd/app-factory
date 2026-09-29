# web-seo — what running it taught

**What belongs here, and what does not.** `SKILL.md` is the method: what to do, in what
order. This file is what was **learned by running it** — the facts that were discovered
rather than designed, each with the run that produced it.

**Why it lives here and not in a project's memory.** A lesson about this operation
belongs to none of the places it touches. *"An orphan page is never fetched"* is not a
fact about one site, or one product page, or the studio catalogue — it is a fact about
reading a site in search. Filed under any one project it loads in that project's
sessions and never in the others, which is where it is needed. Filed here it travels
with the skill, to every session the skill loads in.

**Adding one.** A dated line, what was expected, what happened, and what it costs to
forget. If it is a rule about how to do the work, it belongs in `SKILL.md` instead.

---

## A new page with no inbound link produced the whole baseline finding

*2026-08-30, the first baseline.* `add-app-to-site` had shipped pages that were in the
sitemap and reachable by URL, and the expectation was that the sitemap was enough.
Every "Discovered — currently not indexed" page in the portfolio turned out to be a
page nothing pointed at; both orphans the audit found were unindexed. The rule in §0 —
confirm a new page is linked, not just listed — exists because of this run.

**Cost of forgetting:** a page that ships without a link looks shipped, sits in the
sitemap, and is never fetched; the next reading reports it as a failure of the copy.

## Low downloads were never a pricing signal, and now that is testable

*Recorded at the baseline.* The studio's own strategy note said low downloads are not a
pricing signal because there has been no promotion. Before this skill that claim was an
opinion; with index coverage per property it became a measurement. A page that was
never crawled has not failed at anything — and several product pages had never been
crawled.

**Cost of forgetting:** a price is cut, or an app is killed, on the strength of traffic
that nothing was ever in a position to generate.

## Every check in the audit was found broken on a real site

*The run that produced `audit.py`.* Nothing in it comes from a generic checklist. One
pass found 20 pages with no meta description, 13 descriptions truncated by an unescaped
quote inside the attribute, 4 paid-product pages with no structured data, 2 pages with
zero inbound internal links (both unindexed), 3 products with two competing pages each
— one pair sharing a byte-identical title — 24 canonicals pointing at URLs that
redirect, and 6 titles too long to survive a result page.

**Cost of forgetting:** a check gets removed as "theoretical", and the class of
breakage it caught returns without a symptom.

## The audit cannot see a canonical that redirects

*2026-08-30.* 24 canonicals pointed at URLs that returned a redirect rather than a 200.
The audit is a static read of the repo and reported all of them as fine, because the
`<link rel="canonical">` was well-formed; only `curl` or `npm run verify:deploys` saw
the redirect. This is why §1 lists what the audit does not cover.

**Cost of forgetting:** a clean audit is read as a clean site, and a whole error class
stays invisible.

## Two pages for one product compete, and consolidating beat any rewording

*From the baseline.* Three separate products each had two pages describing the same
app on two domains — a legacy page and a newer one. They competed with each other for
the same query, Google kept one, and two of the losers were orphans. Rewriting titles
to differentiate them was the obvious fix and the wrong one; admitting there should be
one page, and consolidating with a 301 while both were still unindexed, was worth more
than any wording. It is the reason a duplicate title is ranked the most serious finding
in §2, and the reason §7 says one product, one page, one domain.

**Cost of forgetting:** two half-pages are tuned against each other for months, and the
301 is finally done after one of them has earned something to lose.

## Coverage per property, never as a total

*The first baseline.* One mature property was 23 of 24 pages indexed, while five
properties under one studio domain managed 5 of 54 between them. A studio-wide figure
would have said "38% indexed" and hidden the fact that three whole domains had nothing.
The same habit — averaging a well-indexed domain with an empty one — would have hidden
the whole finding of that date.

**Cost of forgetting:** the report shows a plausible middling number, and nobody looks
at the domains that are at zero.

## Indexed for sixteen months and never once shown

*The standing example of the "indexed, zero impressions" row.* One property had both
its pages indexed for sixteen months without a single impression, because nothing on
them matched a phrase anyone types — the pages carried the product's name and not the
job it does. Indexing is the floor, not the goal; a property that reaches full indexing
with impressions at zero has simply joined this case, and the work moves to relevance.

**Cost of forgetting:** effort goes into getting more pages indexed on a site whose
indexed pages are already invisible.

## Borrowed demand: the traffic was for a competitor's product

*Seen on one property.* Nearly all of its traffic arrived on a competitor's product
name, because the domain had previously belonged to a different product. Real traffic,
worth keeping — and no evidence at all that anything ranked for what the app is.

**Cost of forgetting:** the property is reported as ranking, a positioning is judged to
work, and the numbers evaporate the day the old brand's searches stop.

## No product site linked to any other

*As of the baseline.* The free apps exist to bring people who may later buy a paid one,
and `cross_property_click` was the only direct evidence of that working. It was zero,
and it was zero because no product site linked to any other at all; the only route out
of a free app's page was a footer link. That is a linking and copy problem, and it was
being read as a traffic problem.

**Cost of forgetting:** sessions rise on the free properties, the funnel number stays
at zero, and the response is more search work instead of one link on the page.

## Why no Search Console client ships here

*A design decision, recorded so it is not re-litigated.* A Google API client is a
dependency with its own auth flow, its own failure modes and its own upgrade treadmill,
and every site already has some way of reading its own numbers — a script, an export,
or the Search Console UI. What the skill needs is the numbers, however they arrive.

**Cost of forgetting:** a client gets added, breaks on the next auth change, and the
monthly reading stops because the tool stopped rather than because the site did.

## Five of seven Vercel projects were failing on `fatal: bad object`

*Found while checking what breaks silently.* The ignored-build step diffed against a
commit that had fallen out of Vercel's shallow clone. Because the commit it could not
find was the one that had to succeed, the deploy could never recover on its own, and
nothing raised an error — the site simply served the old pages. The guard now in each
`vercel.json` is what prevents it.

**Cost of forgetting:** the guard is removed as clutter, and the next stuck deploy is
found by the next audit reporting the same fix twice.
