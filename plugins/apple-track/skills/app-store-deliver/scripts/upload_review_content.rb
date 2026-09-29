#!/usr/bin/env ruby
# upload_review_content.rb — deliver everything App Review reads before it opens
# the app: the contact details, the demo account, the review notes, and the
# ATTACHMENT (a demonstration video or PDF).
#
# `deliver` handles the contact/notes fields, but it CANNOT upload the attachment
# — there is no Spaceship model for it — so a demo video recorded for a reviewer
# has no way to reach ASC without this. That gap is why the script exists.
#
# Usage:
#   ruby upload_review_content.rb <bundle-id> <version> [options]
#
#   --slug NAME        hub folder (default: derived from the bundle id's last part)
#   --platform P       MAC_OS | IOS  (default MAC_OS)
#   --attachment PATH  file to attach; default: the first match of
#                        <hub>/<slug>/media/apple/review/*.{mp4,mov,pdf}
#   --no-attachment    push the text fields only
#   --force            replace an attachment that is already present
#   --dry-run          show what would change, write nothing
#
# Text fields are read from the hub, the same tree `deliver` uses:
#   <hub>/<slug>/store/apple/metadata/review_information/
#     first_name.txt last_name.txt email_address.txt phone_number.txt
#     demo_user.txt demo_password.txt notes.txt
# An empty demo_user/demo_password means "no demo account required".
#
# Confirm with the user before running — this writes to App Store Connect.

require_relative "asc_common"
require "digest"
require "net/http"
require "uri"

pos, _ = ASC.parse_args(ARGV)
bundle, version = pos
abort "usage: upload_review_content.rb <bundle-id> <version> [--slug NAME] [--platform MAC_OS|IOS]" unless bundle && version

def flag(name, default = nil)
  i = ARGV.index(name)
  i && ARGV[i + 1] && !ARGV[i + 1].start_with?("--") ? ARGV[i + 1] : default
end
slug     = flag("--slug", bundle.split(".").last)
platform = flag("--platform", "MAC_OS")
dry      = ARGV.include?("--dry-run")
force    = ARGV.include?("--force")
skip_att = ARGV.include?("--no-attachment")
tree     = ASC.tree(slug, hub: flag("--hub"), repo: flag("--repo"))   # hub, or the repo's fastlane/
$stdout.sync = true

info = tree[:review_info]
abort "no review_information in the #{tree[:name]} at: #{info}" unless Dir.exist?(info)
read = ->(f) { p = File.join(info, "#{f}.txt"); File.exist?(p) ? File.read(p, encoding: "UTF-8").strip : "" }

attachment = flag("--attachment")
if attachment.nil? && !skip_att
  attachment = Dir[File.join(tree[:review_media], "*.{mp4,mov,pdf}")].sort.first
end

ASC.token!
rc = ASC.rc
app_id = ASC.app_id(bundle)

ver = ASC.body(rc.get("v1/apps/#{app_id}/appStoreVersions",
                      { "filter[platform]" => platform, limit: 20 }))["data"]
        .find { |v| v.dig("attributes", "versionString") == version }
abort "version #{version} (#{platform}) not found for #{bundle}" unless ver
state = ver.dig("attributes", "appStoreState") || ver.dig("attributes", "appVersionState")
puts "app #{bundle}  version #{version} [#{platform}]  state=#{state}"
if %w[WAITING_FOR_REVIEW IN_REVIEW PENDING_APPLE_RELEASE].include?(state)
  abort "  ✗ metadata is FROZEN in this state — uploading would pull the build out of review."
end

# ---------------------------------------------------------------- review detail
detail = begin
  ASC.body(rc.get("v1/appStoreVersions/#{ver['id']}/appStoreReviewDetail"))["data"]
rescue StandardError
  nil
end

demo_user = read.("demo_user")
demo_pass = read.("demo_password")
attrs = {
  contactFirstName: read.("first_name"), contactLastName: read.("last_name"),
  contactPhone: read.("phone_number"), contactEmail: read.("email_address"),
  notes: read.("notes"),
  demoAccountRequired: !(demo_user.empty? && demo_pass.empty?)
}
attrs[:demoAccountName]     = demo_user unless demo_user.empty?
attrs[:demoAccountPassword] = demo_pass unless demo_pass.empty?
attrs.reject! { |_, v| v.is_a?(String) && v.empty? }

