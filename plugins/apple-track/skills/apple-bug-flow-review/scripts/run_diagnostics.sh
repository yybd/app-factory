#!/usr/bin/env bash
#
# run_diagnostics.sh — collect build-time bug signals for an Apple app.
#
# Wraps the three cheap, no-test build-time passes from
# references/runtime-diagnostics.md:
#   1. compiler warnings
#   2. strict-concurrency pass (temporary lens for data races)
#   3. Clang/Swift static analyzer
#
# It does NOT run sanitizers/Main Thread Checker/Instruments — those need a test
# target or a hands-on run (Phase 3/4). Read the reference before relying on
# this; map every reported issue to a bug-catalog category and confirm it.
#
# Usage:
#   run_diagnostics.sh -s <scheme> [-d <destination>] [-p <project.xcodeproj> | -w <workspace.xcworkspace>] [-o <outdir>]
#
# Examples:
#   run_diagnostics.sh -s MyApp -d 'platform=iOS Simulator,name=iPhone 15'
#   run_diagnostics.sh -s MyApp -d 'platform=macOS' -w MyApp.xcworkspace
#
# Tips:
#   xcodebuild -list                              # find scheme names
#   xcrun simctl list devices available           # find an iOS destination

set -uo pipefail

SCHEME=""
DEST=""
PROJECT_FLAG=()
OUTDIR=""

while getopts "s:d:p:w:o:h" opt; do
  case "$opt" in
    s) SCHEME="$OPTARG" ;;
    d) DEST="$OPTARG" ;;
    p) PROJECT_FLAG=(-project "$OPTARG") ;;
    w) PROJECT_FLAG=(-workspace "$OPTARG") ;;
    o) OUTDIR="$OPTARG" ;;
    h) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option"; exit 2 ;;
  esac
done

if [[ -z "$SCHEME" ]]; then
  echo "error: -s <scheme> is required. Run 'xcodebuild -list' to find it." >&2
  exit 2
fi

if [[ -z "$DEST" ]]; then
  DEST="platform=iOS Simulator,name=iPhone 15"
  echo "note: no -d destination given; defaulting to: $DEST" >&2
fi

OUTDIR="${OUTDIR:-$(mktemp -d -t bugflow)}"
mkdir -p "$OUTDIR"
echo "→ output dir: $OUTDIR"

COMMON=("${PROJECT_FLAG[@]}" -scheme "$SCHEME" -destination "$DEST")

# 1. Compiler warnings -------------------------------------------------------
echo "→ [1/3] building + collecting compiler warnings…"
xcodebuild build "${COMMON[@]}" -quiet > "$OUTDIR/build.log" 2>&1
grep -nE 'warning:|error:' "$OUTDIR/build.log" > "$OUTDIR/warnings.txt" || true
echo "   $(wc -l < "$OUTDIR/warnings.txt" | tr -d ' ') warning/error lines → $OUTDIR/warnings.txt"

# 2. Strict-concurrency lens (data races at compile time) --------------------
echo "→ [2/3] strict-concurrency pass (temporary lens; not a code change)…"
xcodebuild build "${COMMON[@]}" \
  SWIFT_STRICT_CONCURRENCY=complete \
  OTHER_SWIFT_FLAGS='-Xfrontend -warn-concurrency' \
  -quiet > "$OUTDIR/concurrency.log" 2>&1
grep -niE 'concurrency|sendable|actor|main actor|data race' "$OUTDIR/concurrency.log" \
  > "$OUTDIR/concurrency_warnings.txt" || true
echo "   $(wc -l < "$OUTDIR/concurrency_warnings.txt" | tr -d ' ') concurrency lines → $OUTDIR/concurrency_warnings.txt"

# 3. Static analyzer ---------------------------------------------------------
echo "→ [3/3] Clang/Swift static analyzer…"
xcodebuild analyze "${COMMON[@]}" -quiet > "$OUTDIR/analyze.log" 2>&1
grep -niE 'warning:|note:' "$OUTDIR/analyze.log" > "$OUTDIR/analyzer.txt" || true
echo "   $(wc -l < "$OUTDIR/analyzer.txt" | tr -d ' ') analyzer lines → $OUTDIR/analyzer.txt"

echo ""
echo "================ SUMMARY ================"
echo "warnings:            $(wc -l < "$OUTDIR/warnings.txt" | tr -d ' ')"
echo "concurrency signals: $(wc -l < "$OUTDIR/concurrency_warnings.txt" | tr -d ' ')"
echo "analyzer signals:    $(wc -l < "$OUTDIR/analyzer.txt" | tr -d ' ')"
echo "full logs + filtered lists in: $OUTDIR"
echo "Next (dynamic): run the XCUITest smoke flows under TSan/ASan + Main Thread"
echo "Checker, and watch the console for SwiftUI runtime warnings (see"
echo "references/runtime-diagnostics.md §4–§6)."
