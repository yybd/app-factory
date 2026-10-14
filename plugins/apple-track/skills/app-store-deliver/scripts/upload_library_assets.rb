#!/usr/bin/env ruby
# upload_library_assets.rb — send files to the app's App Asset Library and place them on
# a listing localization: the product page HEADER and SEARCH RESULTS creative assets, and
# the iPhone Duo screenshots that `deliver` has no display type for.
#
# Usage:
#   ruby upload_library_assets.rb <bundle-id> <locale> <file> [<file> …] \
#        [--version 1.1] [--platform IOS] [--kind creative|screenshot] \
#        [--only header|search] [--replace] [--submit] [--frame HH:MM:SS:FF] \
#        [--cpp-loc ID | --ppo-loc ID] [--dry-run]
#
#   <locale>       App Store locale code (he, en-US …) — placements are per localization.
#   <file>         an upload-ready file from the canonical media tree:
#                    <App>/<locale>/creative/*            → --kind creative (inferred)
#                    <App>/<locale>/screenshots-duo-*/*   → --kind screenshot (inferred)
#   --version      the App Store version to place on (default: the editable one).
#   --kind         override the inference. Decides the asset CATEGORY, which can never
#                  be changed after upload: CREATIVE_ASSETS or APP_SCREENSHOTS_AND_PREVIEWS.
#   --only         creative only: place on just the header, or just search results. A
#                  16:9 universal file otherwise goes to both.
#   --replace      delete this localization's existing placement in the same type+group
#                  first. Without it, a full group is reported and skipped.
#   --submit       ALSO send the uploaded assets to App Review on their own (no app
#                  version). That is the way onto a version that is already live — see
#                  the two-step flow in references/asset-library-api.md.
#   --cpp-loc ID   place on a custom product page localization instead of the version.
#   --ppo-loc ID   place on a product page optimization treatment localization.
#   --dry-run      read everything, upload nothing, print the plan.
#
# What it does, in Apple's order (Uploading and managing image assets / Placing assets):
#   1. GET  apps/{id}/assetLibrary                 the library id
#   2. GET  appAssetLibraryRefData                 specs, placement types, groups, limits
#   3. reuse an asset already in the library with the same referenceName and byte size,
#      or POST appAssetLibraryImages|Videos → PUT the parts → PATCH uploaded:true → poll
#      to PREPARE_FOR_SUBMISSION (or APPROVED)
#   4. resolve placements from the PROCESSED specId — never from a hard-coded table —
#      and POST appAssetLibraryPlacements per type × group
#   5. --submit: POST reviewSubmissions + reviewSubmissionItems → PATCH submitted:true
#
# Confirm with the user before running without --dry-run — this writes to App Store
# Connect, and --submit sends work to App Review.

