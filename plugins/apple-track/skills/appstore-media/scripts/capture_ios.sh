#!/bin/bash
# capture_ios.sh — run the demo flow on a simulator, recording video and collecting screenshots.
# Part of the appstore-media skill. Requires Xcode 16+.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: capture_ios.sh -s <scheme> [-w <workspace>|-p <project>] [options]

Options:
  -s SCHEME      Xcode scheme (required)
  -w PATH        .xcworkspace path (or -p for .xcodeproj)
  -p PATH        .xcodeproj path
  -t TEST        Test to run, e.g. MyAppUITests/DemoFlowTests (default: whole UI test target detection fails -> required)
  -d DEVICE      Simulator name (default: "iPhone 17 Pro Max")
  -l LOCALES     Comma-separated locales (default: "he,en-US")
  -m MODE        screenshots | video | both (default: both)
  -o DIR         Output root (default: ./AppStoreMedia)
  -n APPNAME     App name for output folder (default: scheme)

Example:
  capture_ios.sh -s MyApp -p MyApp.xcodeproj -t MyAppUITests/DemoFlowTests -l he,en-US -m both
EOF
  exit 1
}

DEVICE="iPhone 17 Pro Max"; LOCALES="en-US"; MODE="both"; OUT="./AppStoreMedia"
SCHEME=""; CONTAINER=(); TEST=""; APPNAME=""
while getopts "s:w:p:t:d:l:m:o:n:h" opt; do
  case $opt in
    s) SCHEME="$OPTARG";;
    w) CONTAINER=(-workspace "$OPTARG");;
    p) CONTAINER=(-project "$OPTARG");;
    t) TEST="$OPTARG";;
    d) DEVICE="$OPTARG";;
    l) LOCALES="$OPTARG";;
    m) MODE="$OPTARG";;
    o) OUT="$OPTARG";;
    n) APPNAME="$OPTARG";;
    *) usage;;
  esac
done
[ -z "$SCHEME" ] && usage
[ -z "$TEST" ] && { echo "ERROR: -t TEST is required (e.g. MyAppUITests/DemoFlowTests)"; exit 1; }
APPNAME="${APPNAME:-$SCHEME}"

# --- boot simulator ---------------------------------------------------------
UDID=$(xcrun simctl list devices available | grep -F "$DEVICE (" | head -1 | grep -oE '[0-9A-F-]{36}') || true
[ -z "${UDID:-}" ] && { echo "ERROR: simulator '$DEVICE' not found. xcrun simctl list devices"; exit 1; }
xcrun simctl bootstatus "$UDID" -b >/dev/null
open -a Simulator --args -CurrentDeviceUDID "$UDID" 2>/dev/null || true

# Clean status bar: Apple-style 9:41, full battery & signal.
xcrun simctl status_bar "$UDID" override \
  --time "9:41" --batteryState charged --batteryLevel 100 \
  --cellularBars 4 --wifiBars 3 --dataNetwork wifi

IFS=',' read -ra LOCS <<< "$LOCALES"
for LOC in "${LOCS[@]}"; do
  REGION=$( [ "$LOC" = "he" ] && echo "he_IL" || echo "${LOC/-/_}" )
  DEST="$OUT/$APPNAME/$LOC/raw"
  mkdir -p "$DEST"
  RESULT="$DEST/run.xcresult"; rm -rf "$RESULT"
  echo "=== Locale $LOC (region $REGION) on $DEVICE ==="

  # --- start video recording (background) -----------------------------------
  VIDEO_PID=""
  if [ "$MODE" != "screenshots" ]; then
    xcrun simctl io "$UDID" recordVideo --codec h264 --force "$DEST/preview_raw.mp4" &
    VIDEO_PID=$!
    sleep 1
  fi

  # --- run the demo flow ------------------------------------------------------
  set +e
  xcodebuild test "${CONTAINER[@]}" -scheme "$SCHEME" \
    -destination "platform=iOS Simulator,id=$UDID" \
    -only-testing:"$TEST" \
    -testLanguage "${LOC%%-*}" -testRegion "$REGION" \
    -resultBundlePath "$RESULT" | grep -E "Test (Case|Suite)|error|passed|failed" || true
  TEST_STATUS=$?
  set -e

  # --- stop recording ---------------------------------------------------------
  if [ -n "$VIDEO_PID" ]; then
    kill -INT "$VIDEO_PID" 2>/dev/null || true
    wait "$VIDEO_PID" 2>/dev/null || true
    echo "Video: $DEST/preview_raw.mp4"
  fi

  # --- extract screenshot attachments from the result bundle ------------------
  if [ "$MODE" != "video" ] && [ -d "$RESULT" ]; then
    mkdir -p "$DEST/screenshots"
    if xcrun xcresulttool export attachments --path "$RESULT" --output-path "$DEST/screenshots" 2>/dev/null; then
      echo "Screenshots: $DEST/screenshots/ (see manifest.json for name mapping)"
    else
      echo "NOTE: 'xcresulttool export attachments' unavailable (needs Xcode 16+)."
      echo "      Fallback: use fastlane snapshot for stills, or open $RESULT in Xcode and export attachments."
    fi
  fi
  [ "$TEST_STATUS" -ne 0 ] && echo "WARNING: test exited non-zero for $LOC — inspect $RESULT"
done

xcrun simctl status_bar "$UDID" clear || true
echo ""
echo "Done. Next: scripts/convert_preview.sh for videos, then scripts/verify_assets.py."
