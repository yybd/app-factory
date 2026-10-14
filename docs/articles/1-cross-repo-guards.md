*English · [עברית](1-cross-repo-guards.he.md)*

# My agent stood in one repo and pushed another: hooks that stop blind commits across repos

Coding agents like Claude Code are excellent inside one folder. They read a whole project, track down bugs and ship features. The moment a task crosses from one repository into another, something basic breaks, and nothing warns you.

This post covers the problem, what I tried first, and **RepoGuards**: a small open-source set of Claude Code hooks that run inside the session, at the moment the agent calls a tool.

---

## The problem: a session sees one `git status`

One of my apps spans several repos: the app's code, a data repo for the stores (copy, prices, screenshots), and a website. A routine task like "prepare the next release" touches all three.

The agent opens a session in the app folder and gets to work. At some point it needs to update the store data, so it reaches out with `git -C ../app-hub …`.

Here is what is easy to miss. **The session sees exactly one `git status`, the one for the folder it is standing in.** Whatever is open in the other repo isn't "missing" from its view. It is **invisible**. That is how an agent says "done" over a clean status while the other repo is left in a mess.

Two operations get dangerous in that situation:

1. **`commit -a` or `add .` in a foreign repo.** These sweep up *everything* dirty there, including work the agent never saw.
2. **`push` to a foreign repo.** A push publishes a **whole branch**, not just the commit you made. On 7 September 2026 a push like this sent 20 commits from one of my app repos. 18 of them were written before that session even started.

Without a guard, this is what happens:

- **Someone else's work lands in your commit.** Files another developer or a parallel session left open get swept in without a word.
- **Old commits go public without anyone deciding to publish them.** One push ships everything that piled up on the branch, and there is no undo.
- **Files get overwritten in a place the agent doesn't own.** It writes into a path another repo maintains and never learns that someone is responsible for it.
- **"Done" is said over a mess.** The agent's own status is clean, and the open work in the other repo is simply forgotten.

---

## What didn't work: one more line in the instructions file

The obvious first attempt was a line in `CLAUDE.md`: "never make a sweeping commit outside your own folder". It works until it doesn't. In a long session with a crowded context, that instruction is one line among hundreds.

**An instruction is a request. A hook is a mechanism.** A Claude Code `PreToolUse` hook runs before every tool call. It sees the exact command and can refuse it or attach context to it. It doesn't need the model to remember anything.

---

## What RepoGuards does

RepoGuards sits between the agent and the commands it runs. Before a command goes out, RepoGuards checks where it is aimed. If it is aimed at a repo the session is not standing in, RepoGuards responds in one of three ways, depending on the risk.

### 1. It stops what can't be undone

Two operations are not allowed in a foreign repo: **a sweep** (`commit -a`, `add .`) and **`push`**. The first scoops up work the agent never saw, and the second publishes it.

Refusing is only half the job. A bare "Access Denied" just sends the agent off to try a different route. So RepoGuards says *why* the operation stopped and what to look at first.

This is the message, word for word, as the guard prints it today: it is the real hook's output on two throwaway repos named like mine, not a mock-up written for the post. I first ran into it on 29 September, while publishing this project. A session standing in RepoGuards' own repo was asked to push the App Factory repo next door, and I had already approved that push myself, in chat.

```
`git push` targets the 'app-factory' repo (…/app-factory), which this
session is not standing in — this session is in …/cross-repo-guards.
A push publishes a WHOLE BRANCH, not the commit you just made, and it
cannot be undone — including commits that were there before this session.
It would publish 3 commit(s):
  d0fe45b 0.4.4: every script answers --help, and the docs match the tools
  ac5456f ci: clone RepoGuards beside the checkout, so the skipped checks run
  87b75ce evals: a first suite for app-store-review-compliance, and a runner
Look first, from here:
  git -C …/app-factory log @{u}..HEAD --oneline    # everything this would publish
  python3 $REPO_GUARDS/tools/close.py              # every place, and its push radius
Then either move the session to …/app-factory and push there, or ask
the owner to push. Do not push a branch you have no picture of.
```

My approval didn't count, and that is deliberate: the hook can't tell a real approval from a hallucinated one, and it doesn't try to. That day the agent moved the session into the right repo, read the six commits that were about to go out (three of them a fortnight old), and pushed from there. Since then the refusal does the reading itself: it lists what the push would publish, so the agent, and you, see the whole branch before anything leaves the machine.

### 2. It shows the agent what it can't see

Most writes into a foreign repo are legitimate, such as editing one file or committing explicit paths. RepoGuards doesn't block them, but it doesn't let them run blind either. It attaches **the other repo's state** to the command: which branch it is on, what is open there, and how many commits are waiting to be pushed.

```
[foreign] `git reset` reaches into 'repo-guards' (…/repo-guards), and this
session stands in …/app-factory. What is dirty there is invisible from here —
this is it:
  [current branch there: main]
  (clean — nothing uncommitted there)
  (13 commits there are unpushed — a push publishes all of them)
Stage only what you wrote. `python3 $REPO_GUARDS/tools/close.py` shows every
place at once.
```

RepoGuards doesn't decide anything here, and it doesn't warn. It gives the agent what it would have seen if it had been standing there, and the agent decides with the full picture.

### 3. It respects ownership

A repo can declare that certain paths are its own, in `.claude/owns.json`. RepoGuards refuses writes to those paths from outside. It catches the agent's editing tools, and it also catches writes through the shell: redirection (`>`), `sed -i`, `cp`, `mv`, `tee` and `rm`. That wasn't always so: until 10 September it blocked `Edit`, and `> file` walked straight past it.

**Seven hooks in all. Two of them block, and the rest report.** For example, at the end of every turn one of them names the work left uncommitted in another repo, so it isn't forgotten.

---

## Closing: what this session wrote, everywhere

The other half of the problem is finishing properly. `close.py` reports **every** place the session touched: what you changed, what was already there, how many commits are unpushed, **and how many of those predate the session**. With `--commit` it stages only paths that a writing tool of *this* session named, so a parallel session's work is never swept in.

It commits, but **it doesn't push or publish.** Both are irreversible. What it gives you instead is the thing you can't do from memory: the exact push radius of each place.

---

## What it can't do

- **It fails open.** A guard that blocks by mistake stops work, and a guard that crashes stops everything. So every change to the ownership guard is run across all its branches before it takes effect.
- **Writes from inside a script are out of reach.** The hook sees the command line, not what the program does once it runs. `python3 build.py` can write anywhere. That limit is stated in the README, not hidden.
- **A target computed at run time is allowed.** `git -C $DIR push` resolves inside the shell, so the hook sees a variable. Anything it can't parse with confidence, it allows.
- **"Not declared" and "forgot to declare" look the same to it.** So a separate check runs at the end of every turn, looking for a local skill that nobody declared.

Each of these limits has a test that expects ALLOW, so the edge is a decision on the record rather than an accident.

---

## From prompt engineering to systems engineering

You can't rely on a language model's self-discipline in a three-hour session. You can rely on code that runs before every command, refuses the two operations with no way back, and hands the agent the picture it was missing.

RepoGuards is open source (MIT): **[github.com/yybd/repo-guards](https://github.com/yybd/repo-guards)**. It is built for Claude Code and tested only there. The hooks use Claude Code's hook protocol and tool names. The idea carries over to any agent that has a pre-tool hook; the code doesn't, yet. It stands on its own and needs nothing else to work.

*Part two: why I stopped writing one giant instructions file, and what replaced it. 40 skills that load only where they're needed, in [App Factory](https://github.com/yybd/app-factory).*
