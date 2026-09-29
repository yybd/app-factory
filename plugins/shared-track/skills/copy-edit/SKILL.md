---
name: copy-edit
description: >-
  Tighten existing product copy — App Store / Google Play listing text, marketing and
  product sites, README marketing sections, in-app strings, replies to store reviews —
  when it reads clumsily: long sentences, stacked clauses, the same point made twice,
  throat-clearing openers, jargon the buyer does not know, or a translation that reads
  as a translation rather than as the language. Use when the user says copy is
  convoluted, wordy, clunky, unprofessional, hard to read, sounds machine-written,
  "מסורבל", "מנוסח רע", "נשמע כאילו מודל כתב", or asks to rewrite, tighten, sharpen or
  polish existing text in any language. This skill EDITS text that already exists; it
  does not decide what to say. Run it before delivering copy to a store or deploying a
  site.
---

# Copy edit — make it read once

This skill is the pass that finds the sentences a reader will stumble on, in every
language the text ships in. It applies a project's own voice rules; it does not
invent them.

**The gap this closes:** copy can pass every banned-word check and still be hard to
read. Clumsiness is a sentence problem — length, clause depth, repetition — and
nothing catches it unless something goes looking. In a language nobody on the team
reads, nothing is looking at all.

## Prerequisites

- **Tools:** none beyond Claude Code — `measure_copy.py` is stdlib Python 3.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — `$APP_HUB/PRODUCT.md` is the studio voice; without
  it the repo's own `PRODUCT.md`, `CLAUDE.md` or shipped copy sets the standard.
- **Other tracks:** `app-store-metadata` (apple-track) re-validates edited store
  fields; the deliver skills (`app-store-deliver`, apple-track; `play-store-deliver`,
  android-track) re-deliver them.

## The single test — two halves

**1. Can a reader get each sentence on the first pass?** If you have to re-read to
parse it, it fails, whatever else is right about it.

**2. Did the reader know what it means *for them*, immediately?** Parsing a sentence and
receiving its point are different things, and a sentence can pass the first and fail the
second. This half is not about simpler words or shorter sentences — it is about whether
the line lands as a thing the reader already recognises from their own use, rather than an
accurate description they then have to decode.

The test: after one read, could they say **what they would do with it** — not what the
sentence said. If they have to assemble the picture, it failed, however plain the words.

```
The app holds the text you send over and over and puts it where you type: a custom
keyboard on iPhone and iPad.
```

Every word is simple, the syntax is clean, and it passes every other check in this file.
It still fails, because "puts it where you type" makes the reader work out what that
means — autocomplete? does it type for me? — and the word that would have answered it,
*keyboard*, arrives after the colon. `The app puts the text you send over and over on a
keyboard you can reach inside any app` is longer and lands at once.

What this half catches that nothing else does:

- **An abstract mechanism where the reader already has a name for the thing.** "Puts it
  where you type" instead of "a keyboard".
- **Accurate but unanchored.** "A snippet and text-template manager" is true, and the
  reader still has to build the picture from it.
- **The point arriving in the second half of the sentence**, after the setup.
- **What it *is* structurally, instead of what it *does for you*.**

Everything below is a way of finding the sentences that fail either half before a
reader does.

## Workflow

### 1. Read the project's standard first

Find the voice standard and read it — don't work from memory, and don't invent
rules the project didn't set:

1. `PRODUCT.md` at the repo root, or in the hub the project belongs to
   (for a studio: `$APP_HUB/PRODUCT.md`, the master voice; a site or app
   repo may add a thinner layer on top of it).
2. Failing that, `CLAUDE.md`, a style guide, or the existing shipped copy.

The standard owns the voice, the banned vocabulary and the studio's own rules. This
skill owns the craft: sentence length, clause depth, restatement, jargon, the
rhythms of machine-written text, and translation alignment. If the standard is
silent on a point below, the point still applies — it is a property of readable
prose, not of one house style.

