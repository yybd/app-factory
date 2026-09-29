*English · [עברית](README.he.md)*

# docs

Three kinds of document, and the difference between them is who reads them and when.

## [`contracts/`](contracts) — what something must contain

Read these when you are setting a thing up, or when a skill says it cannot find
something. Each one describes a shape that skills depend on, and each has a script that
creates what it describes.

| | | |
|---|---|---|
| [hub.md](contracts/hub.md) | a data repo several apps share: profiles, listing text, media, prices | `factory/init_hub.py` |
| [keys.md](contracts/keys.md) | the credentials folder, and what the skills do and do not do with it | `factory/init_keys.py` |
| [site.md](contracts/site.md) | what the stores actually need from a website, which is one URL that resolves | `factory/check_urls.py` |

**All three are optional.** Every skill that can use a hub works without one; a studio
with no website still ships, as long as the privacy URL it gives the stores resolves.

## [`decisions/`](decisions) — why something is the way it is

**Not instructions.** These are records: what was decided, what was measured to settle
it, and what was rejected and on what grounds. Several of the decisions look wrong at
first glance, and without the record they get re-asked every few weeks and re-answered
from scratch. **What saves the time is rarely the decision — it is the alternative that
was ruled out.**

They are dated, and they describe the state at the time. A decision record that
contradicts today's code is not a bug in the record.

| | |
|---|---|
| [1 — when a repo is not private](decisions/1-shared-context-repos.md) | why a shared data repo and a website are not "one project", and what that means for where a skill lives |
| [2 — what shipping this as a product required](decisions/2-product-readiness.md) | the readiness assessment, and what it found blocking |
| [3 — the studio flow, as it was actually run](decisions/3-studio-flow.md) | one studio's full launch sequence, hub and site repo included — the record the product lifecycle was distilled from |

## [`maintenance/`](maintenance) — keeping it true

| | |
|---|---|
| [1 — what is checked, when](maintenance/1-plan.md) | the cadences, what runs in CI, and the large part that no machine can check |

---

## Where the product documentation is

Not here. A document a person reads to *use* this lives at the root:

[QUICKSTART](../QUICKSTART.md) · [TRUST](../TRUST.md) ·
[COMPATIBILITY](../COMPATIBILITY.md) · [SKILLS](../SKILLS.md) ·
[APP-LIFECYCLE](../APP-LIFECYCLE.md) · [HOW-IT-WORKS](../HOW-IT-WORKS.md) ·
[CONTRIBUTING](../CONTRIBUTING.md)
