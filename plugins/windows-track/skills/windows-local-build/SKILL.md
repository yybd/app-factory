---
name: windows-local-build
description: >-
  Build a Tauri app's Windows version on a Mac and test it in a local VM, with no
  GitHub Actions and no Windows PC: cross-compile the exe and NSIS installer with
  cargo-xwin, then install, run a windowless self-test, screenshot, cut the network
  and roll back snapshots in a Parallels VM through prlctl. Use when the user wants
  a Windows build without CI, has run out of Actions minutes, asks to cross-compile
  for Windows, test in Parallels or compare x64 and arm64, when makensis crashes
  with std::bad_alloc, or says "לבנות לווינדוס מהמק", "לבדוק בווינדוס בלי GitHub",
  "בנייה מקומית לווינדוס". It does NOT add the updater or write the feed
  (windows-direct-distribution), does not Authenticode-sign, and does not measure
  speed on real x64 hardware.
---

# Build and test a Windows app locally, from a Mac

Building Windows in GitHub Actions is the easy default and the expensive one: on a
private repo a Windows minute counts twice, and an allowance that runs out stops
every build in every repo until the month turns. A Tauri app does not need it. The
installer **cross-compiles on the Mac**, and a Windows VM on the same Mac **installs
and checks** it — both driven from one script.

Three things carry the weight, and each has its reasons in
[references/local-build.md](references/local-build.md):

1. **makensis needs a UTF-8 locale.** Without one it dies with `std::bad_alloc`,
   which reads like a memory problem and is not. The script sets `LC_ALL` itself.
2. **The VM sees only some of the Mac.** Never assume a project folder is shared;
   check, and stage files through a folder that is.
3. **The check runs without a window** (`--selftest`), because the VM is often
   someone's working Windows, and a test that opens windows over it is a test
   nobody runs.

## Prerequisites

- **Tools:** a Tauri 2 app with an NSIS target; on the Mac `brew install nsis llvm`,
  `cargo install --locked cargo-xwin`,
  `rustup target add x86_64-pc-windows-msvc aarch64-pc-windows-msvc`, Node (`npx`),
  `python3`. For testing: Parallels Desktop with a Windows 10/11 VM (`prlctl` ships
  with it). Building alone needs no VM.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** not used.
- **Other tracks:** none.

## Workflow

### 1. First: does the repo already have a script?

