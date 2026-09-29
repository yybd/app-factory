#!/usr/bin/env bash
# sync_from_hub.sh — pull an app's App Store metadata, screenshots and App Preview
# videos from the hub (the source of truth) down into the app repo's fastlane/ tree,
# right before `deliver`, and VERIFY the result is complete.
#
# Screenshots/videos are read from the CANONICAL media tree owned by appstore-media
# (<slug>/media/apple/<App>/<locale>/{screenshots,app-preview}/) and flattened into
# fastlane/screenshots/<locale>/ — the layout `deliver` requires.
#
# The hub holds the canonical, per-locale, fastlane-format metadata and the
# release notes (by version). fastlane never authors metadata; it only uploads
# what this script mirrors in. Run it every time you deliver.
#
# After syncing, it verifies that every required field is present and non-empty
# for every locale. If anything is missing, it reports exactly what, points you
# at the skill that fills the hub (store-metadata-writer), and EXITS NON-ZERO so
# the caller does not upload incomplete data.
#
# Usage:
#   sync_from_hub.sh <slug> <version> <app-repo> [--hub DIR] [--locales a,b,c]
#                    [--platform ios|osx]
#
#   <slug>      the app's hub folder name  ($APP_HUB/<slug>/)
#   <version>   marketing version being shipped (selects the release notes)
#   <app-repo>  the app's native project root (contains, or will get, fastlane/)
#   --hub DIR   override the hub root (default: $APP_HUB, else $DEV_ROOT/app-hub)
#   --locales   assert this exact locale set is present (else verify whatever the
#               hub has). Comma-separated, e.g. en-US,he,de-DE
#   --platform  resolve PER-PLATFORM field overrides for a universal app (one app
#               record, both iOS + macOS). A field whose value should differ by
#               platform is authored in the hub as `<field>.<platform>.txt`
#               alongside the shared `<field>.txt` — e.g.
#               `promotional_text.ios.txt` (an iOS-only promo) next to the
#               canonical `promotional_text.txt` (Mac/shared). With
#               `--platform ios`, each `<field>.ios.txt` is overlaid on top of
#               `<field>.txt` in the synced tree; the `.osx.txt` files are
#               ignored (and vice versa). WITHOUT `--platform`, all
#               `*.ios.txt`/`*.osx.txt` overrides are EXCLUDED so the synced tree
#               is the clean canonical set. Run sync once per platform, then run
#               that platform's `deliver`, before syncing the next.
#
#   --discard-repo-extras  delete listing text that exists in the repo's fastlane/
#               and nowhere in the hub. The sync stops on it by default: this
#               directory has ONE writer (this script), so anything else found in
#               it was authored by a tool that should have written to the hub, and
#               --delete would destroy it without a word. Back-port it first.
#   --skip-copy-check  ship anyway when the copy gate reports a difference between
#               the English and a translation that is DELIBERATE. The gate compares
#               every locale against the English claim by claim (copy-edit's
#               measure_copy.py) and blocks on a translation that is missing,
#               untranslated, or carries a different number of claims.
#
# The hub is READ-only here; only <app-repo>/fastlane/ is written. The repo copy
# is disposable (git-ignore it) — the hub is the truth.

set -euo pipefail

slug="${1:-}"; version="${2:-}"; app_repo="${3:-}"
# The hub's location is $APP_HUB, written into the environment by the deploy from
# grove's registry; $DEV_ROOT/app-hub is the layout the install instructions produce.
# A hardcoded home-directory path is neither, and was the default here — correct on
# the machine it was written on, silently wrong on every other, and invisible to
# test_portability, which used to scan only .md and .json.
hub="${APP_HUB:-${DEV_ROOT:+$DEV_ROOT/app-hub}}"; locales_csv=""; shot_fallback=""; platform=""; skip_copy_check=0; discard_repo_extras=0; standalone=0
shift $(( $# < 3 ? $# : 3 )) || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --hub) hub="$2"; shift 2 ;;
    --locales) locales_csv="$2"; shift 2 ;;
    --screenshot-fallback) shot_fallback="$2"; shift 2 ;;   # reuse this locale's media for locales lacking their own
    --platform) platform="$2"; shift 2 ;;                   # ios|osx — apply that platform's <field>.<platform>.txt overrides
    --standalone) standalone=1; shift ;;                    # no hub: the repo's fastlane/ IS the source of truth
    --skip-copy-check) skip_copy_check=1; shift ;;          # ship a translation that deliberately differs from the English
    --discard-repo-extras) discard_repo_extras=1; shift ;;  # delete repo-only listing text instead of back-porting it
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$slug" || -z "$version" || -z "$app_repo" ]]; then
  echo "usage: sync_from_hub.sh <slug> <version> <app-repo> [--hub DIR] [--locales a,b,c] [--screenshot-fallback LOC] [--platform ios|osx] [--skip-copy-check] [--discard-repo-extras]" >&2
  exit 2
