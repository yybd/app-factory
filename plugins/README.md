*English · [עברית](README.he.md)*

# The plugins — six tracks of skills, and one that does setup

**What this folder is.** The app skills, distributed as plugins from this repo's
marketplace (`app-factory`). One directory per track.

| Track | Skills | What |
|---|---|---|
| `apple-track` | 16 | the App Store, and direct macOS distribution |
| `android-track` | 9 | Google Play |
| `shared-track` | 7 | cross-store — profile, prices, release, copy |
| `web-track` | 4 | websites |
| `capacitor-track` | 2 | Capacitor apps |
| `design-track` | 1 | design and frontend |
| `factory-setup` | 1 | setup, and the one that is on everywhere |
| **total** | **40** | |

*Counted from disk 2026-09-11.*

---

## Two facts that decide everything else

**1. Which repos load which track is decided by the registry**, through each repo's own
`.claude/settings.json`. The registry is grove's, and `python3 factory/deploy.py` is what
turns it into those files.

**2. What loads is not this folder — it is a snapshot of it.** Installation copied the
skills into `~/.claude/plugins/cache/app-factory/<track>/<version>/`, and every session
reads from the copy. Editing here does not reach it by itself: deploy, then **open a new
session**.

**The directory is the version, not the commit** — so `claude plugin update` is a no-op
between releases, however much the content changed. That is what makes a version bump
the thing that reaches anyone, and why `factory/deploy.py` reinstalls rather than
updating when a byte comparison says the copy is still stale.

---

## How a plugin actually reaches a session

That mechanism — the two registrations, why old versions
stay under `.in_use/`, what enters a session's context and what does not, the two routes
to enabling a track globally, and the guard that notices when the copy and the repo have
diverged — is one subject and it is documented once, in **grove**: its `plugins/README.md`.
Grove owns the deployment and ships the guard; describing it again here would be two
accounts of one thing, drifting.

**What belongs to this repo** is what those tracks contain, which track a repo should
carry, and the decisions behind both:

* **[SKILLS.md](../SKILLS.md)** — every track and skill, and where each one loads.
* **[docs/decisions/](../docs/decisions/)** — why the hub and the site are not "one project".
* **[../HOW-IT-WORKS.md](../HOW-IT-WORKS.md)** — the short version of the loading path.

---

## Commands

```bash
python3 factory/deploy.py        # the registry → settings, the repo → the copies, verify
claude plugin list               # what is installed, and at which version
claude plugin details apple-track   # inventory and token cost
```

In every case — **restart the session** for the update to take hold.
