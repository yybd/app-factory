*English · [עברית](2-skills-and-tracks.he.md)*

# An app factory: 40 skills that take an app from code to the App Store and Google Play

The usual way to steer a coding agent is one big instructions file. People pack hundreds of lines into `.cursorrules` or `CLAUDE.md` to teach the agent every workflow: how to ship to Apple, how to write tests, how to update a price list.

For me that held up until roughly the third app. The file grew past what the agent keeps in focus, rules started to contradict each other, and the agent offered me an Android deploy while I was editing a website.

**The failure isn't that the agent forgets. It's that it was told everything at once, whether or not it applied.**

This is part two of a series on running AI agents across several repos. It covers what replaced the giant file: **App Factory**, an open-source library of Claude Code skills that works as a production line. It takes a repo with an app's code and carries it all the way to a live app on the App Store and Google Play: the name, signing, store-policy compliance, screenshots, copy in every language, in-app purchases, upload and release. Everything described here comes from the skills' own code.

---

## A skill is a document that loads only when it's needed

In Claude Code, a skill is an instructions document, usually with scripts next to it. The agent loads it **only when its description matches what you asked for**. The descriptions are the only part that is always in context.

That changes the math. Having 40 skills available costs about 7,000 tokens of descriptions, not tens of thousands of lines of instructions. And you pay even that only in a repo where you turned them on.

The real difference isn't the tokens, though. An instructions file tells the agent *what* to do. A skill in the factory also brings the tool that does it: a script that checks your name against Apple's length limit, captures the app in a simulator, or uploads the AAB to Play and shows you what landed. The agent orchestrates; the scripts execute and check.

---

## The production line

This is the full path of an app, from the first line of code to the next version:

```
0  identity          app-identity · app-profile          name, features, one dossier everyone quotes
1  the binary        credentials → signing → compliance → i18n → icon → build
2  privacy URL       required before any store will accept a submission
3  media             appstore-media · play-store-media   captured from the running app
4  version           read from the project file, never from memory
5  copy              store-metadata-writer → each store's metadata skills
6  store listing     app-store-deliver · play-store-deliver   pull and diff first
7  binary to store   ship-apple-app · play-store-ship
8  after             review replies · price sync · keywords
```

### Step 0: identity, before anyone quotes it

**`app-identity`** starts from the code. Its script `read_app_identity.sh` pulls the product name, display name, bundle id and localized names out of the project. Then the skill decides three names with you: the one under the icon, the store name, and the subtitle.

That decision has a real script behind it, `check_name.py`:
- It queries the public iTunes Search API for the apps in your category.
- It checks the 30-character limit on name and subtitle, and words repeated between the two.
- It checks whether the second half of your name already appears in a competitor's name.
- And the most interesting part: for every advantage you want to sell, it counts how many competitors already claim it in their descriptions. An advantage that more than four of them claim gets the label **TABLE STAKES — do not sell on this**.

The skill never picks the name on its own ("Never pick the name unilaterally"), and it says outright that it can't clear a trademark.

**`app-profile`** writes one dossier, `profile.md`, that every copy skill quotes. It reads the code (strings, screens, entitlements, StoreKit), researches competitors on the web with a source for every claim, and interviews you.

Its iron rule: **no skill invents a claim.** If a field is wrong, you fix it in the dossier, not in the listing. Without web access, the market section is marked TODO rather than guessed.

### Step 1: the binary

**Keys.** `apple-credentials` and `android-credentials` are the only owners of certificates and keys. The secrets live outside every repo, under `$KEYS_ROOT`, and are read in place. They are never copied or printed.

**Signing.** `diagnose_signing.py` does three things:
- lists your signing certificates (`security find-identity`);
- decodes and classifies every provisioning profile;
- reads the signing settings out of `project.pbxproj`.

A detail I learned the hard way: `-allowProvisioningUpdates` only creates development profiles. So the App Store distribution profile is created through the App Store Connect API, without opening a browser.

**Compliance, before the build.** `scan_project.py` scans the project and returns evidence, not a score. Among other things, it looks for:
- an API that needs a permission string, such as `AVCaptureDevice` without `NSCameraUsageDescription`;
- "Required-Reason APIs" such as `UserDefaults`;
- a third-party SDK without a privacy manifest, a known cause of ITMS-91053 rejections;
- social login without Sign in with Apple, and account creation without a way to delete the account.

Findings are ranked in four tiers, from 🔴 blocker to ⚪ info. Fixes that only add something, such as a permission string or a `PrivacyInfo.xcprivacy` skeleton, are applied automatically. A fix that removes something waits for your approval.

On the Android side, `play-store-compliance` checks the target API level, permissions, and the list of forms you have to fill in on the Console.

Compliance runs *before* the build because its findings change the project. If you find them after archiving, you archive twice.

**Localization.** The scripts find missing, unused or untranslated keys, and text hardcoded in the source.

**Icons.**
- On iOS: one 1024 icon.
- On Android: the adaptive icon is scaled to fit the 66-of-108dp safe zone. `--safe-zone-check` shows what would be cropped before a single file is written.

