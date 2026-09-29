# app-identity — what running it taught

**What belongs here, and what does not.** `SKILL.md` is the method: what to do, in what
order. This file is what was **learned by running it** — the facts that were discovered
rather than designed, each with the run that produced it.

**Why it lives here and not in a project's memory.** A lesson about this operation
belongs to none of the places it touches. *"A tail that duplicates a live listing is a
4.3 exposure"* is not a fact about one app, or one store, or the README — it is a fact
about naming an app. Filed under any one project it loads in that project's sessions
and never in the others, which is where it is needed. Filed here it travels with the
skill, to every session the skill loads in.

**Adding one.** A dated line, what was expected, what happened, and what it costs to
forget. If it is a rule about how to do the work, it belongs in `SKILL.md` instead.

---

## The name is usually already wrong when this skill arrives

*Why Step 1b exists.* The skill was designed around the rename request — a developer
asking what to call the app. A rename request is rare; arriving at an app whose name
is already wrong is not, and the original workflow had no step that judged the name
the app already carried. So the current name now gets the same test a candidate would
face, before anything is proposed. The other half of the lesson: a name that is merely
unexciting is not a reason to rename, because the cost lands on every downstream
surface — store text, captions, README, profile, site.

**Cost of forgetting:** a wrong name is carried through every listing skill because
nobody was asked to judge it — or a fine one is churned because it bored someone.

## A name that describes a feature the category already has

*The example behind the split in Step 2.* `File & Password Vault`, for an app in a
category where 12 of 119 competitors already encrypt, looked like a differentiator. It
was a category descriptor: it read as generic *and* failed to differentiate, and that
wording is what draws Guideline 4.3 comparisons. The expectation was that the feature
set the app apart; counting the category showed a tenth of it already claimed the same
thing. The measure is the iTunes Search API — pull the category and count how many
descriptions already claim it — and `check_name.py --claims` does the count.

**Cost of forgetting:** the name's highest-weight slot is spent on a word that ranks
the app among a hundred lookalikes.

## A tail that duplicates a live listing

*From checking candidates against the store.* `Quicknote: Smart Reply Keyboard` was a
candidate; `Texty: Smart Reply Keyboard` was already on the store. The same tail on two
listings is not a coincidence to Apple — it is a 4.3 exposure — and it was found only
because the tail and each adjacent word pair were searched in existing app names.
`check_name.py` does that search.

**Cost of forgetting:** a candidate is presented unchecked and the collision surfaces
in review.

## A version bump is not a feature change, and features are not a bump

*Why Step 5 asks instead of reading.* The expectation was that `MARKETING_VERSION`
says whether this run is a version event. It does not: the marketing version gets
bumped in Xcode without new user-facing features, and features land without a bump
yet. So the baseline from Step 1 is the suggested answer, and only the developer's
answer decides.

**Cost of forgetting:** a changelog entry for a version with nothing in it, or a
release whose changes are never written down.

## A clumsy README line is copied onto every surface

*Why Step 6b runs `copy-edit` here and not only on the listing.* The README is what
every listing and site skill lifts from, so a sentence that reads badly here is copied
onto the store page and the website, in each locale. The records — bundle id,
platform, version, build settings, paths — are left alone: they are facts, not prose,
and tightening them costs precision for no reader.

**Cost of forgetting:** one awkward feature line, fixed on the store page, comes back
from the README at the next refresh.
