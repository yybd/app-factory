*English · [עברית](FAQ.he.md)*

# FAQ — and the glossary

Questions that came out of watching someone install this, and the six words this
project uses in a particular way.

---

## The words

| | |
|---|---|
| **track** | One plugin — a group of skills that belong together, like `apple-track` or `web-track`. Seven of them ship here. You install a track, and you enable it per repo. |
| **skill** | One `SKILL.md` and whatever scripts it runs. A model reads its description in every session where the track is enabled, and reads the body only when the skill fires. |
| **marketplace** | The catalogue Claude Code installs plugins from — this repo is one. Adding it teaches the machine where the tracks are; installing a track copies it. |
| **hub** | An **optional** second repo where several apps keep their profiles, listing text, media and prices, so the copy is written once and reviewed in one place. With one app there is no reason for it. `$APP_HUB` names it. Its shape: [`docs/contracts/hub.md`](docs/contracts/hub.md). |
| **grove** | A **separate, optional** marketplace for people working across several repos: one registry deciding which tracks load where, plus guards against writing into the repo you are not standing in. Nothing here requires it. |
| **standalone** | Working without a hub. The app repo's own `fastlane/` is the source of truth, which is the layout Apple's `deliver` and Google's `supply` already read. Selected automatically when there is no hub. |
| **`$KEYS_ROOT`** | The folder holding the credentials, deliberately outside every repo and not a git directory. Skills read the files where they sit and copy them nowhere. [`docs/contracts/keys.md`](docs/contracts/keys.md). |
| **`${CLAUDE_PLUGIN_ROOT}`** | Claude Code expands this to the installed plugin's own directory, so a skill can name its scripts without knowing where the machine put them. It reaches **its own** plugin only — never another one, which is why skills ask for each other by name. |

---

## Installing

**Do I have to install all seven tracks?**
No, and you should not. `factory/enable.py` reads the repo and proposes the ones its
files justify — an `.xcodeproj` means Apple, a `build.gradle` means Android. Each track
you enable costs tokens in every session in that repo, which is the whole reason the
allocation is per repo.

**The CLI said the plugin is "disabled by default — enable it with `claude plugin
enable`". Should I?**
No. That command switches the track on for **every directory on the machine**, which is
what the per-repo setting exists to prevent: App Store skills loading in a website. The
file `enable.py` wrote is what enables it, here and only here.

**I installed it and no skills appeared.**
Three things have to be true, and only the third is obvious: the track is installed, it
is enabled in this repo, and **the session started after both**. Skills load at session
start. `python3 factory/enable.py --check` answers the first two, and fails if a track
is enabled but not installed.

**I opened the session in a subdirectory and nothing loaded.**
Claude Code reads settings from **the directory the session opened in**, not from the
git root. A monorepo with the app in `apps/mobile/` needs the tracks enabled there.
Run `enable.py` from that directory; it notices and enables it in the right place.

**Do I need grove? A hub? A website?**
None of the three. Grove is for many repos at once. A hub is for several apps sharing
one source of copy. A website is only needed to the extent that both stores demand a
privacy URL that resolves, which can be one page anywhere.

---

## Using

**How do I update?**
```bash
claude plugin marketplace update app-factory
claude plugin update <track>@app-factory
```
Then open a new session. Note that `update` compares **versions**, not content — if the
version has not moved, nothing is copied, which is correct: a release is a version.

**How do I turn a track off?**
```bash
python3 $AF/factory/enable.py --tracks apple-track   # only this one
python3 $AF/factory/enable.py --none                 # all of them off here
```
(`$AF` is the marketplace checkout — [QUICKSTART.md](QUICKSTART.md) names it.)
It changes only this repo's `.claude/settings.json`, and only the `@app-factory` keys in
it. To remove a track from the machine entirely: `claude plugin uninstall <track>@app-factory`.

**How much does a track cost me?**
Every enabled track puts its skills' **descriptions** in context in every session — the
bodies load only when a skill fires. Each track's README prints its own figure; `apple-track`
is the largest. That number is why the tracks are separate plugins rather than one.

**Can I use one skill without the rest of its track?**
Not selectively — a plugin installs whole. But a skill only *runs* when you ask for the
work it does, so an unused skill costs its description and nothing else.

**A skill did something I did not expect.**
[TRUST.md](TRUST.md) is the account of what these skills read, write and send, and what
they will never do without asking. Every upload is confirmed first; nothing pushes.

---

## Credentials

**Where do my keys go?**
Into `$KEYS_ROOT`, which `factory/init_keys.py --create` sets up outside every repo and
gitignores from the first byte. You fill it in by hand. Each track resolves a credential
in one documented order: the environment, then `$KEYS_ROOT/credentials.json`, then a
folder convention.

**Does anything here see my keys?**
The resolvers return a **path**; the file itself is read by `fastlane`, `notarytool` or
the store API at the moment of use. Nothing here prints a secret, copies one into a
repo, or commits one. That is checked rather than promised — see TRUST.md.

**I set the environment variable and it still says it cannot find it.**
`python3 <track>/shared/credentials.py` (Apple or Android) prints exactly which sources
it looked at and what each answered.

---

## Troubleshooting

**A script says "grove is not on this machine".**
Only `factory/deploy.py` and the dashboard genuinely need it; both are the maintainer's
tools. For everything else set the variable it asked for — `$KEYS_ROOT`, `$APP_HUB` —
in your shell or in `~/.claude/settings.json` under `env`.

**I edited a skill and nothing changed.**
The session reads an installed **copy**, not this repo. Commit, deploy, and open a new
session. [HOW-IT-WORKS.md](HOW-IT-WORKS.md) is the mechanism, and the trap.

**Where do I report something wrong?**
[CONTRIBUTING.md](CONTRIBUTING.md) for a fix, and [SECURITY.md](SECURITY.md) for
anything involving credentials or a store account.
