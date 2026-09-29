#!/usr/bin/env bash
# read_app_identity.sh — surface the app's CURRENT name across every surface so the
# skill can show "current → proposed" before changing anything. Read-only.
#
# Usage: read_app_identity.sh [PROJECT_DIR]
#   PROJECT_DIR defaults to the current directory. The script looks for the first
#   *.xcodeproj it can find and reports the on-device naming build settings, the
#   bundle id, the target name, any Info.plist display names, the localized
#   InfoPlist.strings overrides, and the source-of-truth README identity block.
#
# It prefers a literal scan of project.pbxproj / Info.plist (fast, no build) over
# `xcodebuild -showBuildSettings` (slow, needs a scheme). For the authoritative
# resolved value, run the xcodebuild line printed at the end.

set -euo pipefail
root="${1:-.}"

say() { printf '%s\n' "$*"; }
hr()  { printf '%s\n' "------------------------------------------------------------"; }

pbxproj="$(find "$root" -maxdepth 3 -name project.pbxproj -not -path '*/.build/*' 2>/dev/null | head -1)"
if [[ -z "$pbxproj" ]]; then
  say "No .xcodeproj found under: $root"
  say "Pass the project directory explicitly, e.g.: read_app_identity.sh \$DEV_ROOT/MyApp"
  exit 0
fi
projdir="$(cd "$(dirname "$pbxproj")/.." && pwd)"
say "Project: $(dirname "$pbxproj")"
hr

# --- Build settings that decide the on-device name (literal, per-config) ---
say "ON-DEVICE NAME — build settings (from project.pbxproj):"
for key in PRODUCT_NAME INFOPLIST_KEY_CFBundleDisplayName INFOPLIST_KEY_CFBundleName PRODUCT_BUNDLE_IDENTIFIER PRODUCT_MODULE_NAME GENERATE_INFOPLIST_FILE; do
  vals="$(grep -oE "${key} = [^;]+;" "$pbxproj" 2>/dev/null | sed -E "s/${key} = //; s/;\$//" | sort -u || true)"
  if [[ -n "$vals" ]]; then
    while IFS= read -r v; do say "  ${key} = ${v}"; done <<< "$vals"
  else
    say "  ${key} = (not set — inherits default)"
  fi
done
hr

# --- Target names (often the same as PRODUCT_NAME's default) ---
# pbxproj puts `isa = PBXNativeTarget` on the line after `ID /* Name */ = {`, so
# slurp the whole file (perl -0777) and match across the newline.
say "TARGETS:"
targets="$(perl -0777 -ne 'while(/\/\* ([^*]+) \*\/ = \{\s*isa = PBXNativeTarget\b/g){print "$1\n"}' "$pbxproj" 2>/dev/null | sort -u || true)"
if [[ -n "$targets" ]]; then
  while IFS= read -r t; do [[ -n "$t" ]] && say "  $t"; done <<< "$targets"
else
  say "  (could not parse)"
fi
hr

# --- Info.plist display names (when a hand-maintained Info.plist exists) ---
say "Info.plist display names (hand-maintained plists):"
found_plist=0
while IFS= read -r plist; do
  [[ "$plist" == *"/.build/"* ]] && continue
  dn="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleDisplayName' "$plist" 2>/dev/null || true)"
  bn="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleName' "$plist" 2>/dev/null || true)"
  if [[ -n "$dn" || -n "$bn" ]]; then
    found_plist=1
    say "  $plist"
    [[ -n "$dn" ]] && say "    CFBundleDisplayName = $dn"
    [[ -n "$bn" ]] && say "    CFBundleName        = $bn"
  fi
done < <(find "$projdir" -maxdepth 4 -name 'Info.plist' 2>/dev/null)
[[ "$found_plist" == 0 ]] && say "  (none — names come from build settings / generated Info.plist)"
hr

# --- Localized display name overrides ---
say "Localized display names (InfoPlist.strings per .lproj):"
found_loc=0
while IFS= read -r f; do
  line="$(grep -E 'CFBundleDisplayName' "$f" 2>/dev/null | head -1 || true)"
  if [[ -n "$line" ]]; then
    found_loc=1
    locale="$(basename "$(dirname "$f")")"
    say "  ${locale}: ${line}"
  fi
done < <(find "$projdir" -maxdepth 4 -name 'InfoPlist.strings' 2>/dev/null)
[[ "$found_loc" == 0 ]] && say "  (none — single name for all locales)"
hr

# --- Source-of-truth README identity block ---
readme="$(find "$projdir" -maxdepth 2 -iname 'README.md' -not -path '*/.build/*' 2>/dev/null | head -1)"
say "README source-of-truth identity block:"
if [[ -n "$readme" ]]; then
  say "  $readme"
  grep -iE '^\s*-?\s*\**\s*(App name|App Store name|Subtitle|Bundle id)\b' "$readme" 2>/dev/null | sed 's/^/    /' || say "    (no identity block found — skill should add one)"
else
  say "  (no README.md — skill should create one as the source of truth)"
fi
hr

# --- App version (baseline for the "did the version change?" question) ---
say "VERSION — baseline for Step 5 (the skill must still ASK the developer; a bump"
say "is not necessarily new features, nor new features necessarily a bump):"
mver="$(grep -oE 'MARKETING_VERSION = [^;]+;' "$pbxproj" 2>/dev/null | sed -E 's/MARKETING_VERSION = //; s/;$//' | sort -u || true)"
if [[ -n "$mver" ]]; then
  while IFS= read -r v; do say "  MARKETING_VERSION = $v"; done <<< "$mver"
else
  say "  MARKETING_VERSION = (not set in pbxproj — check Info.plist CFBundleShortVersionString)"
fi
if [[ -n "${readme:-}" ]]; then
  vlabel="$(grep -iE '^\s*(\*\*)?Version\b|^##+\s*Version history' "$readme" 2>/dev/null | head -3 || true)"
  if [[ -n "$vlabel" ]]; then
    say "  README version label / history:"
    while IFS= read -r l; do [[ -n "$l" ]] && say "    $l"; done <<< "$vlabel"
  else
    say "  README version label: (none yet — add one above the feature list on a version change)"
  fi
fi
hr

# --- Authoritative resolved values (optional, slower) ---
say "For the AUTHORITATIVE resolved name (needs a scheme, slower), run:"
say "  xcodebuild -showBuildSettings -project \"$(dirname "$pbxproj")\" 2>/dev/null \\"
say "    | grep -E ' (PRODUCT_NAME|PRODUCT_BUNDLE_IDENTIFIER|INFOPLIST_KEY_CFBundleDisplayName|FULL_PRODUCT_NAME) ='"
