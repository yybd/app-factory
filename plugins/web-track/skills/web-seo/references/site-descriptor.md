# `seo-site.json` — what this skill needs to know about your site

A site repo keeps one of these at `.claude/seo-site.json`. **It is optional.** Without
it a single-site layout is assumed — the repo is the site, and the properties are
whatever the canonicals turn out to name — which is right for most sites and wrong only
for a repo that serves several properties out of subdirectories.

Everything here is a fact about *your* site that no skill can derive. It exists because
the audit used to carry two constants naming one machine's checkout and one studio's
seven hostnames, which is what kept it in a private repo instead of in the skill.

```json
{
  "root": ".",

  "properties": {
    "_comment": "hostname → the directory that is that property's web root, relative to `root`. A single-site repo can leave this out entirely.",
    "www.example.com": ".",
    "docs.example.com": "sites/docs"
  },

  "trailing_slash": false,
  "analytics_script": "analytics.js",
  "sitemap_command": "npm run seo",
  "publish_command": "npm run deploy",
  "verify_command": "npm run verify:deploys",

  "skip_dirs": ["storybook-static"],

  "search_console": {
    "_comment": "Only needed for the live half — impressions, queries, index coverage. The audit is entirely offline and needs none of it.",
    "properties": ["sc-domain:example.com"],
    "credentials": "$KEYS_ROOT/google/search-console.json"
  },
  "analytics": {
    "ga4_property": "properties/000000000",
    "credentials": "$KEYS_ROOT/google/analytics.json"
  }
}
```

## What each field changes

| Field | Without it | With it |
|---|---|---|
| `properties` | every host a canonical names is treated as a property, rooted at the tree | each property is audited against its own directory, and a canonical pointing at an undeclared host is an error |
| `trailing_slash` | the trailing-slash check is skipped | `false` makes a canonical with a trailing slash an error, because it will 308-redirect |
| `analytics_script` | the "unmeasured page" check is skipped | a page without that script is an error |
| `sitemap_command` | a missing sitemap is reported without a fix | the report names the command that generates it |
| `publish_command` | the skill says "publish it however this project publishes" | the skill can say exactly what to run |
| `search_console` / `analytics` | the offline audit still runs in full | the live reading is possible |

## The rule these follow

**A check that depends on a declaration is skipped when there is no declaration, never
guessed.** A site that has not told the skill what its analytics file is called is not a
site with no analytics — and reporting every page as unmeasured because the file is not
named `analytics.js` is the kind of finding that teaches people to ignore the whole
report.

## Committing is not publishing

`publish_command` is here because that distinction has cost real time: a repo whose
hosting has git deployment switched off serves the old page until something is run. An
SEO fix that is committed and not published is a fix that does not exist, and the next
audit reports the same finding.
