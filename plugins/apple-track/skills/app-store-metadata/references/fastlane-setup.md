# fastlane setup, deliver, and upload

## Is fastlane already here?
Signals: a `fastlane/` dir with `Fastfile`, `fastlane` in the `Gemfile`,
`which fastlane`, or `bundle exec fastlane --version`. If any are present, skip
install and go straight to configuring/using `deliver`.

## Installing fastlane (ask first — changes the environment)
Prefer Bundler so the version is pinned with the repo:
```bash
# Gemfile
source "https://rubygems.org"
gem "fastlane"
```
```bash
bundle install
bundle exec fastlane --version
```
Alternatives: `brew install fastlane`, or `gem install fastlane` (may need
`sudo`/rbenv). On Apple Silicon, Bundler + system Ruby usually works; if Ruby is
too old, point the user to rbenv. Don't `sudo gem install` without asking.

## Initialize deliver (metadata)
For an app that already exists in App Store Connect:
```bash
bundle exec fastlane deliver init   # downloads current metadata into fastlane/metadata
```
This is the easiest way to get a correct folder skeleton + current live text. If
the app record doesn't exist yet, that's portal/website work first (see
metadata-spec.md → "Done on the App Store Connect website").

## Appfile
```ruby
app_identifier "com.your.bundleid"
apple_id "you@example.com"
# team_id / itc_team_id if you belong to multiple teams
```

## Multi-app: one lane per app
A single `fastlane/` folder serves multiple apps by giving each its own
`app_identifier` and `metadata_path`:
```ruby
lane :metadata_word do
  deliver(
    app_identifier: "com.you.word",
    metadata_path: "./fastlane/metadata/<app>",
    screenshots_path: "./fastlane/screenshots/<app>",
    skip_binary_upload: true,
    skip_screenshots: true,        # flip to false when doing screenshots
    force: true,                   # skip the HTML preview confirmation in CI
    run_precheck_before_submit: false
  )
end
```

## Validate before upload
- Run the skill's `validate_metadata.py` first (local char-limit/required checks).
- `deliver` can run a `precheck` (Apple-side metadata rules) — useful but not a
  substitute for reading the guidelines.
- Do a dry run that won't publish: `deliver(..., verify_only: true)` or upload
  with `submit_for_review: false` so nothing goes live unintentionally.

## Upload (ask first — outward-facing)
```bash
bundle exec fastlane metadata_word        # the lane above
# or text only, no screenshots:
bundle exec fastlane deliver --skip_screenshots --skip_binary_upload
```
Uploading talks to App Store Connect and is rate-limited; confirm with the user
before running, and never set `submit_for_review: true` without explicit
approval. Authentication uses the Apple ID (may prompt for 2FA / an
app-specific password, or an App Store Connect API key for CI).

## After upload — finish on the website
`deliver` stops at metadata/screenshots. Remind the user of the website-only
steps (age rating, pricing, App Privacy, export compliance, Submit) listed in
[metadata-spec.md](metadata-spec.md#done-on-the-app-store-connect-website).