if (ARGV & %w[-h --help]).any?  # the usage needs no gems and no credentials
  puts File.readlines(__FILE__, encoding: "UTF-8").drop(1).take_while { |l| l.start_with?("#") }.map { |l| l.sub(/^# ?/, "") }
  exit 0
end

require_relative "asc_common"
require "net/http"
require "uri"

pos, opts = ASC.parse_args(ARGV)
bundle, locale, *files = pos
abort "usage: upload_library_assets.rb <bundle-id> <locale> <file> [<file> …] [--dry-run]" if bundle.nil? || locale.nil? || files.empty?
files.each { |f| abort "not found: #{f}" unless File.file?(f) }

platform = opts[:platform] || "IOS"
dry      = opts[:"dry-run"] == true
replace  = opts[:replace] == true
submit   = opts[:submit] == true
only     = opts[:only]
abort "--only takes header or search" if only && !%w[header search].include?(only)
$stdout.sync = true

CREATIVE_TYPES = { "header" => "PRODUCT_PAGE_HEADER_ASSET", "search" => "APP_STORE_SEARCH_RESULTS_ASSET" }.freeze
VIDEO_EXT = %w[.mov .m4v .mp4].freeze

def kind_of(path, forced)
  return forced if forced
  # The canonical tree (appstore-media) keeps creative assets in a `creative/` folder.
  # Everything else this script is handed is a screenshot or preview that deliver can't send.
  path.split(File::SEPARATOR).include?("creative") ? "creative" : "screenshot"
end

def dims(path)
  if VIDEO_EXT.include?(File.extname(path).downcase)
    out = `ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "#{path}" 2>/dev/null`
    w, h = out.strip.split(",").map(&:to_i)
  else
    out = `sips -g pixelWidth -g pixelHeight "#{path}" 2>/dev/null`
    w = out[/pixelWidth: (\d+)/, 1].to_i
    h = out[/pixelHeight: (\d+)/, 1].to_i
  end
  [w, h]
end

ASC.token!
rc = ASC.rc
app_id = ASC.app_id(bundle)

# ── 1. the library ────────────────────────────────────────────────────────────
lib = ASC.body(rc.get("v1/apps/#{app_id}/assetLibrary"))["data"]
abort "no asset library for #{bundle} — App Store Connect has not enabled it for this app" unless lib
lib_id = lib["id"]
puts "asset library #{lib_id}"

# ── 2. the reference data: what the store accepts, read now rather than remembered ──
# Apple: "Placement group identifiers and their limits come from the reference data
# rather than an enumeration, so you need to read them at runtime." A table copied into
# this file would be the thing that falls behind when the next device ships.
ref = ASC.body(rc.get("v1/appAssetLibraryRefData"))["data"]
ref = ref.is_a?(Array) ? ref.first : ref
ra = ref["attributes"]
groups = (ra["placementProfileGroups"] || []).to_h { |g| [g["placementProfileGroupId"], g] }
ptypes = (ra["placementTypes"] || []).to_h { |t| [t["placementTypeId"], t] }
specs  = ((ra["imageSpecs"] || []) + (ra["videoSpecs"] || [])).to_h { |s| [s["specId"], s] }
feature_id = opts[:"cpp-loc"] ? "CUSTOM_PRODUCT_PAGES" : opts[:"ppo-loc"] ? "PRODUCT_PAGE_OPTIMIZATIONS" : "APP_STORE_VERSIONS"
feature = (ra["features"] || []).find { |f| f["featureId"] == feature_id }
abort "reference data has no #{feature_id} feature for this app — treat it as unavailable" unless feature

# {[type, group] => maxCount} for the surface being placed on
limits = {}
(feature["placementPolicies"] || []).each do |pol|
  (pol["groupLimits"] || []).each do |gl|
    t = gl["placementType"] || pol["placementType"]
    (gl["groupIds"] || []).each { |g| limits[[t, g]] = gl["maxCount"] }
  end
end

# The spec a file of this size and extension will be matched to. Apple matches it during
# processing and reports the real one as `specId`; this prediction is only for the plan,
# and the processed value is compared against it below.
def predict_specs(specs, w, h, ext)
  specs.values.select do |s|
    d = s["dimensions"] || {}
    d["minWidth"].to_i <= w && w <= d["maxWidth"].to_i &&
      d["minHeight"].to_i <= h && h <= d["maxHeight"].to_i &&
      (s["fileExtensions"] || []).map(&:downcase).include?(ext) &&
      (d["minWidth"] == d["maxWidth"] || ratio_ok?(w, h, s["aspectRatio"]))
  end
end

# A range spec is a box, and a box is not a shape: a 21:9 header at 3840 wide sits inside
# the 3:2 search box and was planned onto search results until
# the ratio was checked too. Only for RANGE specs: an exact spec is already a shape, and
# Apple labels some exact ones with a ratio rounded far past 1% (the Duo inner display,
# 2007×2853, is not any of the ratios the catalog names).
def ratio_ok?(w, h, ratio)
  return true if ratio.nil? || !ratio.include?(":")
  a, b = ratio.split(":").map(&:to_f)
  return true if a.zero? || b.zero?
  ((w.to_f / h) - (a / b)).abs <= 0.01 * (a / b)
end

# A version's platform (IOS, MAC_OS …) against the STORE a placement group belongs to.
# The reference data names stores, not platforms — IPHONE_APP_STORE, IPAD_APP_STORE, and
# ANY for the header and search groups, which one asset serves on iPhone and iPad alike.
# Comparing the two directly matched nothing and planned no placements at all (measured
# on the first run against a live library).
def store_platforms(platform)
  { "IOS"      => %w[IPHONE_APP_STORE IPAD_APP_STORE ANY],
    "MAC_OS"   => %w[MAC_APP_STORE ANY],
    "TV_OS"    => %w[TV_APP_STORE ANY],
    "VISION_OS" => %w[VISION_PRO_APP_STORE ANY] }.fetch(platform, ["ANY"])
end

# Every (placement type, group) on this platform that accepts the spec and the category.
def resolve(spec_id, category, wanted_types, ptypes, groups, limits, platform)
  out = []
  wanted_types.each do |t|
    pt = ptypes[t] or next
    next unless (pt["acceptsAssetCategories"] || []).include?(category)
    (pt["specMappings"] || []).each do |m|
      next unless (m["specs"] || []).include?(spec_id)
      g = groups[m["placementGroupId"]]
      next if g && g["platform"] && !store_platforms(platform).include?(g["platform"])
      next unless limits.key?([t, m["placementGroupId"]])   # not offered on this surface
      out << [t, m["placementGroupId"]]
    end
  end
  out.uniq
end

# ── the surface: a version localization unless a CPP / PPO localization was named ──
surface_rel, surface_type, surface_id =
  if opts[:"cpp-loc"]
    ["appCustomProductPageLocalization", "appCustomProductPageLocalizations", opts[:"cpp-loc"]]
  elsif opts[:"ppo-loc"]
    ["appStoreVersionExperimentTreatmentLocalization", "appStoreVersionExperimentTreatmentLocalizations", opts[:"ppo-loc"]]
  else
    vs = ASC.body(rc.get("v1/apps/#{app_id}/appStoreVersions",
           opts[:version] ? { "filter[platform]" => platform, "filter[versionString]" => opts[:version] }
                          : { "filter[platform]" => platform }))["data"]
    abort "no #{platform} version found" if vs.empty?
    v = opts[:version] ? vs.first : (vs.find { |x| x.dig("attributes", "appStoreState") != "READY_FOR_SALE" } || vs.first)
    state = v.dig("attributes", "appStoreState")
    puts "version #{v.dig('attributes', 'versionString')} (#{platform}) — #{state}"
    if %w[WAITING_FOR_REVIEW IN_REVIEW PENDING_APPLE_RELEASE].include?(state)
      abort "✗ the version is #{state}: its metadata is frozen. Placing now would pull it out of review."
    end
    loc = ASC.localizations(v["id"]).find { |l| l.dig("attributes", "locale") == locale }
    abort "no #{locale} localization on that version" unless loc
    ["appStoreVersionLocalization", "appStoreVersionLocalizations", loc["id"]]
  end
existing = ASC.body(rc.get("v1/#{surface_type}/#{surface_id}/placements", { "limit" => 200 }))["data"] || []
puts "#{surface_rel} #{surface_id}: #{existing.size} placement(s) already there"

def upload_parts(path, ops)
  bytes = File.binread(path)
  ops.each_with_index do |op, i|
    uri = URI(op["url"])
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = (uri.scheme == "https")
    http.read_timeout = 300
    req = Net::HTTPGenericRequest.new(op["method"], true, true, uri.request_uri)
    (op["requestHeaders"] || []).each { |hdr| req[hdr["name"]] = hdr["value"] }
    req.body = bytes[op["offset"], op["length"]]
    resp = http.request(req)
    abort "upload part #{i + 1} failed: #{resp.code} #{resp.body}" unless resp.code.to_i.between?(200, 299)
  end
  puts "  uploaded #{ops.size} part(s)"
end

# Poll to a placeable state. The asset-delivery poll throws transient 500s often enough
# that treating one as fatal fails an upload that succeeded (see SKILL.md, Gotchas).
def wait_processed(rc, res_type, id)
  90.times do
    begin
      a = ASC.body(rc.get("v1/#{res_type}/#{id}"))["data"]["attributes"]
      case a["state"]
      when "PREPARE_FOR_SUBMISSION", "READY_FOR_REVIEW", "WAITING_FOR_REVIEW", "IN_REVIEW", "ACCEPTED", "APPROVED"
        return a
      when "FAILED", "REJECTED"
        abort "  ✗ #{a['state']}: #{a['stateDetails'].inspect}"
      end
    rescue StandardError => e
      puts "  (poll: #{e.class} — retrying)"
    end
    sleep 4
  end
  abort "  ✗ timed out waiting for processing"
end

submitted = []
files.each do |path|
  name = File.basename(path)
  ext = File.extname(path).downcase
  video = VIDEO_EXT.include?(ext)
  kind = kind_of(path, opts[:kind])
  category = kind == "creative" ? "CREATIVE_ASSETS" : "APP_SCREENSHOTS_AND_PREVIEWS"
  wanted = if kind == "creative"
             only ? [CREATIVE_TYPES[only]] : CREATIVE_TYPES.values
           else
             [video ? "APP_PREVIEW" : "APP_SCREENSHOT"]
           end
  res_type = video ? "appAssetLibraryVideos" : "appAssetLibraryImages"
  ref_name = "#{locale}/#{name}"
  w, h = dims(path)
  puts "\n#{name}  #{w}x#{h}  #{category}"

  guesses = predict_specs(specs, w, h, ext)
  if guesses.empty?
    puts "  ✗ no specification in the reference data accepts #{w}x#{h}#{ext} — not uploaded"
    next
  end
  plan = guesses.flat_map { |s| resolve(s["specId"], category, wanted, ptypes, groups, limits, platform) }.uniq
  if plan.empty?
    puts "  ✗ #{w}x#{h} matches #{guesses.map { |s| s['shortName'] }.join(', ')}, but no #{wanted.join('/')} " \
         "group on #{platform} / #{feature_id} takes it — not uploaded"
    next
  end
  plan.each { |t, g| puts "  plan: #{t} × #{g}  (limit #{limits[[t, g]]})" }

  # 3. reuse before uploading — the library exists so that a file goes up once
  same = ASC.body(rc.get("v1/appAssetLibraries/#{lib_id}/#{video ? 'videos' : 'images'}",
                         { "filter[referenceName]" => ref_name }))["data"] || []
  reuse = same.find { |a| a.dig("attributes", "fileSize") == File.size(path) &&
                          !%w[FAILED ARCHIVED REJECTED AWAITING_UPLOAD].include?(a.dig("attributes", "state")) }
  if dry
    puts reuse ? "  would reuse #{reuse['id']} (#{reuse.dig('attributes', 'state')})" : "  would upload #{File.size(path)} bytes"
    next
  end

  if reuse
    asset_id = reuse["id"]
    attrs = reuse["attributes"]
    puts "  reusing #{asset_id} — #{attrs['state']}"
  else
    body = { data: { type: res_type,
                     attributes: { fileName: name, fileSize: File.size(path), category: category,
                                   referenceName: ref_name },
                     relationships: { assetLibrary: { data: { type: "appAssetLibraries", id: lib_id } } } } }
    body[:data][:attributes][:previewFrameTimeCode] = opts[:frame] if video && opts[:frame]
    r = ASC.body(rc.post("v1/#{res_type}", body))["data"]
    asset_id = r["id"]
    upload_parts(path, r.dig("attributes", "uploadOperations") || [])
    # Commit takes `uploaded` alone — the asset library has no checksum, and sending
    # `sourceFileChecksum` here is rejected.
    rc.patch("v1/#{res_type}/#{asset_id}", { data: { type: res_type, id: asset_id, attributes: { uploaded: true } } })
    attrs = wait_processed(rc, res_type, asset_id)
    puts "  processed #{asset_id} — #{attrs['state']}"
  end

  # 4. place, from the spec Apple actually matched
  spec_id = attrs["specId"]
  if spec_id && !guesses.map { |s| s["specId"] }.include?(spec_id)
    puts "  ⚠ Apple matched spec #{spec_id}, not the predicted one — placing by Apple's"
  end
  targets = spec_id ? resolve(spec_id, category, wanted, ptypes, groups, limits, platform) : plan
  targets.each do |t, g|
    here = existing.select { |p| p.dig("attributes", "placementType") == t && p.dig("attributes", "placementGroup") == g }
    if here.size >= limits[[t, g]].to_i
      unless replace
        puts "  · #{t} × #{g}: full (#{here.size}/#{limits[[t, g]]}) — skipped; --replace to swap"
        next
      end
      here.each { |p| rc.delete("v1/appAssetLibraryPlacements/#{p['id']}") }
      puts "  · removed #{here.size} placement(s) from #{t} × #{g}"
    end
    begin
      rc.post("v1/appAssetLibraryPlacements",
              { data: { type: "appAssetLibraryPlacements",
                        attributes: { placementType: t, placementGroup: g },
                        relationships: { (video ? :video : :image) => { data: { type: res_type, id: asset_id } },
                                         surface_rel.to_sym => { data: { type: surface_type, id: surface_id } } } } })
      puts "  ✓ placed: #{t} × #{g}"
    rescue StandardError => e
      # The parent is already approved: placing needs an APPROVED asset. That is the
      # two-step flow — --submit now, re-run this command after approval.
      puts "  ✗ #{t} × #{g}: #{e.message.lines.first&.strip}"
    end
  end
  submitted << [res_type == "appAssetLibraryImages" ? :appAssetLibraryImage : :appAssetLibraryVideo, res_type, asset_id] \
    if submit && !%w[APPROVED IN_REVIEW WAITING_FOR_REVIEW].include?(attrs["state"])
end

# ── 5. standalone review: assets approved ahead of any version ────────────────
if submit && !dry
  if submitted.empty?
    puts "\nnothing to submit — every asset is already approved or in review"
  else
    sub = ASC.body(rc.post("v1/reviewSubmissions",
            { data: { type: "reviewSubmissions", attributes: { platform: platform },
                      relationships: { app: { data: { type: "apps", id: app_id } } } } }))["data"]
    submitted.each do |rel, type, id|
      rc.post("v1/reviewSubmissionItems",
              { data: { type: "reviewSubmissionItems",
                        relationships: { reviewSubmission: { data: { type: "reviewSubmissions", id: sub["id"] } },
                                         rel => { data: { type: type, id: id } } } } })
    end
    rc.patch("v1/reviewSubmissions/#{sub['id']}",
             { data: { type: "reviewSubmissions", id: sub["id"], attributes: { submitted: true } } })
    puts "\nsubmitted #{submitted.size} asset(s) for review — submission #{sub['id']}"
  end
end
puts dry ? "\ndry run — nothing was uploaded" : "\ndone"
