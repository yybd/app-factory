*English · [עברית](2-product-readiness.he.md)*

# The factory as a product — what is required, and in what order

*Written 2026-09-11, after a sweep of all 40 skills, 152 plugin files, the documents and
the registry.*

## What is actually being sold here

Two layers, and they differ in readiness rather than merely in subject:

**The mechanics** — the registry, the seven guards, `close.py`, the staleness check, the
script check, portability. **Entirely generic.** It does not know what an app is and does
not care whose studio this is. It is also the part with no equivalent: it answers "a
session working across several repos" — a problem anyone with more than one repo has.

**The store tracks** — 33 of the 40 skills. They assume a **hub**: a data repo they read
from and write to. Without one they point at a directory that does not exist.

**The conclusion that sets the order:** the mechanics can be released almost immediately;
the store tracks require the hub contract to be written — and that is a missing
component, not a cleanup.

## What is already closed

| | |
|---|---|
| Portability — relative registry, derived base, anchors | ✅ verified against a second machine built inside the test |
| `$KEYS_ROOT` — no skill names anyone's credentials folder | ✅ |
| An offer to create a credentials folder, or point at an existing one | ✅ `factory/init_keys.py`, and `deploy` reports it |
| Registry: a template ships, the registry itself is machine data | ✅ `registry.example.json` |
| Studio identifiers — bundle ids, a GitHub account, a service-account filename | ✅ zero remain |
| Fingerprints — the brand, the products, the subject matter | ✅ zero remain |
| Secrets inside the repo | ✅ swept: none |
| Licence | ✅ MIT, in the root and in all eight manifests |
| The tools speak English | ✅ commands, guards' messages, pipelines, the dashboard |

## What blocks release, by size

### 1 · The hub contract — ✅ built 2026-09-11

**33 skills read `$APP_HUB`; 59 references to `DATA.md` alone.** The hub is a data repo
with a defined structure — `DATA.md` (studio data and accounts), `PRODUCT.md` (voice),
`<slug>/profile.md` (an app's profile), `<slug>/store/`, `<slug>/media/` — **and that
structure is written down nowhere.** It exists as a convention among the skills.

**Built:** [`docs/contracts/hub.md`](../contracts/hub.md) states the contract, derived from
the skills rather than invented, and `factory/init_hub.py` creates what it describes —
report / `--create` / `--app <slug>`, never overwriting a file that exists. `deploy.py`
reports a missing hub **only when the registry holds apps**, so an installation using the
mechanics alone is never told about a hub it does not need.

### 2 · The site assumption — ✅ built 2026-09-11

**Built:** [`docs/contracts/site.md`](../contracts/site.md). The measurement changed the
shape of the answer: what the shipped skills need from a website is **one URL that
resolves**, not a site. A studio with no website is a normal case and is now treated as
one; `$SITE` is an optional registry flag, and `factory/check_urls.py` verifies the URLs
the stores will actually read.

### 3 · Packaging for someone who is not the owner

An installation path verified end to end: clone → marketplace add → deploy → init_keys →
register-project → the first skill that works. **The early steps have been walked on a
real fresh clone** and two breakages found there were fixed: a first `deploy` reporting
forty false failures, and a pipeline that could only pass on one machine.

## The proposed order

**No structural blocker remains.** What is left is the ordinary work of a first release:
a walked-through installation on a machine that is not this one, and a first user.
