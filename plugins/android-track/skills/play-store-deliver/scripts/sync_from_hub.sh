#!/usr/bin/env bash
# sync_from_hub.sh — pull an app's Google Play metadata from the hub (source of
# truth) down into the app repo's fastlane/metadata/android tree, before `supply`,
# and VERIFY the result is complete.
#
# The hub holds the canonical, per-locale, fastlane-format Play metadata plus the
# changelogs (by versionCode) and graphics. fastlane never authors metadata; it
# only uploads what this script mirrors in. Run it every time you supply.
#
# After syncing it verifies every required field is present and non-empty for
# every locale. If anything is missing, it reports what, points you at the skill
# that fills the hub (store-metadata-writer), and EXITS NON-ZERO so the caller
# does not upload incomplete data.
#
# Usage:
#   sync_from_hub.sh <slug> <versionCode> <app-repo> [--hub DIR] [--locales a,b,c]
#
#   <slug>         the app's hub folder name ($APP_HUB/<slug>/)
#   <versionCode>  the integer versionCode being shipped (selects the changelog)
#   <app-repo>     the app's native project root
#   --hub DIR      override the hub root (default: $APP_HUB, else $DEV_ROOT/app-hub)
#   --locales      assert this exact locale set is present (comma-separated)
#
# Hub is READ-only; only <app-repo>/fastlane/ is written. The repo copy is
# disposable (git-ignore it) — the hub is the truth.

set -euo pipefail

slug="${1:-}"; vcode="${2:-}"; app_repo="${3:-}"
# The hub's location is $APP_HUB, written into the environment by the deploy from
# grove's registry; $DEV_ROOT/app-hub is the layout the install instructions produce.
# A hardcoded home-directory path is neither, and was the default here — correct on
# the machine it was written on, silently wrong on every other, and invisible to
# test_portability, which used to scan only .md and .json.
hub="${APP_HUB:-${DEV_ROOT:+$DEV_ROOT/app-hub}}"; locales_csv=""
shift $(( $# < 3 ? $# : 3 )) || true
skip_copy_check=0; discard_repo_extras=0; standalone=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --hub) hub="$2"; shift 2 ;;
    --locales) locales_csv="$2"; shift 2 ;;
    --standalone) standalone=1; shift ;;                    # no hub: the repo's fastlane tree IS the truth
    --skip-copy-check) skip_copy_check=1; shift ;;   # ship a translation that deliberately differs from the English
    --discard-repo-extras) discard_repo_extras=1; shift ;;  # delete repo-only listing text instead of back-porting it
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$slug" || -z "$vcode" || -z "$app_repo" ]]; then
  echo "usage: sync_from_hub.sh <slug> <versionCode> <app-repo> [--hub DIR] [--locales a,b,c] [--skip-copy-check] [--discard-repo-extras]" >&2
  exit 2
fi

# $APP_HUB may be unset on a machine that has not been deployed, and --hub may not have
# been passed. Saying so here beats the alternative: an empty $hub makes every path below
# absolute from the filesystem root, so the failure arrives as "no metadata at
# /<slug>/store/..." — a message about the wrong thing entirely.
# ── two modes, and no hub is the second one, not a failure ───────────────────────
# A studio keeps its listing text in a hub and this mirrors it into the repo. Someone
# with one app has no hub, authors in `fastlane/metadata/android/` directly, and has
# nothing to sync FROM. Both SKILL.md files promised that mode and no script implemented
# it, so it failed at the first command. Detected, not declared: `--standalone` forces
# it and an unreachable hub selects it.
if [[ "$standalone" != "1" ]] && { [[ -z "$hub" ]] || [[ ! -d "$hub" ]]; }; then
  standalone=1
  echo "· no hub ($([[ -z "$hub" ]] && echo 'none configured' || echo "$hub is not there")) —"
  echo "  standalone mode: $app_repo/fastlane/metadata/android is the source of truth."
  echo "  To use a hub instead: set \$APP_HUB, or pass --hub DIR."
fi


src="$hub/$slug/store/play"
dst="$app_repo/fastlane/metadata/android"
required="title short_description full_description"   # Play per-locale required fields