fi
if [[ -n "$platform" && "$platform" != "ios" && "$platform" != "osx" ]]; then
  echo "✗ --platform must be 'ios' or 'osx' (got '$platform')" >&2
  exit 2
fi

# $APP_HUB may be unset on a machine that has not been deployed, and --hub may not have
# been passed. Saying so here beats the alternative: an empty $hub makes every path below
# absolute from the filesystem root, so the failure arrives as "no metadata at
# /<slug>/store/..." — a message about the wrong thing entirely.
# ── two modes, and no hub is the second one, not a failure ───────────────────────
# A studio keeps its listing text in a hub and this script mirrors it into the repo.
# Someone with one app has no hub, authors in `fastlane/` directly, and for them there
# is nothing to sync FROM — the repo already holds the truth. Both SKILL.md files
# promised that mode; no script implemented it, so the promise failed at the first
# command. It is detected rather than declared: `--standalone` forces it, and an
# unreachable hub selects it on its own.
if [[ "$standalone" != "1" ]] && { [[ -z "$hub" ]] || [[ ! -d "$hub" ]]; }; then
  standalone=1
  echo "· no hub ($([[ -z "$hub" ]] && echo 'none configured' || echo "$hub is not there")) —"
  echo "  standalone mode: $app_repo/fastlane is the source of truth, and nothing is copied."
  echo "  To use a hub instead: set \$APP_HUB, or pass --hub DIR."
fi

# the override suffix we KEEP+overlay; the other platform's overrides are dropped
other_platform=""; [[ "$platform" == "ios" ]] && other_platform="osx"
[[ "$platform" == "osx" ]] && other_platform="ios"

src="$hub/$slug/store/apple"
dst="$app_repo/fastlane"
required="name subtitle description keywords"   # Apple per-locale required fields

# ── the sibling send-surface ───────────────────────────────────────────────────
# We are not the only writer under fastlane/. play-store-deliver's sync stages the
# Play listing into fastlane/metadata/android/ — a SUBTREE of ours, because that is
# the path `supply` reads by default, exactly as fastlane/metadata/ is the path
# `deliver` reads. Both are fed from the same hub and both are disposable.
#
# So this sync owns fastlane/metadata/<locale>/ and fastlane/screenshots/, and it
# must treat that one subtree as none of its business: not deleted by --delete, not
# read as repo-only work by the guard below, not counted as a locale, not fed to the
# copy gate. Shipping one app's 1.4 to both stores in one session found all four.
sibling_dir="android"                    # fastlane/metadata/android — play-store-deliver
sibling_skill="play-store-deliver"