### 2. Measure before you judge

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/copy-edit/scripts/measure_copy.py <file-or-dir>...
```

It reports, per sentence: length, subordinate-clause markers, em-dash asides, and
**adjacent sentences with high word overlap** — the restatement pattern, which is
the defect that most reliably survives a manual read.

It reads **every locale**, not only English. The locale comes from the path
(`metadata/de-DE/description.txt`, `i18n/ja.json`, `profile.he.md`) and decides how
the text is measured: per-language clause markers, characters instead of words for
Japanese and Chinese, and a closing line naming any language that got the length
checks only — so "nothing found" in a language is never mistaken for "nothing
there".

Treat it as a spotlight, not a verdict. A 30-word sentence that reads cleanly can
stay; a 15-word one that has to be parsed twice must go. The tool finds candidates,
you judge them.

**And a clean report is not clean copy.** The spotlight warning above is usually read
as "some flags are false" — the more expensive direction is the other one. The script
measures length, clause depth and restatement. It cannot measure whether a point
arrives on the first read, which is the half of the test most failures live in. A
product page whose every sentence was short, unrepetitive and correctly built once
returned zero candidates while opening three consecutive sections with a negation the
reader had to hold before receiving the point. **Zero candidates means no length or
restatement problems were found. Read it yourself anyway** — start with §3b, then read
the whole thing once at a reader's pace.

### 3. Edit, in this order

Order matters: cutting first means not polishing sentences that shouldn't exist.

1. **Cut what repeats.** Two sentences making one point → keep the better one.
2. **Split what's compound.** One idea per sentence.
3. **Unstack the clauses.** At most one subordinate clause; no clause inside a clause.
4. **Delete the throat-clearing.** Start at the fact.
5. **Then** tune the wording.

**Stop when it reads.** A rule is a reason to *look*, not a reason to change. If the
sentence lands on the first pass, leave it — including when it runs long, and including
when it carries a dash. Every edit made to satisfy a rule rather than a reader is a
regression, and they accumulate faster than the flaws they replace.

### 3b. Strip the machine tells

Go through the text a second time looking only for these. They survive step 3
because each sentence is individually correct and short — they are rhythm, not
grammar:

- **Parallel runs of three or four.** The cadence is the tell; a person writes one
  clause or two.
- **Short sentences used for drama.** Once in a page is a choice, twice is a style.
- **The em-dash flourish** — an aside appended to make a line resonate rather than
  to add information.
- **Aphoristic closers.** A balanced fragment ending a section. Cut it.
- **Clever inversions as headings.** Name the thing instead.
- **The same promise, three times**, across an intro, a section and a footer.
- **Explaining the arithmetic** the reader can do.
- **Uniform rhythm.** Not every line gets the same shape — the `X — Y` em-dash template,
  or a run of sentences all landing between twelve and twenty words. A person writes
  unevenly: a long thought, then a short one. Mix periods, colons and commas.
- **The negation opener, repeated.** "A dial is not a background." "A collection is not
  a colour scheme." Each is a fine line; three in a row is a template, and the cost is
  not only rhythm. A negation makes the reader hold what the thing *is not* before
  they are given what it *is*, so a run of them delays the point section after
  section. One per page, where the wrong assumption is genuinely worth naming. The
  degenerate case is worth its own look: `not a photograph of a watch, and not a
  picture of one` denies two words that mean the same thing to the reader, which asks
  them to find a distinction that was never there.
- **Spec voice** — one clause, one fact, one length, no asides, nothing left implicit.
  Grammatically perfect and reads like documentation. **This is the one tell an editor
  creates rather than removes**, and the only one that gets *worse* the more carefully the
  rules above are applied. If a pass has split every long sentence and deleted every dash,
  it has probably produced this.

The test: would the developer who built the thing write that line in a README?

### 3c. Check the jargon against the audience

On a store listing or a product site, a term of art is either explained where it
first appears or replaced by its meaning; implementation detail that changes no
decision comes out entirely and stays in the spec.

Read a customer-facing string as someone who has never seen the product. "In
place", "recursive", "content signature", "security-scoped" are invisible to the
person who wrote them and opaque to everyone else. A project's standard may list
the terms its own copy keeps reaching for — read that list.

### 4. Every language: write the sentence, keep the text aligned

Each sentence in a target language is written from the **meaning**, in that
language's syntax. English carries long subordinate chains; most languages don't,
and a literal carry-over reads as translationese even when every word is correct.
The voice rules travel with it: hype words have equivalents in every language, and
they are just as banned.

**Across the text the versions stay aligned** — same claims, same order, one unit
to one unit; a bullet is one unit however the target language punctuates inside it.
Never merge two sentences into one, drop one, or add one.

Two reasons, and the second is the one that gets forgotten:

- The reviewer reads one language better than the others, and side-by-side review
  only works if the units correspond.
- In the languages nobody on the team reads, this comparison is the **only** check.
  A German listing that grew a claim and a Japanese one that lost a bullet look
  identical to a reader who cannot read them.

#### 4a. Read the target language on its own, not against the source

The unit-count comparison catches a lost bullet. It cannot catch a sentence where
every claim survived and the writing is still not the language — and that is the
common defect, because the person who wrote it was reading the English while they
typed. Take a second pass with the source **out of sight** and read only the target,
as someone who has never seen the English. Four things surface only that way:

- **A verb carried over by dictionary, not by meaning.** English `keeps` became a
  Hebrew verb for physically holding; `reads` became the verb for reading aloud,
  where the action was extraction. Each word maps to the entry in a dictionary and
  to nothing a person would say.
- **A grammatical frame that does not exist in the target.** English fronts a cleft —
  *"the slow part was never writing them"* — and the literal shape lands as a word
  order the reader has to re-parse. Rebuild the sentence around the same fact.
- **A pronoun that lost its referent in the reordering.** Word order changes between
  languages, so *"it"* and *"from there"* can end up pointing at the wrong noun, or at
  one buried three clauses back. Check every pronoun against what now precedes it.
- **A claim that dissolved inside a sentence rather than vanishing with its unit.**
  *"Nothing is uploaded, and it works offline"* came back as only the first half. The
  unit count still matches, so nothing flags it. Compare claims **within** each unit,
  not just the number of units.

None of this is visible to a checker, and none of it is visible to the person who
wrote the translation while looking at the source. It needs a reader of that language
reading it cold. When the project has one, that read is the step — send it, and treat
what they flag as a defect, not a preference. When it has none, say so plainly rather
than reporting the language as checked.

**A count mismatch means a claim was dropped or added — never that a sentence needs
splitting or merging.** Find the missing or extra claim and fix *that*. Reshaping a
sentence that reads well so a counter agrees is how a good paragraph becomes spec voice;
when the two languages genuinely say the same thing in a different number of sentences,
change the side that reads worse, or leave both alone.

`measure_copy.py` compares every locale against the English source — store metadata
directories, versioned release notes, `i18n/*.json`, and `x.md` / `x.<lang>.md`
twins — and reports differing unit counts, missing fields, and translations still
identical to the English. Treat a mismatch as a content bug until proven otherwise,
and check which side is wrong rather than assuming it is the translation.

### 5. Preserve meaning exactly

Editing is not re-deciding. Every fact, number, limit, product name and caveat in
the original must survive. If a sentence seems wrong rather than clumsy, that is a
question for the owner, not something to fix while tightening. Flag it, don't
silently rewrite it away.

### 6. Re-measure, then show the diff

Run the script again, then show the user before/after for the sentences that
actually changed — not the whole file. They are judging the writing, so give them
the writing, not a wall of context.

## Who runs this, and when

It is a step inside the authoring skills, not only something a user asks for by
name. Any skill that writes customer-facing text runs it before that text is
delivered: store listing metadata and release notes, product and marketing sites,
README marketing sections, in-app strings, and public replies to store reviews.

A user can also invoke it directly on text that already shipped.

## Where the pieces live

Keeping this updatable means knowing which file holds which half:

| Part | Where |
|---|---|
| The craft — this workflow, the checks, the order of edits | this file |
| The measurement | `${CLAUDE_PLUGIN_ROOT}/skills/copy-edit/scripts/measure_copy.py` |
| The voice — what the project sounds like, its banned words, its own jargon | the project's `PRODUCT.md` (the studio: `$APP_HUB/PRODUCT.md`) |
| Which skill runs this pass, at which step, over which surface | the map at the end of that `PRODUCT.md` |

A rule about **how sentences work** belongs here. A rule about **what we sound
like** belongs in the project's standard. When a new surface starts producing copy,
it gets a step in its own authoring skill and a row in that map.

## Boundaries

- **Does not decide content.** What the product is and why it's worth using comes
  from the project's own source of truth (for studio apps, `<slug>/profile.md`).
- **Does not author new store fields.** It edits fields that exist.
- **Does not change character-limited fields without re-validating.** Editing
  changes lengths, so re-run the store validator afterwards — for the App Store, the
  **`app-store-metadata`** skill's validator over `<metadata-root>` (that skill is in
  another plugin, apple-track, so invoke it by name and let it find its own script)
  (name ≤30, subtitle ≤30, keywords ≤100, promo ≤170, description ≤4000).
- **Edited text must be re-delivered.** Editing the source alone changes nothing the
  user can see: store text goes back through the deliver skill, site text through
  its build.
