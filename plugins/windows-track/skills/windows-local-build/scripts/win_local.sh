#!/usr/bin/env bash
# Build a Tauri app for Windows on a Mac, and check it in a local Parallels VM —
# no GitHub Actions, no Windows machine on the build side.
#
#   win_local.sh build   [x64|arm64|all]   cross-compile the exe and its NSIS installer
#   win_local.sh test    [x64|arm64|all]   run `<exe> --selftest` inside the VM (no window), print it
#   win_local.sh install [x64|arm64]       install the newest installer silently in the VM
#   win_local.sh open                      open the installed app; returns when its window closes
#   win_local.sh close                     close it
#   win_local.sh shot    [file.png]        screenshot of the VM's screen
#   win_local.sh offline | online          cut or restore the VM's network (whole VM)
#   win_local.sh snapshot                  save the VM as $WIN_SNAPSHOT (once, before a first install)
#   win_local.sh fresh                     go back to $WIN_SNAPSHOT, to test a first install
#   win_local.sh shares                    what the VM sees of the Mac — run this first
#
# Run it from the app's directory (the one holding package.json and src-tauri/), or
# copy it into the repo. Everything app-specific is read from the project or set here:
#   WIN_VM        the Parallels VM's name            (default: "Windows 11")
#   WIN_APP_DIR   the Tauri project                  (default: the current directory)
#   WIN_BIN       the exe's name, without .exe       (default: [package] name in src-tauri/Cargo.toml)
#   WIN_PRODUCT   the install folder's name          (default: productName in tauri.conf.json)
#   WIN_STAGE     a Mac folder the VM can see        (default: ~/Downloads/<bin>-vm)
#   WIN_HOME_VM   how the VM sees the Mac's $HOME    (default: \\Mac\Home)
#   WIN_SNAPSHOT  the clean snapshot's name          (default: clean)
#
# One-time setup on the Mac: brew install nsis llvm; cargo install --locked cargo-xwin;
# rustup target add x86_64-pc-windows-msvc aarch64-pc-windows-msvc.

# -h / --help prints the header above and touches nothing.
case "${1:-}" in -h|--help|"") awk 'NR>1 && !/^#/{exit} NR>1{sub(/^# ?/,""); print}' "$0"; exit 0;; esac
set -euo pipefail

VM="${WIN_VM:-Windows 11}"
APP="$(cd "${WIN_APP_DIR:-.}" && pwd)"
TAURI="$APP/src-tauri"
SNAP="${WIN_SNAPSHOT:-clean}"

# cargo-xwin calls LLVM tools (clang-cl, lld-link, llvm-lib) that Xcode's toolchain lacks.
if command -v brew >/dev/null 2>&1 && [ -d "$(brew --prefix llvm 2>/dev/null)/bin" ]; then
  PATH="$(brew --prefix llvm)/bin:$PATH"; export PATH
fi
# makensis crashes with std::bad_alloc when the locale is not UTF-8 — and a bare shell,
# a launchd job or an agent's subprocess often has none. Nothing in the error says so.
export LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

need_project() { [ -d "$TAURI" ] || { echo "no src-tauri/ in $APP — run from the app, or set WIN_APP_DIR" >&2; exit 2; }; }

bin_name() {
  [ -n "${WIN_BIN:-}" ] && { echo "$WIN_BIN"; return; }
  need_project
  # The first `name =` under [package]; a [[bin]] with another name needs WIN_BIN.
  awk '/^\[package\]/{p=1; next} /^\[/{p=0} p && /^name *=/{gsub(/.*= *"|".*/, ""); print; exit}' "$TAURI/Cargo.toml"
}

product_name() {
  [ -n "${WIN_PRODUCT:-}" ] && { echo "$WIN_PRODUCT"; return; }
  python3 - "$TAURI/tauri.conf.json" <<'PY' 2>/dev/null || bin_name
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["productName"])
PY
}

triple() { case "$1" in x64) echo x86_64-pc-windows-msvc ;; arm64) echo aarch64-pc-windows-msvc ;; *) echo "unknown arch: $1 (x64|arm64|all)" >&2; exit 2 ;; esac; }
arches() { [ "${1:-all}" = all ] && echo "x64 arm64" || echo "$1"; }

