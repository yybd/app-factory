# App Store metadata spec (fastlane deliver)

last-verified: 2026-06-02
sources:
- https://docs.fastlane.tools/actions/deliver/
- App Store Connect Help (field limits, localizations)

## fastlane deliver folder layout

A single `fastlane/` folder can serve several apps; each app points `deliver` at
its own `metadata_path`. Typical layout (multi-app shown):

```
fastlane/
  Fastfile                      # one deliver lane per app
  Appfile                       # apple_id, team
  metadata/
    <app>/                      # or just metadata/ for a single app
      copyright.txt             # shared (not per-locale)
      primary_category.txt
      primary_first_sub_category.txt
      primary_second_sub_category.txt
      secondary_category.txt
      secondary_first_sub_category.txt
      secondary_second_sub_category.txt
      review_information/
        first_name.txt
        last_name.txt
        phone_number.txt
        email_address.txt
        demo_user.txt           # demo account user (if login-gated)
        demo_password.txt
        notes.txt               # App Review notes (demo mode steps, etc.)
      <locale>/                 # one folder per language, e.g. en-US, de-DE, he
        name.txt
        subtitle.txt
        description.txt
        keywords.txt
        promotional_text.txt
        release_notes.txt       # "What's New"
        support_url.txt
        marketing_url.txt
        privacy_url.txt
  screenshots/
    <app>/
      <locale>/                 # screenshots per locale (see screenshots.md)
```

## Per-locale text fields and limits

These vary slightly by Apple's current rules; validate the *translated* string,
not the source. Character counts are characters, not bytes.

| File | Field | Limit | Notes |
|------|-------|-------|-------|
| `name.txt` | App name | **30** | Per locale. Must match usage; no prices/emojis. |
| `subtitle.txt` | Subtitle | **30** | Per locale. |
| `keywords.txt` | Keywords | **100** total | Comma-separated, NO spaces after commas (spaces waste the budget). Per locale. |
| `description.txt` | Description | **4000** | Per locale. |
| `promotional_text.txt` | Promotional text | **170** | Per locale. Can be changed WITHOUT a new build. |
| `release_notes.txt` | What's New | **4000** | Per locale. Required for updates (not first version). |
| `support_url.txt` | Support URL | URL | Required. Must be reachable (Guideline 1.5). |
| `marketing_url.txt` | Marketing URL | URL | Optional. |
| `privacy_url.txt` | Privacy Policy URL | URL | Required when the app has accounts or collects data (most apps). |

## Shared (not per-locale) fields

| File | Field | Notes |
|------|-------|-------|
| `copyright.txt` | Copyright | e.g. "2026 Your Company". |
| `primary_category.txt` | Primary category | Apple category key (e.g. `PRODUCTIVITY`, `UTILITIES`). |
| `secondary_category.txt` | Secondary category | Optional. |
| `*_first_sub_category.txt`, `*_second_sub_category.txt` | Sub-categories | Only some categories (e.g. Games) use these; leave empty otherwise. |
| `review_information/*` | App Review contact + demo | `notes.txt` is where demo-mode/login steps go. Include `demo_user`/`demo_password` only if there's a login. |

## Locale codes (App Store)

Common codes fastlane expects (folder names): `en-US`, `en-GB`, `en-AU`,
`en-CA`, `de-DE`, `fr-FR`, `fr-CA`, `es-ES`, `es-MX`, `it`, `pt-BR`, `pt-PT`,
`nl-NL`, `sv`, `da`, `fi`, `no`, `ru`, `pl`, `tr`, `ar-SA`, `he`, `ja`, `ko`,
`zh-Hans`, `zh-Hant`, `th`, `vi`, `id`, `ms`, `hi`, `cs`, `sk`, `hu`, `ro`,
`uk`, `el`, `hr`, `ca`. (Apple periodically adds languages — verify a less-
common code in App Store Connect if `deliver` rejects it.)

**Primary language**: every app has one primary language; its localization must
be complete. Other locales fall back to the primary for any field left empty —
so partial localization is allowed, but the primary must be full.

## Done on the App Store Connect website

fastlane `deliver` uploads listing text, screenshots, app previews, categories,
and review information. It does NOT handle these — guide the user to do them on
the App Store Connect website (and the Apple Developer portal):

- **Creating the app record** — needs a registered Bundle ID first
  (Certificates, Identifiers & Profiles), then "New App" in App Store Connect.
  (fastlane `produce` can create the record via API as an alternative — mention
  it, but the bundle ID/identifier setup is portal work.)
- **Age rating questionnaire** — answered in App Store Connect.
- **Pricing & availability** — price tier, territories, pre-orders.
- **App Privacy "nutrition label"** — the data-collection questionnaire (must
  match the privacy manifest / actual behavior).
- **Export compliance / encryption** — declared at submission.
- **Content rights, in-app purchase creation & review**, TestFlight beta info,
  and the final **Submit for Review** button.

When you hand off, give the exact path: e.g. "App Store Connect → your app →
App Information → Age Rating → Edit". Don't claim a step is done if it can only
be done on the website.
