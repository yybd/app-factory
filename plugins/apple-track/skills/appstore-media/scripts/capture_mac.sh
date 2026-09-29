#!/bin/bash
# capture_mac.sh — capture screenshots/video of a single Mac app window.
# Part of the appstore-media skill. Needs Screen Recording permission for Terminal
# (System Settings > Privacy & Security > Screen Recording) — otherwise output is blank.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: capture_mac.sh -a <AppName> [options]

Options:
  -a APP         App name as it appears in the menu bar (required)
  -m MODE        screenshot | video | both (default: both)
  -W WIDTH       Window width to set (default: 1440)
  -H HEIGHT      Window height to set (default: 900)   # 16:10 for screenshots; use 1600x900 (16:9) when capturing App Preview footage
  -o DIR         Output root (default: ./AppStoreMedia)
  -l LOCALE      Locale label for the output folder (default: current). NOTE: relaunch
                 the app with the right language first, e.g.:
                 open -a "MyApp" --args -AppleLanguages "(he)"
  -s SECONDS     Max video length before auto-stop (default: 40)
  -n NAME        Base filename (default: capture)

Typical flow per locale:
  open -a "MyApp" --args -AppleLanguages "(he)" -DemoMode -CaptureMode
  capture_mac.sh -a MyApp -l he -m both        # run while the XCUITest flow drives the app
EOF
  exit 1
}

APP=""; MODE="both"; W=1440; H=900; OUT="./AppStoreMedia"; LOCALE="current"; SECS=40; NAME="capture"
while getopts "a:m:W:H:o:l:s:n:h" opt; do
  case $opt in
    a) APP="$OPTARG";; m) MODE="$OPTARG";; W) W="$OPTARG";; H) H="$OPTARG";;
    o) OUT="$OPTARG";; l) LOCALE="$OPTARG";; s) SECS="$OPTARG";; n) NAME="$OPTARG";;
    *) usage;;
  esac
done
[ -z "$APP" ] && usage
DEST="$OUT/$APP/$LOCALE/raw"; mkdir -p "$DEST"

# --- bring app forward and normalize the window -------------------------------
osascript <<EOF
tell application "$APP" to activate
delay 0.5
tell application "System Events" to tell process "$APP"
  set position of front window to {120, 80}
  set size of front window to {$W, $H}
end tell
EOF
sleep 0.5

# --- read the actual window bounds --------------------------------------------
read -r X Y WW HH <<< "$(osascript -e "
tell application \"System Events\" to tell process \"$APP\"
  set p to position of front window
  set s to size of front window
  return (item 1 of p as text) & \" \" & (item 2 of p as text) & \" \" & (item 1 of s as text) & \" \" & (item 2 of s as text)
end tell")"
REGION="$X,$Y,$WW,$HH"
echo "Window region: $REGION"

if [ "$MODE" != "video" ]; then
  # -o = no window shadow (we capture a region anyway). Retina displays double the pixels — good.
  screencapture -x -R"$REGION" "$DEST/${NAME}.png"
  read -r PW PH <<< "$(sips -g pixelWidth -g pixelHeight "$DEST/${NAME}.png" | awk '/pixel/ {printf "%s ", $2}')"
  echo "Screenshot: $DEST/${NAME}.png (${PW}x${PH})"
  # The window grab includes the title bar, so it is almost never an accepted Mac
  # size (e.g. 1440x952@2x = 2880x1904). Compose an upload-ready copy at 2880x1800
  # (scale-to-fit + white pad, flattened to RGB — App Store Connect rejects alpha).
  if [ "$PW" = "2880" ] && [ "$PH" = "1800" ]; then
    : # already an accepted Mac size
  elif command -v ffmpeg >/dev/null; then
    COMPOSED="$DEST/${NAME}-2880x1800.png"
    ffmpeg -y -loglevel error -i "$DEST/${NAME}.png" \
      -vf "scale=2880:1800:force_original_aspect_ratio=decrease,pad=2880:1800:(ow-iw)/2:(oh-ih)/2:white,format=rgb24" \
      "$COMPOSED" && echo "Upload-ready: $COMPOSED (2880x1800, RGB, no alpha)"
  else
    echo "NOTE: ${PW}x${PH} is not an accepted Mac size and ffmpeg is missing — compose to 2880x1800 (no alpha) before upload (see references/apple-specs.md)."
  fi
fi

if [ "$MODE" != "screenshot" ]; then
  echo "Recording video for up to ${SECS}s — run the demo flow NOW. Ctrl+C the flow's terminal won't stop this; it auto-stops."
  rm -f "$DEST/${NAME}_raw.mov"   # screencapture -v won't overwrite an existing movie (silent skip → stale take)
  screencapture -v -V "$SECS" -R"$REGION" "$DEST/${NAME}_raw.mov" || true
  if [ -f "$DEST/${NAME}_raw.mov" ]; then
    echo "Video: $DEST/${NAME}_raw.mov"
    echo "Next: scripts/convert_preview.sh -p mac \"$DEST/${NAME}_raw.mov\""
  else
    echo "ERROR: no recording produced — grant Screen Recording permission to this terminal and retry."
  fi
fi
