# Security

## What this project handles

These skills sign binaries and upload them to the App Store and Google Play, so a
machine running them is one step from a live store listing. They handle **paths to
credentials** — an App Store Connect API key, a Play service account, an upload keystore
— and never the credential's contents: the resolvers return where a file is, and
`fastlane`, `notarytool` or the store API reads it at the moment of use.

Three properties are held deliberately, and each is checked rather than promised:

- **No secret is printed, copied into a repo, or committed.** `factory/init_keys.py`
  writes a `.gitignore` that refuses everything *before* it creates a folder.
- **Nothing outward-facing happens without confirmation.** Every upload, submission and
  publish is shown and asked about first. Nothing pushes a git branch.
- **Nothing writes into a repo the session is not standing in.** That guard is grove's
  and optional; what is not optional is that a skill here names exact paths rather than
  sweeping a directory.

[TRUST.md](TRUST.md) is the full account of what is read, written and sent.

## Reporting a vulnerability

Open a GitHub issue for anything that is **not** itself sensitive — a script that logs
more than it should, a path that escapes where it was meant to stay, a check that can be
bypassed.

For anything that would expose a credential or a store account if written publicly, do
not open an issue. Report it privately through GitHub's **Report a vulnerability** on the
Security tab, which is not publicly visible. Include what you ran, what you expected, and
what happened; do not include the credential itself.

Expect an acknowledgement within a few days. This is a small project: there is no
bounty, no SLA, and no dedicated security team, and saying so plainly is better than
implying otherwise.

## Scope

**In scope:** anything shipped in this repository — the seven tracks, their scripts, the
hooks, and the tools under `factory/`.

**Out of scope**, because they are somebody else's: Claude Code itself and its plugin
mechanism (report those to Anthropic), `fastlane` and the gems it pulls, the store APIs,
and any third-party skill listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
whose upstream still maintains it.

## What you should check on your own machine

- `$KEYS_ROOT` is outside every git repository. `python3 factory/init_keys.py` reports
  where it thinks it is.
- A service account has the **narrowest** Play permissions that work. Listing edits and
  binary upload are separate rights; most work needs only one of them.
- An App Store Connect API key with the App Manager role can do considerably more than
  deliver a listing. Use the smallest role that works for what you actually run.
- Nothing here needs `sudo`, and no script asks for it. One that did would be a bug
  worth reporting.
