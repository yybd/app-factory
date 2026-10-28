# Building and testing Windows locally — the facts and their reasons

## The cross-compile chain

Tauri supports cross-compiling its **NSIS** bundle from macOS or Linux (not MSI —
WiX runs only on Windows). The pieces:

| Piece | Why it is there |
|---|---|
| `cargo-xwin` | Builds Rust for `*-pc-windows-msvc` off Windows: it fetches the MSVC CRT and Windows SDK headers and libraries (with `xwin`) and drives the LLVM tools against them. Passed to Tauri as `--runner cargo-xwin`. |
| `brew install llvm` | `clang-cl`, `lld-link`, `llvm-lib` — the MSVC-compatible front ends Xcode's toolchain does not include. The script prepends `$(brew --prefix llvm)/bin` to `PATH`. |
| `brew install nsis` | `makensis`, which Tauri calls to produce the `-setup.exe`. |
| rustup targets | `x86_64-pc-windows-msvc` and `aarch64-pc-windows-msvc` — install both, or only the one you ship. |

The first build downloads the SDK into cargo-xwin's cache (several hundred MB) and
accepts Microsoft's license for it. Later builds reuse it.

**`--bundles nsis`** keeps Tauri from trying the Mac bundles on a Windows target, and
**`--target`** is mandatory: without it Tauri builds for the host.

### `makensis` and `std::bad_alloc`

`makensis` on macOS aborts with `std::bad_alloc` when the process has no UTF-8
locale. Nothing in the message points at the locale — it reads like running out of
memory, and the obvious fixes (more memory, another NSIS version) change nothing. A
terminal usually has `LANG` set; a bare `bash -c`, a launchd job or an agent's
subprocess often does not, which is why the same command "works in my terminal".
The fix is two variables, and the script sets them unconditionally:

```bash
export LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
```

### `ring` on arm64, and why a desktop app wants native-tls anyway

**`ring` does not build for `aarch64-pc-windows-msvc` under cargo-xwin.** It is
pulled in by `rustls` — for example through `ureq` or `reqwest` with their rustls
features. Its build script calls `clang` while cargo-xwin passes `clang-cl` flags, and
the build stops with:

```
clang: error: no such file or directory: '/imsvc'
```

The x64 target builds fine, so the failure shows up only once arm64 is added. The fix
that worked: drop rustls and use the platform's TLS (SChannel on Windows) through
`native-tls`. With `ureq` 2:

```toml
ureq = { version = "2", default-features = false, features = ["json", "native-tls"] }
native-tls = "0.2"
```

```rust
let agent = ureq::AgentBuilder::new()
    .tls_connector(std::sync::Arc::new(native_tls::TlsConnector::new()?))
    .build();
```

(`reqwest`: `default-features = false, features = ["native-tls", …]`.) Then
`cargo tree -i ring` should print nothing — if it prints a path, something else still
pulls rustls in.

**The stronger reason is the user's network, not the build.** Filtering networks —
a corporate TLS-inspecting proxy, or an ISP-level content filter (NetFree and Rimon
are common examples in Israel) — re-sign HTTPS with their own root certificate,
installed in the Windows certificate store. rustls with a bundled root list
(`webpki-roots`) does not know that root and rejects every connection, so the app
fails exactly on the filtered machines, while browsers on them work. SChannel trusts
whatever the system trusts. This is a reasoned recommendation, **not yet tested on a
machine behind such a filter** — if the app's users may sit behind one, test there
before calling it settled. (`rustls-native-certs` / `rustls-platform-verifier` is
the rustls-side alternative, but it does not solve the arm64 build above.)

## The VM through Parallels

`prlctl exec <vm> --current-user cmd /c "<command>"` runs a command **as the
signed-in Windows user**, in their session, and returns its output and exit code.
`--current-user` matters: without it the command runs as SYSTEM, sees a different
`%LOCALAPPDATA%`, no mapped drives, and cannot show a window on the user's screen.

### What the VM can see

Parallels decides which Mac folders a VM sees, and the answer varies by VM: "Shared
Profile" maps Desktop, Documents, Downloads and a few more; "Share Mac" maps all of
home; custom shared folders appear as `\\Mac\<name>`. A project under any other folder
is often **invisible** to the VM. Check, do not assume:

```bat
net use              :: drive letters mapped to \\Mac\…
dir \\Mac\Home       :: which home folders are actually there
```

(`win_local.sh shares` runs both.) Then stage through a folder that appears. The
script copies each file to `<arch>/` under `WIN_STAGE` (default `~/Downloads/<bin>-vm`)
and addresses it as `\\Mac\Home\Downloads\…`; set `WIN_HOME_VM` if the VM reaches
the Mac's home under another name. The VM then copies the exe to its **own** disk
before running it: an installed app runs from a local disk, and an exe on a network
share behaves differently (zone marks, file locking, speed).

Building **on** a share inside the VM is slow for the same reason; cross-compiling on
the Mac avoids it altogether.

### `prlctl exec`'s two quirks

1. **It sometimes fails before running anything** — `PrlJob_GetResult: Invalid
   argument` or `PrlJob_GetRetCode: Invalid argument`, with no output. A retry a
   couple of seconds later succeeds. The script retries once, only on that message;
   any other failure is the command's own and is passed through.
2. **It waits for the whole process tree.** A command that starts a GUI app returns
   when the app quits, not when its window appears. Run `open` in the background, or
   close the app from a second call (`taskkill /im <bin>.exe`).

Quoting: the command crosses the Mac shell, `prlctl` and `cmd`. Prefer single quotes
on the Mac side for a literal backslash path (`'dir \\Mac\Home'`), and keep `&`
chains inside the one quoted argument.

