# Delivering In-App Purchases via the official App Store Connect API

`fastlane deliver` handles the app listing but **not** in-app purchases. IAPs go up
through the **official App Store Connect API** (token-auth with the same `.p8`).

> ⚠️ **There is NO IAP model in `Spaceship::ConnectAPI`** (verified through fastlane
> 2.234). `app.get_in_app_purchases`, `iap.upsert_localization`,
> `iap.set_price_schedule`, `iap.upload_review_screenshot`, `iap.submit_for_review`
> — **none of these exist.** The only IAP model that exists is the legacy
> `Spaceship::Tunes` one, which needs interactive Apple-ID/2FA login and does NOT
> work with the `.p8` token. So drive the IAP endpoints with **raw HTTP** through
> the token client (below). This is the path that works.

## Hub layout (the IAP source of truth)

Authored by **`app-store-metadata`** (orchestrated by `store-metadata-writer`) into
the hub; this skill only **syncs + uploads** it — it never writes this:

```
$APP_HUB/<slug>/store/apple/iap/<product-id>/
  product.txt            # reference name · type · cleared_for_sale · price_usd
  price.txt              # price point / tier (optional; may be set already in ASC)
  <locale>/display_name.txt    # the per-locale Display Name users see (≤30)
  <locale>/description.txt     # the per-locale Description (≤45)
  review/notes.txt             # review notes for the App Review team
  review/screenshot.png        # REQUIRED reviewer screenshot (copied here by app-store-metadata
                               #   from media/apple/<App>/<locale>/iap/review_screenshot.png)
```

The `Pro:` line in the app's README / profile tells you a product exists and its
product id; the per-locale copy is lifted from the profile like all other copy.

## The raw token client

```ruby
require "spaceship"
Spaceship::ConnectAPI.token = Spaceship::ConnectAPI::Token.create(
  key_id:    "<AppleCredentials.asc_key[:key_id]>",
  issuer_id: "<Issuer ID from DATA.md>",
  filepath:  File.expand_path("<.p8 path from DATA.md>")
)
rc = Spaceship::ConnectAPI.client.tunes_request_client   # has .get/.post/.patch/.delete
def body(r); r.body.is_a?(Hash) ? r.body : JSON.parse(r.body); end
# paths are prefixed with the API version: "v1/..." or "v2/..."
```

## Endpoint map — the paths that actually work

| Operation | Endpoint (note the version) |
|-----------|------------------------------|
| List an app's IAPs | `GET v1/apps/{appId}/inAppPurchasesV2` → `data[].{id, attributes.productId/name/inAppPurchaseType/state}` |
| Read / patch one IAP | **`GET`/`PATCH v2/inAppPurchases/{id}`**  ← single resource is **v2**; `v1/inAppPurchases/{id}` 404s |
| Create an IAP | `POST v2/inAppPurchases` (attributes `name`, `productId`, `inAppPurchaseType`; relationship `app`) |
| Reach a sub-resource | follow the IAP's `relationships.<name>.links.related` URL — do **not** hand-build `v1/inAppPurchases/{id}/<rel>` (404: "relationship does not exist") |
| Localizations (list) | follow `relationships.inAppPurchaseLocalizations.links.related` |
| Localization (create) | `POST v1/inAppPurchaseLocalizations` — attrs `{locale,name,description}`, relationship **`inAppPurchaseV2`** → `{type:"inAppPurchases", id}` |
| Localization (update) | `PATCH v1/inAppPurchaseLocalizations/{locId}` — attrs `{name,description}` |
| Review note | it's an **attribute** `reviewNote` on the IAP → `PATCH v2/inAppPurchases/{id}` `{attributes:{reviewNote}}` |
| Review screenshot | relationship `appStoreReviewScreenshot` — **use `scripts/upload_iap_screenshot.rb`** (reserve→upload→commit on `inAppPurchaseAppStoreReviewScreenshots`; there is no Spaceship model, so it drives raw HTTP). It refuses illegal sizes and alpha up front, `--force` replaces an attached shot, and it polls `assetDeliveryState.state` to `COMPLETE` — a commit that returns 200 can still fail delivery |
| Price | relationship `iapPriceSchedule` (schedule id == IAP id). Manual prices via `inAppPurchasePriceSchedules`; often already set in ASC — read before writing |

## Working recipe (idempotent — localization + review note)

Covers the common case: the IAP already exists (price + reviewer screenshot set in
ASC), and only the per-locale text + review note are missing (state
`MISSING_METADATA`). Setting them flips it to `READY_TO_SUBMIT`.

```ruby
iid = body(rc.get("v1/apps/#{app_id}/inAppPurchasesV2", {limit:200}))["data"]
        .find { |p| p.dig("attributes","productId") == PID }["id"]

iap  = body(rc.get("v2/inAppPurchases/#{iid}"))
locs = body(rc.get(iap.dig("data","relationships","inAppPurchaseLocalizations","links","related")
                      .sub("https://api.appstoreconnect.apple.com/","")))["data"]

locales.each do |loc|
  name = File.read("#{iap_dir}/#{loc}/display_name.txt").strip
  desc = File.read("#{iap_dir}/#{loc}/description.txt").strip
  if (m = locs.find { |x| x.dig("attributes","locale") == loc })
    rc.patch("v1/inAppPurchaseLocalizations/#{m['id']}",
      {data:{type:"inAppPurchaseLocalizations", id:m['id'], attributes:{name:name, description:desc}}})
  else
    rc.post("v1/inAppPurchaseLocalizations",
      {data:{type:"inAppPurchaseLocalizations",
             attributes:{locale:loc, name:name, description:desc},
             relationships:{inAppPurchaseV2:{data:{type:"inAppPurchases", id:iid}}}}})
  end
end

rc.patch("v2/inAppPurchases/#{iid}",
  {data:{type:"inAppPurchases", id:iid, attributes:{reviewNote: File.read("#{iap_dir}/review/notes.txt").strip}}})
```

A ready-to-run version is `scripts/provision_iap.rb`, which also creates the product,
sets the price and attaches the reviewer screenshot.

## Rules
- **The reviewer screenshot is mandatory** — a product without it can't be
  submitted. Check its `assetDeliveryState`; if missing, upload it (reserve→commit)
  before relying on `READY_TO_SUBMIT`. If neither the hub nor ASC has one, stop and
  report it (same verify-or-block gate as the metadata sync).
- **Don't submit the IAP standalone for a metadata push.** Setting localization +
  review note + price + screenshot moves it to `READY_TO_SUBMIT`; it then ships
  **attached to the next app-version submission** (`ship-apple-app`'s job).
- **Confirm before writing** — creating/patching IAPs is outward-facing.
- **Never invent copy or prices** — everything traces to the hub; missing → fill it
  in `store-metadata-writer` / `app-store-metadata`, then re-run.
- **Read before you write** — price schedule and reviewer screenshot are often
  already set in ASC; GET the IAP's relationships first and skip what's done.
