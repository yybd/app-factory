#!/usr/bin/env bash
# Sign a Windows installer with the Sparkle EdDSA key and write a WinSparkle appcast.
#
# WinSparkle verifies the same Ed25519 signature Sparkle does, so Sparkle's own
# `sign_update` signs the .exe — one key for the Mac and Windows builds of an app.
# The appcast written here holds ONE item: the release being published. It is a
# separate feed from the macOS one on purpose (see references/winsparkle.md).
#
# Usage:
#   make_windows_appcast.sh <installer.exe>
#
# Config via environment variables:
#   DOWNLOAD_URL               absolute URL the installer will be served from
#                              (REQUIRED — the VERSIONED copy, so the signature
#                              always matches the bytes behind the URL)
#   VERSION                    release version (default: parsed from a Tauri NSIS
#                              name, <Product>_<version>_x64-setup.exe)
#   SIGN_UPDATE                path to Sparkle's sign_update (REQUIRED)
#   SPARKLE_KEY_FILE           exported private key file, OR
#   SPARKLE_KEYCHAIN_ACCOUNT   the login-Keychain account holding the key
#   OUT_DIR                    where appcast.xml is written (default: release/windows)
#   APPCAST_TITLE              <channel><title>           (default: "Updates")
#   RELEASE_NOTES_URL          <sparkle:releaseNotesLink> (optional)
#   INSTALLER_ARGS             sparkle:installerArguments, e.g. "/S" for a silent
#                              NSIS install (default: none — the installer's own UI)
#   SPARKLE_OS                 windows | windows-x64 | windows-arm64 (default: windows)
#
# Nothing is uploaded. Upload the installer first and appcast.xml LAST, so the
# feed never advertises a build that is not downloadable yet.

# -h / --help prints the header above and touches nothing.
case "${1:-}" in -h|--help) awk 'NR>1 && !/^#/{exit} NR>1{sub(/^# ?/,""); print}' "$0"; exit 0;; esac
set -euo pipefail

SRC="${1:-}"
[ -n "$SRC" ] && [ -f "$SRC" ] || { echo "❌ usage: $0 <installer.exe>  (--help for the options)"; exit 1; }
[ -n "${DOWNLOAD_URL:-}" ] || { echo "❌ DOWNLOAD_URL is required"; exit 1; }
case "$DOWNLOAD_URL" in https://*) ;; *) echo "❌ DOWNLOAD_URL must be an absolute https URL"; exit 1;; esac
[ -n "${SIGN_UPDATE:-}" ] && [ -x "$SIGN_UPDATE" ] \
  || { echo "❌ SIGN_UPDATE must point at Sparkle's sign_update"; exit 1; }

VERSION="${VERSION:-}"
if [ -z "$VERSION" ]; then
  VERSION="$(basename "$SRC" | sed -nE 's/.*_([0-9]+(\.[0-9]+)+)_[^_]*-setup\.exe$/\1/p')"
  [ -n "$VERSION" ] || { echo "❌ cannot read the version from the file name — set VERSION"; exit 1; }
fi

KEY_ARGS=()
if [ -n "${SPARKLE_KEY_FILE:-}" ]; then
  [ -f "$SPARKLE_KEY_FILE" ] || { echo "❌ SPARKLE_KEY_FILE not found: $SPARKLE_KEY_FILE"; exit 1; }
  KEY_ARGS=(--ed-key-file "$SPARKLE_KEY_FILE")
elif [ -n "${SPARKLE_KEYCHAIN_ACCOUNT:-}" ]; then
  KEY_ARGS=(--account "$SPARKLE_KEYCHAIN_ACCOUNT")
else
  echo "❌ set SPARKLE_KEY_FILE or SPARKLE_KEYCHAIN_ACCOUNT"; exit 1
fi

OUT_DIR="${OUT_DIR:-release/windows}"
TITLE="${APPCAST_TITLE:-Updates}"
OS="${SPARKLE_OS:-windows}"
case "$OS" in windows|windows-x64|windows-arm64) ;; *) echo "❌ SPARKLE_OS: $OS"; exit 1;; esac

echo "▶︎ signing $(basename "$SRC") (EdDSA)…"
# Prints: sparkle:edSignature="…" length="…"
SIG_ATTRS="$("$SIGN_UPDATE" "${KEY_ARGS[@]}" "$SRC")"
[[ "$SIG_ATTRS" == sparkle:edSignature=*length=* ]] \
  || { echo "❌ unexpected sign_update output: $SIG_ATTRS"; exit 1; }

NOTES=""
[ -n "${RELEASE_NOTES_URL:-}" ] && NOTES="
            <sparkle:releaseNotesLink>${RELEASE_NOTES_URL}</sparkle:releaseNotesLink>"
ARGS=""
[ -n "${INSTALLER_ARGS:-}" ] && ARGS=" sparkle:installerArguments=\"${INSTALLER_ARGS}\""

mkdir -p "$OUT_DIR"
cat > "$OUT_DIR/appcast.xml" <<XML
<?xml version="1.0" encoding="utf-8"?>
<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" version="2.0">
    <channel>
        <title>${TITLE}</title>
        <item>
            <title>${VERSION}</title>
            <pubDate>$(LC_ALL=C date -R 2>/dev/null || LC_ALL=C date "+%a, %d %b %Y %H:%M:%S %z")</pubDate>${NOTES}
            <sparkle:version>${VERSION}</sparkle:version>
            <sparkle:shortVersionString>${VERSION}</sparkle:shortVersionString>
            <enclosure url="${DOWNLOAD_URL}" sparkle:os="${OS}"${ARGS} ${SIG_ATTRS} type="application/octet-stream"/>
        </item>
    </channel>
</rss>
XML

echo "✅ $OUT_DIR/appcast.xml — version $VERSION → $DOWNLOAD_URL"
echo "   upload the installer to that URL first, then the appcast."
