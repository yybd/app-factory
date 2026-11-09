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
#   --type TYPE         NON_CONSUMABLE | CONSUMABLE | NON_RENEWING_SUBSCRIPTION
#                       (default: product.txt's `type:`, else NON_CONSUMABLE)
#   --territory T       base territory for pricing (default USA)
#   --mirror-from PID   copy the territory availability from an existing product
#                       (its 175-territory set), instead of every territory Apple lists
#   --no-price          leave pricing alone
#   --no-screenshot     skip the reviewer screenshot
#   --open-version      the product is APPROVED, a locale's text changed, and there is
#                       no draft version to put it in: open one (POST
#                       inAppPurchaseVersions). It goes to review with the next app
#                       version. Without this flag the script stops and says so.
#   --dry-run           report what would change, write nothing
#
# Changing the text of an APPROVED product: App Store Connect keeps the approved
# localizations read-only ("Cannot edit InAppPurchaseLocalization when it is in
# ACTIVE state") and edits go to a draft — a second localization record per locale,
# state PREPARE_FOR_SUBMISSION, inside a newer inAppPurchaseVersion. The script
# always compares against and writes to that draft, never the approved record.
#
# Hub layout it reads (authored by app-store-metadata):
#   <hub>/<slug>/store/apple/iap/<product-id>/
#     product.txt              # key: value lines — reference_name:, type: (also
#                              #   product_id:, cleared_for_sale:, not read here).
#                              #   An older "reference name · type" first line still works.
#     price.txt                # customer price, e.g. "19.99 USD (tier 10177 …)"
#     <locale>/display_name.txt   ≤30
#     <locale>/description.txt    ≤45
#     review/notes.txt
#     review/screenshot.png
#
# Confirm with the user before running — this writes to App Store Connect.

