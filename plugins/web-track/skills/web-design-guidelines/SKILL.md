---
name: web-design-guidelines
description: >-
  Review UI code for Web Interface Guidelines compliance. Use when asked to "review my
  UI", "check accessibility", "audit design", "review UX", or "check my site against
  best practices" ("בדוק נגישות", "ביקורת ממשק"). It reports findings only; it does NOT
  fix them, and does NOT decide a page's structure (page-builder).
metadata:
  author: vercel
  version: "1.0.0"
argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

> **Not ours.** This skill and the guidelines it fetches are **Vercel Labs'**, MIT
> licensed, © 2025 Vercel Labs — see `THIRD_PARTY_NOTICES.md` at the repository root.
> It is redistributed here with a single change, the offline fallback below.

## Prerequisites

- **Tools:** none beyond Claude Code; `WebFetch` needs network access to
  raw.githubusercontent.com, with the offline fallback below.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** not used.
- **Other tracks:** none — the fallback reads `page-builder`'s checklists, in this
  same plugin; `frontend-design` (design-track) is only a boundary.

## How It Works

1. Fetch the latest guidelines from the source URL below
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the fetched guidelines
4. Output findings in the terse `file:line` format

## Guidelines Source

Fetch fresh guidelines before each review:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Use WebFetch to retrieve the latest rules. The fetched content contains all the rules and output format instructions.

**Fallback if the fetch fails** (offline, URL moved, network error): do not skip the audit. Fall back to the companion `page-builder` checklists — `${CLAUDE_PLUGIN_ROOT}/skills/page-builder/references/checklists/pre-delivery.md` plus the per-area acceptance checks in that skill's `references/`: `i18n-rtl.md`, `responsive-mobile.md`, `seo-metadata.md`, `forms-conversion.md`, and `performance.md` — and **tell the user** the live guidelines were unavailable so the review used the local baseline instead.

## Usage

When a user provides a file or pattern argument:
1. Fetch guidelines from the source URL above
2. Read the specified files
3. Apply all rules from the fetched guidelines
4. Output findings using the format specified in the guidelines

If no files specified, ask the user which files to review.

## Boundaries

- **It reports; it does not fix.** Findings come back as `file:line` with the rule
  each one breaks, and the change is the user's to make or to ask for.
- **It does not decide structure** (`page-builder`) or visual direction
  (`frontend-design`) — it measures what exists against a published set of rules.
