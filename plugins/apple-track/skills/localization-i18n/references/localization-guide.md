# In-app localization — concepts & how-to

last-verified: 2026-06-03
source: Apple localization docs (NSLocalizedString, String Catalogs, stringsdict)

## How localized strings work
Code asks for a key; at runtime the system returns the value for the user's
preferred language, falling back to the **base/development language** if that
locale lacks the key.

```swift
// classic
let s = NSLocalizedString("status_word_closed", comment: "shown when Word isn't running")
// modern (String Catalog auto-extracts these)
let s = String(localized: "status_word_closed")
```
The **key** is the same across all languages; only the **value** differs. If a
key is referenced in code but missing from the catalog, the user sees the raw
key (e.g. "status_word_closed") — looks broken.

## Two storage formats
- **Classic `.strings`** — one `Localizable.strings` per `*.lproj` folder
  (`en.lproj`, `he.lproj`, …), entries `"key" = "value";`. Plus `.stringsdict`
  for plurals. Simple, explicit, what many existing projects use.
- **String Catalog `.xcstrings`** (Xcode 15+) — a single JSON catalog with all
  languages, plural/device variations, and translation state, edited in Xcode's
  catalog UI. Xcode auto-extracts `String(localized:)` / SwiftUI `Text("…")`
  keys into it. Preferred for new work.

### Migrating classic → String Catalog
In Xcode: select the `.strings` file → Editor → **Migrate to String Catalog**
(or add a new String Catalog and let Xcode extract). It folds all `.lproj`
values into one `.xcstrings`. This is a project change — do it with the user's
agreement, commit before/after, and verify all locales carried over.

## Base/development language
Every project has one. It must be **100% complete** — it's the fallback for
every other locale. Partial translation in other locales is fine (they fall back
per-key), but gaps there mean mixed-language UI. The audit flags per-locale gaps
against the base.

## Format strings & placeholders
Preserve specifiers and their order when translating:
- `%@` (object/string), `%d` (int), `%1$@`, `%2$d` (positional — important when
  word order changes between languages).
- Keep the same number and type of placeholders in every translation; reorder
  with positional specifiers rather than moving `%@` around blindly.

## Plurals — use stringsdict / plural variations, not if/else
Languages have different plural rules (zero/one/two/few/many/other). Don't write
`count == 1 ? "1 item" : "\(count) items"`.
- Classic: a `Localizable.stringsdict` with `NSStringPluralRuleType` variants per
  language.
- String Catalog: right-click the key → **Vary by Plural**.
Then call with the count; the system picks the correct form per locale.

## RTL (Hebrew, Arabic)
- Use **leading/trailing**, not left/right, in Auto Layout and SwiftUI padding/
  alignment — the system mirrors automatically for RTL.
- Use natural text alignment (`.natural`) so text aligns to the reading
  direction.
- Avoid hardcoded `.left`/`.right`, `NSTextAlignment.left`, or leftward
  constraints for user content — flag them.
- Test by running in an RTL language (or Xcode's "Right-to-Left pseudolanguage").
- Images that imply direction (arrows, back chevrons) may need mirroring.

## Practical tips
- Keep keys descriptive and stable (`status_word_closed`, not `label1`); renaming
  a key orphans translations.
- Always pass a meaningful `comment:` — it's the context translators see.
- A value identical to the base language usually means "not translated yet" —
  the audit flags these; confirm before assuming it's intentional.
- Don't delete a "never referenced" key until you've checked it isn't built
  dynamically (e.g. `NSLocalizedString("err_\(code)", …)`).