# A Mac path under $HOME, as the VM sees it.
HOME_VM="${WIN_HOME_VM:-\\\\Mac\\Home}"
winpath() {
  case "$1" in "$HOME"/*) ;; *) echo "not under \$HOME: $1 — WIN_STAGE must be a folder the VM sees" >&2; exit 2 ;; esac
  local rel="${1#"$HOME"/}"
  echo "$HOME_VM\\${rel//\//\\}"
}

# prlctl exec now and then fails before running anything ("PrlJob_GetResult: Invalid
# argument", or PrlJob_GetRetCode); one retry clears it. It also waits for the whole
# process tree, so a command that opens a window returns only when it is closed.
vm() {
  local out; out=$(prlctl exec "$VM" --current-user cmd /c "$*" 2>&1) && { printf '%s\n' "$out"; return 0; }
  case "$out" in
    *PrlJob_Get*) sleep 2; prlctl exec "$VM" --current-user cmd /c "$*" ;;
    *) printf '%s\n' "$out" >&2; return 1 ;;
  esac
}

# Put a file where the VM can see it; prints its path as the VM sees it.
stage() {
  local dir; dir="${WIN_STAGE:-$HOME/Downloads/$(bin_name)-vm}/$2"
  mkdir -p "$dir"; cp -f "$1" "$dir/"; winpath "$dir/$(basename "$1")"
}

exe_for() { echo "$TAURI/target/$(triple "$1")/release/$(bin_name).exe"; }

cmd="$1"; shift
case "$cmd" in
  build)
    need_project
    for a in $(arches "${1:-all}"); do
      echo "▶︎ build $a"
      (cd "$APP" && npx tauri build --runner cargo-xwin --target "$(triple "$a")" --bundles nsis)
    done ;;
  test)
    bin=$(bin_name); fail=0
    for a in $(arches "${1:-all}"); do
      exe=$(exe_for "$a")
      [ -f "$exe" ] || { echo "no build for $a — win_local.sh build $a" >&2; exit 1; }
      src=$(stage "$exe" "$a")
      out="${WIN_STAGE:-$HOME/Downloads/$bin-vm}/$a/selftest.json"; rm -f "$out"
      # Copied to the VM's own disk first: what users run is an installed exe, not one on a share.
      dest="%LOCALAPPDATA%\\$bin-selftest\\$a"
      vm "mkdir $dest 2>nul & copy /y \"$src\" $dest\\ >nul & $dest\\$bin.exe --selftest \"$(winpath "$out")\"" || fail=1
      echo "── $a"; cat "$out" 2>/dev/null || { echo "no result (does the app handle --selftest?)"; fail=1; }
    done
    exit $fail ;;
  install)
    a="${1:-x64}"
    inst=$(ls -t "$TAURI/target/$(triple "$a")/release/bundle/nsis/"*.exe 2>/dev/null | head -1)
    [ -n "$inst" ] || { echo "no installer for $a — win_local.sh build $a" >&2; exit 1; }
    # /S is NSIS's silent install. A perMachine installMode raises UAC and waits for a click.
    vm "\"$(stage "$inst" "$a")\" /S" ;;
  open)  vm "\"%LOCALAPPDATA%\\$(product_name)\\$(bin_name).exe\"" ;;
  close) vm "taskkill /im $(bin_name).exe" ;;
  shot)
    f="${1:-$TAURI/target/vm.png}"; prlctl capture "$VM" --file "$f" >/dev/null; echo "$f" ;;
  # The whole VM loses its network — anything else running there included.
  offline) prlctl set "$VM" --device-set net0 --disconnect ;;
  online)  prlctl set "$VM" --device-set net0 --connect ;;
  snapshot) prlctl snapshot "$VM" --name "$SNAP" ;;
  fresh)
    # The plain snapshot-list prints ids only, never names, so the name is matched in its JSON.
    id=$(prlctl snapshot-list "$VM" --json | python3 -c '
import json, sys
snaps = json.load(sys.stdin)
print(next((i for i, s in snaps.items() if s.get("name") == sys.argv[1]), ""))' "$SNAP")
    [ -n "$id" ] || { echo "no snapshot named '$SNAP' — win_local.sh snapshot" >&2; exit 1; }
    prlctl snapshot-switch "$VM" --id "$id" ;;
  shares)
    echo "── mapped drives";   vm "net use"
    echo "── $HOME_VM";        vm "dir $HOME_VM" ;;
  *) echo "unknown command: $cmd — win_local.sh --help" >&2; exit 2 ;;
esac