if (ARGV & %w[-h --help]).any?  # the usage needs no gems and no credentials
  puts File.readlines(__FILE__, encoding: "UTF-8").drop(1).take_while { |l| l.start_with?("#") }.map { |l| l.sub(/^# ?/, "") }
  exit 0
end

require_relative "asc_common"
require "uri"

pos, _ = ASC.parse_args(ARGV)
slug, pid, bundle = pos
abort "usage: provision_iap.rb <slug> <product-id> <bundle-id> [--locales a,b]" unless slug && pid && bundle

def flag(n, d = nil)
  i = ARGV.index(n); i && ARGV[i + 1] && !ARGV[i + 1].start_with?("--") ? ARGV[i + 1] : d
end
dry       = ARGV.include?("--dry-run")
territory = flag("--territory", "USA")
mirror    = flag("--mirror-from")
no_price  = ARGV.include?("--no-price")
no_shot   = ARGV.include?("--no-screenshot")
open_ver  = ARGV.include?("--open-version")
tree      = ASC.tree(slug, hub: flag("--hub"), repo: flag("--repo"))   # hub, or the repo's fastlane/
root      = tree[:iap].call(pid)
abort "no IAP tree in the #{tree[:name]} at: #{root}" unless Dir.exist?(root)
$stdout.sync = true

rd = ->(p) { File.exist?(p) ? File.read(p, encoding: "UTF-8").strip : nil }

# product.txt is `key: value` lines, as app-store-metadata and store-metadata-writer
# write it. A hub written before that has "reference name · type" on the first line —
# read that too, rather than creating a product named after the whole line.
product = rd.(File.join(root, "product.txt")).to_s
kv      = /\A\s*([a-z_]+)\s*:\s*(.*?)\s*\z/
fields  = product.lines.filter_map { |l| (m = l.match(kv)) && [m[1], m[2]] }.to_h
first   = product.lines.first.to_s
legacy  = first.match?(kv) ? [] : first.split("·").map(&:strip)
TYPES   = %w[NON_CONSUMABLE CONSUMABLE NON_RENEWING_SUBSCRIPTION].freeze
as_type = ->(t) { t.to_s.strip.upcase.gsub(/[\s-]+/, "_") }
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
  ref = (fields["reference_name"] || legacy[0]).to_s
  ref = pid if ref.empty?
  abort "reference name is #{ref.length} chars (max 64)" if ref.length > 64
  # The type cannot be changed after creation, so an unreadable `type:` stops here
  # rather than defaulting. The old first-line format never drove the type; it does
  # now only when it names one this script can create.
  type = flag("--type") || fields["type"] || (TYPES.include?(as_type.(legacy[1])) ? legacy[1] : "NON_CONSUMABLE")
  type = as_type.(type)
  abort "type #{type.inspect} is not one this script creates (#{TYPES.join(' | ')}) — " \
        "auto-renewable subscriptions use the subscription API" unless TYPES.include?(type)
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
# A locale can hold TWO records: the approved one (read-only — PATCHing it fails with
# "Cannot edit InAppPurchaseLocalization when it is in ACTIVE state") and a
# PREPARE_FOR_SUBMISSION draft beside it, in a newer inAppPurchaseVersion. Keying the
# list by locale kept whichever came last, and on a live product (2026-11-09) that was the
# approved one. So: group by locale, and write only to a record that is not locked.
LOCKED = %w[APPROVED WAITING_FOR_REVIEW].freeze
OPEN_V = %w[PREPARE_FOR_SUBMISSION REJECTED DEVELOPER_REJECTED].freeze
load_locs = lambda do
  (ASC.body(rc.get(rel.("inAppPurchaseLocalizations"), { limit: 200 }))["data"] || [])
    .group_by { |l| l.dig("attributes", "locale") }
end
# The draft version, if one is open — where a draft for an approved-only locale goes.
load_draft = lambda do
  link = rel.("versions")
  vs = link ? (begin ASC.body(rc.get(link, { limit: 50 }))["data"] rescue nil end) || [] : []
  vs.select { |v| OPEN_V.include?(v.dig("attributes", "state")) }
    .max_by { |v| v.dig("attributes", "version").to_i }
end
have  = load_locs.()
draft = nil
draft_looked = false
same = ->(r, n, d) { r && r.dig("attributes", "name") == n && r.dig("attributes", "description") == d }

locales.each do |loc|
  name = rd.(File.join(root, loc, "display_name.txt"))
  desc = rd.(File.join(root, loc, "description.txt"))
  next puts("  [#{loc}] no display_name.txt — skipped") unless name
  if name.length > 30 || (desc && desc.length > 45)
    abort "  [#{loc}] over limit — display_name #{name.length}/30, description #{desc&.length}/45"
  end
  # Once any locale is approved, the product is live and new text belongs in a draft.
  live   = have.values.flatten.any? { |r| r.dig("attributes", "state") == "APPROVED" }
  recs   = have[loc] || []
  cur    = recs.find { |r| !LOCKED.include?(r.dig("attributes", "state")) }   # the editable one
  locked = recs.find { |r| LOCKED.include?(r.dig("attributes", "state")) }

  if cur
    if same.(cur, name, desc)
      puts "  [#{loc}] already set#{locked ? ' (in the draft)' : ''}"
    elsif dry
      puts "  [#{loc}] [dry-run] would update#{locked ? ' the draft' : ''}"
    else
      rc.patch("v1/inAppPurchaseLocalizations/#{cur['id']}",
               { data: { type: "inAppPurchaseLocalizations", id: cur["id"],
                         attributes: { name: name, description: desc }.compact } })
      puts "  [#{loc}] updated#{locked ? ' (draft)' : ''}"
    end
  elsif locked || live
    # Only an approved (or in-review) record — or a locale the approved product never
    # had. Unchanged text needs no draft at all.
    next puts("  [#{loc}] already set (#{locked.dig('attributes', 'state')})") if same.(locked, name, desc)
    if locked&.dig("attributes", "state") == "WAITING_FOR_REVIEW"
      abort "  [#{loc}] the text is in review (WAITING_FOR_REVIEW) and cannot be changed now — " \
            "wait for the verdict, then re-run"
    end
    draft, draft_looked = load_draft.(), true unless draft_looked
    if draft.nil?
      if dry && !open_ver
        puts "  [#{loc}] [dry-run] text changed on an APPROVED product and no draft version is open — " \
             "a real run stops here; --open-version would open one"
        next
      end
      unless open_ver
        abort "  [#{loc}] the product is APPROVED and the text changed, but no draft version is open. " \
              "Approved localizations are read-only; the change goes into a new version " \
              "(POST inAppPurchaseVersions), which ships with the next app-version submission. " \
              "Re-run with --open-version to open it, or open it in App Store Connect " \
              "(edit the product's localization there) and re-run."
      end
      if dry
        puts "  [#{loc}] [dry-run] would open a new IAP version, then write the draft"
        next
      end
      created = ASC.body(rc.post("v1/inAppPurchaseVersions",
        { data: { type: "inAppPurchaseVersions",
                  relationships: { inAppPurchase: { data: { type: "inAppPurchases", id: iid } } } } }))
      draft = created["data"]
      puts "  ✓ opened IAP version #{draft.dig('attributes', 'version')} (#{draft.dig('attributes', 'state')})"
      # Opening a version may copy the approved text forward into drafts — re-read and
      # take that draft if it appeared, rather than adding a second one.
      have = load_locs.()
      redo
    end
    if dry
      puts "  [#{loc}] [dry-run] would create a draft in version #{draft.dig('attributes', 'version')}"
    else
      rc.post("v2/inAppPurchaseLocalizations",
              { data: { type: "inAppPurchaseLocalizations",
                        attributes: { locale: loc, name: name, description: desc }.compact,
                        relationships: { version: { data: { type: "inAppPurchaseVersions", id: draft["id"] } } } } })
      puts "  [#{loc}] created (draft in version #{draft.dig('attributes', 'version')})"
    end
  elsif dry
    puts "  [#{loc}] [dry-run] would create"
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
      # Price points come 200 a page, cheapest first, so a USA price above about $24.49
      # is on page two or later. links.next cannot be followed as a path: the tunes
      # client drops its query string, and page two comes back unfiltered and repeats
      # forever. Take the cursor out of it and send it with the filter and limit again.
      pp = nil
      cursor = nil
      pages = 0
      loop do
        q = { "filter[territory]" => territory, limit: 200 }
        q[:cursor] = cursor if cursor
        page = ASC.body(rc.get("v2/inAppPurchases/#{iid}/pricePoints", q))
        pages += 1
        pp = (page["data"] || []).find { |p| p.dig("attributes", "customerPrice") == want }
        nxt = page.dig("links", "next")
        break if pp || nxt.nil? || pages >= 25
        prev, cursor = cursor, URI.decode_www_form(URI(nxt).query.to_s).to_h["cursor"]
        break if cursor.nil? || cursor == prev
      end
      abort "  no #{territory} price point at #{want} (#{pages} page(s) read)" unless pp
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
