---
name: factory-setup
description: >-
  Set up the app factory in a repo, or say why its skills are not loading. Use when a
  store or release skill that should exist is missing, when the user asks "why aren't
  the skills loading here", "set up the factory", "enable the tracks", "which tracks
  does this repo need" ("למה אין לי את הסקילים", "תפעיל את המסלולים"), or after
  installing the marketplace for the first time. It reads the repo to decide what it
  is, proposes the tracks that follow, and writes the repo's own
  .claude/settings.json. It does NOT install plugins, does NOT change the machine's
  global settings, and does NOT commit — enabling a track is a fact about one repo.
---

# Setting up the factory in a repo

A track is enabled **per repo**, in that repo's own `.claude/settings.json`. That is
deliberate: App Store skills have no business loading in a website, and a plugin
installed at user scope loads in every directory on the machine.

The cost of that choice is a failure with no symptom — a repo where nothing was
enabled looks exactly like a repo where the skills decided they were not relevant.
Both are silence. This skill exists to break it.

## Prerequisites

- **Tools:** none beyond Claude Code and Python 3 (stdlib).
- **Credentials:** none.
- **Hub (`$APP_HUB`):** not used.
- **Other tracks:** none — this one is about which of them load.

The marketplace has to be known to this machine once:

```bash
claude plugin marketplace add <path-or-github-repo>
```

## Workflow

**1. Look at what is already on.**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/enable.py --check
```

It prints which tracks this repo has, and — when it has none — what the repo looks
like and which tracks would follow.

**2. Enable them.** The proposal comes from files the project has whether or not
anyone described it: an `.xcodeproj`, a `build.gradle`, a `capacitor.config.ts`.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/enable.py --yes          # take the proposal
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/enable.py --tracks a,b   # choose instead
```

The tool ships inside this plugin, so that path exists on any machine that installed
the marketplace — including one that added it from GitHub, where there is no
`~/app-factory` to run anything out of. `<checkout>/factory/enable.py` is a shim that
runs the same file, for the documentation that points at it.

**3. Install what is now enabled**, once per machine. Enabling and installing are two
different things, and a track enabled but not installed loads nothing:

```bash
claude plugin install <track>@app-factory
```

> **The CLI will then say the plugin is "disabled by default — enable it with
> `claude plugin enable`". Do not run that** — it switches the track on for every
> directory on the machine, which is the one thing per-repo enablement exists to
> prevent. The settings file written in step 2 is what enables it here.

**4. Open a new session.** Skills load at session start; nothing takes effect in the
session that ran the command.

## The trap worth knowing

Claude Code reads settings from **the directory the session opened in**, not from the
git root. A repo enabled at its root gives a session opened two directories down
nothing at all. Enable it where you actually work — a monorepo with an app in
`apps/mobile/` needs the settings there.

## Boundaries

- **It writes one file in one repo**, and only the `@app-factory` keys inside
  `enabledPlugins`. Every other key, and every plugin from another marketplace, is
  left as found.
- **It does not install, and does not commit.** Installing is per machine; committing
  the settings file is the repo's decision.
- **It does not install, and `--check` says so.** A track enabled but not installed
  loads nothing, and `--check` fails on that rather than reporting the settings file
  as if it were the whole answer.
- **It does not set up credentials or a data repo.** `factory/init_keys.py` in the
  checkout makes the credentials folder; `factory/init_hub.py` makes a hub, if you
  want one.
- For many repos at once, and for the guards that keep a session from writing into the
  wrong one, that is [grove](https://github.com/yybd/cross-repo-guards) — a separate
  marketplace this one does not require.

## Related skills

Every track's own README lists what it holds: `plugins/<track>/README.md`.
