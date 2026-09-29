#!/bin/bash
# capture_selfrender.sh — TEMPLATE for the permission-free macOS capture flow.
# Copy into <slug>/media/apple/capture.sh and fill the CONFIG block + SCENES.
# See references/macos-capture.md for the matching app-side hooks and gotchas.
#
# STILLS need NO system permission: in -CaptureAll the app renders its OWN window to a
# 2× PNG per scene into its sandbox tmp; this script flattens to RGB and lays them out.
# VIDEO needs Screen Recording (records the live self-driving window).
#
# Usage:  ./capture.sh            # the still screenshots (no permissions)
#         ./capture.sh video      # the App Preview video (needs Screen Recording)
#         ./capture.sh video-ai   # staged long recording for an interactive feature
#         REBUILD=1 ./capture.sh  # force a fresh build first
set -euo pipefail

# ---- CONFIG (edit these) -----------------------------------------------------
APP="__APP_DISPLAY_NAME__"                 # the built product / menu-bar name
BUNDLE_ID="__BUNDLE_ID__"                   # e.g. com.acme.myapp
SCHEME="__SCHEME__"                         # xcodebuild scheme
# Both are absolute paths on YOUR machine — the template cannot know either, so they
# are placeholders like the names above. The hub one has a sensible default when
# $APP_HUB is set: the deploy writes it, and it is where the media belongs.
PROJ="__PROJECT_DIR__"                      # absolute path to the .xcodeproj's directory
ROOT="${APP_HUB:?set $APP_HUB, or replace this with an absolute path}/__SLUG__/media/apple"
LOCALE="en-US"
NAMES="01_hero 02_feature 03_style 04_paywall 05_extra"   # output names; order = store order
# ------------------------------------------------------------------------------

# ---- locating this skill's helper scripts ------------------------------------
# This file is a TEMPLATE, so the copy that actually runs sits in the hub beside the
# app's media — and neither $0 nor $ROOT points anywhere near convert_preview.sh and
# winframe.swift, which stay behind in the skill. $CLAUDE_PLUGIN_ROOT would name the
# skill but is set only when Claude Code invokes it, never when a person runs the copy.
# So search: beside the copy first (so a self-contained bundle keeps working), then the
# plugin root, then the cache — sha-globbed, since the sha moves with every update —
# then the working copy.
skill_script() {
  local name="$1" here c
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  for c in "$here/$name" \
           "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/skills/appstore-media/scripts/$name" \
           "$HOME"/.claude/plugins/cache/*/apple-track/*/skills/appstore-media/scripts/"$name" \
           "${APP_FACTORY:-/nonexistent}/plugins/apple-track/skills/appstore-media/scripts/$name"; do
    [[ -f "$c" ]] && { printf '%s\n' "$c"; return 0; }
  done
  echo "ERROR: cannot find $name (appstore-media skill)." >&2
  echo "  Looked beside this script, under \$CLAUDE_PLUGIN_ROOT, in the plugin cache," >&2
  echo "  and in \$APP_FACTORY. Refresh with: python3 factory/deploy.py" >&2
  return 1
}

DD="/tmp/${SCHEME}-dd"; APP_PATH="$DD/Build/Products/Debug/$APP.app"
SHOTS="$ROOT/$APP/$LOCALE/screenshots"; mkdir -p "$SHOTS"
RAW="$ROOT/$APP/$LOCALE/raw"; mkdir -p "$RAW"
CONTAINER="$HOME/Library/Containers/$BUNDLE_ID/Data/tmp"

if [ "${REBUILD:-}" = "1" ] || [ ! -d "$APP_PATH" ]; then
  echo "Building ${APP}..."
  ( cd "$PROJ" && xcodebuild -scheme "$SCHEME" -configuration Debug \
      -derivedDataPath "$DD" -destination 'platform=macOS' build >/dev/null )
fi
# Copy bundled demo art into the built app (sandbox can't read external paths).
cp "$ROOT"/demo-source*.png "$APP_PATH/Contents/Resources/" 2>/dev/null || true

flatten() { ffmpeg -y -loglevel error -i "$1" \
  -vf "scale=$3:$4:force_original_aspect_ratio=decrease,pad=$3:$4:(ow-iw)/2:(oh-ih)/2:white,format=rgb24" "$2"; }
