*English · [עברית](QUICKSTART.he.md)*

# Quickstart — from nothing to a working skill

Fifteen minutes, one app, no data repo. Every step says what it changes and how to see
that it worked.

If a step's check fails, stop there. Each one exists because the failure it catches is
otherwise invisible — a skill that did not load looks exactly like a skill that decided
it was not relevant.

---

## 1 · Install the marketplace

```bash
claude plugin marketplace add yybd/app-factory
```

**Check:** `claude plugin marketplace list` names `app-factory`.

That clones it to `~/.claude/plugins/marketplaces/app-factory/`, which is where the
commands below find `factory/`. Give it a name, so the rest stays short:

```bash
export AF=~/.claude/plugins/marketplaces/app-factory
```

To work from your own checkout instead — to read the skills, or change one — clone it
and add that path (`git clone https://github.com/yybd/app-factory ~/app-factory`, then
`claude plugin marketplace add ~/app-factory`), and set `AF=~/app-factory`.

Either way: this makes the tracks *available*, and turns none of them on. And a
`marketplace add` under a name that already exists **replaces** it silently, so pick one
of the two and stay with it.

---

## 2 · Turn on the tracks this app needs

From the app's own repo:

```bash
cd ~/code/my-app
python3 $AF/factory/enable.py
```

It looks at the repo, proposes the tracks that follow, and explains each one. Take the
proposal with `--yes`, or choose with `--tracks apple-track,shared-track`.

Then install what it enabled — enabling and installing are different, and a track
enabled but not installed loads nothing:

```bash
claude plugin install apple-track@app-factory
claude plugin install shared-track@app-factory
claude plugin install factory-setup@app-factory   # optional: says when a repo has no track on
```

> **The CLI will then say a plugin is "disabled by default — enable it with
> `claude plugin enable`". Do not.** That command switches the track on for every
> directory on the machine, which is the one thing this setup exists to avoid. The
> file `enable.py` wrote is what enables it — here, and only here.

**Check:** `python3 $AF/factory/enable.py --check` lists the tracks as on
**and installed**; it fails if one is enabled but not installed.

> **A track is enabled per repo, in that repo's `.claude/settings.json`.** That is on
> purpose: App Store skills have no business loading in a website. Claude Code reads
> that file from **the directory the session opens in**, not from the git root — so a
> monorepo with the app in `apps/mobile/` needs it enabled there.

---

## 3 · Open a new session

Skills load at session start. Nothing you did above affects a session already running.

```bash
cd ~/code/my-app && claude
```

**Check:** ask *"what skills do you have for shipping this app?"* — the reply should
name skills from the tracks you enabled. If it does not, the settings file is in the
wrong directory; §2's note says which.

---

## 4 · Use one

Nothing needs configuring for this one:

> *"Review this app against the App Store review guidelines."*

That runs `app-store-review-compliance`, which reads the project and reports what would
get it rejected. It needs no credentials, no data repo, and changes nothing.

**Check:** you get findings about *your* project — a missing privacy string, a
permission with no usage description — rather than a generic checklist.

---

## 5 · When you want to ship, add credentials

Signing and uploading need secrets that must never be in a repo:

```bash
python3 $AF/factory/init_keys.py --create
```

It creates a folder — outside every repo, gitignored from the first byte — with a
`credentials.json` naming where each credential is. Fill it in by hand. The skills read
the files in place and copy them nowhere.

**Check:** `python3 $AF/factory/init_keys.py` reports the folder as set up.

Point the skills at it with `KEYS_ROOT` in your shell, or in
`~/.claude/settings.json` under `env`.

---

## That is the whole install

What you have now: an app repo whose sessions carry the store skills, credentials the
shipping skills can find, and nothing enabled anywhere it is not wanted.

## Two things you do NOT need

**A data repo.** Several skills can read one — a place where an app's profile, listing
text and media live so that several apps share one source of truth. With one app that
is overhead, and every skill that can use a hub works without one: the repo's own
`fastlane/` is the source of truth instead, and the delivery skills detect that and say
so. When you want one: `python3 $AF/factory/init_hub.py --create`.

**Grove.** A separate marketplace that decides which tracks load where from one central
registry, and guards a session from writing into a repo it is not standing in. It is
the right answer once you are working across several repos at once. It is not required,
and nothing here depends on it.

## Where to look next

| | |
|---|---|
| what a track holds | `plugins/<track>/README.md` |
| what the skills will do to your repos | [TRUST.md](TRUST.md) |
| what has to be installed for a given skill | [COMPATIBILITY.md](COMPATIBILITY.md) |
| the whole path from code to a live listing | [APP-LIFECYCLE.md](APP-LIFECYCLE.md) |
| what a word here means, and how to update or turn a track off | [FAQ.md](FAQ.md) |
