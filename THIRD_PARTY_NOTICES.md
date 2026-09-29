# Third-party notices

Most of this repository is original work under the MIT licence in [`LICENSE`](LICENSE).
**Two skills are not ours**, and this file is where that is said. Both are redistributed
under permissive licences, and both keep their own terms — the repository's MIT licence
does not extend to them.

Verified against the upstream repositories, not inferred from the text.

---

## `frontend-design` — Apache License 2.0

| | |
|---|---|
| **Where it ships here** | `plugins/design-track/skills/frontend-design/` |
| **Upstream** | [`anthropics/skills`](https://github.com/anthropics/skills/tree/main/skills/frontend-design) |
| **Licence** | Apache-2.0 · full text at [`LICENSE.txt`](plugins/design-track/skills/frontend-design/LICENSE.txt), fetched from upstream unchanged |
| **Modified?** | Yes — the changes are listed in [`NOTICE`](plugins/design-track/skills/frontend-design/NOTICE) |

Apache-2.0 asks three things of a redistributor, and until now this repository did none
of them: ship the licence, keep the attribution, and give notice on modified files. The
skill's own frontmatter said *"Complete terms in LICENSE.txt"* — a line copied verbatim
from upstream, pointing at a file that was not here.

## `web-design-guidelines` — MIT

| | |
|---|---|
| **Where it ships here** | `plugins/web-track/skills/web-design-guidelines/` |
| **Upstream** | Vercel Labs — the skill wrapper, and the guidelines it fetches at runtime from [`vercel-labs/web-interface-guidelines`](https://github.com/vercel-labs/web-interface-guidelines) |
| **Licence** | MIT |
| **Modified?** | One addition: the offline fallback paragraph |

```
MIT License

Copyright (c) 2025 Vercel Labs

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Note that this skill **fetches** the guidelines at review time rather than carrying a
copy of them, so the rules it applies are always upstream's current ones. That also
makes the URL a live dependency: it has moved once already, which is why the skill
carries an offline fallback.

---

## Adding to this file

A skill that came from somewhere else gets three things, and a checker cannot tell you
when one is missing:

1. Its licence text, beside the skill.
2. A `NOTICE` naming the upstream and every change, when the text was modified.
3. A row here, and the right `license` in that track's `plugin.json`.