# ── the sibling send-surface ───────────────────────────────────────────────────
# fastlane/ is shared. app-store-deliver's sync stages the App Store listing into
# fastlane/metadata/<locale>/ and fastlane/screenshots/ — the paths `deliver` reads
# — while this one owns fastlane/metadata/android/, the path `supply` reads. One
# root, two surfaces, both fed from the same hub.
#
# Our --delete is therefore scoped to the android subtree and MUST STAY THERE.
# Widening $dst by one level to fastlane/metadata would silently delete the whole
# App Store listing on every run; the mirror-image mistake cost a session once.
case "$dst" in
  */fastlane/metadata/android) : ;;
  *) echo "✗ refusing to run: dst must be <app-repo>/fastlane/metadata/android, got '$dst'" >&2
     echo "  This script runs rsync --delete against dst. Anything wider deletes the" >&2
     echo "  App Store listing that app-store-deliver stages alongside it." >&2
     exit 2 ;;
esac

if [[ "$standalone" == "1" ]]; then
  # Everything below copies the hub into the repo, so it is skipped whole — and the
  # VERIFY step still runs against the repo, which is the half that refuses an upload
  # with a missing locale, an over-limit field or no changelog for this versionCode.
  if [[ ! -d "$dst" ]]; then
    echo "✗ nothing to deliver — no $dst, and no hub to build it from." >&2
    echo "  Author the listing first: the play-store-metadata skill scaffolds and fills it." >&2
    exit 1
  fi
  echo "· standalone: verifying $dst as authored (no copy)"
  src="$app_repo/fastlane/metadata"
  graphics_msg="whatever is already under $dst/<locale>/images/ (not staged from a hub)"
else

if [[ ! -d "$src/metadata" ]]; then
  echo "✗ SYNC FAILED — no hub metadata at: $src/metadata" >&2
  echo "  Nothing has been authored for this app yet. Run the skill that fills the hub:" >&2
  echo "     → store-metadata-writer   (writes $slug/store/play/metadata from the profile)" >&2
  exit 1
fi
mkdir -p "$dst"

have_rsync=0; command -v rsync >/dev/null 2>&1 && have_rsync=1

