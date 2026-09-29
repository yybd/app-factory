*English · [עברית](HOW-IT-WORKS.he.md)*

# How the Factory Works Under the Hood

This document explains the technical mechanics of the Factory: how a Skill you write loads into the AI agent's memory, why it only loads in specific projects, and how the Cache mechanism actually works.

> **Grove is optional.** [Grove (cross-repo-guards)](https://github.com/yybd/cross-repo-guards) decides which tracks load where from one central registry, and adds guards for working across several repos. Without it, `factory/enable.py` writes the same setting per repo, and everything below works the same way. This document is about how a track **loads**, which is the same either way.

---

## How does the system decide which tracks to load?

By default, if you install a Claude plugin, it loads **in every directory on your machine**. This is a disaster, as it means the AI will offer you App Store deployment skills even when you are working on a WordPress website.

To prevent this, the Factory operates on an **Opt-In** basis for each track, via 3 configuration layers:

```text
~/.claude/settings.json          ← User settings (every directory). Nothing from this
                                   marketplace belongs here except factory-setup.
<repo>/.claude/settings.json     ← Project Settings (loaded only here). Tracks are enabled here!
<repo>/.claude/settings.local.json
```

**The lever:** a project's own `.claude/settings.json` can turn on a track that the user's settings never mention. Two ways to write it, and they produce the same file:

```
factory/enable.py             →  <repo>/.claude/settings.json     one repo, no registry
$GROVE/tools/registry.json    →  <repo>/.claude/settings.json     many repos, from one list
```

### The Directory Trap
Note that Claude Code reads `settings.json` from the **directory where the session was opened (cwd)**, not from the Git root!
Therefore, if you open a session in `<project>/`, all tracks will load. But if you navigate down to `<project>/apps/mobile/` and open a session there – the AI won't find the file, and will load **zero tracks**.
*Solution:* enable the track in the directory you actually open sessions in. A monorepo with the app in `apps/mobile/` needs the settings there, not at the root.

---

## The Deployment Pipeline

When you edit a `SKILL.md` file or a hook inside the Factory, **the change does not happen immediately**.
The AI does not read files from this Repo; it reads from a hidden Cache directory belonging to Claude at `~/.claude/plugins/cache`.

To release your changes to production, you must run:
```bash
python3 factory/deploy.py
```

**What does this script actually do? (Sequence of Operations)**
1. **Settings sync**, when grove is installed: reads its registry and updates `.claude/settings.json` across the repos it lists. **`deploy.py` is the maintainer's tool and needs grove for the whole run** — a consumer never runs it. Per repo, `factory/enable.py` writes the same file and needs nothing.
2. **Copy to Cache:** Removes the old versions from Claude's plugins directory and copies over the new version.
3. **Validation:** Verifies that the copies are byte-for-byte identical to the source code, and checks the integrity of translations and references.

*(You can run `python3 factory/deploy.py --check` to see what requires fixing without actually changing anything).*

---

## 3 Traps You Must Know

If you edited something and the AI "isn't listening", there's a 99% chance you fell into one of the following traps:

1. **"I Deployed but didn't open a new session"**
   Skills and hooks load into the AI's memory **only at the moment the session opens**. If you deployed while the terminal with the AI was open, it will continue running with the old version. You must close and open a brand new session.

2. **"The code in the Repo is not the code that runs" (I forgot to Deploy)**
   You fixed a bug in one of the skills, committed the code, reported that everything works – but the AI keeps tripping on the same bug. The answer: you forgot to Deploy to the cache. The code updated in Git, but the AI is reading from `~/.claude/plugins/cache`.

3. **Commit before Deploy**
   Claude's built-in deployment command (`claude plugin update`) signs the cache with the Hash of the latest commit (HEAD). If you deploy changes that you haven't committed yet, the cache "fakes" its identity, and in the future the system will refuse to update it claiming it is already up to date. `deploy.py` intentionally blocks you from doing this.

---

### The One Sentence to Remember
**A Skill is text loaded at session start; a Hook is a program that runs every time the AI performs an action. Both ride in the same package (Plugin), are copied to the same cache, and wake up at the exact same moment – session start.**
