#!/usr/bin/env ruby
# dedup_screenshots.rb — remove duplicate screenshots and fix ordering in an App
# Store version's screenshot sets. `fastlane deliver` against the current ASC API
# can 500 on the post-upload verification, retry, and leave DUPLICATE screenshots
# in a set (same fileName twice). This keeps one of each fileName and reorders the
# set alphabetically by fileName (01_…, 02_… → stable order).
#
# Usage:
#   ruby dedup_screenshots.rb <bundle-id> [--platform MAC_OS] [--version 2.0]
#                             [--locales en-US,en-GB] [--dry-run]
#
#   --platform   MAC_OS | IOS | TV_OS   (default MAC_OS)
#   --version    marketing version       (default: the single editable version found)
#   --locales    default: all localizations on the version
#   --dry-run    report duplicates without deleting
#
# Idempotent: a clean set is left untouched. Run with the ASC key in the hub DATA.md.

require_relative "asc_common"

pos, opts = ASC.parse_args(ARGV)
bundle = pos[0]
abort "usage: dedup_screenshots.rb <bundle-id> [--platform MAC_OS] [--locales a,b] [--dry-run]" unless bundle
platform    = opts[:platform] || "MAC_OS"
version_str = opts[:version]
dry         = ARGV.include?("--dry-run")

ASC.token!
rc = ASC.rc
app_id = ASC.app_id(bundle)

versions = ASC.body(rc.get("v1/apps/#{app_id}/appStoreVersions",
  version_str ? {"filter[platform]"=>platform, "filter[versionString]"=>version_str}
              : {"filter[platform]"=>platform}))["data"]
abort "no version found for #{platform}" if versions.empty?
v = version_str ? versions.first : versions.find { |x| x.dig("attributes","appStoreState") != "READY_FOR_SALE" } || versions.first
puts "version #{v.dig('attributes','versionString')} (#{platform})#{dry ? ' [dry-run]' : ''}"

locs = ASC.localizations(v["id"])
targets = ASC.locales_arg(opts)
locs = locs.select { |l| targets.include?(l.dig("attributes","locale")) } if targets

locs.each do |l|
  lid = l["id"]; lc = l.dig("attributes","locale")
  sets = ASC.body(rc.get("v1/appStoreVersionLocalizations/#{lid}/appScreenshotSets"))["data"]
  sets.each do |set|
    setid = set["id"]; dt = set.dig("attributes","screenshotDisplayType")
    scs = ASC.body(rc.get("v1/appScreenshotSets/#{setid}/appScreenshots", { limit: 50 }))["data"]
    keep = {}; dupes = []
    scs.each { |s| fn = s.dig("attributes","fileName"); keep[fn] ? dupes << s : keep[fn] = s["id"] }
    if dupes.empty?
      puts "  [#{lc}/#{dt}] #{scs.size} ok"
      next
    end
    puts "  [#{lc}/#{dt}] #{scs.size} → removing #{dupes.size} duplicate(s): #{dupes.map { |s| s.dig('attributes','fileName') }.join(', ')}"
    next if dry
    dupes.each { |s| rc.delete("v1/appScreenshots/#{s['id']}") }
    ordered = keep.keys.sort.map { |fn| keep[fn] }
    rc.patch("v1/appScreenshotSets/#{setid}/relationships/appScreenshots",
             { data: ordered.map { |id| { type: "appScreenshots", id: id } } })
    final = ASC.body(rc.get("v1/appScreenshotSets/#{setid}/appScreenshots", { limit: 50 }))["data"]
    puts "    now: #{final.map { |s| s.dig('attributes','fileName') }.join(', ')}"
  end
end
puts "Done."
