---
name: windows-direct-distribution
description: >-
  Give a Windows desktop app (Tauri first) automatic updates outside any store:
  WinSparkle loaded at runtime, the NSIS installer signed with the same EdDSA key
  as Sparkle on the Mac, and a Windows appcast of its own beside the macOS one. Use
  when the user wants a Windows build that updates itself, adds WinSparkle, asks
  for a Windows appcast or update feed, or says "עדכונים אוטומטיים בווינדוס",
  "הפצה לווינדוס", "WinSparkle". It does NOT Authenticode-sign the installer, does
  not publish to the Microsoft Store, and does not upload — hosting stays the
  app's own script. The Mac half is macos-direct-distribution's job.
---

# Direct distribution + auto-updates for a Windows app

Give a Windows app what `macos-direct-distribution` gives a Mac one: a download
from your own server that updates itself. The updater is **WinSparkle**, which
reads the Sparkle appcast format and verifies the same EdDSA signature — so a Tauri
app that already ships on the Mac with Sparkle keeps **one** signing key for both.

Three things carry the weight, and each has a reason in
[references/winsparkle.md](references/winsparkle.md):

1. **The DLL is loaded at runtime and fails open.** A missing updater must never
   stop the app from starting.
2. **Windows has its own feed** (`<releases>/windows/appcast.xml`). A Mac release
   that regenerates `appcast.xml` would otherwise wipe the Windows item silently.
3. **The enclosure points at the versioned installer**, never the stable download
   link, so the signature always describes the bytes behind the URL.

## Prerequisites

- **Tools:** a Tauri 2 app with an NSIS Windows build (CI on `windows-latest` is
  enough; no Windows machine is needed to build). On the Mac: Sparkle's
  `sign_update` (in the `bin/` of a Sparkle release, or under DerivedData after an
  Xcode project resolved the package), `curl`, `unzip`, `shasum`.
- **Credentials:** the Sparkle EdDSA key pair. An app with a Mac Sparkle build
  already has one — reuse it, as either the exported key file or its login-Keychain
  account. An app without one generates it once with Sparkle's `generate_keys` (see
  `macos-direct-distribution`'s Sparkle reference for generating and backing it up).
- **Hub (`$APP_HUB`):** not used — everything is in the app's own repo.
- **Other tracks:** none required. `apple-track`'s `macos-direct-distribution` is
  the Mac half, if the app has one.

**A Windows machine is needed once**, for step 6. Building and signing do not
need one; proving that an installed app updates itself does.

## Workflow

### 1. Confirm the plan with the user

- The **Windows appcast URL** — beside the Mac feed, in its own folder:
  `https://<host>/<app>/releases/windows/appcast.xml`. It is compiled into every
  installed copy, so it cannot move later without stranding them.
- **The key:** reuse the Mac's Sparkle key (normal), or a new pair. Read the
  public half (base64), and say which: an app shipped with the wrong public key
  cannot verify anything, and only a manual reinstall fixes it.
- **No Authenticode** unless the owner says otherwise: SmartScreen will warn
  "unknown publisher" on first download. Say so before it surprises them.

### 2. Fetch the DLL — locally and in CI

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/windows-direct-distribution/scripts/fetch_winsparkle.sh
```

It writes `src-tauri/winsparkle/WinSparkle.dll`, pinned to 0.9.4 and checked
against its SHA-256. **Add `src-tauri/winsparkle/` to `.gitignore`** — a
third-party binary does not belong in the repo, and in a public one it is
someone else's file published under your name.

In the Windows CI job, before `tauri build`, paste
[assets/fetch-winsparkle-step.yml](assets/fetch-winsparkle-step.yml): the same pin
and checksum, in PowerShell. Keep the two pins in step.

### 3. Bundle it with the Windows build only

Copy [assets/tauri.windows.conf.json](assets/tauri.windows.conf.json) to
`src-tauri/`. Tauri merges it into `tauri.conf.json` on Windows only. It narrows
the targets to NSIS and puts `WinSparkle.dll` next to the exe. If the file
already exists, merge the `bundle.resources` entry into it rather than
overwriting.

A missing DLL now fails the **build** — which is what makes failing open at
runtime safe.

### 4. Add the updater to the app

1. Copy [assets/winsparkle.rs](assets/winsparkle.rs) to `src-tauri/src/` and fill
   the four placeholders: `__APPCAST_URL__`, `__EDDSA_PUBLIC_KEY__`, and the
   fallback `__COMPANY__` / `__PRODUCT__` (used only when `tauri.conf.json` has no
   `bundle.publisher` / `productName`).
2. `Cargo.toml`:
   ```toml
   [target.'cfg(target_os = "windows")'.dependencies]
   libloading = "0.8"
   ```
3. `lib.rs`: `#[cfg(target_os = "windows")] mod winsparkle;`, call
   `winsparkle::init(app.handle())` inside `.setup`, and run
   `winsparkle::cleanup()` on `RunEvent::Exit` — which means switching
   `.run(ctx)` to `.build(ctx)?.run(|app, event| …)`.
