#!/usr/bin/env bash
# Generate / refresh a Sparkle appcast for the DIRECT distribution channel.
#
# Drop the notarized DMG(s) for each release into the release directory and run
# this. Each DMG is signed with the EdDSA key in your login Keychain via
# Sparkle's `sign_update`, and an appcast.xml with absolute download URLs +
# signatures is written.
#
# Why sign_update (not generate_appcast): both ship with Sparkle, but
# generate_appcast needs interactive Keychain approval the first time and silently
# skips signing if denied (e.g. in CI / a non-GUI shell). sign_update is
# deterministic. The cost is that this script handles a flat list of DMGs rather
# than generating binary deltas — fine for most apps.
#
# Config via environment variables:
#   (arg 1)                    release directory       (default: release)
#   SPARKLE_KEYCHAIN_ACCOUNT   keychain key account    (default: app's default key)
#   DOWNLOAD_URL_PREFIX        absolute URL dir prefix (REQUIRED; trailing slash)
#   APPCAST_TITLE              <channel><title>        (default: "Updates")
#
# Publish: upload the DMG(s) AND appcast.xml so the appcast is reachable at the
# exact SUFeedURL the app was built with.
set -euo pipefail

RELEASE_DIR="${1:-release}"
ACCOUNT="${SPARKLE_KEYCHAIN_ACCOUNT:-}"
PREFIX="${DOWNLOAD_URL_PREFIX:-}"
TITLE="${APPCAST_TITLE:-Updates}"

if [ -z "$PREFIX" ]; then
  echo "Set DOWNLOAD_URL_PREFIX to the absolute URL directory your DMGs live under," >&2
  echo "e.g. DOWNLOAD_URL_PREFIX='https://downloads.example.com/myapp/releases/'" >&2
  exit 2
fi

SU=$(find ~/Library/Developer/Xcode/DerivedData -path "*artifacts/sparkle/Sparkle/bin/sign_update" 2>/dev/null | head -1)
if [ -z "${SU:-}" ] || [ ! -x "$SU" ]; then
  echo "sign_update not found. Resolve the Sparkle package first:" >&2
  echo "  xcodebuild -scheme '<Your App> (Direct)' -resolvePackageDependencies" >&2
  exit 1
fi
if ! ls "$RELEASE_DIR"/*.dmg >/dev/null 2>&1; then
  echo "No .dmg in $RELEASE_DIR/. Put the notarized release DMG(s) there first." >&2
  exit 1
fi

acct=(); [ -n "$ACCOUNT" ] && acct=(--account "$ACCOUNT")
OUT="$RELEASE_DIR/appcast.xml"
{
  echo '<?xml version="1.0" standalone="yes"?>'
  echo '<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" version="2.0">'
  echo '    <channel>'
  echo "        <title>${TITLE}</title>"
  for dmg in "$RELEASE_DIR"/*.dmg; do
    [ -e "$dmg" ] || continue
    mp=$(hdiutil attach "$dmg" -nobrowse -readonly | grep -oE '/Volumes/.*' | head -1)
    app=$(ls -d "$mp"/*.app | head -1)
    plist="$app/Contents/Info.plist"
    short=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$plist" 2>/dev/null || echo "")
    build=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$plist" 2>/dev/null || echo "$short")
    minos=$(/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' "$plist" 2>/dev/null || echo "")
    hdiutil detach "$mp" -quiet >/dev/null
    sig=$("$SU" "${acct[@]}" "$dmg")   # → sparkle:edSignature="..." length="..."
    url="${PREFIX}$(basename "$dmg")"
    echo '        <item>'
    echo "            <title>${short}</title>"
    echo "            <sparkle:version>${build}</sparkle:version>"
    echo "            <sparkle:shortVersionString>${short}</sparkle:shortVersionString>"
    [ -n "$minos" ] && echo "            <sparkle:minimumSystemVersion>${minos}</sparkle:minimumSystemVersion>"
    echo "            <enclosure url=\"${url}\" type=\"application/octet-stream\" ${sig} />"
    echo '        </item>'
  done
  echo '    </channel>'
  echo '</rss>'
} > "$OUT"

echo "Wrote ${OUT}"
echo "Upload ${RELEASE_DIR}/*.dmg and appcast.xml; serve the appcast at your SUFeedURL."
