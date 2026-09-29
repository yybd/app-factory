#!/usr/bin/env ruby
# provision_iap.rb — create or update an In-App Purchase end to end, in every
# locale the hub holds.
#
# `deliver_iap.rb` updates the per-locale text of an IAP that already exists and
# aborts otherwise. This one owns the whole lifecycle, so a new Pro product can go
# from nothing to READY_TO_SUBMIT in one command:
#
#   create → localizations (all locales) → review note → price → availability → screenshot
#
# Every step is idempotent and reports "already set" rather than rewriting, so it
# is safe to re-run after a partial failure.
#
# Usage:
#   ruby provision_iap.rb <slug> <product-id> <bundle-id> [options]
#
#   --locales a,b,c     restrict to these (default: every locale dir in the hub)
#   --type TYPE         NON_CONSUMABLE (default) | CONSUMABLE | NON_RENEWING_SUBSCRIPTION
#   --territory T       base territory for pricing (default USA)
#   --mirror-from PID   copy the territory availability from an existing product
#                       (its 175-territory set), instead of every territory Apple lists
#   --no-price          leave pricing alone
#   --no-screenshot     skip the reviewer screenshot
#   --dry-run           report what would change, write nothing
#
# Hub layout it reads (authored by app-store-metadata):
#   <hub>/<slug>/store/apple/iap/<product-id>/
#     product.txt              # reference name · type   (first line; "·" separated)
#     price.txt                # customer price, e.g. "19.99 USD (tier 10177 …)"
#     <locale>/display_name.txt   ≤30
#     <locale>/description.txt    ≤45
#     review/notes.txt
#     review/screenshot.png
#
# Confirm with the user before running — this writes to App Store Connect.

require_relative "asc_common"

pos, _ = ASC.parse_args(ARGV)
slug, pid, bundle = pos
abort "usage: provision_iap.rb <slug> <product-id> <bundle-id> [--locales a,b]" unless slug && pid && bundle

def flag(n, d = nil)
  i = ARGV.index(n); i && ARGV[i + 1] && !ARGV[i + 1].start_with?("--") ? ARGV[i + 1] : d
end
dry       = ARGV.include?("--dry-run")
type      = flag("--type", "NON_CONSUMABLE")
territory = flag("--territory", "USA")
mirror    = flag("--mirror-from")
no_price  = ARGV.include?("--no-price")
no_shot   = ARGV.include?("--no-screenshot")
tree      = ASC.tree(slug, hub: flag("--hub"), repo: flag("--repo"))   # hub, or the repo's fastlane/
root      = tree[:iap].call(pid)
abort "no IAP tree in the #{tree[:name]} at: #{root}" unless Dir.exist?(root)
$stdout.sync = true

rd = ->(p) { File.exist?(p) ? File.read(p, encoding: "UTF-8").strip : nil }
locales = (flag("--locales")&.split(",") ||
           Dir.children(root).select { |d| File.directory?(File.join(root, d)) && d != "review" }).sort

ASC.token!
rc = ASC.rc
app_id = ASC.app_id(bundle)

# ---------------------------------------------------------------- 1. create/find
rec = ASC.body(rc.get("v1/apps/#{app_id}/inAppPurchasesV2", { limit: 200 }))["data"]
        .find { |p| p.dig("attributes", "productId") == pid }
if rec
  iid = rec["id"]
  puts "IAP #{pid} id=#{iid} state=#{rec.dig('attributes', 'state')}"
else
  ref = (rd.(File.join(root, "product.txt")) || pid).split("·").first.to_s.strip
  ref = pid if ref.empty?
  abort "reference name is #{ref.length} chars (max 64)" if ref.length > 64
  puts "IAP #{pid} does not exist — creating as #{ref.inspect} (#{type})"
  if dry
    puts "  [dry-run] stopping: everything below needs the created product"
    exit 0
  end
  created = ASC.body(rc.post("v2/inAppPurchases",
    { data: { type: "inAppPurchases",
              attributes: { name: ref, productId: pid, inAppPurchaseType: type, familySharable: false },
              relationships: { app: { data: { type: "apps", id: app_id } } } } }))
  iid = created.dig("data", "id")
  puts "  ✓ created id=#{iid}"
end

iap  = ASC.body(rc.get("v2/inAppPurchases/#{iid}"))
rel  = ->(n) { iap.dig("data", "relationships", n, "links", "related")&.sub("https://api.appstoreconnect.apple.com/", "") }

# ------------------------------------------------------------- 2. localizations
have = (ASC.body(rc.get(rel.("inAppPurchaseLocalizations")))["data"] || [])
         .to_h { |l| [l.dig("attributes", "locale"), l] }
locales.each do |loc|
  name = rd.(File.join(root, loc, "display_name.txt"))
  desc = rd.(File.join(root, loc, "description.txt"))
  next puts("  [#{loc}] no display_name.txt — skipped") unless name
  if name.length > 30 || (desc && desc.length > 45)
    abort "  [#{loc}] over limit — display_name #{name.length}/30, description #{desc&.length}/45"
  end
  cur = have[loc]
  if cur && cur.dig("attributes", "name") == name && cur.dig("attributes", "description") == desc
    puts "  [#{loc}] already set"
  elsif dry
    puts "  [#{loc}] [dry-run] would #{cur ? 'update' : 'create'}"
  elsif cur
    rc.patch("v1/inAppPurchaseLocalizations/#{cur['id']}",
             { data: { type: "inAppPurchaseLocalizations", id: cur["id"],
                       attributes: { name: name, description: desc }.compact } })
    puts "  [#{loc}] updated"
  else
    rc.post("v1/inAppPurchaseLocalizations",
            { data: { type: "inAppPurchaseLocalizations",
                      attributes: { locale: loc, name: name, description: desc }.compact,
                      relationships: { inAppPurchaseV2: { data: { type: "inAppPurchases", id: iid } } } } })
    puts "  [#{loc}] created"
  end
