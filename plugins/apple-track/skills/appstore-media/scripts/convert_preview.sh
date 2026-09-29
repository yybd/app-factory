#!/bin/bash
# convert_preview.sh — convert a raw recording into an App Store-compliant App Preview.
# Scales to the exact accepted resolution, 30fps, H.264 High@4.0 ~11Mbps,
# and guarantees a conformant stereo AAC audio track (silent if none).
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: convert_preview.sh -p <profile> <input> [output]

Profiles (Apple "accepted resolutions"):
  iphone            886x1920  (portrait)
  iphone-landscape  1920x886
  ipad              1200x1600 (portrait)
  ipad-landscape    1600x1200
  mac               1920x1080 (landscape only)

Examples:
  convert_preview.sh -p iphone AppStoreMedia/MyApp/he/raw/preview_raw.mp4
  convert_preview.sh -p mac capture_raw.mov MyApp_preview_he.mp4

The output is padded (letterboxed with the clip's own blurred edges avoided — plain
scale+pad) if the aspect ratio differs slightly; large mismatches mean you captured
the wrong device/window shape — fix the capture instead.
EOF
  exit 1
}

PROFILE=""
while getopts "p:h" opt; do case $opt in p) PROFILE="$OPTARG";; *) usage;; esac; done
shift $((OPTIND-1))
IN="${1:-}"; [ -z "$IN" ] && usage
[ -f "$IN" ] || { echo "ERROR: no such file: $IN"; exit 1; }

command -v ffmpeg >/dev/null || { echo "ERROR: ffmpeg required — brew install ffmpeg"; exit 1; }
command -v ffprobe >/dev/null || { echo "ERROR: ffprobe required — brew install ffmpeg"; exit 1; }

case "$PROFILE" in
  iphone)            TW=886;  TH=1920;;
  iphone-landscape)  TW=1920; TH=886;;
  ipad)              TW=1200; TH=1600;;
  ipad-landscape)    TW=1600; TH=1200;;
  mac)               TW=1920; TH=1080;;
  *) echo "ERROR: unknown profile '$PROFILE'"; usage;;
esac

OUTFILE="${2:-${IN%.*}_appstore_${PROFILE}.mp4}"

# --- duration check (15-30s required) -----------------------------------------
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
DUR_INT=${DUR%.*}
TRIM=()
if [ "$DUR_INT" -gt 30 ]; then
  echo "WARNING: input is ${DUR_INT}s; Apple requires 15-30s."
  echo "         Auto-trimming to the FIRST 30s. For a proper edit, cut in iMovie first"
  echo "         (per imovie-plan.md) and re-run this script on the export."
  TRIM=(-t 30)
elif [ "$DUR_INT" -lt 15 ]; then
  echo "ERROR: input is ${DUR_INT}s — below Apple's 15s minimum. Re-record a longer flow."
  exit 1
fi

HAS_AUDIO=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$IN" | head -1)

VF="scale=${TW}:${TH}:force_original_aspect_ratio=decrease,pad=${TW}:${TH}:(ow-iw)/2:(oh-ih)/2:black,fps=30,format=yuv420p"

if [ -n "$HAS_AUDIO" ]; then
  ffmpeg -y -i "$IN" ${TRIM[@]+"${TRIM[@]}"} -vf "$VF" \
    -c:v libx264 -profile:v high -level 4.0 -b:v 11M -maxrate 12M -bufsize 24M \
    -c:a aac -b:a 256k -ar 44100 -ac 2 \
    -movflags +faststart "$OUTFILE"
else
  # Inject a silent stereo AAC track — App Store Connect validates the audio stream.
  ffmpeg -y -i "$IN" -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
    ${TRIM[@]+"${TRIM[@]}"} -vf "$VF" \
    -c:v libx264 -profile:v high -level 4.0 -b:v 11M -maxrate 12M -bufsize 24M \
    -c:a aac -b:a 256k -ar 44100 -ac 2 -shortest \
    -map 0:v:0 -map 1:a:0 \
    -movflags +faststart "$OUTFILE"
fi

echo ""
echo "Output: $OUTFILE (${TW}x${TH}, 30fps, H.264 High@4.0, AAC stereo)"
echo "Verify before upload: python3 scripts/verify_assets.py \"$OUTFILE\""
