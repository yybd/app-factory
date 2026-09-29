# store-metadata-writer — what running it taught

**What belongs here, and what does not.** `SKILL.md` is the method: what to do, in what
order. This file is what was **learned by running it** — the facts that were discovered
rather than designed, each with the run that produced it.

**Why it lives here and not in a project's memory.** A lesson about this operation
belongs to none of the places it touches. *"A release note written in the app repo's
`fastlane/` is gone at the next send"* is not a fact about the hub, or the app repo, or
one store — it is a fact about writing a listing. Filed under any one project it loads
in that project's sessions and never in the others, which is where it is needed. Filed
here it travels with the skill, to every session the skill loads in.

**Adding one.** A dated line, what was expected, what happened, and what it costs to
forget. If it is a rule about how to do the work, it belongs in `SKILL.md` instead.

---

## The listing moved to the hub so the app repo's copy could not drift

*A design decision, recorded so it is not re-litigated.* Listing metadata was once
authored in the app repo's `fastlane/metadata`, beside the code, on the expectation
that keeping it next to the app kept it current. The risk that removes nothing is
drift: two copies of one listing — the hub's profile and the repo's fastlane tree —
and nothing to say which is right. So the hub became the source of truth and
`fastlane/` a generated artifact: `sync_from_hub.sh` materializes it only at the moment
of send, which is why it cannot drift. You are the bridge that fills the hub; fastlane
is the bridge that carries it to the store, and the user runs that outward-facing step.
Both directories are on the same machine — the profile's `Project:` field points at the
local app repo the sync later targets. A sync that exits with "missing data" is
therefore not an error to work around in `fastlane/`; it is a request to complete the
hub.

**Cost of forgetting:** a field is patched in `fastlane/`, the next sync overwrites it,
and the store receives the older text.

## Release notes written in the app repo's `fastlane/` vanish without a report

*From the rule in Step 1.* The natural place to type this release's "What's New" is
the `fastlane/metadata/<locale>/release_notes.txt` the upload reads — and that tree is
rebuilt from the hub on every send. Text written there is deleted without being
reported: no warning, no diff, the hub's text ships in its place. Release notes live in
the hub, by version (`<slug>/store/apple/release-notes/<version>/<locale>.txt`,
`<slug>/store/play/changelogs/<versionCode>/<locale>.txt`), and nowhere else.

**Cost of forgetting:** the notes for a release are typed once, sent never, and nobody
learns it until the store page shows the previous version's text.

## The release is not the app's first

*The example behind the rule in Step 1.* The profile describes the app, not its
history, so listing copy written from it reads like a launch — while version 1.0 is
already `READY_FOR_SALE` and the release being authored is 2.0. "First public release"
on a live app's What's New is wrong in a way App Review may not catch and every
existing user will. Check the app's store status before writing notes; if an earlier
version is live, the notes say what changed.

**Cost of forgetting:** an update announces its own launch.

## A 403 on the privacy URL is not proof of absence

*From the privacy-URL check in Step 2.* The expectation was that one request settles
whether the page exists. It does not: a host's anti-bot layer answers 403 to a
non-browser User-Agent while the page is live, and a soft 200 can front a page that is
not there. The check that settles it is `curl -A '<browser UA>' -I <url>` and reading
the page title — and it has to pass before the URL goes into the listing, because a
dead privacy URL fails App Review.

**Cost of forgetting:** a live page is reported dead and rebuilt, or a dead one is
submitted and the review is rejected for it.

## A written price goes stale

*From the divergences in Step 3.* A price in the description, the promotional text or
the release notes looked harmless — it was true when written. Storefront prices vary
by country, and the number goes stale the first time the tier changes; a profile may
even record a stale StoreKit price, so lifting it from there is no safer. The price
lives only in the IAP / pricing config, and free text says "one-time purchase, not a
subscription" without the number.

**Cost of forgetting:** the listing quotes a price the store no longer charges, in
every locale, until someone notices.

## The `.storekit` description is almost always longer than 45

*From authoring the IAP listing in Step 4.* The obvious source for the IAP
`description.txt` is the description already in the app's `.storekit` configuration.
Apple's limit for the App Store IAP description is 45 characters, and the `.storekit`
text nearly always exceeds it — it was written for a different field with different
room. Rewrite it to fit; do not copy it.

**Cost of forgetting:** the deliver-time validator rejects the IAP, or a sentence cut
mid-word ships on the purchase sheet.

## What a listing draft reliably produces, and re-reading reliably misses

*Why Step 6b is required, not optional.* Writing a listing produces the same faults
every time: two sentences making one point, a promise repeated in three places, a term
of art the buyer does not know ("in place", "recursive", "content signature"), and the
rhythms that mark machine-written text. Re-reading one's own draft finds none of them,
because the writer already knows what each sentence meant. `copy-edit` is the pass that
applies `PRODUCT.md`'s rules from outside; character limits are the reason it runs
before delivering — tightening changes lengths, so the store validator runs again
afterwards.

**Cost of forgetting:** the faults ship, on both stores, in every locale that was
translated from the draft.