if [[ "$standalone" == "1" ]]; then
  # Nothing to mirror. Everything below this point copies the hub into the repo, so it
  # is skipped whole — and the VERIFY step at the end still runs, against the repo. That
  # is the half that matters either way: it is what refuses an upload with a missing
  # locale, an over-limit field or a release note for the wrong version.
  if [[ ! -d "$dst/metadata" ]]; then
    echo "✗ nothing to deliver — no $dst/metadata, and no hub to build it from." >&2
    echo "  Author the listing first: the app-store-metadata skill scaffolds and fills it." >&2
    exit 1
  fi
  echo "· standalone: verifying $dst/metadata as authored (no copy)"
  # The verification below is shared, and it reads what the hub branch would have
  # computed. Standalone derives the same facts from the repo instead: the locales are
  # whatever folders are actually there, and the per-platform overlay and the media
  # staging did not happen, so their reports say so rather than being left unset —
  # `set -u` would otherwise abort the run at the first report line.
  src="$dst"
  expected=()
  if [[ -n "$locales_csv" ]]; then
    IFS=',' read -ra expected <<< "$locales_csv"
  else
    for d in "$dst/metadata"/*/; do
      [[ -d "$d" ]] || continue
      b="$(basename "$d")"
      [[ "$b" == "review_information" || "$b" == "$sibling_dir" ]] && continue
      expected+=("$b")
    done
  fi
  shot_warn=()
  n_shots=$(find "$dst/screenshots" -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' \) 2>/dev/null | wc -l | tr -d ' ')
  shots_msg="$n_shots file(s) already in $dst/screenshots/ — authored here, not staged from a hub"
  [[ "$n_shots" == "0" ]] && shot_warn+=("no screenshots in $dst/screenshots/ — deliver would ship none")
  override_msg="not applied (standalone: the repo's files are used as they are)"
else

if [[ ! -d "$src/metadata" ]]; then
  echo "✗ SYNC FAILED — no hub metadata at: $src/metadata" >&2
  echo "  Nothing has been authored for this app yet. Run the skill that fills the hub:" >&2
  echo "     → store-metadata-writer   (writes $slug/store/apple/metadata from the profile)" >&2
  exit 1
fi
mkdir -p "$dst/metadata" "$dst/screenshots"

have_rsync=0; command -v rsync >/dev/null 2>&1 && have_rsync=1

# --- 0b) work that exists only in the repo -----------------------------------
# The rsync below runs with --delete: whatever sits in fastlane/metadata and not
# in the hub is gone, silently. That is right for a derived copy and destructive
# for text a different tool authored there — and a tool that writes into this
# directory instead of the hub is the case the field check cannot see, because
# the hub looks complete while the repo holds the newer words.
#
# A file the hub cannot reproduce at all BLOCKS. A file that exists in both and
# differs only warns: that is the normal state after the hub is updated, and
# blocking on it would stop every sync.
if [[ -d "$dst/metadata" ]]; then
  orphan=(); drift=(); sibling_n=0
  while IFS= read -r -d '' f; do
    rel="${f#$dst/metadata/}"
    locale="${rel%%/*}"
    # The Play sync's staged output — reproducible from the same hub, and about to
    # be regenerated by its own run. Counting it as un-back-ported work is how this
    # guard told someone their listing was about to be lost when it was not.
    if [[ "$locale" == "$sibling_dir" ]]; then sibling_n=$((sibling_n+1)); continue; fi
    cands=()
    if [[ "$(basename "$f")" == "release_notes.txt" && "$locale" != "$rel" ]]; then
      # Notes live in the version archive, under the locale's own name — and
      # only the version being synced counts. Notes for an earlier release do
      # not make this release's notes reproducible, which is exactly the case
      # where the repo holds newer text the hub never received.
      for c in "$src/release-notes/$version/$locale.txt" "$src/release-notes/$version/$locale.ios.txt" "$src/release-notes/$version/$locale.osx.txt"; do
        [[ -e "$c" ]] && cands+=("$c")
      done
    else
      for c in "$src/metadata/$rel" "${src}/metadata/${rel%.txt}.ios.txt" "${src}/metadata/${rel%.txt}.osx.txt"; do
        [[ -e "$c" ]] && cands+=("$c")
      done
    fi
    if [[ ${#cands[@]} -eq 0 ]]; then
      orphan+=("$rel")
    else
      same=0
      for c in "${cands[@]}"; do cmp -s "$c" "$f" && { same=1; break; }; done
      [[ $same -eq 0 ]] && drift+=("$rel")
    fi
  done < <(find "$dst/metadata" -type f -name '*.txt' -print0 2>/dev/null)

  # directories this sync never writes — an older workflow, or another tool
  unmanaged=()
  for d in "$dst"/metadata_*; do
    [[ -d "$d" ]] && unmanaged+=("$(basename "$d")")
  done

  [[ $sibling_n -gt 0 ]] &&
    echo "ℹ fastlane/metadata/$sibling_dir/ — $sibling_n file(s) staged by $sibling_skill from the same hub; not ours, left untouched"

  if [[ ${#orphan[@]} -gt 0 && "$discard_repo_extras" != "1" ]]; then
    echo
    echo "✗ SYNC STOPPED — the repo holds listing text the hub cannot reproduce:"
    printf '   - fastlane/metadata/%s\n' "${orphan[@]}"
    [[ $sibling_n -gt 0 ]] &&
      echo "   (fastlane/metadata/$sibling_dir/ is NOT in this list — that is $sibling_skill's" &&
      echo "    staged output, and this sync leaves it alone.)"
    echo
    echo "This sync would delete it. It is not a stale copy — it is work that was"
    echo "never back-ported. Put it in the hub first:"
    echo "   → store-metadata-writer   (fields + release notes, into $slug/store/apple/)"
    echo "   → appstore-media          (captures, into $slug/media/apple/)"
    echo "Then re-sync. To delete it anyway: --discard-repo-extras."
    exit 1
  fi
  [[ ${#orphan[@]} -gt 0 ]] &&
    echo "⚠ discarding ${#orphan[@]} repo-only file(s) (--discard-repo-extras)"
  [[ ${#drift[@]} -gt 0 ]] &&
    printf '⚠ hub and repo differ (the hub wins): %s\n' "$(IFS=', '; echo "${drift[*]}")"
  [[ ${#unmanaged[@]} -gt 0 ]] &&
    echo "⚠ not written by this sync, and not read by deliver: ${unmanaged[*]} — " \
         "back-port anything you need into the hub, then delete the folder"
fi

# --- 1) metadata tree (exclude the release-notes archive — it's foldered by
# version — and the per-platform override files `*.ios.txt`/`*.osx.txt`, which
# are NOT canonical fields; the matching one is overlaid below in step 1b)
if [[ $have_rsync -eq 1 ]]; then
  # --exclude "/$sibling_dir/" does double duty: the hub has no such directory to
  # send, and under --delete (NOT --delete-excluded) an excluded path on the
  # RECEIVING side is protected — which is the whole reason it is here.
  rsync -a --delete --exclude 'release-notes/' --exclude "/$sibling_dir/" \
    --exclude '*.ios.txt' --exclude '*.osx.txt' "$src/metadata/" "$dst/metadata/"
else
  # clear what this sync owns, and only that — `rm -rf "$dst/metadata"` would take
  # the sibling subtree with it, which is the rsync bug in its cruder form
  mkdir -p "$dst/metadata"
  find "$dst/metadata" -mindepth 1 -maxdepth 1 ! -name "$sibling_dir" -exec rm -rf {} + 2>/dev/null || true
  cp -R "$src/metadata/." "$dst/metadata/"
  rm -rf "$dst/metadata/release-notes"
  find "$dst/metadata" \( -name '*.ios.txt' -o -name '*.osx.txt' \) -delete 2>/dev/null || true
fi

# --- 1b) per-platform field overrides: overlay <field>.<platform>.txt onto
# <field>.txt for the requested platform (a universal app's iOS and macOS
# listings share one hub but a few fields — e.g. promotional_text — differ).
override_msg="(none)"
if [[ -n "$platform" ]]; then
  applied=()
  for ov in "$src/metadata"/*/*."$platform".txt; do
    [[ -e "$ov" ]] || continue
    loc="$(basename "$(dirname "$ov")")"
    field="$(basename "$ov" ".$platform.txt")"
    mkdir -p "$dst/metadata/$loc"
    cp "$ov" "$dst/metadata/$loc/$field.txt"
    applied+=("$loc/$field")
  done
  if [[ ${#applied[@]} -gt 0 ]]; then
    override_msg="$platform: ${applied[*]}"
  else
    override_msg="$platform: no <field>.$platform.txt overrides in the hub (canonical values used)"
  fi
fi

# --- 2) this version's release notes → fastlane's per-locale release_notes.txt
# Two passes, and the order is the point: the shared <locale>.txt lands first,
# then <locale>.<platform>.txt overwrites it for the platform being delivered.
# A universal app can need genuinely different notes per platform ("the menu bar
# app" on Mac, "the keyboard" on iPhone) — the same case the <field>.<platform>.txt
# overrides serve in step 1b, which cannot be expressed here because this archive
# is foldered by version and its file names are locales.
rn="$src/release-notes/$version"
if [[ -d "$rn" ]]; then
  for f in "$rn"/*.txt; do
    [[ -e "$f" ]] || continue
    locale="$(basename "$f" .txt)"
    # skip the platform variants in the first pass — and, with no --platform,
    # skip them entirely so the canonical notes are what ships
    case "$locale" in *.ios|*.osx) continue ;; esac
    mkdir -p "$dst/metadata/$locale"
    cp "$f" "$dst/metadata/$locale/release_notes.txt"
  done
  if [[ -n "$platform" ]]; then
    rn_override=()
    for f in "$rn"/*."$platform".txt; do
      [[ -e "$f" ]] || continue
      locale="$(basename "$f" ".$platform.txt")"
      mkdir -p "$dst/metadata/$locale"
      cp "$f" "$dst/metadata/$locale/release_notes.txt"
      rn_override+=("$locale")
    done
    [[ ${#rn_override[@]} -gt 0 ]] &&
      echo "release notes ($platform): overrode ${rn_override[*]}"
  fi
fi

# --- locales to handle: the asserted set, else whatever metadata landed
# (minus review_information, which is app-level, not a locale)
expected=()
if [[ -n "$locales_csv" ]]; then
  IFS=',' read -ra expected <<< "$locales_csv"
else
  for d in "$dst/metadata"/*/; do
    [[ -d "$d" ]] || continue
    b="$(basename "$d")"
    # neither is a locale: review contact info is app-level, and the sibling
    # subtree is another store's listing entirely
    [[ "$b" == "review_information" || "$b" == "$sibling_dir" ]] && continue
    expected+=("$b")
  done
fi

# --- 3) screenshots + App Preview videos → FLAT fastlane/screenshots/<locale>/
# Consume the CANONICAL media tree owned by appstore-media:
#   <slug>/media/apple/<App>/<locale>/screenshots*/  (upload-ready stills, one
#                                                     directory per device class)
#   <slug>/media/apple/<App>/<locale>/app-preview/   (upload-ready App Preview video[s])
# deliver needs a FLAT per-locale folder (screenshots/<locale>/<files>) and CANNOT
# read the nested media tree — so copy leaf files in per locale. Videos go in the
# SAME locale folder (deliver detects them by extension). Legacy fallback: an
# already-flattened store/apple/screenshots/<locale>/.
rm -rf "$dst/screenshots"; mkdir -p "$dst/screenshots"
media="$hub/$slug/media/apple"

# A UNIVERSAL app (one bundle id, macOS + iOS) keeps every device class in the same
# per-locale media folder — mac_*, iphone_*, ipad_* side by side — but `deliver`
# uploads ONE platform per run and reads ONE flat folder. Handing it the whole set
# offers Mac stills to the iOS listing, where they are not a valid size. So when
# --platform is given, keep only that platform's stills. Discriminate by PIXEL SIZE,
# not by filename: the Mac App Store accepts exactly four, everything else is iOS.
is_mac_shot() {
  local dims
  dims="$(sips -g pixelWidth -g pixelHeight "$1" 2>/dev/null \
          | awk '/pixelWidth/{w=$2} /pixelHeight/{h=$2} END{print w"x"h}')"
  case "$dims" in
    1280x800|1440x900|2560x1600|2880x1800) return 0 ;;
    *) return 1 ;;
  esac
}
# keep this still for the platform being delivered? (no --platform → keep all)
want_shot() {
  [[ -z "$platform" ]] && return 0
  if [[ "$platform" == "osx" ]]; then is_mac_shot "$1"; else ! is_mac_shot "$1"; fi
}
shots_n=0; vids_n=0; skipped_n=0; with_media=" "; no_media=()
for loc in "${expected[@]}"; do
  destloc="$dst/screenshots/$loc"; copied=0
  for appdir in "$media"/*/; do          # one <App> per root, but glob to be safe
    # EVERY device directory, not just `screenshots/`. appstore-media keeps one
    # per device class — screenshots/ for iPhone, screenshots-ipad13/ for the
    # 13" iPad — and reading only the first one is not a smaller sync, it is a
    # DELETION: deliver runs with overwrite_screenshots, so a set that arrives
    # missing the iPad stills does not leave them alone, it replaces the set and
    # they are gone from the live listing. One app had 16 iPad screenshots on the
    # store and 0 in the flattened folder, and the sync reported success.
    shopt -s nullglob
    shotdirs=("$appdir$loc"/screenshots*/)
    shopt -u nullglob
    [[ ${#shotdirs[@]} -gt 0 ]] || continue
    mkdir -p "$destloc"
    for shotdir in "${shotdirs[@]}"; do
      # The device folders reuse filenames (01_home.png in both), so anything
      # beyond the primary is prefixed with its device suffix. deliver picks the
      # device by PIXEL SIZE, never by filename, so renaming is free.
      dirbase="$(basename "$shotdir")"
      prefix=""
      [[ "$dirbase" != "screenshots" ]] && prefix="${dirbase#screenshots-}_"
      for img in "$shotdir"*.png "$shotdir"*.jpg "$shotdir"*.jpeg; do
        [[ -e "$img" ]] || continue
        want_shot "$img" || { skipped_n=$((skipped_n+1)); continue; }
        cp "$img" "$destloc/$prefix$(basename "$img")"; shots_n=$((shots_n+1)); copied=1
      done
    done
    for vid in "$appdir$loc/app-preview"/*.mp4 "$appdir$loc/app-preview"/*.mov "$appdir$loc/app-preview"/*.m4v; do
      [[ -e "$vid" ]] || continue; cp "$vid" "$destloc/"; vids_n=$((vids_n+1))
    done
  done
  if [[ $copied -eq 0 && -d "$src/screenshots/$loc" ]]; then   # legacy flat fallback
    mkdir -p "$destloc"; cp "$src/screenshots/$loc/"* "$destloc/" 2>/dev/null && copied=1 && shots_n=$((shots_n+1))
  fi
  if [[ $copied -eq 1 ]]; then with_media+="$loc "; else no_media+=("$loc"); fi
done

# --- reuse a fallback locale's media for locales that have text but no media of
# their own (e.g. en-GB reusing en-US English screenshots). Apple does NOT share
# screenshots across locales, so each locale needs its own copy. Opt-in only.
shot_warn=()
if [[ ${#no_media[@]} -gt 0 ]]; then
  if [[ -n "$shot_fallback" && -d "$dst/screenshots/$shot_fallback" ]]; then
    for loc in "${no_media[@]}"; do
      [[ "$loc" == "$shot_fallback" ]] && continue
      mkdir -p "$dst/screenshots/$loc"
      cp "$dst/screenshots/$shot_fallback/"* "$dst/screenshots/$loc/" 2>/dev/null || true
      with_media+="$loc(←$shot_fallback) "
    done
  else
    for loc in "${no_media[@]}"; do shot_warn+=("$loc: no screenshots in the canonical media tree (media/apple/<App>/$loc/) — deliver would ship none; add per-locale media or pass --screenshot-fallback <loc>"); done
  fi
fi
shots_msg="$shots_n still(s), $vids_n preview video(s) → $dst/screenshots/<locale>/  [locales:$with_media]"
# never drop stills silently — say what --platform filtered out and why
[[ $skipped_n -gt 0 ]] && shots_msg="$shots_msg
    ($skipped_n still(s) held back as not --platform $platform; deliver the other platform to ship them)"

fi   # end of the hub-backed branch; standalone joins here for verification

# --- 4) VERIFY completeness -------------------------------------------------
# ($expected was computed above)

missing=()
warn=()
if [[ ${#expected[@]} -eq 0 ]]; then
  missing+=("no locale metadata found in $src/metadata")
else
  for loc in "${expected[@]}"; do
    d="$dst/metadata/$loc"
    if [[ ! -d "$d" ]]; then missing+=("$loc: locale folder missing"); continue; fi
    for field in $required; do
      [[ -s "$d/$field.txt" ]] || missing+=("$loc: $field.txt missing or empty")
    done
    [[ -s "$d/release_notes.txt" ]] || warn+=("$loc: release_notes.txt — none for version $version (required for updates)")
  done
fi
# merge screenshot warnings (skip empties so the array stays clean under set -u)
for w in "${shot_warn[@]:-}"; do [[ -n "$w" ]] && warn+=("$w"); done

if [[ "$standalone" == "1" ]]; then
  echo "metadata: $dst/metadata (authored here; nothing was copied)"
else
  echo "metadata: synced $src/metadata → $dst/metadata"
fi
if [[ -n "$platform" ]]; then
  echo "platform overrides ($platform): $override_msg   [.$other_platform.txt ignored]"
fi
echo "screenshots: $shots_msg"

if [[ ${#missing[@]} -gt 0 ]]; then
  echo
  echo "✗ SYNC INCOMPLETE — the hub is missing required data:"
  printf '   - %s\n' "${missing[@]}"
  echo
  echo "Fill the hub, then re-sync. Run the previous skill:"
  echo "   → store-metadata-writer   (authors $slug/store/apple/metadata from the profile)"
  echo "   (standalone / no hub: author the fields with app-store-metadata directly in fastlane/)"
  echo "Not uploading — incomplete metadata."
  exit 1
fi

if [[ ${#warn[@]} -gt 0 ]]; then
  echo "⚠ warnings (not blocking):"
  printf '   - %s\n' "${warn[@]}"
fi

# ── the copy gate ──────────────────────────────────────────────────────────────
# Completeness is not correctness. A locale can have every required field and
# still ship a translation that lost a claim, gained one, or was never translated
# — and in a language nobody here reads, this comparison is the only thing that
# would ever notice. Blocking, with an explicit override, for the same reason the
# missing-field check blocks: it is cheaper to stop here than on a live listing.
# measure_copy.py ships in the shared-track plugin, not this one, and neither form of
# addressing finds it alone: $CLAUDE_PLUGIN_ROOT is unset when this script is run by
# hand or by another script, and in the installed cache every track sits under its own
# commit sha, so shared-track's path is not derivable from ours by a relative walk.
# Hence a search: the checkout layout beside us, then the sha-globbed cache, then the
# working copy. Resolving through $0 first is what keeps it working outside Claude Code.
resolve_copy_check() {
  local here up4 c
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # scripts → <skill> → skills → <track>: that is plugins/ in a checkout, and the
  # track's own directory (the level holding the shas) in the installed cache.
  up4="$(cd "$here/../../../.." 2>/dev/null && pwd || true)"

  # 1. a checkout or worktree: plugins/<track>/skills/... → plugins/shared-track/...
  if [[ -n "$up4" && -f "$up4/shared-track/skills/copy-edit/scripts/measure_copy.py" ]]; then
    printf '%s\n' "$up4/shared-track/skills/copy-edit/scripts/measure_copy.py"; return 0
  fi

  # 2. the installed cache: <marketplace>/<track>/<sha>/skills/... — shared-track carries
  #    a different sha than ours, so the level above us is globbed, never spelled out.
  for c in "$up4"/../shared-track/*/skills/copy-edit/scripts/measure_copy.py \
           "${CLAUDE_PLUGIN_ROOT:-/nonexistent}"/../../shared-track/*/skills/copy-edit/scripts/measure_copy.py \
           "$HOME"/.claude/plugins/cache/*/shared-track/*/skills/copy-edit/scripts/measure_copy.py; do
    [[ -f "$c" ]] && { printf '%s\n' "$c"; return 0; }
  done

  # 3. the working copy, for a run from outside the plugin system altogether.
  #    $APP_FACTORY is the anchor a deploy writes; the literal checkout path that
  #    stood here is what this repo's own portability rule forbids.
  c="${APP_FACTORY:-/nonexistent}/plugins/shared-track/skills/copy-edit/scripts/measure_copy.py"
  [[ -f "$c" ]] && { printf '%s\n' "$c"; return 0; }
  return 1
}

copy_check="$(resolve_copy_check || true)"
if [[ "$skip_copy_check" == "1" ]]; then
  echo "⚠ copy check skipped (--skip-copy-check)"
elif [[ -z "$copy_check" ]]; then
  echo
  echo "✗ COPY CHECK UNAVAILABLE — measure_copy.py not found (shared-track / copy-edit)."
  echo "   This gate blocks, so a missing measurer is a failure and not a warning:"
  echo "   otherwise \"never ran\" and \"passed\" read identically in this output."
  echo "   → refresh the installed plugins:  python3 factory/deploy.py"
  echo "   → or ship without the comparison: re-run with --skip-copy-check."
  echo "Not uploading — the listing text was never compared across languages."
  exit 1
elif ! command -v python3 >/dev/null 2>&1; then
  echo
  echo "✗ COPY CHECK UNAVAILABLE — python3 not found, and this gate blocks."
  echo "   → install python3, or re-run with --skip-copy-check to ship without it."
  echo "Not uploading — the listing text was never compared across languages."
  exit 1
else
  # Point the gate at the locale folders this sync owns. "$dst/metadata" would walk
  # into fastlane/metadata/$sibling_dir/ and compare Apple's English against the
  # PLAY listing's translations — different fields, different files, a failure that
  # names a file this skill does not write and cannot fix.
  gate_paths=(); for loc in "${expected[@]}"; do gate_paths+=("$dst/metadata/$loc"); done
  if ! copy_out="$(python3 "$copy_check" "${gate_paths[@]}" --parity-only --fail-on-parity 2>&1)"; then
    echo
    echo "$copy_out"
    echo
    echo "✗ COPY CHECK FAILED — a translation does not match the English source."
    echo "Fix the hub ($slug/store/...), then re-sync. The skills that own this:"
    echo "   → copy-edit               (edits the copy, in every language)"
    echo "   → store-metadata-writer   (authors/repairs the per-locale fields)"
    echo "If the difference is deliberate, re-run with --skip-copy-check."
    echo "Not uploading — the listing text disagrees with itself across languages."
    exit 1
  fi
  echo "✓ copy check — every translation matches the English claim for claim"
fi

echo "✓ sync verified — all required fields present for: ${expected[*]}"

# ── the staged tree is a build directory ───────────────────────────────────────
# We only reach here on a clean run, which is exactly the condition that makes
# untracking safe: every field was reproduced from the hub, so git is holding a
# second copy of something the hub owns and nothing would be lost. Report; do not
# act. A repo that authors its listing locally (no hub entry) never gets here, so
# this cannot fire on the one setup where fastlane/ IS the source of truth.
if command -v git >/dev/null 2>&1 && git -C "$app_repo" rev-parse --git-dir >/dev/null 2>&1; then
  tracked_n="$(git -C "$app_repo" ls-files -- fastlane | wc -l | tr -d ' ')"
  if [[ "${tracked_n:-0}" -gt 0 ]]; then
    # Real repo config, if any, must survive the untracking — only staged output goes.
    cfg="$(git -C "$app_repo" ls-files -- 'fastlane/Fastfile' 'fastlane/Appfile' 'fastlane/Deliverfile' 'fastlane/Pluginfile' | tr '\n' ' ')"
    # Sibling screenshot folders this sync does not write: dead sets from an older layout.
    stale="$(cd "$app_repo" 2>/dev/null && ls -d fastlane/screenshots-* 2>/dev/null | tr '\n' ' ' || true)"
    echo
    echo "⚠ the repo still tracks the staged listing ($tracked_n files under fastlane/)"
    echo "   fastlane/ is a build directory, rebuilt here from the hub on every run —"
    echo "   it is NOT the source of truth, and tracking it keeps a second copy that"
    echo "   goes stale, and turns a --platform-scoped sync into a phantom deletion."
    [[ -n "$stale" ]] && echo "   dead sets this sync never writes: $stale"
    if [[ -n "$cfg" ]]; then
      echo "   KEEP tracked (real repo config, not staged output): $cfg"
      echo "   → untrack the staged content only, then add the staged paths to .gitignore"
    else
      echo "   no Fastfile/Appfile/Deliverfile — this folder is pure staged output."
      echo "   → offer the user:"
      [[ -n "$stale" ]] && echo "        rm -rf $stale"
      echo "        git rm -r --cached fastlane && echo 'fastlane/' >> .gitignore"
      echo "     (files stay on disk; delivery is unaffected)"
    fi
  fi
fi

if [[ "$standalone" == "1" ]]; then
  echo "done: $dst verified in place   (now run: fastlane deliver)"
else
echo "done: $src → $dst   (now run: fastlane deliver)"
fi
echo "reminder: the ASC credential is resolved by shared/credentials.rb — the environment,"
echo "          then \$KEYS_ROOT/credentials.json, then the hub's DATA.md."
