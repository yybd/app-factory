# WinSparkle — details

WinSparkle is the Windows counterpart of Sparkle: a DLL that fetches an appcast,
compares versions, shows its own native update dialog, downloads the installer,
checks its signature and runs it. Everything below was read from WinSparkle 0.9.4's
`include/winsparkle.h` and README, not from memory.

## The facts the setup stands on

- **Same signature as Sparkle.** EdDSA (Ed25519), compatible with Sparkle's tools. The
  Mac build's key and Sparkle's `sign_update` sign the `.exe`, so an app that ships on
  both platforms keeps **one** key. The key "will be used to verify EdDSA signature of
  the update file" (the header), so every enclosure carries `sparkle:edSignature`.
  What WinSparkle does with an enclosure that has none was not tested — do not find
  out in production.
- **Configuration comes before `win_sparkle_init()`.** `set_appcast_url`,
  `set_eddsa_public_key` (since 0.9.0, returns 1 on success and 0 on a bad key),
  `set_app_details`, `set_app_build_version`, the callbacks — all are called before
  `init`. `win_sparkle_cleanup()` runs on exit.
- **The installer has to be able to close the app.** `can_shutdown` and
  `shutdown_request` are the two callbacks that let it. Without them the installer
  runs against a running exe and either fails or asks the user to close it by hand.
- **Versions.** `set_app_build_version` is compared with the appcast's
  `sparkle:version`, and the display version with `sparkle:shortVersionString`. The
  asset sets both to the package version, and the script writes both to the release
  version — so "newer" means a higher version number, nothing else.
- **`company` and `product`** in `set_app_details` name the registry key WinSparkle
  keeps its state under (`HKCU\Software\<company>\<product>\WinSparkle`). Changing them later
  forgets the user's "skip this version" and the last-check time. Nothing worse.
- **The appcast item.** `sparkle:os="windows"` (or `windows-x64` / `windows-arm64` —
  the arch-specific values are read only by the matching DLL).
  `sparkle:installerArguments` passes flags to the installer: `/S` for a silent NSIS
  install, `/passive` for MSI. `length` may be `0`.
- **Calling convention.** Every function is `__cdecl`, which on x64 and ARM64 is the
  one C convention, so `extern "C"` is right there. A 32-bit build is the only place
  that distinction would matter.

## Why loaded at runtime, and why it fails open

The asset loads `WinSparkle.dll` by full path with `libloading`, rather than linking
an import library. Two reasons:

1. No `.lib` in the repo and no link step to configure per architecture.
2. **A missing or broken DLL costs only the updater.** Every failure logs a warning
   and the app starts. An updater that can stop the app from opening is worse than
   no updater: the user cannot even reach the version that would fix it.

The price of failing open: a build that lost its DLL looks fine and never updates.
That is why the DLL is a bundled resource, which fails the BUILD when the file is
missing, and why step 6 of the skill checks that the installed app has it.

## Why a separate Windows feed

The macOS release flow usually regenerates `appcast.xml` from scratch, with the Mac
items only. A Windows item in that file is wiped by the next Mac release, silently,
and Windows users stop getting updates. Give Windows its own file —
`<releases>/windows/appcast.xml` — and let each platform own its feed.

## Why the enclosure points at the versioned copy

The script signs one specific set of bytes. A "stable" URL (`App-Setup.exe`, the
website's download link) is overwritten by every release, so for a window during an
upload, or forever after a failed one, the signature in the feed would describe a
different file than the URL serves, and WinSparkle refuses it. The versioned URL
(`<version>/App-Setup-<version>.exe`) never changes once written. The stable copy is
for people. The versioned copy is for the updater.

**Upload order:** the versioned installer, then the stable copy, then the appcast
**last**, so the feed never advertises a file that is not there yet.

## No Authenticode, and what that costs

The setup here does not code-sign the installer. Windows SmartScreen will show
"Windows protected your PC — unknown publisher" on the first download, until the
file builds reputation. That is a choice the app owner makes, not a bug. The EdDSA
signature is a separate thing: it protects the UPDATE path, so an installer swapped
on the server is refused by apps already installed. It does not stand in for
Authenticode, and Authenticode does not stand in for it.

If the owner later buys a certificate, sign the installer BEFORE running
`make_windows_appcast.sh`: signing changes the bytes, and the EdDSA signature has to
describe the final file.

## Not a Tauri app?

The C API is the same from any language: load the DLL (or link `WinSparkle.lib`),
make the same calls in the same order. The appcast script and the feed layout do not
care what built the installer. The asset's code is the only Tauri-specific part.
