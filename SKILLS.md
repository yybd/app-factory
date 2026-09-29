*English · [עברית](SKILLS.he.md)*

# Skills and tracks

The rule that decides where a skill lives: **a skill needed while working on an app
lives in the factory, inside the track it belongs to; a skill needed only while standing
inside one particular project lives in that project.**

For how loading and deployment work, see [HOW-IT-WORKS.md](HOW-IT-WORKS.md).

---

## The tracks

Skills are grouped into tracks, and a track is enabled **per repo**, in that repo's own
`.claude/settings.json` — written by `factory/enable.py`, or from one central registry
when grove is installed.

**The guards are not here.** `grove` is its own marketplace and is **optional**. It
decides where tracks load from one central registry, which is the right answer once you
work across several repos. Without it, `factory/enable.py` enables tracks per repo.

| Track | Skills | Intended for |
|---|---|---|
| `apple-track` | 16 | app repos |
| `android-track` | 9 | app repos |
| `shared-track` | 7 | app repos **and** the hub |
| `web-track` | 4 | the website |
| `capacitor-track` | 2 | app repos |
| `design-track` | 1 | apps and the site alike |
| `factory-setup` | 1 | **everywhere** — see below |

*Counted from disk, and checked: `factory/check_skills.py` fails when a number written
here stops matching what is on disk. Copied counts were wrong repeatedly, which is why
they are no longer trusted to a person's memory.*

---

### Apple track — 16

`ship-apple-app` · `app-store-deliver` · `app-store-metadata` ·
`app-store-review-compliance` · `app-store-reviews-responder` · `apple-credentials` ·
`code-signing-provisioning` · `apple-app-store-screenshots` · `appstore-media` ·
`apple-bug-flow-review` · `apple-hig-design-review` · `notarize-and-distribute` ·
`macos-direct-distribution` · `app-icon-generator` · `aso-keywords` · `localization-i18n`

**Note:** several of these look generic — an icon generator, localization — and are not.
They are specific to Apple's system: `.xcstrings`, ASO fields that exist nowhere else.

### Android track — 9

`play-store-ship` · `android-credentials` · `play-store-compliance` ·
`play-store-metadata` · `play-store-media` · `android-icon-generator` ·
`play-store-deliver` · `play-store-reviews-responder` · `android-run-device`

### Shared track — 7

* **Cross-store tooling:** `prepare-app-release` (the main orchestrator) · `launch-app`
  (a first release) · `app-identity` (deciding the name for both stores) · `copy-edit`.
* **Hub skills:** `app-profile` · `store-metadata-writer` · `price-sync`.

The hub skills run while you work on an app but write straight into the hub, which is
why they must be shared rather than living in either place.

### Design track — 1

`frontend-design`. Entirely generic, and needed anywhere a user interface is built —
HTML/CSS inside a Capacitor app or on the site.

### Web track — 4

`page-builder` · `web-design-guidelines` · `web-seo` · `content-site-structure`. Page
structure, SEO, and site review — plus the content-site scaffold, which is the one
skill here that runs **only when the user asks for it by name**: it writes a repo's
whole content tree, so it must never start because a site happened to be mentioned.

### `factory-setup` — 1

`factory-setup`, and one `SessionStart` hook. **This is the only track that is on
everywhere**, and that is exactly what it is for: a repo where nobody enabled a track
loads no skills, and looks identical to a repo where the skills decided they were not
relevant. Both are silence. The hook says so once per repo, and the skill turns the
right tracks on.

With grove installed, its `register-project` and `deploy` skills do the same job from a
central registry, for someone working across many repos. Neither is required.

### Local skills

A project can carry skills of its own, in its `.claude/skills/`. A site repo might hold
`add-app-to-site`, `translate-site`, `reference-page` — each edits only that site's own
assets, so there is no reason for them to load in the factory or in an app.

A local skill should declare what it owns in that repo's `.claude/owns.json`, so a
session standing elsewhere is refused rather than silently bypassing it. The factory
reports any local skill that no declaration covers.


