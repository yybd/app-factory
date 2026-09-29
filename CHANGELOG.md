# Changelog

One version across all seven tracks, because they are not independent: a delivery script
runs `shared-track`'s copy measurer, `price-sync` reads `apple-track`'s credential
resolver. Per-track versions would need a compatibility matrix, and an unmaintained
compatibility matrix is worse than no version.

**A version is how an update reaches anyone.** `claude plugin update` acts when the
version moves, so a change that does not bump it is a change nobody receives.

This project follows [semantic versioning](https://semver.org). Before 1.0, a minor
bump may change a skill's behaviour; a patch fixes something without changing what a
skill does.

## Unreleased

## 0.4.0

A minor bump: two Android skills do something they did not do before. The first
release from the public repository.

- **`play-store-ship` (android-track): `--draft`.** An app that has never been
  published accepts only draft releases — the commit fails with HTTP 400 "Only
  releases with status draft may be created on draft app." `publish_aab.py --draft`
  creates one (exclusive with `--rollout`), and the error now names the flag.
- **`play-store-deliver` (android-track): one-time products through
  `monetization.onetimeproducts`.** The `inappproducts` resource the reference
  described answers 403 "Please migrate to the new publishing API" for every app. The
  reference is rewritten around the working flow — `convertRegionPrices`, a patch with
  `allowMissing`, then activating the purchase option — and the new
  `play_iap.py` runs it from the hub, stopping first when the default listing
  language or the price is missing.
- **The product-name check reads the whole tree, in any case.** It scanned `plugins/`
  only, case-sensitively, and treated `_` as part of a word — so a name inside a video
  filename in a script comment, and one inside a lower-case domain in a decision record,
  both passed. It now reads every tracked file, and the commit-message hook shares the
  same matcher. The two it found are gone.

## 0.3.0

A minor bump: one skill changed what it does, and a new one was added. The content
architecture of a multilingual site stopped being a convention every site is measured
against and became a scaffold you ask for by name.

- **`content-site-structure` (web-track) — new, and it runs only when you ask for it.**
  It lays down the tree (`text/<lang>/` for prose, `data/` for records, `media/` for
  files, `i18n/<lang>.json` for UI strings), a `locales.json` manifest, an Astro engine
  that renders all of it at build time, and a validator. Its description says NOT
  baseline, NOT default, and the skill itself checks four things before writing a file:
  the user asked by name, no site is already in the tree, the site is not catalog-driven,
  and Astro is acceptable. Any one of those failing stops it — there is no partial
  scaffold of "the parts that are safe anyway".
- **It asks before it writes `locales.json`.** Four questions, two of which cannot be
  taken back: what a missing translation does (fail the build, render the default
  language with a visible notice, or hide the page — silence is not an option), and
  whether the default language lives at `/` or `/<lang>`. The second reaches every
  address the site will ever have indexed.
- **`page-builder` no longer prescribes a content tree.** Its step 8 declared
  `text/<lang>/`, `data/` and `media/` a baseline for every project — and a site
  already in this track keeps its prose in key/value i18n catalogs, so the pre-delivery
  checklist had been failing a live site since the day it was written. What remains is
  the principle: prose and UI strings are authored outside the markup, each in its own
  place, and no markup inside a translation value. The checklist now tests that, not
  one particular tree, and adds captions per language.
- **`frontend-design` says where content comes from.** The skill that actually writes
  the markup never mentioned it, so the convention died at the hand-off from planning.
  It now says to find the project's arrangement before writing markup — and to say so
  rather than invent one when there is none.

- **Commit messages are checked like files that ship, because they are.**
  `factory/check_commit_message.py` runs on `commit-msg` and refuses a message naming a
  machine path, a live URL or App Store id, or a product from the maintainer's list. The
  patterns are now defined once and imported by `tests/test_portability.py`, which asks
  the same three questions of shipped files. Where the name list is absent it says so
  and passes; `--no-verify` still skips it.
- **`deploy.py` installs that hook**, as its own step before verification.
  `core.hooksPath` is per-clone git config and is never committed, so a fresh checkout
  has the check off and nothing says so — the exact silence `deploy.py` exists for.

## 0.2.1

A patch: nothing changed what a skill does. Two documented claims were corrected after a
real release contradicted them, and a CI check stopped failing on work that was fine.

- **`pull_and_diff`'s `STALE` was documented as if it meant something.** It compares
  media by byte size, and Apple re-encodes every PNG it serves — so a pixel-perfect set
  reports STALE on every file. On one release it fired eighteen times and was wrong
  eighteen times. `app-store-deliver` now says to rule out re-encoding first, and gives
  the check that actually decides: download the live asset through its
  `imageAsset.templateUrl` and hash the decoded pixels, not the bytes.
- **A missing `keystore.properties` does not produce an unsigned AAB — `bundleRelease`
  dies.** `android-credentials` promised the quiet failure; the loud one is a bare
  `java.lang.NullPointerException (no error message)` at `:app:signReleaseBundle` that
  names neither signing nor the keystore, and sends you looking at the artifact instead
  of at the missing file. Both outcomes are now written down, with the NPE named as the
  first thing to trace back to this cause.

- **CI was failing on a check that passed everywhere it was written.** `check_scripts.py`
  exempts Pillow from the import check — a build runner has nothing installed — and then
  ran `--help` anyway, which the three image scripts refuse to answer without it. The
  exemption now covers both halves: a declared dependency that is genuinely absent makes
  a script "checked statically only", reported by name, never failed on. It is narrow —
  a real fault in those scripts still fails wherever Pillow is installed, which is every
  machine that runs the skill. And the runner now installs Pillow, so the gate exercises
  all 57 rather than 54.

## 0.2.0

A minor bump rather than a patch: several skills changed what they do, not only how
well. The changelog folder moved to `changelogs/<versionCode>/<locale>.txt`,
`prepare-app-release` swapped two steps, and `enable.py` now ships inside the
`factory-setup` plugin (`factory/enable.py` is a shim, so existing instructions still
work).

### What a stranger following QUICKSTART hit, fixed

- **`init_keys`, `init_hub`, `check_urls` read `$KEYS_ROOT` / `$APP_HUB` before grove.**
  They said "grove is not on this machine" to a reader the page had just told did not
  need it. The message, when it does appear, now says grove is optional and what to set
  instead. The dashboard still needs grove and says why.
- **`credentials.py --keystore <app>`** exists. `play-store-ship` had invoked it since
  0.1.0; the function existed and the flag did not.
- **One changelog shape**: `changelogs/<versionCode>/<locale>.txt`. `store-metadata-writer`
  said flat, `publish_aab --notes-dir` reads a folder. `prepare-app-release` bumps the
  version *before* writing the changelog whose folder is named after it.
- `stage_release.sh` works from the project, not from inside the plugin cache.
  `asc_common.rb` no longer swallows the argument after a boolean flag (`--force
  --locales en-US` uploaded a preview to every locale). `verify_assets.py` fails on a
  path that does not exist instead of passing with "0 checked". `frameshot.py` says
  Pillow is missing instead of a traceback. The localisation scan no longer counts
  `id:`/`on:`/`to:` as languages.
- **`enable.py`** honours a `false`, enables a monorepo app in the directory the session
  opens in, does not propose `web-track` for a Capacitor app's own `index.html`, reports
  enabled-but-not-installed as a failure, and warns about the CLI's "enable it with
  `claude plugin enable`" hint, which enables globally.
- **The setup hook** prints the real path of `enable.py` (a GitHub-added marketplace is
  cloned whole into `~/.claude/plugins/marketplaces/`), speaks up when the tracks are
  enabled at the git root and the session opened below it, and names a settings file
  that exists and does not parse.
- Skills stopped describing what does not ship: `web-seo`'s `snapshot.py`, `price-sync`'s
  live store read.

### The hub stopped being assumed

- **Standalone works in Ruby too.** `asc_common.rb` aborted without `$APP_HUB`, so all
  seven App Store helpers died in the mode both deliver skills promise — including the
  step they call MANDATORY. `ASC.tree` now returns the hub when there is one and the app
  repo's own `fastlane/` when there is not, and both `pull_and_diff` guards run in either
  mode.
- **`## Prerequisites` at the top of every skill** — tools with their install commands,
  credentials and how they are found, whether the hub is required/optional/unused, and
  which other plugin's skills it leans on. Four of 39 had one.
- `launch-app` writes its state file to the repo without a hub; `play-store-media`,
  `play-store-ship`, `android-icon-generator` and `prepare-app-release` each gained the
  second path.
- **`DATA.md` is no longer described as where a credential lives** (11 places). The
  resolvers ranked it third and called it legacy; the prose said otherwise.
- One owner for Play graphics (`play-store-media`). `deliver_iap.rb` removed — an exact
  subset of `provision_iap.rb`. `notarize_dmg.py store-creds` removed — a fallback for a
  skill in the same plugin. `apple_creds.py check` asks the resolver instead of four
  folders of its own.

### Being installable by someone else

- **`enable.py` ships inside the `factory-setup` plugin**, so it is on any machine that
  installed the marketplace. `factory/enable.py` stays as a shim.
- **QUICKSTART's first line works**: `claude plugin marketplace add yybd/app-factory`,
  and `$AF` for the checkout it creates.
- **[FAQ.md](FAQ.md)** — a glossary of the eight words this project uses in a particular
  way, plus how to update, how to turn a track off, and what the CLI's "enable it with
  `claude plugin enable`" hint actually does (it enables globally).
- **[SECURITY.md](SECURITY.md)** — what is handled, what is checked, how to report.
- **`factory/bump_version.py`** — the version in all eight places, and the release steps
  printed rather than run. [CONTRIBUTING.md](CONTRIBUTING.md#releasing) documents them.
- `APP-LIFECYCLE.md` is a product map again: eight steps, both shapes, only skills that
  ship. The studio run-book it was is
  [`docs/decisions/3-studio-flow.md`](docs/decisions/3-studio-flow.md).
- `factory/deploy.py` is marked the maintainer's tool (it needs grove), reinstalls what
  `update` left stale, and `factory/README.md` indexes every script with that column.

### New checks

- **A missing or malformed `## Prerequisites`** (`check_skills --strict`): the four
  lines are fixed, and the hub one must say `not used` / `optional` / `required` —
  which is the word a person without a hub is looking for.
- Two descriptions sharing a **trigger sentence** without quoting it (`check_skills`) —
  three pairs were, and are not now. A shared boundary sentence is a note, not a failure.
- A **script named in a skill that ships nowhere** (`check_skills`).
- A test that ran **zero checks** is shown as `·` with "NOTHING VERIFIED", not `✓` (`ci.py`).
- **Product names**, from a list outside the repo (`~/.claude/.app-factory/fingerprints.txt`),
  because a name in prose has no shape a regex can find; skipped loudly when there is
  no list (`test_portability`). Its first run found one more.

## 0.1.0

The first version that exists as a version. Everything before it was a git SHA, which
is what `claude plugin update` fell back to — so "is it up to date" had no answer a
person could read.

Six tracks, 38 skills: Apple (16), Android (9), cross-store (7), web (3), Capacitor (2),
design (1).

### The install stopped assuming one machine

- **One credential resolver per track**, asked in a documented order: the environment,
  then `$KEYS_ROOT/credentials.json`, then the folder convention, then a studio hub's
  `DATA.md` for an installation that predates the JSON. Three mechanisms answered this
  before and they did not agree — one of them read an identifier out of labelled prose
  in a markdown file, which no other developer has.
- **The hub is optional.** Both delivery skills promised a mode where the repo's own
  `fastlane/` is the source of truth; no script implemented it, so it failed at the
  first command. It works now, and is selected automatically when there is no hub.
  Verification runs in both modes — only the copying is conditional.
- **The Android track stopped assuming Capacitor.** Native is the default; a hybrid
  project is an explicit branch. Both Gradle DSLs are read, and the JDK version is taken
  from the project's own toolchain rather than hardcoded.
- **No default language.** The localisation scan discovers a project's languages from
  its own translation tables instead of searching for Hebrew, and capture, templates and
  fonts take the locale from the app.
- **`price-sync` and `web-seo` ship their scripts.** Both drove tools that lived in a
  private repo, so for anyone else both skills began with a command that did not exist.

### Skills got a shape, and a checker that enforces it

- Every description is within budget, says when to use the skill and what it is **not**
  for, and carries trigger phrases in both languages. Ten were over budget; the largest
  was 2,675 characters — a document, loaded in every session that enabled the track.
- Every skill has a `Boundaries` section. Twenty had none, and overlap is what a library
  this size produces on its own: three skills claimed the screenshot job.
- `factory/check_skills.py` enforces all of it, including the failure that is invisible
  on screen: a hyphenated word split across lines, which a folded YAML scalar turns into
  two words and a skill name that matches nothing.

### Single sources for things written many times

- Apple's accepted media dimensions, in one JSON the scripts read and the reference
  table is generated from. Seven copies had already disagreed about which iPhone family
  a size belongs to.
- The certificate table, read by both signing skills instead of written out twice.
- Each track's README is generated from the skills it holds.

### Fixed

- `reviews.py` and the dashboard's store column referred to a name their module never
  defined; the Play reviews skill could not run at all, including `--help`.
- The dashboard read a registry path that exists only where someone had made it a
  symlink by hand, so it could not run on a fresh clone.
- Around 25 script references resolved only from a directory a session is never in.
- Seven shipped scripts defaulted to a path under one person's home directory.
- The Play metadata scripts did not understand the layout their own skill sends them to,
  and created `images/icon/` as a directory where `supply` reads `images/icon.png`.
- The hub contract, its initialiser and the skills described three different trees.
- `app-profile` resolved the hub with `git rev-parse`, so from an app repo it wrote the
  profile into the wrong repository.
- Contradictions between skills: the media/copy order, which skill uploads, the Play
  changelog shape, and an in-app-purchase limit that was wrong by 120 characters.

### Licensing

- `frontend-design` is Apache-2.0, derived from `anthropics/skills`; its licence and a
  notice of what was changed now ship beside it.
- `web-design-guidelines` is MIT, © 2025 Vercel Labs, and says so.
- Both plugin manifests previously claimed the work as MIT and ours.

### Checkers

Four were green while every one of the above was true. Each now catches its own blind
spot, and each was verified by reintroducing the bug it was written for:

| | was | now |
|---|---|---|
| `check_scripts` | parse and imports | also runs `--help`, which is what catches a missing attribute |
| `test_portability` | `.md` and `.json` | every shipped file, plus real app names and store ids |
| `check_references` | anchored paths only | relative paths resolved against the citing file |
| `check_bilingual` | documents with a language line | also those without one |