### Step 3: media from the app itself

**`appstore-media`** doesn't ask you for screenshots. It takes them:
1. `capture_ios.sh` boots a simulator and sets a clean status bar: 9:41, full battery, full signal.
2. It runs an XCUITest once per language, recording video at the same time.
3. It exports the stills from the test results.

Then three scripts prepare the output:
- **`frameshot.py`** puts a device bezel and a caption band around the shot. For Hebrew captions it **refuses to run** if the imaging library can't lay out right-to-left text. Producing nothing beats producing text backwards.
- **`convert_preview.sh`** makes a preview video at exactly the size Apple wants. It cuts anything over 30 seconds, rejects anything under 15, and adds a silent audio track, because a preview without one is rejected.
- **`verify_assets.py`** checks every file against one table of sizes and fails on any mismatch.

On the Android side, `play-store-media` captures with `adb` and produces the feature graphic at exactly 1024×500. Play requires it before a listing can go live.

### Step 5: copy, in every language, without inventing anything

**`store-metadata-writer`** reads the dossier and writes each store's fields within that store's limits. Along the way:
- it never puts a price in the text;
- it checks that the privacy URL actually loads, using a browser User-Agent, because a 403 served to a bot doesn't prove the page is missing;
- it knows the small Hebrew trap: Apple calls the language `he`, and Play calls it `iw-IL`.

Every piece of text a customer will read goes through **`copy-edit`**. Its script, `measure_copy.py`, measures:
- sentences that are too long, and stacked clauses, with separate lists for English, German, French, Spanish and Hebrew;
- adjacent sentences that restate each other;
- **parity between translations: it counts claims per language.** If the Hebrew has one claim fewer than the English, something fell out in translation. In a language nobody on the team reads, that is the only check there is.

### Step 6: the store listing, and a pull before every upload

This is the step that costs the most when it's skipped. Someone edited the listing in the Console between releases, and a blind upload overwrites their edits. Worse, both stores replace the whole image set they're given, so an image you didn't send is simply deleted.

So every upload starts with a mandatory script, `pull_and_diff`. It pulls the **live** listing from the store and compares it with what you hold. The result is one of three:
- **in sync**: everything matches.
- **adds**: the store field is empty, so filling it is safe.
- **CONFLICT**: both sides have text, and it differs. Stop and carry the change back into the source text.

Media is checked too. On Play, the comparison is by the SHA-256 of each image, not by file name.

The upload itself uses `fastlane deliver` and `supply`:
- for Apple, `submit_for_review: false` is set explicitly;
- for Play, a `--validate_only` run goes first, and the real upload only after it.

**In-app purchases** are set up automatically in both stores:
- **Apple:** `provision_iap.rb` creates the product, its translations, the reviewer note, the price, the availability and the reviewer screenshot. A step that's already done reports "already set" instead of being rewritten.
- **Play:** `play_iap.py` works against the new API, `monetization.onetimeproducts`. The old `inappproducts` API now answers 403 for every app, which I found out when it broke halfway through a release. Prices for every country are computed with `convertRegionPrices` from one base price.

### Step 7: the binary to the store

**Apple.** `ship-apple-app` starts with a pre-flight table. Anything missing is sent back to the skill that owns it, because `ship-apple-app`'s job is to verify, not to author. Then it runs, in order:
1. `xcodebuild archive`
2. an export with manual signing
3. `altool --validate-app`
4. the upload
5. attaching the build to the version

**Google Play.** `publish_aab.py` opens an edit, uploads the AAB, assigns it to a track (`internal` by default) and commits. Then it **opens a fresh edit and reads back what actually landed**.

Its options:
- `--rollout 0.1` releases to 10% of users.
- `--dry-run` uploads and stages, then discards.
- `--draft` exists because of an app that has never been published. Play accepts only draft releases from such an app, and without the flag the commit fails with HTTP 400.

Any failure discards the open edit, so nothing is left half-done.

### Step 8: after release

- **Review replies** in both stores, in the reviewer's language. No reply is posted without an explicit yes for that reply.
- **`price-sync`** compares the prices in StoreKit files and on the website against one source of truth, `prices.json`, and fails on any disagreement. It never changes a price: it reports, and you decide.
- **`aso-keywords`** checks the keyword field and finds words wasted because they already appear in the name.

---

## Two orchestrators: the first launch and the next version

Each skill in those steps does one thing. Above them sit two orchestrators that put them in order without doing their work.

**`launch-app`** is for an app that has never shipped:
- It reads from the dossier where the app is distributed: App Store, Google Play, Mac outside the store.
- It keeps a state file for each launch, `LAUNCH.md`, updated in the same session that closes a stage. A launch that takes two weeks doesn't start from scratch every time.
- It enforces the order: identity before everything, the privacy URL before submission, media before copy.
- If the app already has a live listing, it stops and points you to the other orchestrator.

**`prepare-app-release`** is the same map for version N+1, in seven steps in a fixed order:
- The version number is set before the copy, because the changelog folder is named after the versionCode.
- It **hands off the website part explicitly** instead of doing it quietly, because the site's skills load only inside the site's repo.