kill_app() { pkill -x "$APP" 2>/dev/null || true; for _ in $(seq 1 24); do pgrep -x "$APP" >/dev/null || break; sleep 0.25; done; }
last_name() { echo "$NAMES" | awk '{print $NF}'; }

# All still scenes from ONE launch (the app cycles scenes and self-renders each).
stills() {
  local LAST; LAST="$(last_name)"
  for try in 1 2 3; do
    for n in $NAMES; do rm -f "$CONTAINER/$n.png"; done
    kill_app; sleep 0.6
    open -n "$APP_PATH" --args -DemoMode -CaptureMode -CaptureAll
    for _ in $(seq 1 50); do [ -f "$CONTAINER/$LAST.png" ] && break; sleep 0.4; done
    [ -f "$CONTAINER/$LAST.png" ] && break
    echo "  (retry $try: sequence did not finish)"
  done
  local ok=1
  for n in $NAMES; do
    if [ -f "$CONTAINER/$n.png" ]; then flatten "$CONTAINER/$n.png" "$SHOTS/$n.png" 2880 1800
      echo "screenshot: $SHOTS/$n.png"
    else echo "MISSING: $n"; ok=0; fi
  done
  kill_app; [ "$ok" = 1 ] || return 1
}

# winframe.swift prints "<id> <x> <y> <w> <h>" for the app's main window (keyed by PID).
frame() {
  local wf; wf="$(skill_script winframe.swift)" || return 1
  swift "$wf" "$(pgrep -x "$APP" | head -1)" 2>/dev/null || true
}

video() {  # needs Screen Recording
  if ! screencapture -x -t png /tmp/_probe.png 2>/dev/null; then
    echo "Screen Recording not granted to this terminal. Grant it (System Settings >"
    echo "Privacy & Security > Screen Recording), restart the terminal, then re-run."; return 3
  fi
  rm -f /tmp/_probe.png
  local FRAME="" ID X Y W H
  for try in 1 2 3; do
    kill_app; open -n "$APP_PATH" --args -DemoMode -DemoScene video -CaptureMode; sleep 2
    FRAME="$(frame)"; [ -n "$FRAME" ] && break; echo "  (retry $try: window not found)"
  done
  [ -n "$FRAME" ] || { echo "ERROR: window never appeared — try REBUILD=1"; kill_app; return 1; }
  read -r ID X Y W H <<< "$FRAME"
  rm -f "$RAW/preview_raw.mov"
  echo "recording ~21s while the app self-drives..."
  screencapture -v -V 21 -R "$X,$Y,$W,$H" "$RAW/preview_raw.mov" || true
  kill_app
  [ -f "$RAW/preview_raw.mov" ] || { echo "no recording produced"; return 1; }
  local APREV="$ROOT/$APP/$LOCALE/app-preview"; mkdir -p "$APREV"
  local conv; conv="$(skill_script convert_preview.sh)" || return 1
  "$conv" -p mac "$RAW/preview_raw.mov" "$APREV/${APP}_preview.mp4"
}

video_ai() {  # stage the app; record long while the user does the real interactive flow
  if ! screencapture -x -t png /tmp/_probe.png 2>/dev/null; then
    echo "Screen Recording not granted — grant it and retry."; return 3; fi
  rm -f /tmp/_probe.png
  local FRAME="" ID X Y W H
  for try in 1 2 3; do
    kill_app; open -n "$APP_PATH" --args -DemoMode -DemoScene ai -CaptureMode -VideoSize; sleep 2
    FRAME="$(frame)"; [ -n "$FRAME" ] && break; echo "  (retry $try: window not found)"
  done
  [ -n "$FRAME" ] || { echo "ERROR: window never appeared"; kill_app; return 1; }
  read -r ID X Y W H <<< "$FRAME"
  rm -f "$RAW/preview_ai_raw.mov"
  echo "Recording ~50s. Do the real interactive flow on the app window NOW (close other apps first)."
  screencapture -v -V 50 -R "$X,$Y,$W,$H" "$RAW/preview_ai_raw.mov" || true
  kill_app
  echo "Raw clip: $RAW/preview_ai_raw.mov — cut the relevant ~6-8s, BLUR any face/name, then convert+verify."
}

case "${1:-stills}" in
  stills)   stills;;
  video)    video;;
  video-ai) video_ai;;
  all)      stills; video;;
  *) echo "usage: ./capture.sh [stills|video|video-ai|all]"; exit 1;;
esac
echo "Done."
