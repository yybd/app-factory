#!/usr/bin/env ruby
# upload_iap_screenshot.rb — upload the App Review screenshot for an In-App
# Purchase. There is no Spaceship model and `fastlane deliver` does not manage
# IAPs, so this drives the raw reserve -> upload -> commit flow on
# `inAppPurchaseAppStoreReviewScreenshots` via the token API.
#
# Usage:
#   ruby upload_iap_screenshot.rb <product-id> <bundle-id> <image-path> [--force]
#
#   --force   replace a screenshot that is already attached (default: skip)
#
# The image MUST match one of the APP's screenshot specifications and carry no
# alpha channel — an arbitrary crop of the paywall is rejected. See
# app-store-metadata's SKILL.md for the legal sizes per platform. One screenshot
# serves every platform: Universal Purchase means one shared IAP record.
#
# Confirm with the user before running — this writes to App Store Connect.

require_relative "asc_common"
require "digest"
require "net/http"
require "uri"

pos, opts = ASC.parse_args(ARGV)
pid, bundle, image = pos
abort "usage: upload_iap_screenshot.rb <product-id> <bundle-id> <image-path> [--force]" unless pid && bundle && image
abort "image not found: #{image}" unless File.exist?(image)
force = ARGV.include?("--force")
$stdout.sync = true

# Guard the two mistakes this asset actually fails on, before touching the API.
# The accepted sizes come from `shared/apple-specs.json` at the track root — the one
# place they are written — rather than a fourth copy here. Both orientations count.
SPECS = JSON.parse(File.read(File.expand_path("../../../shared/apple-specs.json", __dir__)))
LEGAL = SPECS["screenshots"].values.flatten.flat_map { |fam| fam["sizes"] }
             .flat_map { |(w, h)| [[w, h], [h, w]] }.uniq.freeze
png = File.binread(image, 26)
abort "not a PNG: #{image}" unless png[0, 8] == "\x89PNG\r\n\x1a\n".b
w = png[16, 4].unpack1("N")
h = png[20, 4].unpack1("N")
alpha = [4, 6].include?(png[25].ord)
abort "#{w}x#{h} is not a legal App Store screenshot size — see app-store-metadata" unless LEGAL.include?([w, h])
abort "image has an alpha channel; App Store Connect rejects transparency" if alpha
puts "image #{w}x#{h}, no alpha, #{File.size(image)} bytes"

ASC.token!
rc = ASC.rc
app_id = ASC.app_id(bundle)

rec = ASC.body(rc.get("v1/apps/#{app_id}/inAppPurchasesV2", { limit: 200 }))["data"]
        .find { |p| p.dig("attributes", "productId") == pid }
abort "IAP #{pid} not found in ASC" unless rec
iid = rec["id"]
puts "IAP #{pid} id=#{iid} state=#{rec.dig('attributes', 'state')}"

existing = ASC.body(rc.get("v2/inAppPurchases/#{iid}/appStoreReviewScreenshot"))["data"] rescue nil
if existing
  if force
    rc.delete("v1/inAppPurchaseAppStoreReviewScreenshots/#{existing['id']}")
    puts "  deleted existing screenshot (#{existing.dig('attributes', 'fileSize')} bytes)"
  else
    abort "  a screenshot is already attached — pass --force to replace it"
  end
end

# 1. reserve
res = ASC.body(rc.post("v1/inAppPurchaseAppStoreReviewScreenshots",
  { data: { type: "inAppPurchaseAppStoreReviewScreenshots",
            attributes: { fileName: File.basename(image), fileSize: File.size(image) },
            relationships: { inAppPurchaseV2: { data: { type: "inAppPurchases", id: iid } } } } }))
sid  = res.dig("data", "id")
ops  = res.dig("data", "attributes", "uploadOperations") || []
abort "no uploadOperations returned" if ops.empty?
puts "  reserved id=#{sid}, #{ops.size} upload operation(s)"

# 2. upload the bytes exactly as each operation dictates
bytes = File.binread(image)
ops.each_with_index do |op, i|
  uri = URI(op["url"])
  http = Net::HTTP.new(uri.host, uri.port)
  http.use_ssl = (uri.scheme == "https")
  req = Net::HTTPGenericRequest.new(op["method"], true, true, uri.request_uri)
  (op["requestHeaders"] || []).each { |hdr| req[hdr["name"]] = hdr["value"] }
  req.body = bytes[op["offset"], op["length"]]
  resp = http.request(req)
  abort "upload part #{i + 1} failed: #{resp.code} #{resp.body}" unless resp.code.to_i.between?(200, 299)
  puts "  uploaded part #{i + 1}/#{ops.size}"
end

# 3. commit with the checksum ASC verifies against
rc.patch("v1/inAppPurchaseAppStoreReviewScreenshots/#{sid}",
  { data: { type: "inAppPurchaseAppStoreReviewScreenshots", id: sid,
            attributes: { uploaded: true, sourceFileChecksum: Digest::MD5.hexdigest(bytes) } } })

# 4. poll — a commit that "succeeds" can still fail asset delivery
# ASC returns a transient 500 on this poll often enough that treating it as fatal
# aborts an upload that already succeeded — the commit above lands, the poll blows
# up, and the caller is told it failed. Retry the poll instead. (Measured.)
20.times do
  begin
    a = ASC.body(rc.get("v1/inAppPurchaseAppStoreReviewScreenshots/#{sid}")).dig("data", "attributes")
    st = a.dig("assetDeliveryState", "state")
    if st == "COMPLETE"
      puts "screenshot COMPLETE (checksum #{a['sourceFileChecksum']})"
      exit 0
    elsif st == "FAILED"
      abort "asset delivery FAILED: #{a.dig('assetDeliveryState', 'errors')}"
    end
  rescue StandardError => e
    puts "  (poll: #{e.class} — retrying)"
  end
  sleep 3
end
abort "timed out waiting for asset delivery"
