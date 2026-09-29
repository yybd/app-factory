# Delivering Google Play in-app products & subscriptions

`fastlane supply` delivers the **listing** but **not** in-app products. Play
monetization is delivered through the **Google Play Developer API**
(AndroidPublisher v3), authenticated with the **same service-account JSON**
`shared/credentials.py` resolves. Two resources, both under `monetization`:

- **One-time products** (what used to be "managed products") →
  `monetization.onetimeproducts`, REST path `applications/{pkg}/oneTimeProducts`.
- **Subscriptions** → `monetization.subscriptions` (base plans + offers).

**The old `inappproducts` resource is retired.** It answers **403 "Please migrate
to the new publishing API"** for every app, measured 2026-09-07 and again on
2026-09-26. A 403 there looks exactly like a missing permission and is not one — do
not go looking for a role to grant.

## Hub layout (the source of truth)

Authored by `play-store-metadata` into the hub; this skill only uploads it:

```
$APP_HUB/<slug>/store/play/iap/<product-id>/
  product.txt               # product_id, type, status — and `price: 6.99 USD` if no price.txt
  price.txt                 # optional: `6.99 USD` — the BASE price; regions are converted
  <locale>/name.txt         # ≤55 chars (title.txt is accepted too)
  <locale>/description.txt  # ≤200 chars
  # subscriptions only:
  base-plans.txt            # base plan ids + billing period + renewal type
```

A `<locale>/` folder for the app's **default listing language** is mandatory — see
the traps.

## One-time products — the script

```bash
# rehearsal: validates the hub, reads the default language, converts the price,
# prints the body. Writes nothing.
python3 ${CLAUDE_PLUGIN_ROOT}/skills/play-store-deliver/scripts/play_iap.py \
  --package <pkg> --dir $APP_HUB/<slug>/store/play/iap/<product-id> --dry-run

# the real thing: upsert, then activate the purchase option
python3 ${CLAUDE_PLUGIN_ROOT}/skills/play-store-deliver/scripts/play_iap.py \
  --package <pkg> --dir $APP_HUB/<slug>/store/play/iap/<product-id>

# what is live
python3 ${CLAUDE_PLUGIN_ROOT}/skills/play-store-deliver/scripts/play_iap.py --package <pkg> --list
```

It uses `publish_aab.py`'s auth (stdlib + an `openssl`-signed JWT), so there is
nothing to install. It is idempotent: a second run patches the same product, and
skips activation when the option is already `ACTIVE`.

## The flow it runs (three calls)

1. **`POST applications/{pkg}/pricing:convertRegionPrices`** with
   `{"price": {"currencyCode": "USD", "units": "6", "nanos": 990000000}}`.
   Returns `convertedRegionPrices` (a map region → `{price: Money, …}`) and a
   **`regionVersion.version`** such as `2025/03`. One USD base became 173 regions.
   Read-only, so `--dry-run` runs it too.

2. **`PATCH applications/{pkg}/oneTimeProducts/{productId}`** with the query
   `allowMissing=true` (this is what makes it an upsert),
   `updateMask=listings,purchaseOptions`, and
   `regionsVersion.version=<the version from step 1>`. Body:

   ```json
   {
     "packageName": "<pkg>", "productId": "<product-id>",
     "listings": [{"languageCode": "en-GB", "title": "…", "description": "…"}],
     "purchaseOptions": [{
       "purchaseOptionId": "buy",
       "buyOption": {"legacyCompatible": true, "multiQuantityEnabled": false},
       "regionalPricingAndAvailabilityConfigs": [
         {"regionCode": "AE", "price": {"currencyCode": "AED", "units": "26", "nanos": 990000000},
          "availability": "AVAILABLE"}
       ]
     }]
   }
   ```

   `legacyCompatible: true` is what lets a Play Billing client that queries the
   product the old way (`querySkuDetails` / `INAPP` product details without a
   purchase option id) still see it. Only one purchase option per product may carry it.

3. **`POST applications/{pkg}/oneTimeProducts/{productId}/purchaseOptions:batchUpdateStates`**
   with `{"requests": [{"activatePurchaseOptionRequest": {"packageName": …,
   "productId": …, "purchaseOptionId": "buy"}}]}`. The patch alone does not put
   the option on sale; until it is `ACTIVE`, the billing client answers "no such
   product".

None of these run inside an edit.

## Traps

- **The default listing language, not en-US.** The API refuses a product that has
  no listing in the app's **default** listing language — and that is whatever the
  Console was set to when the app was created, measured as **en-GB** on one app.
  The script reads it (`edits/{id}/details` → `defaultLanguage`) and stops before
  writing if the hub has no folder for it.
- **No payments profile → `400 FAILED_PRECONDITION` from `convertRegionPrices`.**
  Nothing is wrong with the request; the developer account has no payments profile
  yet (Console → Settings → Payments profile). Nothing can be priced until it does.
- **Converted prices are Play's, not the App Store's.** A 6.99 USD base converted
  to ₪21 in Israel while the App Store tier for the same product was ₪24.90. If the
  two stores must match in a region, that is a per-region override in the hub, and a
  decision for the user — not something to fix silently.
- **`inappproducts` 403** — see the top. Any sample code still calling
  `inappproducts.update` / `insert` is dead.

## Subscriptions

`monetization.subscriptions` (`applications/{pkg}/subscriptions`): `productId`,
per-locale `listings` (title / description / benefits), `basePlans` (id, billing
period, auto-renewing) and optional `offers`. The same `regionsVersion` and
`convertRegionPrices` apply to base-plan prices, and base plans are activated
separately (`basePlans:activate`). Not yet scripted — verify the method names
against the API reference before the first run, and record what was measured here.

## Rules
- **Verify before upload** — the same gate as the listing sync: if a product's
  name/description/price is missing in the hub, stop and point back to
  `play-store-metadata` (then `store-metadata-writer`) to fill it.
- **Confirm before publishing** — creating/activating products is outward-facing.
  `--dry-run` first.
- **Never invent** prices or copy — everything traces to the hub.
- Some monetization settings still finalize only in the **Play Console** (tax and
  compliance, the payments profile itself) — tell the user what's left.
