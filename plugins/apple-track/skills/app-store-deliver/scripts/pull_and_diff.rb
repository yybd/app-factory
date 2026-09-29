#!/usr/bin/env ruby
# encoding: utf-8
# pull_and_diff.rb — MANDATORY pre-upload guard for app-store-deliver.
#
# Downloads the listing that is ACTUALLY on App Store Connect and diffs it
# against the hub. The hub is only the source of truth if nobody edited the
# listing on the ASC website since the last deliver — and people do. Delivering
# without this check silently reverts those edits.
#
# Also reports the version's appStoreState: metadata is frozen once a version
# is WAITING_FOR_REVIEW / IN_REVIEW, so uploading means pulling it out of the
# review queue.
#
# MEDIA is checked too, by SIZE and not by name. Two failures made that
# necessary, both shipped unnoticed and both caught only because a human asked:
#   * `deliver` does not upload App Preview videos at all (it processes stills
#     silently), so a recaptured preview can sit on disk for days while ASC
#     serves the old clip — under an unchanged filename.
#   * screenshots renamed by a scene-order change leave their predecessors in
#     the set, still showing whatever the app used to be called.
# Comparing filenames alone sees neither. Comparing bytes sees both.
#
# WHAT IT CANNOT SEE: this compares the hub against the store, so it is blind to
# an asset that is wrong in BOTH. A capture that was never redone after a rename
# matches byte for byte and reports in sync while showing the old product name in
# every locale. Only looking at the asset catches that.
#
# Usage: pull_and_diff.rb <slug> <bundle-id> <version> [--platform IOS|MAC_OS] [--hub DIR | --repo DIR]
# Exit 0 = the local listing matches the store (safe to deliver). Exit 2 = they differ.
#
# "Local" is the hub when there is one, and the app repo's fastlane/ tree when there
# is not — see ASC.tree. The guard is mandatory in both modes; it used to abort in
# the second.
#
# NOTE: run with a UTF-8 locale (LANG/LC_ALL) or Ruby dies reading Hebrew files.

require_relative "asc_common"

pos, opts = ASC.parse_args(ARGV)
slug, bundle, version = pos
abort "usage: pull_and_diff.rb <slug> <bundle-id> <version> [--platform IOS|MAC_OS] [--hub DIR | --repo DIR]" unless slug && bundle && version
platform = opts[:platform] || "IOS"

tree = ASC.tree(slug, hub: opts[:hub], repo: opts[:repo])
src  = tree[:name]                                   # "hub" or "repo", for the report
meta = tree[:metadata]
abort "no #{src} metadata at #{meta}" unless Dir.exist?(meta)
puts "comparing the store against the #{src}: #{tree[:root]}"

ASC.token!
app_id = ASC.app_id(bundle)
ver    = ASC.version(app_id, platform: platform, version: version)
state  = ver["attributes"]["appStoreState"]

puts "app #{bundle}  version #{version} [#{platform}]  state=#{state}"
if %w[WAITING_FOR_REVIEW IN_REVIEW PENDING_APPLE_RELEASE].include?(state)
  puts "!! metadata is FROZEN in this state — uploading requires removing the"
  puts "!! submission from review and losing its place in the queue. Stop and ask."
end

# Release notes live in release-notes/<version>/, NOT in metadata/. A copy left
# in metadata/ from an earlier version made this gate report a CONFLICT on every
# locale for notes that were in fact correct — the surest way to teach someone to
# ignore the gate. Resolve the versioned source, honouring the same
# <locale>.<platform>.txt override sync_from_hub applies, and fall back to
# metadata/ only for a repo that has no versioned tree.
def release_notes_path(tree, version, platform, loc)
  dir = tree[:release_notes].call(version)
  return nil unless dir && Dir.exist?(dir)
  plat = platform == "MAC_OS" ? "osx" : "ios"
  [File.join(dir, "#{loc}.#{plat}.txt"), File.join(dir, "#{loc}.txt")].find { |f| File.exist?(f) }
end

FIELDS = { "description" => "description", "keywords" => "keywords",
           "promotionalText" => "promotional_text", "whatsNew" => "release_notes" }

diffs = []
ASC.localizations(ver["id"]).each do |l|
  a = l["attributes"]; loc = a["locale"]
  FIELDS.each do |api_key, file|
    path = release_notes_path(tree, version, platform, loc) if file == "release_notes"
    path ||= File.join(meta, loc, "#{file}.txt")
    next unless path && File.exist?(path)
    store = a[api_key].to_s.strip
    local = File.read(path, encoding: "utf-8").strip
    if store == local
      puts "  in sync   #{loc}/#{file}"
    elsif store.empty?
      # the store has nothing here (e.g. whatsNew on a first version) — the
      # hub only ADDS content, it cannot destroy anything. Not a conflict.
      puts "  #{src} adds  #{loc}/#{file} (empty on the store)"
    else
      diffs << "#{loc}/#{file}"
      puts "  CONFLICT  #{loc}/#{file}"
      puts "      store: #{store[0, 100]}"
      puts "      #{src}  : #{local[0, 100]}"
    end
  end
