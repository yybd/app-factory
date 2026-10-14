# Articles — drafts, not documentation

Blog drafts about this project. Each is written in Hebrew, and the English copy beside it is an adaptation for an international reader rather than a line-by-line translation. They are **not** product documentation and
nothing links to them from the install path: they argue a case for a reader who has
never seen this repo, which is a different job from telling someone how to use it.

They are kept because the argument in them is the one this project is built on, and
re-deriving it costs more than keeping a draft. They are dated by their content and are
not maintained against the code — a draft that contradicts today's behaviour is a draft,
not a bug.

| | |
|---|---|
| 1 — guards for a multi-repo agent: [English](1-cross-repo-guards.md) · [עברית](1-cross-repo-guards.he.md) | the case for blocking a write into a repo the session is not standing in. About RepoGuards, not about this repo. |
| 2 — skills and tracks: [English](2-skills-and-tracks.md) · [עברית](2-skills-and-tracks.he.md) | why one large instruction file does not hold, and what replaces it |

Both were revised on 2026-09-29, when the two repositories went public: the link is in
place, and the second describes per-repo tracks through `enable.py` rather than a
registry every user must have.

**Published on 2026-10-14 on the author's own site**, in English and Hebrew. That
site is now the articles' home: its sources live in the website repo
(`text/<lang>/blog/*.md`), and that is the copy to edit. The files here are the drafts
they started from, kept because the argument in them is the one this project is built
on — they may lag the published version, and a difference between the two is resolved
in favour of the site.

**Last checked against the code on 2026-10-14** (App Factory with `windows-track`, 41
skills in eight tracks; RepoGuards 0.3.1). The two guard messages quoted in the first
are the real hook's output on that day, on throwaway repos named like the real ones.
The second gained the Windows track, and its counts — skills, tracks, and the size of
their descriptions, about 8,100 tokens — were recounted from disk.