puts "  contact : #{attrs[:contactFirstName]} #{attrs[:contactLastName]} · #{attrs[:contactEmail]}"
puts "  demo    : #{attrs[:demoAccountRequired] ? attrs[:demoAccountName] : 'not required'}"
puts "  notes   : #{attrs[:notes].to_s.length} chars"

if dry
  puts "  [dry-run] would #{detail ? 'PATCH' : 'POST'} the review detail"
else
  if detail
    rc.patch("v1/appStoreReviewDetails/#{detail['id']}",
             { data: { type: "appStoreReviewDetails", id: detail["id"], attributes: attrs } })
    puts "  ✓ review detail updated"
  else
    detail = ASC.body(rc.post("v1/appStoreReviewDetails",
      { data: { type: "appStoreReviewDetails", attributes: attrs,
                relationships: { appStoreVersion: { data: { type: "appStoreVersions", id: ver["id"] } } } } }))["data"]
    puts "  ✓ review detail created"
  end
end

# ------------------------------------------------------------------ attachment
exit 0 if skip_att
if attachment.nil?
  puts "  attachment: none found under #{slug}/media/apple/review/ — skipping"
  exit 0
end
abort "attachment not found: #{attachment}" unless File.exist?(attachment)
size = File.size(attachment)
puts "  attachment: #{File.basename(attachment)} (#{(size / 1024.0 / 1024).round(1)} MB)"
abort "  ✗ over Apple's 500 MB attachment limit" if size > 500 * 1024 * 1024

existing = begin
  ASC.body(rc.get("v1/appStoreReviewDetails/#{detail['id']}/appStoreReviewAttachments"))["data"] || []
rescue StandardError
  []
end
unless existing.empty?
  if force
    existing.each { |a| rc.delete("v1/appStoreReviewAttachments/#{a['id']}") unless dry }
    puts "  removed #{existing.size} existing attachment(s)"
  else
    puts "  ✗ #{existing.size} attachment(s) already present — pass --force to replace"
    exit 0
  end
end

if dry
  puts "  [dry-run] would upload #{File.basename(attachment)}"
  exit 0
end

res = ASC.body(rc.post("v1/appStoreReviewAttachments",
  { data: { type: "appStoreReviewAttachments",
            attributes: { fileName: File.basename(attachment), fileSize: size },
            relationships: { appStoreReviewDetail: { data: { type: "appStoreReviewDetails", id: detail["id"] } } } } }))
aid = res.dig("data", "id")
ops = res.dig("data", "attributes", "uploadOperations") || []
abort "no uploadOperations returned" if ops.empty?
puts "  reserved id=#{aid}, #{ops.size} upload operation(s)"

bytes = File.binread(attachment)
ops.each_with_index do |op, i|
  uri = URI(op["url"])
  http = Net::HTTP.new(uri.host, uri.port)
  http.use_ssl = (uri.scheme == "https")
  http.read_timeout = 300
  req = Net::HTTPGenericRequest.new(op["method"], true, true, uri.request_uri)
  (op["requestHeaders"] || []).each { |h| req[h["name"]] = h["value"] }
  req.body = bytes[op["offset"], op["length"]]
  resp = http.request(req)
  abort "upload part #{i + 1} failed: #{resp.code} #{resp.body}" unless resp.code.to_i.between?(200, 299)
  puts "  uploaded part #{i + 1}/#{ops.size}"
end

rc.patch("v1/appStoreReviewAttachments/#{aid}",
  { data: { type: "appStoreReviewAttachments", id: aid,
            attributes: { uploaded: true, sourceFileChecksum: Digest::MD5.hexdigest(bytes) } } })

# Poll for delivery. ASC returns a transient 500 here often enough that treating
# it as fatal fails an upload that actually succeeded — retry instead.
30.times do
  begin
    a = ASC.body(rc.get("v1/appStoreReviewAttachments/#{aid}")).dig("data", "attributes")
    st = a.dig("assetDeliveryState", "state")
    if st == "COMPLETE"
      puts "attachment COMPLETE — visible in App Review Information"
      exit 0
    elsif st == "FAILED"
      abort "asset delivery FAILED: #{a.dig('assetDeliveryState', 'errors')}"
    end
  rescue StandardError => e
    puts "  (poll: #{e.class} — retrying)"
  end
  sleep 4
end
puts "still processing — check App Store Connect in a minute"
