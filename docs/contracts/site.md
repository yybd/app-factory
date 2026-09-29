*English · [עברית](site.he.md)*

# The website — what is actually required

**The short answer: a URL that resolves.** Both stores demand a privacy-policy URL before
they will accept a submission, and a dead one fails review. Where that page is hosted is
nobody's business but yours.

**A studio with no website is a normal case,** and the factory treats it as one. Nothing in
the mechanics needs a site, and no shipping skill requires one — they require the *URL*,
which is declared once in the hub's `DATA.md` and reused for every app.

---

## The three ways to satisfy it

| | What it costs | What it gives |
|---|---|---|
| **A page anywhere** — a static host, a gist, a docs page | minutes | the store accepts the submission. Nothing more |
| **A website repo, registered as `$SITE`** | a repo and its own skills | per-app pages, a catalogue, product sites — and the media and copy come from the hub rather than being rewritten |
| **A product site per app** | one cluster per app | a domain of its own, translated, with its own legal pages |

The factory does not prefer any of them. It only needs to be told which URL to put in the
listing.

---

## `$SITE` — when you do have a website repo

Mark it in the registry:

```json
"my-site": { "root": "web/my-site", "role": "the website", "site": true,
             "tracks": ["web-track", "design-track"] }
```

That flag is the whole mechanism. `deploy.py` then writes `$SITE` into the machine's
environment beside `$APP_HUB` and `$KEYS_ROOT`, and the skills that hand work off to a
website name it rather than guessing.

**Marked by a flag and not by a role string**, deliberately: a guess here would point
release work at the wrong repo, and a wrong guess in that direction is expensive.

**Without the flag, `$SITE` is simply unset** and every skill that mentions a website says
what to do instead.

---

## What lives in the site repo, and why it is not shipped

A website's own skills — building a page for an app, translating a cluster, writing a
reference page — are **local to that repo** and are not part of the factory. That is the
rule from `docs/skills/1-skill-placement` (in grove) applied
honestly: they act entirely inside one tree and cannot run anywhere else, so shipping them
globally would load them in every session that will never use them.

Seven shipped skills *refer* to a website skill by name. That is the correct cross-plugin
form — the caller names the skill, and the skill resolves its own paths when it runs. See
`3-script-references` (in grove).

---

## The one check worth running

```bash
python3 factory/check_urls.py --slug <app>
```

It reads the marketing, support and privacy URLs from the hub's `DATA.md`, substitutes the
app slug, and asks whether each one resolves. **It is not part of `deploy.py`** — it is the
only thing here that touches the network, and a check that fails when you are offline is a
check people learn to skip. Run it before a submission.

It answers "is something there". It does not read the page: a 200 on an empty privacy
policy passes here and fails review.