---

## Outside the stores, too

**Mac, distributed directly.** `add_direct_target.rb` clones the App Store target into a separate one: no sandbox, hardened runtime on, and Sparkle for automatic updates. It's a separate target rather than a build configuration because Sparkle must never end up in the build that goes to the App Store. The proof is a search confirming there's no trace of Sparkle in the store build.

`notarize_dmg.py` runs the whole chain:
1. notarize the app, and staple it;
2. build the DMG and sign it;
3. notarize the DMG as well;
4. verify both with `spctl` and `stapler validate`.

It refuses to build a DMG from an app that hasn't been stapled.

`make_appcast.sh` signs every release with EdDSA. It uses `sign_update` rather than `generate_appcast`, because the latter silently skips signing when the keychain prompt can't appear.

**Capacitor.** The track carries a catalog of WebView traps measured on real devices. For example, `navigator.share` doesn't exist in Android's WebView, and `toBlob` took 4,120ms where `toDataURL` took 120ms. It also has a localization scanner that discovers the app's languages from the app's own tables.

**The app's website.** `web-seo` runs an offline audit of the built site. It checks titles and descriptions, canonicals, JSON-LD, reciprocal hreflang, orphan pages, broken links and thin content.

---

## Where the human stays

The line stops on purpose at a few points, and that is written down in its own file, `TRUST.md`:
- **No script submits for review.** The upload lands as a draft, and a person presses Submit.
- **A price never changes automatically.**
- **Nothing is pushed to git** unless you ask in that moment.
- **Secrets** are read in place, never copied or printed.
- Every upload and every store commit waits for approval, usually after a `--dry-run`.

And there are things the factory doesn't do, and it says so:
- Signing certificates are created in Xcode, not by a script.
- Play's Console forms (Data safety, the content rating, the payments profile) are manual work. The skill only lists them.
- Play subscriptions aren't scripted yet.
- Windows isn't covered at all.

---

## What loads where

The skills are grouped into seven tracks, and each track is its own plugin:

| Track | Skills | Covers |
|---|---|---|
| `apple-track` | 16 | the App Store, the Mac App Store, and direct distribution outside both |
| `android-track` | 9 | Google Play, and getting a build onto a device |
| `shared-track` | 7 | what is the same in both stores: identity, dossier, copy, release order, prices |
| `web-track` | 4 | a site's structure, an audit of it, and whether search engines find it |
| `capacitor-track` | 2 | web-in-a-shell apps, where the bugs live in the seam |
| `design-track` | 1 | visual craft for any HTML interface |
| `factory-setup` | 1 | on everywhere; says when a repo looks like an app and no track is on |

**Nothing is global.** You turn a track on for one repo, and it is written into that repo's `.claude/settings.json`:

```bash
claude plugin marketplace add yybd/app-factory
cd ~/code/my-app && python3 ~/.claude/plugins/marketplaces/app-factory/factory/enable.py
```

`enable.py` looks at the repo and proposes tracks from what it finds:
- `.xcodeproj` → the Apple track
- `build.gradle` → the Android track
- `capacitor.config` → the Capacitor track
- an Astro or Next config → the web track

Any native platform adds the shared track too. A session opened in the website folder doesn't know `play-store-ship` exists, because that skill never loads there.

---

## Three things I learned the hard way

**1. A commit is not a deployment.** A Claude Code plugin is a *copy* in `~/.claude/plugins/cache`. I fixed a skill, committed it, reported it as fixed, and the machine went on running the broken version. Between "I committed it" and "it is running" there are two steps, and one of them is opening a new session.

**2. `claude plugin update` compares versions, not content.** A change without a version bump reaches nobody. The command answers "already at the latest version" and copies nothing. I measured it: six tracks gave that answer while a byte comparison showed their copies were stale. Since then there is one version for all the tracks, and one script writes it in all eight places.

**3. A check that only ever ran on the machine it was written on hasn't been tested.** CI failed the first time I pushed to GitHub, on a check that had been green on every machine it had ever run on. The difference was one library that was installed on mine and not on the runner.

---

## The knowledge moves from the prompt into the structure

There's no magic here, and no promise that the agent won't make mistakes. There is a production line:
- every step knows what it needs from the step before it;
- every script checks before it writes;
- every step with no way back stays in your hands.

**And every instruction loads only where it's relevant.** What doesn't load can't conflict, can't be forgotten, and can't fire by accident.

The project is open source (MIT): **[github.com/yybd/app-factory](https://github.com/yybd/app-factory)**. It is built for Claude Code and tested only there. The scripts are ordinary command-line tools, but the per-repo loading is Claude Code's plugin system. `QUICKSTART.md` walks the whole thing in fifteen minutes, on one app, with a check after every step.

*Part one of the series: what happens when an agent standing in one repo writes into another, and why the fix was Claude Code hooks rather than one more line in `CLAUDE.md`. That's [RepoGuards](https://github.com/yybd/repo-guards).*