### Snapshots and the network

- `prlctl snapshot <vm> --name clean` once, before the app was ever installed, and
  `prlctl snapshot-switch <vm> --id <id>` to return to it. **`snapshot-list` prints
  only ids, never names** — the name is in `snapshot-list --json`, which is what the
  script matches. Switching discards the VM's current state.
- `prlctl set <vm> --device-set net0 --disconnect` / `--connect` cuts the VM's
  network adapter. It is the whole VM: every program in it goes offline, including
  whatever the user is doing there.

## UTM instead of Parallels

UTM (free, QEMU-based) runs Windows 11 ARM on Apple Silicon. Building is unaffected —
it is on the Mac. Testing is not: UTM's command-line tool (`utmctl`) starts, stops and
lists VMs, and its `exec` and `file` commands work only through the QEMU guest agent,
which has to be installed in Windows and runs as a service — not as the signed-in user,
so no window on their screen and a different `%LOCALAPPDATA%`. It is not a substitute
for `prlctl exec --current-user`, and the script was never tested against it. So
nothing in the script beyond `build` applies. By hand: share a folder in UTM, copy the installer in, install
it, run `<bin>.exe --selftest out.json` from a Windows terminal, read the JSON.

## The `--selftest` pattern

The check that runs in the VM must not open a window: the VM is often the user's own
Windows, in use, and a test that steals focus there is a test they stop running. So
the app answers a flag before Tauri starts, writes JSON to a file, and exits.

**A file, not stdout:** a release build uses the `windows` subsystem (the
`#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]` line Tauri
generates), so it has no console, and printed output can be lost depending on how it
was started. A file always arrives.

In `src-tauri/src/main.rs`, before `run()`:

```rust
fn main() {
    // `--selftest <file>`: run the checks without a window, write them as JSON, exit.
    let args: Vec<String> = std::env::args().collect();
    if let Some(i) = args.iter().position(|a| a == "--selftest") {
        let out = args.get(i + 1).cloned().unwrap_or_else(|| "selftest.json".into());
        let checks = app_lib::selftest::run(&std::env::temp_dir());
        let ok = checks.iter().all(|c| c.ok);
        std::fs::write(&out, serde_json::to_string_pretty(&checks).unwrap()).expect("write selftest");
        std::process::exit(if ok { 0 } else { 1 });
    }
    app_lib::run()
}
```

(`app_lib` is the crate name Tauri generated in `Cargo.toml`'s `[lib]`.) And a
`selftest.rs` in the library:

```rust
use serde::Serialize;
use std::path::Path;

#[derive(Serialize)]
pub struct Check { pub name: String, pub ok: bool, pub detail: String }

fn check(name: &str, r: Result<String, String>) -> Check {
    let (ok, detail) = match r { Ok(d) => (true, d), Err(d) => (false, d) };
    Check { name: name.into(), ok, detail }
}

pub fn run(dir: &Path) -> Vec<Check> {
    let target = format!("{}-{}", std::env::consts::OS, std::env::consts::ARCH);
    let mut checks = vec![Check { name: "target".into(), ok: true, detail: target }];
    // One check per thing the app relies on that could differ by platform — e.g. its
    // database engine and version, a search index, a writable data folder:
    checks.push(check("data folder", (|| {
        std::fs::create_dir_all(dir).map_err(|e| e.to_string())?;
        let f = dir.join("selftest.tmp");
        std::fs::write(&f, "ok").map_err(|e| e.to_string())?;
        std::fs::remove_file(&f).map_err(|e| e.to_string())?;
        Ok(dir.display().to_string())
    })()));
    checks
}
```

Make each `detail` **exact** — a version string, a computed value printed to fixed
precision — so outputs from different builds can be compared by eye or by `diff`.
The same flag runs on the Mac (`<app> --selftest out.json`), which makes the Mac
build the reference the Windows ones are compared against.

Other scripted checks follow the same shape: a flag handled before `run()`, doing one
operation on a path given on the command line (importing a file into a scratch
folder, twice, to prove the second run changes nothing), and exiting.

## x64 under emulation

On Apple Silicon a Windows VM is ARM64. An arm64 build runs natively; an x64 build
runs under Windows' x64 emulation, transparently. That is good enough to prove
behaviour — and most users' PCs are x64, so the x64 build is the one that matters.
`test all` runs both and prints them one after the other; differences point at a
platform-specific dependency (a C library compiled differently, a path assumption).

## What the VM cannot show

1. **Speed on real x64 hardware.** Emulation adds an unknown cost, so timings in the
   VM say nothing in either direction. Before a first release, run once on an
   ordinary x64 PC. No Mac offers an x64 Windows VM — UTM's x64 emulation is far too
   slow to judge by.
2. **WebView2 on an offline Windows 10.** Windows 11 always has WebView2. An older
   Windows 10 may not, and Tauri's default installer **downloads** it at install time
   — which fails without a network. For users who may be offline, build a second
   installer with the runtime inside:

   ```json
   { "bundle": { "windows": { "webviewInstallMode": { "type": "offlineInstaller" } } } }
   ```

   It adds roughly 150 MB. Ship it beside the small one rather than instead of it.
3. **Windows 7 and 8.** Not supported: WebView2 and Tauri 2 require Windows 10 or
   later. Say so on the download page — there is no build that fixes it.
4. **SmartScreen.** An unsigned installer downloaded from the web shows "unknown
   publisher"; one copied in from a share may not. Signing is a separate decision
   (see `windows-direct-distribution`).
