*English · [עברית](2-skills-and-tracks.he.md)*

# From one instructions file to 40 skills: why I stopped writing a giant CLAUDE.md

The usual way to steer a coding agent is one big instructions file. People pack hundreds of lines into `.cursorrules` or `CLAUDE.md` to teach the agent every workflow: how to ship to Apple, how to write tests, how to update a price list.

For me that held up until roughly the third app. The file grew past what the agent keeps in focus, rules started to contradict each other, and the agent offered me an Android deploy while I was editing a website.

**The failure isn't that the agent forgets. It's that it was told everything at once, whether or not it applied.**

This is part two of a series on running AI agents across several repos. It covers what replaced the giant file: **App Factory**, an open-source library of Claude Code skills that build, describe and ship apps to the App Store and Google Play.

---

## A skill is a document that loads only when it's needed

In Claude Code, a skill is an instructions document, sometimes with scripts next to it. The agent loads it **only when its description matches what you asked for**. The descriptions are the only part that is always in context.

That changes the math. Having 40 skills available costs about 7,000 tokens of descriptions, not tens of thousands of lines of instructions. And you pay even that only in a repo where you turned them on.

---

## Tracks: what loads where

The skills are grouped into seven tracks, and each track is its own plugin:

| Track | Skills | Covers |
|---|---|---|
| `apple-track` | 16 | the App Store, the Mac App Store, and direct distribution outside both |
| `android-track` | 9 | Google Play, and getting a build onto a device |
| `shared-track` | 7 | what is the same in both stores: naming, copy, release order, prices |
| `web-track` | 4 | a site's structure, an audit of it, and whether search engines find it |
| `capacitor-track` | 2 | web-in-a-shell apps, where the bugs live in the seam |
| `design-track` | 1 | visual craft for any HTML interface |
| `factory-setup` | 1 | on everywhere; says when a repo looks like an app and no track is on |

**Nothing is global.** You turn a track on for one repo, and it is written into that repo's `.claude/settings.json`:

```bash
claude plugin marketplace add yybd/app-factory
cd ~/code/my-app && python3 ~/.claude/plugins/marketplaces/app-factory/factory/enable.py
```

The script reads the repo, works out what it is (Xcode? Gradle? Capacitor? a website?) and proposes the tracks that fit. A session opened in the website folder doesn't know `play-store-ship` exists, because that skill never loads there.

---

## Executors and orchestrators

The more skills I wrote, the clearer it became that shipping a release isn't one task. It's seven steps, and things go wrong not in any one step but **in the order between them, and in the step nobody remembered**.

So there are two kinds of skill:

1. **Executors** do one thing. `play-store-ship` builds, signs and uploads an AAB. `app-icon-generator` writes every icon size from one image.
2. **Orchestrators** put the executors in order without doing their work. `prepare-app-release` runs identity, store-policy compliance, media, copy, version bump, build and upload. The website part it **hands off explicitly** instead of doing it quietly, because the site's own skills load only inside the site's repo.

---

## What the skills do to your repo

That's the first question I'd ask before turning on 40 documents that run scripts, so it has its own file, `TRUST.md`.

In short: the skills write files in the repo you point them at, and they read keys and passwords in place, without copying or printing them. They upload to the stores only at the end of skills whose whole job is uploading, and an upload lands as a draft. **They never submit an app for review, never change a price, and never push to git unless you ask in that moment.**

---

## Three things I learned the hard way

**1. A commit is not a deployment.** A Claude Code plugin is a *copy* in `~/.claude/plugins/cache`. I fixed a skill, committed it, reported it as fixed, and the machine went on running the broken version. Between "I committed it" and "it is running" there are two steps, and one of them is opening a new session.

**2. `claude plugin update` compares versions, not content.** A change without a version bump reaches nobody. The command answers "already at the latest version" and copies nothing. I measured it: six tracks gave that answer while a byte comparison showed their copies were stale. Since then there is one version for all the tracks, and one script writes it in all eight places.

**3. A check that only ever ran on the machine it was written on hasn't been tested.** CI failed the first time I pushed to GitHub, on a check that had been green on every machine it had ever run on. The difference was one library that was installed on mine and not on the runner.

---

## The knowledge moves from the prompt into the structure

There's no magic here, and no promise that the agent won't make mistakes. What there is is more modest: **every instruction loads only where it is relevant.** What doesn't load can't conflict, can't be forgotten, and can't fire by accident.

The project is open source (MIT): **[github.com/yybd/app-factory](https://github.com/yybd/app-factory)**. It is built for Claude Code and tested only there: the scripts the skills run are ordinary command-line tools, but the per-repo loading is Claude Code's plugin system. `QUICKSTART.md` walks the whole thing in fifteen minutes, on one app, with a check after every step.

*Part one of the series: what happens when an agent standing in one repo writes into another, and why the fix was Claude Code hooks rather than one more line in `CLAUDE.md`. That's [RepoGuards](https://github.com/yybd/repo-guards).*