4. A manual "Check for updates" control, if the app has one: expose a
   `#[tauri::command]` that calls `winsparkle::check_with_ui()` on Windows and
   returns an error elsewhere, and register it in `invoke_handler`. WinSparkle
   draws its own dialog — the front end only invokes it.

Check it compiles for Windows before going further. `cargo check` on the Mac does
not build the `cfg(windows)` code; run the Windows CI job.

### 5. Sign the installer and write the feed

After the CI build produced `<Product>_<version>_x64-setup.exe`:

```bash
DOWNLOAD_URL='https://<host>/<app>/releases/windows/<version>/<App>-Setup-<version>.exe' \
SIGN_UPDATE=<path>/sign_update \
SPARKLE_KEY_FILE=<path to the exported key>   # or SPARKLE_KEYCHAIN_ACCOUNT='<App>'
OUT_DIR=release/windows \
  bash ${CLAUDE_PLUGIN_ROOT}/skills/windows-direct-distribution/scripts/make_windows_appcast.sh \
  <Product>_<version>_x64-setup.exe
```

It signs with `sign_update` and writes a one-item `appcast.xml`. It uploads
nothing. Upload with the app's own tooling, in this order: the **versioned**
installer (the `DOWNLOAD_URL` above), the stable copy for the website link, and
the appcast **last**. If the app already has a publish script, the clean
integration is to call this script from it — not to grow a second uploader.

### 6. Prove it on a Windows machine — once, before calling it done

A build that compiles has not shown that it updates. On Windows:

1. Install version N from the stable link. Confirm `WinSparkle.dll` sits beside
   the exe in the install folder.
2. Publish version N+1 (step 5).
3. Open N and use the manual check (or wait for the automatic one). Expect
   WinSparkle's dialog offering N+1; let it install; the app closes, the
   installer runs, and N+1 opens.

If nothing appears, the app logs `WinSparkle disabled: …` — read it before
anything else. Until this has passed once, report the work as **built, not
verified**.

### 7. Document it

Add the Windows half to the README's distribution section: the feed URL, where
the DLL comes from (and that it is gitignored), the key in use, and the three
upload steps in order.

## Scripts & assets

- [scripts/fetch_winsparkle.sh](scripts/fetch_winsparkle.sh) — the pinned,
  checksum-verified DLL (`WINSPARKLE_ARCH=x64|ARM64|Win32`).
- [scripts/make_windows_appcast.sh](scripts/make_windows_appcast.sh) — signs the
  installer and writes the Windows appcast; `--help` lists every variable.
- [assets/winsparkle.rs](assets/winsparkle.rs) — the Tauri module: runtime
  loading, configuration before `init`, the shutdown callbacks, fail-open.
- [assets/tauri.windows.conf.json](assets/tauri.windows.conf.json) — NSIS + the DLL
  as a Windows-only resource.
- [assets/fetch-winsparkle-step.yml](assets/fetch-winsparkle-step.yml) — the CI step.

## References

- [references/winsparkle.md](references/winsparkle.md) — the API facts, why
  runtime loading, why a separate feed, why the versioned enclosure, SmartScreen
  and Authenticode, and the non-Tauri path.

## Boundaries

This skill wires the **updater** and writes the **feed**. It does not build the
CI workflow around it (it adds one step to the one the app has), does not
Authenticode-sign the installer, does not upload or choose hosting, and does not
touch the macOS feed — that is `macos-direct-distribution`, and the two feeds stay
separate files.
