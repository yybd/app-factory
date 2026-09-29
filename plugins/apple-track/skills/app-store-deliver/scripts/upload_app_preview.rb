#!/usr/bin/env ruby
# upload_app_preview.rb — upload an App Preview video to App Store Connect for one
# or more locales. `fastlane deliver` (through 2.234) does NOT upload App Preview
# videos from the screenshots folder — it silently processes only stills — so this
# drives the AppPreview reserve→upload→commit flow directly via the token API.
#
# Usage:
#   ruby upload_app_preview.rb <bundle-id> <video-path> \
#        [--platform MAC_OS] [--version 2.0] [--locales en-US,en-GB] \
#        [--frame 00:00:05:00] [--preview-type DESKTOP] [--force]
#
#   <video-path>     one video used for every listed locale (Mac App Preview = 1920x1080,
#                    15–30s, H.264/HEVC). Pass per-locale by running once per locale.
#   --platform       MAC_OS | IOS | TV_OS         (default MAC_OS)
#   --version        marketing version (default: the single editable version found)
#   --locales        default: all localizations on the version
#   --preview-type   DESKTOP for Mac; IPHONE_67 etc. for iOS (default DESKTOP)
#   --frame          poster still time code HH:MM:SS:FF (default 00:00:05:00)
#   --force          replace an existing preview in the set (default: skip if present)
#
# Confirm with the user before running — this writes to App Store Connect. Video
# processing is polled in-process (~1–3 min per clip).

require_relative "asc_common"

pos, opts = ASC.parse_args(ARGV)
bundle, video = pos
abort "usage: upload_app_preview.rb <bundle-id> <video-path> [--locales a,b] [--platform MAC_OS]" unless bundle && video
abort "video not found: #{video}" unless File.exist?(video)

platform     = opts[:platform] || "MAC_OS"
version_str  = opts[:version]
preview_type = opts[:"preview-type"] || opts[:previewtype] || "DESKTOP"
frame        = opts[:frame] || "00:00:05:00"
force        = ARGV.include?("--force")
$stdout.sync = true

ASC.token!
rc = ASC.rc
app_id = ASC.app_id(bundle)

versions = ASC.body(rc.get("v1/apps/#{app_id}/appStoreVersions",
  version_str ? {"filter[platform]"=>platform, "filter[versionString]"=>version_str}
              : {"filter[platform]"=>platform}))["data"]
abort "no editable version for #{platform}" if versions.empty?
v = version_str ? versions.first : versions.find { |x| x.dig("attributes","appStoreState") != "READY_FOR_SALE" } || versions.first
puts "version #{v.dig('attributes','versionString')} (#{platform})"

locs = ASC.localizations(v["id"])
targets = ASC.locales_arg(opts)
locs = locs.select { |l| targets.include?(l.dig("attributes","locale")) } if targets

locs.each do |l|
  lid = l["id"]; lc = l.dig("attributes","locale")
  sets = Spaceship::ConnectAPI.get_app_preview_sets(app_store_version_localization_id: lid, includes: "appPreviews").to_models
  set = sets.find { |s| s.preview_type == preview_type }
  set ||= Spaceship::ConnectAPI.post_app_preview_set(app_store_version_localization_id: lid,
            attributes: { previewType: preview_type }).first
  full = Spaceship::ConnectAPI::AppPreviewSet.get(app_preview_set_id: set.id)
  if full.app_previews && full.app_previews.any?
    if force
      full.app_previews.each { |p| p.delete! }
      puts "[#{lc}] removed #{full.app_previews.size} existing preview(s)"
    else
      puts "[#{lc}] preview already present — skipping (use --force to replace)"
      next
    end
  end
  puts "[#{lc}] uploading + processing video..."
  preview = Spaceship::ConnectAPI::AppPreview.create(app_preview_set_id: set.id, path: video,
              wait_for_processing: true, frame_time_code: frame)
  puts "[#{lc}] DONE preview id=#{preview.id}"
end
puts "App Preview upload complete."