end

# ---------------------------------------------------------------- 3. review note
note = rd.(File.join(root, "review", "notes.txt"))
if note && !note.empty?
  abort "review note is #{note.length} chars (max 4000)" if note.length > 4000
  if iap.dig("data", "attributes", "reviewNote") == note
    puts "  review note already set"
  elsif dry
    puts "  [dry-run] would set the review note (#{note.length} chars)"
  else
    rc.patch("v2/inAppPurchases/#{iid}",
             { data: { type: "inAppPurchases", id: iid, attributes: { reviewNote: note } } })
    puts "  ✓ review note set (#{note.length} chars)"
  end
end

# --------------------------------------------------------------------- 4. price
unless no_price
  sched = begin ASC.body(rc.get(rel.("iapPriceSchedule")))["data"] rescue nil end
  if sched
    puts "  price schedule already exists — left alone"
  else
    want = rd.(File.join(root, "price.txt")).to_s[/\d+\.\d{2}/]
    if want.nil?
      puts "  no price in price.txt — skipping"
    elsif dry
      puts "  [dry-run] would set #{want} (#{territory})"
    else
      pts = ASC.body(rc.get("v2/inAppPurchases/#{iid}/pricePoints",
                            { "filter[territory]" => territory, limit: 200 }))["data"] || []
      pp = pts.find { |p| p.dig("attributes", "customerPrice") == want }
      abort "  no #{territory} price point at #{want}" unless pp
      rc.post("v1/inAppPurchasePriceSchedules",
        { data: { type: "inAppPurchasePriceSchedules",
                  relationships: {
                    inAppPurchase: { data: { type: "inAppPurchases", id: iid } },
                    baseTerritory: { data: { type: "territories", id: territory } },
                    manualPrices:  { data: [{ type: "inAppPurchasePrices", id: "${p1}" }] } } },
          included: [{ type: "inAppPurchasePrices", id: "${p1}", attributes: { startDate: nil },
                       relationships: {
                         inAppPurchaseV2:         { data: { type: "inAppPurchases", id: iid } },
                         inAppPurchasePricePoint: { data: { type: "inAppPurchasePricePoints", id: pp["id"] } } } }] })
      puts "  ✓ price #{want} #{territory} (proceeds #{pp.dig('attributes', 'proceeds')})"
    end
  end
end

# -------------------------------------------------------------- 5. availability
avail = begin ASC.body(rc.get(rel.("inAppPurchaseAvailability")))["data"] rescue nil end
if avail
  puts "  availability already set"
elsif dry
  puts "  [dry-run] would set availability"
else
  terr =
    if mirror
      src = ASC.body(rc.get("v1/apps/#{app_id}/inAppPurchasesV2", { limit: 200 }))["data"]
              .find { |p| p.dig("attributes", "productId") == mirror }
      abort "  --mirror-from #{mirror} not found" unless src
      sa = ASC.body(rc.get("v2/inAppPurchases/#{src['id']}/inAppPurchaseAvailability")).dig("data", "id")
      ASC.body(rc.get("v1/inAppPurchaseAvailabilities/#{sa}/availableTerritories", { limit: 200 }))["data"]
    else
      ASC.body(rc.get("v1/territories", { limit: 200 }))["data"]
    end
  rc.post("v1/inAppPurchaseAvailabilities",
    { data: { type: "inAppPurchaseAvailabilities",
              attributes: { availableInNewTerritories: true },
              relationships: {
                inAppPurchase:        { data: { type: "inAppPurchases", id: iid } },
                availableTerritories: { data: terr.map { |t| { type: "territories", id: t["id"] } } } } } })
  puts "  ✓ availability set (#{terr.size} territories, open to new ones)"
end

# ---------------------------------------------------------------- 6. screenshot
shot = File.join(root, "review", "screenshot.png")
if !no_shot && File.exist?(shot)
  cur = begin ASC.body(rc.get(rel.("appStoreReviewScreenshot")))["data"] rescue nil end
  if cur
    puts "  reviewer screenshot already attached"
  elsif dry
    puts "  [dry-run] would upload the reviewer screenshot"
  else
    here = File.dirname(File.expand_path(__FILE__))
    puts "  uploading reviewer screenshot…"
    system("ruby", File.join(here, "upload_iap_screenshot.rb"), pid, bundle, shot) ||
      puts("  ⚠️  screenshot upload reported a failure — re-check before submitting")
  end
elsif !no_shot
  puts "  ⚠️  no review/screenshot.png in the hub — REQUIRED before this product can be submitted"
end

final = ASC.body(rc.get("v2/inAppPurchases/#{iid}")).dig("data", "attributes", "state")
puts "IAP state now: #{final}"
puts "It ships attached to the next app-version submission — do not submit it standalone."