---

## Apple ↔ Android: what is mirrored, and what is not

| Role | Apple | Android |
|---|---|---|
| Build and upload | `ship-apple-app` | `play-store-ship` |
| Certificates and signing | `apple-credentials` + `code-signing-provisioning` | `android-credentials` — one, because Android has no provisioning profiles |
| Store policy | `app-store-review-compliance` | `play-store-compliance` |
| Listing files | `app-store-metadata` | `play-store-metadata` |
| Listing delivery | `app-store-deliver` | `play-store-deliver` |
| Media | `appstore-media` (produce) + `apple-app-store-screenshots` (conform one image) | `play-store-media` — one, because Play has no per-device size table |
| Icons | `app-icon-generator` | `android-icon-generator` |
| Reviews | `app-store-reviews-responder` | `play-store-reviews-responder` |
| ASO | `aso-keywords` — the hidden 100-character field | **inside** `play-store-metadata`: Play has no keywords field, so its ranking reads the visible copy |
| Getting a build onto a device | — | `android-run-device` |
| Design review | `apple-hig-design-review` | **a gap.** No Material or Android accessibility review exists here |
| Bug and flow review | `apple-bug-flow-review` | `capacitor-bug-flow-review` covers a web shell; **native Android is a gap** |
| In-app localization | `localization-i18n` | `capacitor-localization` covers JS and HTML; **`strings.xml` is a gap** |

**The three gaps are real and named on purpose.** A parity table that quietly omitted
them would read as completeness. Where a skill exists on one side only, that side's
skill says so in its Boundaries.

**Why some roles are one skill and some are two.** Each split was decided from what the
work actually is, not from symmetry. Apple has two credential skills because creating a
certificate and diagnosing a build that will not sign are different jobs with different
inputs; Android has one because there is one artefact. Apple has two media skills
because producing a set and conforming a single image are different scales of work.

## Who owns what

One topic, one owner. Everything else draws from it. This is the table that decides
which skill to reach for when two look plausible — and each skill's own `Boundaries`
section says the same thing from its side.

| Topic | Owner | Who draws from it |
|---|---|---|
| The app's name, subtitle, and the README identity block | `app-identity` | every metadata, ASO and media skill; runs before all of them |
| The product profile everything is written from | `app-profile` | `store-metadata-writer`, and any site skill |
| Listing text for both stores, kept consistent | `store-metadata-writer` | the two per-store metadata skills |
| The per-store files, limits and validation | `app-store-metadata` · `play-store-metadata` | the two delivery skills read what they produce |
| Uploading a listing | `app-store-deliver` · `play-store-deliver` | nobody — they are the send surface |
| Building, signing and uploading a binary | `ship-apple-app` · `play-store-ship` | nobody |
| The canonical media tree | `appstore-media` | `apple-app-store-screenshots` writes into it; the delivery skills stage from it |
| The 100-character keyword field | `aso-keywords` | `app-store-metadata` writes what it decides |
| Certificates and credentials | `apple-credentials` · `android-credentials` | every skill that signs or uploads |
| A price, everywhere it appears | `price-sync` | nobody — and it never changes one |
| Every customer-facing sentence | `copy-edit` | run over anything before it ships |
| The order a release happens in | `prepare-app-release` (an update) · `launch-app` (a first) | they drive the rest |

---

## The Capacitor path

Capacitor apps are web apps in a native shell, and Apple's standard quality skills —
which look for `.strings` files and native UI — do not apply to them. Hence a dedicated
track:

* **`capacitor-localization`** — checks strings in JavaScript and in HTML templates,
  catches silent translation failures (a Hebrew key shown to an English user), and
  verifies that language templates are siblings rather than merely adjacent.
* **`capacitor-bug-flow-review`** — QA for the seam between the web app and the mobile
  shell. It carries a catalogue of known Capacitor traps (no Web Share in the Android
  WebView, the familiar performance bottlenecks) and how to inspect the WebView from a
  desktop browser.
