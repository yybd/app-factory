# The on-device display name — where it lives and how to change it safely

The "on-device name" is what the user sees: under the app icon (iOS), in the
menu bar and About box (macOS), and in window titles. It is **not** the App
Store listing name (that's `app-store-metadata`), and it does **not** have to
equal the Xcode target name or the bundle id.

## The keys that decide it

| Key | What it controls | Default | Notes |
|-----|------------------|---------|-------|
| `CFBundleDisplayName` | The name shown under the icon / in most UI | falls back to `CFBundleName` | The one users actually read. Can exceed 15 chars. Localizable. |
| `CFBundleName` | Short name (menu bar on macOS, some system UI) | `$(PRODUCT_NAME)` | Apple recommends ≤15 chars or it gets truncated. |
| `PRODUCT_NAME` | Base name of the built product (`Foo.app`) | `$(TARGET_NAME)` | Also the default for `CFBundleName`. Changing this alone renames what's shown when no display name is set, **without** renaming the target. |
| `PRODUCT_BUNDLE_IDENTIFIER` | The bundle id (`com.acme.foo`) | — | **Identity, not a name.** Changing it creates a *different app* to the App Store. Don't touch it to rename. |

### Two project styles
- **Generated Info.plist** (modern Xcode, `GENERATE_INFOPLIST_FILE = YES`): there
  is no hand-edited Info.plist. Set the display name with the **build settings**
  `INFOPLIST_KEY_CFBundleDisplayName` and `INFOPLIST_KEY_CFBundleName`. In the
  Xcode UI these surface as **target → General → Display Name** and as searchable
  rows under **Build Settings**.
- **Hand-maintained Info.plist** (`GENERATE_INFOPLIST_FILE = NO`): set the
  `CFBundleDisplayName` / `CFBundleName` keys directly in the `Info.plist`
  (string values, or `$(PRODUCT_NAME)` to inherit).

`read_app_identity.sh` tells you which style the project uses and prints
the current values for each.

## Decision: rename the display only, or rename the target?

Default to **display only** — it's a one-line, low-risk change and is almost
always what "change the app's name" means.

| You want to… | Change | Cost / risk |
|--------------|--------|-------------|
| Change what users see | `PRODUCT_NAME` and/or `CFBundleDisplayName` | Low. Built product + UI name change; target, scheme, bundle id, source all unchanged. **Preferred.** |
| Rename the Xcode **target** | rename target + scheme + folder/group references | High. Touches the project file, scheme, file paths, sometimes import names. Cosmetic for users — avoid unless the developer wants the *project* renamed. |
| Change the **bundle id** | `PRODUCT_BUNDLE_IDENTIFIER` | **Severe.** It's a new app to the App Store — new app record, lost reviews/installs, signing/profile churn. Never do this just to rename. |

> A measured example: the public name was set to **Quicknote** via
> `PRODUCT_NAME`, while the target name and bundle id
> (`com.example.AppStoreAssetsGenerator`) were intentionally left unchanged —
> display renamed, identity preserved. That's the pattern to prefer.

## How to apply (display-only, the common path)

1. **Pick the keys.** For a generated Info.plist, set
   `INFOPLIST_KEY_CFBundleDisplayName = <New Name>` (and
   `INFOPLIST_KEY_CFBundleName` if the short name should change). Setting
   `PRODUCT_NAME = <New Name>` also works and additionally renames the built
   `.app`; use it when you want the product file renamed too.
2. **Apply to every user-facing target.** App extensions, widgets, a watch app,
   a Share/Action extension each have their own settings — rename the ones whose
   name is visible. System UI often shows the *containing app's* display name for
   extensions, so check what each one actually surfaces before changing it.
3. **Per-config if needed.** If Debug and Release should differ (e.g. a "Foo Dev"
   build), set the key per build configuration; otherwise set it once for all.
4. **Confirm before editing the project file** — it's a code change.

## Localizing the display name (optional)

To show a different name per language, add an `InfoPlist.strings` file in each
`<locale>.lproj` with:

```
"CFBundleDisplayName" = "Localized Name";
"CFBundleName" = "Short";
```

Only do this when the name genuinely differs by locale — most apps keep one
name everywhere. (This is in-app localization; the App Store *listing* name per
locale is separate and lives in `app-store-metadata`.)

## Verify

A rename isn't done until you've seen it resolve:
- **Clean build** (stale Info.plist values cache aggressively): Product → Clean
  Build Folder, then build.
- **Check the built product**: the `.app` name (if you changed `PRODUCT_NAME`)
  and the display name in the right place — iOS: under the icon on the
  simulator/device home screen; macOS: the menu bar app menu and About box.
- **Re-run** `read_app_identity.sh` to confirm the settings now read as
  intended, or run the authoritative
  `xcodebuild -showBuildSettings | grep -E ' (PRODUCT_NAME|INFOPLIST_KEY_CFBundleDisplayName|FULL_PRODUCT_NAME) ='`.

Then record the chosen name in the README (see
`readme-source-of-truth.md`, beside this file).
