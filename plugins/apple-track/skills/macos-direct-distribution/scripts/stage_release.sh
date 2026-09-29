#!/usr/bin/env bash
# Stage a direct-distribution release into a "stable-latest + versioned-archive"
# layout, sign the Sparkle appcast, and print (or run) an S3-compatible upload
# (Cloudflare R2, AWS S3, Backblaze B2, …). Published under <PREFIX>:
#
#   <App>.dmg                  latest — STABLE website URL + appcast enclosure
#   appcast.xml                the appcast XML (served at the SUFeedURL)
#   <version>/<App>-<ver>.dmg  permanent versioned archive (old + current)
#
# The website "Download" button points at .../<App>.dmg, which never changes
# between releases. Old builds stay downloadable under their version folder.
# The appcast advertises only the latest. The app name is read from the .app
# inside the DMG, so nothing here is app-specific.
#
# Usage:  ./stage_release.sh [path/to/<App>-X.Y.dmg]   (default: newest dist/*.dmg)
# Env (to upload): BUCKET, ENDPOINT (S3-compatible), PREFIX (key prefix),
#   DOWNLOAD_URL_PREFIX (public dir, trailing /), UPLOAD_TOOL=wrangler|aws|rclone,
#   RCLONE_REMOTE, SPARKLE_KEYCHAIN_ACCOUNT, DO_UPLOAD=1.
# Auth: wrangler (Cloudflare R2) needs no S3 keys — `wrangler login` once, then
#   just BUCKET. aws/rclone need S3 Access Key + Secret (+ ENDPOINT for aws);
#   aws-cli ≥ 2.23 may need AWS_REQUEST_CHECKSUM_CALCULATION=when_required for R2.
set -euo pipefail
# Run from the PROJECT, not from wherever this file sits. It used to `cd` to its own
# directory first, which was the project when the script lived in one — and is the
# plugin cache now, so `dist/` was never found and `release/` was written next to the
# skill. Paths below are relative to the caller's directory; SCRIPT_DIR is only for
# finding the sibling script.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

DMG="${1:-$(ls -t dist/*.dmg 2>/dev/null | head -1 || true)}"
[ -n "${DMG:-}" ] && [ -f "$DMG" ] || { echo "No DMG. Pass one, or build a notarized DMG into dist/." >&2; exit 1; }

PREFIX="${PREFIX:-releases}"
# The object name the appcast is published under. It MUST match the SUFeedURL
# baked into the app, or Sparkle 404s on every check and the app silently never
# updates. Every studio app that ships a direct channel serves it as
# appcast.xml, so that is the default; override only if an app's SUFeedURL
# genuinely differs.
APPCAST_KEY="${APPCAST_KEY:-appcast.xml}"
# Where the staged layout is written. Kept overridable so a caller can stage
# inside its own project rather than wherever this script happens to be run
# from.
RELEASE_DIR="${RELEASE_DIR:-release}"
PUB="${DOWNLOAD_URL_PREFIX:?Set DOWNLOAD_URL_PREFIX to your public releases dir (trailing /)}"
TOOL="${UPLOAD_TOOL:-aws}"

mp=$(hdiutil attach "$DMG" -nobrowse -readonly | grep -oE '/Volumes/.*' | head -1)
app=$(ls -d "$mp"/*.app | head -1)
APP=$(basename "$app" .app)
VER=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app/Contents/Info.plist")
BUILD=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$app/Contents/Info.plist")
hdiutil detach "$mp" -quiet >/dev/null
echo "Release: $APP $VER (build $BUILD)"

rm -rf "$RELEASE_DIR" && mkdir -p "$RELEASE_DIR/$VER"
cp "$DMG" "$RELEASE_DIR/$APP.dmg"            # constant latest
cp "$DMG" "$RELEASE_DIR/$VER/$APP-$VER.dmg"  # versioned archive

DOWNLOAD_URL_PREFIX="$PUB" bash "$SCRIPT_DIR/make_appcast.sh" "$RELEASE_DIR"

uploads=(
  "$RELEASE_DIR/$VER/$APP-$VER.dmg|$PREFIX/$VER/$APP-$VER.dmg|application/x-apple-diskimage"
  "$RELEASE_DIR/$APP.dmg|$PREFIX/$APP.dmg|application/x-apple-diskimage"
  "$RELEASE_DIR/appcast.xml|$PREFIX/$APPCAST_KEY|application/xml"
)
emit() {
  case "$TOOL" in
    wrangler) printf 'wrangler r2 object put %q --file %q --content-type %q --remote\n' \
              "${BUCKET:-YOUR_BUCKET}/$2" "$1" "$3" ;;
    aws)    printf 'aws s3 cp %q s3://%s/%s --endpoint-url %s --content-type %q\n' \
              "$1" "${BUCKET:-YOUR_BUCKET}" "$2" "${ENDPOINT:-https://ENDPOINT}" "$3" ;;
    rclone) printf 'rclone copyto %q %s:%s/%s --header-upload %q\n' \
              "$1" "${RCLONE_REMOTE:-remote}" "${BUCKET:-YOUR_BUCKET}" "$2" "Content-Type: $3" ;;
    *) echo "Unknown UPLOAD_TOOL=$TOOL" >&2; exit 2 ;;
  esac
}

echo ""; echo "=== Upload ($TOOL) ==="
for u in "${uploads[@]}"; do IFS='|' read -r l k c <<<"$u"; emit "$l" "$k" "$c"; done
if [ "${DO_UPLOAD:-0}" = "1" ]; then
  [ -n "${BUCKET:-}" ] || { echo "Set BUCKET (+ ENDPOINT for aws) to upload." >&2; exit 2; }
  echo ""; echo "Uploading…"
  for u in "${uploads[@]}"; do IFS='|' read -r l k c <<<"$u"; eval "$(emit "$l" "$k" "$c")"; done
fi
echo ""
echo "Download (website): ${PUB}${APP}.dmg     |  Appcast: ${PUB}${APPCAST_KEY}"
