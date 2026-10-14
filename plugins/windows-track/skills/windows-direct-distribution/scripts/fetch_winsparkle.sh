#!/usr/bin/env bash
# Fetch WinSparkle.dll into an app repo, pinned and checksum-verified.
#
# The DLL is a binary from a third party: keep it out of git (add the destination
# to .gitignore) and fetch it before every Windows build — in CI and once per
# clone on a dev machine. A Tauri build that bundles it as a resource fails
# without it, which is the point: an installer without its updater is the
# failure nobody notices until users are stranded on an old version.
#
# Usage:
#   fetch_winsparkle.sh [destination]   (default: src-tauri/winsparkle/WinSparkle.dll)
#
# Config via environment variables:
#   WINSPARKLE_ARCH   x64 | ARM64 | Win32   (default: x64)
#
# The pin below is WinSparkle 0.9.4. Moving it means a new version AND a new
# checksum, taken from the release you downloaded and read — never one copied
# from a page.

# -h / --help prints the header above and touches nothing.
case "${1:-}" in -h|--help) awk 'NR>1 && !/^#/{exit} NR>1{sub(/^# ?/,""); print}' "$0"; exit 0;; esac
set -euo pipefail

WINSPARKLE_VERSION="0.9.4"
WINSPARKLE_SHA256="6037df37fc263bd1650a1c4949681a9d40ffe991d01f35892a406cb5d103c976"
URL="https://github.com/vslavik/winsparkle/releases/download/v${WINSPARKLE_VERSION}/WinSparkle-${WINSPARKLE_VERSION}.zip"
DEST="${1:-src-tauri/winsparkle/WinSparkle.dll}"
ARCH="${WINSPARKLE_ARCH:-x64}"
case "$ARCH" in
  x64|ARM64|Win32) INNER="WinSparkle-${WINSPARKLE_VERSION}/${ARCH}/Release/WinSparkle.dll" ;;
  *) echo "❌ WINSPARKLE_ARCH: $ARCH (x64 | ARM64 | Win32)"; exit 1 ;;
esac

if [ -f "$DEST" ]; then
  echo "✅ $DEST already present — nothing to do."
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "▶︎ downloading WinSparkle ${WINSPARKLE_VERSION}…"
curl -fsSL -o "$TMP/winsparkle.zip" "$URL"

echo "▶︎ verifying checksum…"
echo "${WINSPARKLE_SHA256}  $TMP/winsparkle.zip" | shasum -a 256 -c - >/dev/null \
  || { echo "❌ checksum mismatch — refusing to install"; exit 1; }

unzip -q "$TMP/winsparkle.zip" "$INNER" -d "$TMP"
mkdir -p "$(dirname "$DEST")"
cp "$TMP/$INNER" "$DEST"

echo "✅ WinSparkle ${WINSPARKLE_VERSION} ($ARCH) → $DEST"