Look for a `win*.sh` beside the app's other build scripts. If one exists, **run it**:
it already knows the app's names and the shares of the VM it was written on. If not,
use [scripts/win_local.sh](scripts/win_local.sh) — run it from the app directory, or
**offer to copy it into the repo** so a person can build without opening a session.

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/windows-local-build/scripts/win_local.sh --help
```

It reads the exe name from `src-tauri/Cargo.toml` and the install folder from
`productName` in `tauri.conf.json`; the VM name, the staging folder and the snapshot
name are variables (`WIN_VM`, `WIN_STAGE`, `WIN_SNAPSHOT` …, all in `--help`).

### 2. One-time setup on the Mac, then build

Install the tools under Prerequisites, then:

```bash
win_local.sh build all        # or x64 / arm64
```

This is `npx tauri build --runner cargo-xwin --target <triple> --bundles nsis` per
architecture. The installer lands in
`src-tauri/target/<triple>/release/bundle/nsis/`. The **first** build downloads the
MSVC CRT and Windows SDK headers into cargo-xwin's cache — several hundred MB, once,
and under Microsoft's license terms, which cargo-xwin accepts on your behalf. Say so
before the first run.

If `makensis` crashes with `std::bad_alloc`, the build ran without the script, in a
shell with no UTF-8 locale: `export LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8`.

If **arm64** fails with `clang: error: no such file or directory: '/imsvc'`, the
culprit is `ring`, pulled in by rustls. Switch the HTTP client to `native-tls` — which
a desktop app wants anyway, because filtering networks that re-sign HTTPS with a root
in the Windows store break a bundled root list
([details](references/local-build.md#ring-on-arm64-and-why-a-desktop-app-wants-native-tls-anyway)).

### 3. Find out what the VM sees — before staging anything

```bash
win_local.sh shares           # `net use` and `dir \\Mac\Home` inside the VM
```

Parallels often shares only the "Shared Profile" folders (Desktop, Documents,
Downloads…), not the folder the code lives in. The script stages each file in
`~/Downloads/<bin>-vm` by default and the VM copies it from there to its own disk.
If Downloads is not listed, set `WIN_STAGE` to a folder that is; if the VM reaches
the Mac's home by drive letter only, set `WIN_HOME_VM` (for example `Z:`).

### 4. Give the app a windowless self-test

`win_local.sh test` runs `<exe> --selftest <file>` inside the VM and prints the JSON
the app writes. **An app that does not handle the flag simply opens its window** —
add it first; it is a dozen lines in `main.rs`, in
[references/local-build.md](references/local-build.md#the---selftest-pattern). Check
what the app depends on: the build target, its database engine and version, a
writable data folder, whatever else would differ between platforms.

```bash
win_local.sh test all         # x64 and arm64 side by side
```

On Apple Silicon the VM is ARM64: the arm64 build runs natively, the x64 build under
Windows' emulation. Identical output from both (and from the Mac build) is the
evidence that the platform layer behaves the same.

### 5. Install, open, look

```bash
win_local.sh install x64      # silent NSIS install (/S)
win_local.sh open             # blocks until the window is closed — run it in the background
win_local.sh shot             # PNG of the VM's screen
win_local.sh close
```

`prlctl exec` waits for the whole process tree, so `open` returns only when the app
quits. Start it in the background and take `shot`s, or `close` it from another call.

### 6. First install and no network

```bash
win_local.sh snapshot         # once, on a clean VM, before the app was ever installed
win_local.sh fresh            # back to it: a true first install
win_local.sh offline          # / online
```

`offline` disconnects the **whole VM** — anything else running there loses its
network too. Ask before running it on a VM someone is working in, and always run
`online` afterwards. `fresh` discards the VM's current state; ask before it as well.

### 7. Report what the VM could not show

Name these in the report rather than leaving them implied
([details](references/local-build.md#what-the-vm-cannot-show)):

- **Speed on real x64 hardware** — emulation says nothing about it. One run on an
  ordinary PC before a first release.
- **WebView2 on an offline Windows 10.** Windows 11 ships it; an older Windows 10 may
  not, and Tauri's default installer downloads it. For users without a network, a
  second installer with `webviewInstallMode: offlineInstaller` (about 150 MB more).
- **Windows 7 and 8** are not supported at all: WebView2 and Tauri 2 need Windows 10+.

## Without Parallels

Parallels costs money; **UTM** is free and runs Windows 11 ARM well. Building needs
neither — it happens on the Mac. But UTM has no good equivalent of `prlctl exec
--current-user` (its guest-agent `exec` runs as a service, not as the signed-in user),
so `test`, `install`, `open`, `shot` and the network commands do not work with it. What is left
is by hand: copy the installer into the VM through a shared folder, install it, run
`<exe> --selftest out.json` in a Windows terminal, and read the file.

## Scripts

- [scripts/win_local.sh](scripts/win_local.sh) — build, test, install, open, close,
  shot, offline/online, snapshot/fresh, shares; `--help` lists every variable.

## References

- [references/local-build.md](references/local-build.md) — the cross-compile chain
  and its failures (including `ring` on arm64 and native-tls), Parallels' shares and `prlctl exec`'s quirks, the `--selftest`
  pattern in Rust, x64 under emulation, and what a VM cannot show.

## Boundaries

This skill **builds and checks**. It does not add the updater or write the appcast
(`windows-direct-distribution`), does not Authenticode-sign or notarize anything,
does not upload or publish, and does not build the Mac version. It does not set up
GitHub Actions — it is the way around them.
