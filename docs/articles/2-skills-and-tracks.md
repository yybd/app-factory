*English · [עברית](2-skills-and-tracks.he.md)*

# An app factory: 40 skills that take an app from code to the App Store and Google Play

The usual way to steer a coding agent is one big instructions file: how to ship to Apple, how to write tests, how to update a price list.

For me that held up until roughly the third app. The file grew past what the agent keeps in focus, rules started to contradict each other, and the agent offered me an Android deploy while I was editing a website.

**The failure isn't that the agent forgets. It's that it was told everything at once, whether or not it applied.**

This is part two of a series on running AI agents across several repos. It covers what replaced the giant file: **App Factory**, an open-source library of Claude Code skills that works as a production line. It takes a repo with an app's code and carries it all the way to a live app on the App Store and Google Play.

---

## A skill is instructions plus the tool

In Claude Code, a skill is an instructions document that the agent loads **only when its description matches what you asked for**. Having 40 skills available costs about 7,000 tokens of descriptions, and you pay even that only in a repo where you turned them on.

The bigger difference is something else. An instructions file tells the agent *what* to do. A skill in the factory also brings a script that does it and checks the result. The agent orchestrates; the scripts execute.

---

## The production line: skills that build an app from zero to distribution

```
0  identity        name, features, one dossier everyone quotes
1  the binary      keys → signing → compliance → localization → icon → build
2  media           captured from the running app
3  copy            for each store, in every language
4  store listing   pull and diff before every upload
5  release         the binary to the store
6  after           reviews, prices, keywords
```

**0. Identity.** `app-identity` reads the code and decides the name with you. Its script, `check_name.py`, queries the iTunes Search API for competitors in your category. For every advantage you want to sell, it counts how many competitors already claim it. An advantage that more than four of them claim gets the label **TABLE STAKES — do not sell on this**.

Then `app-profile` writes one dossier, `profile.md`, from the code, competitor research with sources, and an interview with you. Every later text quotes it, and the iron rule is that **no skill invents a claim**.

**1. The binary.** Keys live outside every repo and are read in place, never copied or printed. A compliance scan runs before the build, because its findings change the project. It looks for known rejection causes:
- an API that needs a permission string and doesn't have one;
- an SDK without a privacy manifest;
- social login without Sign in with Apple;
- on Android, the target API level and permissions.

A fix that only adds something is applied automatically. A fix that removes something waits for you.

**2. Media.** `appstore-media` doesn't ask you for screenshots. It boots a simulator with a clean status bar (9:41, full battery), runs an XCUITest once per language, and frames the shots with a device bezel and a caption. For Hebrew captions it refuses to run if the imaging library can't lay out right-to-left text, because producing nothing beats producing text backwards. On Android, `play-store-media` captures with `adb`.

**3. Copy.** Each store gets its own fields within its own limits. Everything a customer will read goes through `copy-edit`, which has my favorite check: **it counts claims per language.** If the Hebrew has one claim fewer than the English, something fell out in translation. In a language nobody on the team reads, that is the only check there is.

**4. Store listing.** Both stores replace the whole image set they're given, and a blind upload overwrites edits someone made in the Console. So every upload starts with `pull_and_diff`, which pulls the **live** listing and compares it with what you hold. If both sides have text and it differs, it stops.

In-app purchases are set up automatically in both stores too. On Play that goes through the new API, because the old one now answers 403 for every app. I found that out when it broke halfway through a release.

**5. Release.**
- **Apple:** `ship-apple-app` checks that every piece is in place and sends anything missing back to the skill that owns it. Then it builds, validates and uploads.
- **Google Play:** `publish_aab.py` uploads the AAB, then **reads back what actually landed**. It supports a partial rollout, a `--dry-run` that discards at the end, and `--draft` for an app that has never been published, without which Play answers HTTP 400.

**6. After.** Review replies go out in the reviewer's language, never without an explicit yes. `price-sync` compares the prices in the app and on the website against one source of truth, and fails on any disagreement.

Two orchestrators sit above these steps. **`launch-app`** runs a first launch and keeps a state file, so a two-week launch doesn't start from scratch every time. **`prepare-app-release`** runs every version after that.

The line goes beyond the stores, too:
- direct Mac distribution: a separate target with Sparkle for updates, plus notarization and signing;
- WebView traps measured on real devices, for Capacitor apps;
- an SEO audit for the app's website.

---

## Where the human stays

The line stops on purpose at a few points, and that is written down in its own file, `TRUST.md`:
- **No script submits for review.** The upload lands as a draft, and a person presses Submit.
- **A price never changes automatically.**
- **Nothing is pushed to git** unless you ask in that moment.

It also says what it doesn't do: signing certificates are created in Xcode, Play's Console forms are manual work, and Windows isn't covered.

---

## What loads where

The skills are grouped into seven tracks, and each track is its own plugin:

| Track | Skills | Covers |
|---|---|---|
| `apple-track` | 16 | the App Store, the Mac App Store, and direct distribution |
| `android-track` | 9 | Google Play, and getting a build onto a device |
| `shared-track` | 7 | what is the same in both stores: identity, copy, release order, prices |
| `web-track` | 4 | a site's structure, an audit of it, and SEO |
| `capacitor-track` | 2 | web-in-a-shell apps |
| `design-track` | 1 | design for any HTML interface |
| `factory-setup` | 1 | says when a repo looks like an app and no track is on |

**Nothing is global.** You turn a track on for one repo:

```bash
claude plugin marketplace add yybd/app-factory
cd ~/code/my-app && python3 ~/.claude/plugins/marketplaces/app-factory/factory/enable.py
```

The script detects what the repo holds (Xcode, Gradle, Capacitor, a website) and proposes the tracks that fit. A session opened in the website folder doesn't know `play-store-ship` exists, because that skill never loads there.

---

## Three things I learned the hard way

**1. A commit is not a deployment.** A Claude Code plugin is a *copy* in `~/.claude/plugins/cache`. I fixed a skill, committed it, reported it as fixed, and the machine went on running the broken version.

**2. `claude plugin update` compares versions, not content.** A change without a version bump reaches nobody. I measured it: six tracks answered "already at the latest version" while a byte comparison showed their copies were stale.

**3. A check that only ever ran on the machine it was written on hasn't been tested.** CI failed the first time I pushed to GitHub, because of one library that was installed on my machine and not on the runner.

---

## Summary

There's no magic here, and no promise that the agent won't make mistakes. There is a production line: every step knows what it needs from the step before it, every script checks before it writes, and every step with no way back stays in your hands. **And every instruction loads only where it's relevant.**

The project is open source (MIT): **[github.com/yybd/app-factory](https://github.com/yybd/app-factory)**. It is built for Claude Code and tested only there. `QUICKSTART.md` walks the whole thing in fifteen minutes, on one app.

*Part one: what happens when an agent standing in one repo writes into another, and why the fix was hooks rather than one more line in `CLAUDE.md`. That's [RepoGuards](https://github.com/yybd/repo-guards).*
