# price-sync — what running it taught

**What belongs here, and what does not.** `SKILL.md` is the method: what to do, in what
order. This file is what was **learned by running it** — the facts that were discovered
rather than designed, each with the run that produced it.

**Why it lives here and not in a project's memory.** A lesson about this operation
belongs to none of the places it touches. *"Lemon Squeezy rounds to `.99`"* is not a
fact about the hub, or the site, or one app — it is a fact about changing a price. Filed
under any one project it loads in that project's sessions and never in the others, which
is where it is needed. Filed here it travels with the skill, to every session the skill
loads in.

**Adding one.** A dated line, what was expected, what happened, and what it costs to
forget. If it is a rule about how to do the work, it belongs in `SKILL.md` instead.

---

## The same figure means different things in different lines

*From the run that produced this skill.* A bulk replace of one price is wrong, and the
first run hit every variety in a single pass:

- the app's **store** price and its **direct** price, which differ on purpose
- a **competitor's** price quoted in a market section
- a **historical** note — "raised from $9.99" — which must keep its old number to still
  make sense
- a **screenshot caption** describing an image that shows the old price, where the text
  and the picture have to change together or not at all

**Cost of forgetting:** a find-and-replace corrupts a competitor comparison and a
history note in one keystroke, and both read as correct afterwards.

## Every price bug so far came from copying one document into another

*Recorded in the skill as the reason for step 1.* Not one came from an API being wrong.
Both stores are a single call away, and the verifier asks them; a figure taken from a
sibling document is a figure whose age nobody knows.

**Cost of forgetting:** the copy looks authoritative — it is in a file, formatted like
data — and it propagates further on the next run.

## The audit answers a question no session can

*2026-09-10.* Running the verifier with nothing changed returned agreement across
`prices.json`, App Store Connect, Lemon Squeezy, every hub document, every `.storekit`
and every page on the sites. That run is the shape worth remembering: **the operation's
trigger is not only "I decided to change a price" but "reality moved while nobody ran"**
— someone edited a dashboard, and no session, no commit and no journal records it. Only
asking does.
