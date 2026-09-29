#!/usr/bin/env bash
# pull_and_diff.sh — MANDATORY pre-upload guard for play-store-deliver.
#
# Downloads the listing that is ACTUALLY on Google Play (fastlane supply init)
# and diffs it against the hub. The hub is only the source of truth if nobody
# edited the listing in the Play Console since the last supply — and people do.
# Delivering without this check silently reverts those edits, INCLUDING media:
# `supply` overwrites the image sets it is given.
#
# Usage: pull_and_diff.sh <slug> <package-name> [--hub DIR | --repo DIR]
# Exit 0 = the local listing matches Play (safe to supply). Exit 2 = they differ.
#
# "Local" is the hub when there is one, and the app repo's fastlane/metadata/android
# tree when there is not — the same two modes sync_from_hub.sh has. This guard is
# MANDATORY in both; it used to exit 1 in the second.
set -euo pipefail

slug="${1:-}"; pkg="${2:-}"
[[ -n "$slug" && -n "$pkg" ]] || { echo "usage: pull_and_diff.sh <slug> <package-name> [--hub DIR | --repo DIR]"; exit 1; }
hub="${APP_HUB:-${DEV_ROOT:+$DEV_ROOT/app-hub}}"; repo="${APP_REPO:-}"
case "${3:-}" in
  --hub)  hub="${4:?}" ;;
  --repo) repo="${4:?}" ;;
esac
if [[ -n "$hub" && -d "$hub" ]]; then
  src="hub"; meta="$hub/$slug/store/play/metadata"; media="$hub/$slug/media/play"
else
  [[ -n "$repo" ]] || { [[ -d "fastlane/metadata/android" ]] && repo="$PWD"; } || true
  [[ -n "$repo" && -d "$repo/fastlane/metadata/android" ]] || {
    echo "✗ no listing source. Either a hub — set \$APP_HUB, or pass --hub DIR — or the app" >&2
    echo "  repo's own fastlane/metadata/android: run from the repo, set \$APP_REPO, or pass --repo DIR." >&2
    exit 1; }
  src="repo"; meta="$repo/fastlane/metadata/android"; media="$meta"      # supply layout: images/ per locale
fi
echo "comparing Play against the $src: $meta"

# The service account is resolved by the track's own resolver, which asks in a
# documented order: $PLAY_SERVICE_ACCOUNT, then $KEYS_ROOT/credentials.json, then the
# folder convention, then the hub's DATA.md for an installation that predates the JSON.
# This line used to grep DATA.md for a heading and take the first path-looking string
# after it — a convention that exists in one studio's markdown file and nowhere else,
# and one that disagreed with what publish_aab.py did three directories away.
creds="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../shared" && pwd)/credentials.py"
key="$(python3 "$creds" --path 2>/dev/null)" || true
if [[ -z "$key" || ! -f "$key" ]]; then
  python3 "$creds" >&2
  exit 1
fi

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
echo "pulling the live Play listing for $pkg …"
FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_HIDE_CHANGELOG=1 \
  fastlane supply init --package_name "$pkg" --json_key "$key" --metadata_path "$tmp/live" >/dev/null 2>&1 || true
[[ -d "$tmp/live" ]] || { echo "download produced nothing — check the key's Play permissions"; exit 1; }

HUB_META="$meta" HUB_MEDIA="$media" LIVE="$tmp/live" SRC="$src" \
python3 - <<'PY'
import os, sys, hashlib, pathlib
meta, media, live = os.environ["HUB_META"], os.environ["HUB_MEDIA"], os.environ["LIVE"]
src = os.environ["SRC"]                       # "hub" or "repo" — the side Play is compared with
diffs = []
def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

for loc in sorted(os.listdir(live)):
    if not os.path.isdir(f"{live}/{loc}"): continue
    for f in ("title", "short_description", "full_description"):
        lp, hp = f"{live}/{loc}/{f}.txt", f"{meta}/{loc}/{f}.txt"
        if not (os.path.exists(lp) and os.path.exists(hp)): continue
        a = open(lp, encoding="utf-8").read().strip()
        b = open(hp, encoding="utf-8").read().strip()
        if a == b:
            print(f"  in sync   {loc}/{f}")
        elif not a:
            # Play has nothing here — the hub only ADDS content. Not a conflict.
            print(f"  {src} adds  {loc}/{f} (empty on Play)")
        else:
            diffs.append(f"{loc}/{f}")
            print(f"  CONFLICT  {loc}/{f}\n      play: {a[:100]}\n      {src} : {b[:100]}")
    # images: compare the SET (count + content hashes), not filenames — supply
    # renames downloads to <n>_<locale>.png
    for kind in ("phoneScreenshots", "sevenInchScreenshots", "tenInchScreenshots"):
        ld, hd = f"{live}/{loc}/images/{kind}", f"{media}/{loc}/images/{kind}"
        lh = sorted(sha(f"{ld}/{x}") for x in os.listdir(ld)) if os.path.isdir(ld) else []
        hh = sorted(sha(f"{hd}/{x}") for x in os.listdir(hd)) if os.path.isdir(hd) else []
        if lh == hh:
            if lh: print(f"  in sync   {loc}/{kind} ({len(lh)} images)")
        else:
            diffs.append(f"{loc}/{kind}")
            print(f"  DIFFERENT {loc}/{kind}: play has {len(lh)}, {src} has {len(hh)}")
    for g in ("icon.png", "featureGraphic.png"):
        lp, hp = f"{live}/{loc}/images/{g}", f"{media}/{loc}/images/{g}"
        if os.path.exists(lp) and os.path.exists(hp):
            if sha(lp) == sha(hp): print(f"  in sync   {loc}/{g}")
            else: diffs.append(f"{loc}/{g}"); print(f"  DIFFERENT {loc}/{g}")
        elif os.path.exists(lp):
            diffs.append(f"{loc}/{g}"); print(f"  MISSING IN HUB {loc}/{g} (Play has it)")

if not diffs:
    print("\n== " + src + " matches Google Play — safe to supply.")
    sys.exit(0)
print(f"\n== {len(diffs)} item(s) differ: {', '.join(diffs)}")
print("== Play may be AHEAD of the " + src + " (edited in the Play Console).")
print("== Back-port anything the owner wants to keep INTO the " + src + " first.")
print("== A blind `supply` OVERWRITES the live media sets. Do not.")
sys.exit(2)
PY