end

# name + subtitle live on the editable appInfo, not the version
ASC.body(ASC.rc.get("v1/apps/#{app_id}/appInfos"))["data"].each do |i|
  next if i["attributes"]["appStoreState"] == "READY_FOR_SALE"
  ASC.body(ASC.rc.get("v1/appInfos/#{i['id']}/appInfoLocalizations"))["data"].each do |l|
    a = l["attributes"]; loc = a["locale"]
    { "name" => "name", "subtitle" => "subtitle" }.each do |api_key, file|
      path = File.join(meta, loc, "#{file}.txt")
      next unless File.exist?(path)
      store = a[api_key].to_s.strip
      local = File.read(path, encoding: "utf-8").strip
      if store == local then puts "  in sync   #{loc}/#{file}"
      else
        diffs << "#{loc}/#{file}"
        puts "  DIFFERENT #{loc}/#{file}\n      store: #{store}\n      #{src}  : #{local}"
      end
    end
  end
end

# ---------------------------------------------------------------------------
# MEDIA — screenshots + App Previews, compared by size against the local tree.
#
# Matching is by BASENAME ACROSS ALL LOCALES on purpose: the delivery fans one
# capture set out to every locale (sync_from_hub's --screenshot-fallback), so a
# per-locale lookup would report six false "missing" for a set that is correct.
local = {}   # basename => size
Dir.glob(tree[:media_glob]).each do |f|
  next unless File.file?(f)
  local[File.basename(f)] = File.size(f)
end

if local.empty?
  puts "\n  media: nothing under #{tree[:media_glob]} — skipped"
else
  seen = {}
  ASC.localizations(ver["id"]).each do |l|
    loc = l["attributes"]["locale"]
    [["appScreenshotSets", "appScreenshots", "screenshot"],
     ["appPreviewSets",    "appPreviews",    "preview"]].each do |set_rel, item_rel, kind|
      ASC.body(ASC.rc.get("v1/appStoreVersionLocalizations/#{l['id']}/#{set_rel}"))["data"].each do |set|
        ASC.body(ASC.rc.get("v1/#{set_rel.sub(/Sets$/, 'Sets')}/#{set['id']}/#{item_rel}"))["data"].each do |item|
          a = item["attributes"]
          name = a["fileName"].to_s
          size = a["fileSize"]
          key  = "#{loc}/#{name}"
          (seen[loc] ||= []) << name
          if !local.key?(name)
            diffs << key
            puts "  ORPHAN    #{loc}/#{name} — on the store, not in the #{src} (#{kind})"
          elsif size && local[name] != size
            diffs << key
            puts "  STALE     #{loc}/#{name} — store #{size} B, #{src} #{local[name]} B (#{kind})"
          end
        end
      end
    end
  end
  # Anything the hub holds for this platform that never reached the store.
  #
  # SCREENSHOTS ONLY, deliberately. Stills carry the studio's mac_/iphone_/ipad_
  # prefix from capture.sh, so "which platform is this" is answerable from the
  # name. App Previews are not: the Mac clip is <App>_preview.mp4 and the
  # iPhone clip <App>_iphone_preview.mp4, which share a prefix — flagging on
  # that basis reported the Mac video as missing from the iOS listing. A preview
  # that is present but old is already caught by STALE, and one the hub never
  # had by ORPHAN; only "captured but never delivered" is out of scope here, and
  # a false alarm every run is worse than that gap.
  seen.each do |loc, names|
    prefixes = names.map { |n| n[/\A(mac|iphone|ipad)_/i]&.downcase }.compact.uniq
    next if prefixes.empty?
    (local.keys - names).each do |n|
      pfx = n[/\A(mac|iphone|ipad)_/i]&.downcase
      next unless pfx && prefixes.include?(pfx)
      diffs << "#{loc}/#{n}"
      puts "  NOT SENT  #{loc}/#{n} — in the #{src}, absent from the store"
    end
  end
  puts "  media     checked #{seen.values.flatten.size} asset(s) against #{local.size} #{src} file(s)"
end

if diffs.empty?
  puts "\n== #{src} matches App Store Connect — safe to deliver."
  exit 0
end
puts "\n== #{diffs.size} field(s) differ: #{diffs.join(', ')}"
puts "== Text: the store may be AHEAD of the #{src} (someone edited it on the website)."
puts "== Media: STALE/ORPHAN means the store holds an older asset under a name that"
puts "==        did not change. deliver will NOT fix a preview — use upload_app_preview.rb."
puts "== Decide per field, and back-port anything the owner wants to keep INTO"
puts "== the #{src} before delivering. Do NOT blind-deliver over this."
exit 2