# --- 0b) work that exists only in the repo -----------------------------------
# The rsync below runs with --delete: whatever sits in the repo's listing tree and
# not in the hub is gone, silently. That is right for a derived copy and
# destructive for text a different tool authored there — and a tool that writes
# here instead of into the hub is the case the field check cannot see, because the
# hub looks complete while the repo holds the newer words.
#
# A file the hub cannot reproduce at all BLOCKS. A file that exists in both and
# differs only warns: that is the normal state after the hub is edited.
if [[ -d "$dst" ]]; then
  orphan=(); drift=()
  while IFS= read -r -d '' f; do
    rel="${f#$dst/}"
    locale="${rel%%/*}"
    cands=()
    if [[ "$(basename "$(dirname "$f")")" == "changelogs" ]]; then
      # this versionCode's changelog only — an earlier release's notes do not make
      # this one reproducible, and that is where repo-only text hides
      for c in "$src/changelogs/$vcode/$locale.txt" "$src/changelogs/$vcode.txt"; do
        [[ -e "$c" ]] && cands+=("$c")
      done
    else
      [[ -e "$src/metadata/$rel" ]] && cands+=("$src/metadata/$rel")
    fi
    if [[ ${#cands[@]} -eq 0 ]]; then
      orphan+=("$rel")
    else
      same=0
      for c in "${cands[@]}"; do cmp -s "$c" "$f" && { same=1; break; }; done
      [[ $same -eq 0 ]] && drift+=("$rel")
    fi
  done < <(find "$dst" -type f -name '*.txt' -print0 2>/dev/null)

  if [[ ${#orphan[@]} -gt 0 && "$discard_repo_extras" != "1" ]]; then
    echo
    echo "✗ SYNC STOPPED — the repo holds listing text the hub cannot reproduce:"
    printf '   - %s\n' "${orphan[@]}"
    echo
    echo "This sync would delete it. It is not a stale copy — it is work that was"
    echo "never back-ported. Put it in the hub first:"
    echo "   → store-metadata-writer   (fields + changelogs, into $slug/store/play/)"
    echo "Then re-sync. To delete it anyway: --discard-repo-extras."
    exit 1
  fi
  [[ ${#orphan[@]} -gt 0 ]] &&
    echo "⚠ discarding ${#orphan[@]} repo-only file(s) (--discard-repo-extras)"
  if [[ ${#drift[@]} -gt 0 ]]; then
    echo "⚠ ${#drift[@]} field(s) differ between hub and repo — the hub wins: ${drift[*]:0:8}${drift[8]:+ …}"
  fi
fi

# --- 1) metadata tree (exclude the changelogs archive — foldered by versionCode)
if [[ $have_rsync -eq 1 ]]; then
  # --delete is safe here only because $dst is the android subtree (asserted above);
  # the App Store listing sits one level up and is never in this transfer's scope
  rsync -a --delete --exclude 'changelogs/' "$src/metadata/" "$dst/"
else
  rm -rf "$dst"; mkdir -p "$dst"; cp -R "$src/metadata/." "$dst/"; rm -rf "$dst/changelogs"
fi

# --- 2) changelog for this versionCode → per-locale changelogs/<versionCode>.txt
#        hub layout: changelogs/<vcode>/<locale>.txt (per-locale) OR changelogs/<vcode>.txt (all locales)
if [[ -d "$src/changelogs/$vcode" ]]; then
  for f in "$src/changelogs/$vcode"/*.txt; do
    [[ -e "$f" ]] || continue
    locale="$(basename "$f" .txt)"; mkdir -p "$dst/$locale/changelogs"; cp "$f" "$dst/$locale/changelogs/$vcode.txt"
  done
elif [[ -f "$src/changelogs/$vcode.txt" ]]; then
  for ld in "$dst"/*/; do [[ -d "$ld" ]] || continue; mkdir -p "${ld}changelogs"; cp "$src/changelogs/$vcode.txt" "${ld}changelogs/$vcode.txt"; done
fi

# --- 3) graphics from media/play if present
if [[ -d "$hub/$slug/media/play" ]]; then
  if [[ $have_rsync -eq 1 ]]; then rsync -a "$hub/$slug/media/play/" "$dst/"; else cp -R "$hub/$slug/media/play/." "$dst/"; fi
  graphics_msg="synced from $hub/$slug/media/play"
else
  graphics_msg="none in hub (skipped)"
fi

fi   # end of the hub-backed branch; standalone joins here for verification

# --- 4) VERIFY completeness -------------------------------------------------
expected=()
if [[ -n "$locales_csv" ]]; then
  IFS=',' read -ra expected <<< "$locales_csv"
else
  for d in "$dst"/*/; do [[ -d "$d" ]] || continue; expected+=("$(basename "$d")"); done
fi

missing=()
warn=()
if [[ ${#expected[@]} -eq 0 ]]; then
  missing+=("no locale metadata found in the hub ($src/metadata)")
else
  for loc in "${expected[@]}"; do
    d="$dst/$loc"
    if [[ ! -d "$d" ]]; then missing+=("$loc: locale folder missing"); continue; fi
    for field in $required; do
      [[ -s "$d/$field.txt" ]] || missing+=("$loc: $field.txt missing or empty")
    done
    [[ -s "$d/changelogs/$vcode.txt" ]] || warn+=("$loc: changelogs/$vcode.txt — none for versionCode $vcode")
  done
fi

if [[ "$standalone" == "1" ]]; then
  echo "metadata: $dst (authored here; nothing was copied)"
else
  echo "metadata: synced $src/metadata → $dst"
fi
echo "graphics: $graphics_msg"

if [[ ${#missing[@]} -gt 0 ]]; then
  echo
  echo "✗ SYNC INCOMPLETE — required data is missing:"
  printf '   - %s\n' "${missing[@]}"
  echo
  echo "Fill the hub, then re-sync. Run the previous skill:"
  echo "   → store-metadata-writer   (authors $slug/store/play/metadata from the profile)"
  echo "   (standalone / no hub: author the fields with play-store-metadata directly in fastlane/)"
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
  # $APP_FACTORY is the anchor a deploy writes; the literal checkout path that
  # stood here is what this repo's own portability rule forbids.
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
  if ! copy_out="$(python3 "$copy_check" "$dst" --parity-only --fail-on-parity 2>&1)"; then
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
echo "done: $src → $dst   (now run: fastlane supply)"
