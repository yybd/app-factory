# Selling the direct build with a licence key

The App Store build is paid for through StoreKit. The direct build — the notarized DMG
from your own site — cannot use StoreKit, so it is unlocked with a **licence key**: the
buyer pays on a hosted checkout, receives a key by email, and pastes it into the app.

Everything below lives **only in the Direct target**. See
[the rule on the App Store build](#the-app-store-build-carries-none-of-it) before
writing a line of it.

## The flow

1. **Checkout.** A merchant of record sells the product on a hosted checkout page and
   handles payment, VAT/sales tax and refunds. Lemon Squeezy is the worked example
   here; Paddle and Gumroad do the same job with their own licence APIs — the shape
   below carries over, the endpoints and field names do not.
2. **Key by email.** The merchant generates a licence key per order and emails it to
   the buyer.
3. **Paywall.** The app's paywall (in the Direct target) has a "Buy" button that opens
   the checkout URL in the browser, and a field to paste the key into.
4. **Activation.** The app calls the merchant's **public licence API** — for Lemon
   Squeezy `POST https://api.lemonsqueezy.com/v1/licenses/activate`, with
   `deactivate` and `validate` beside it. These endpoints take the licence key itself
   as the credential. **No API key, no secret, ships in the app** — a store API key
   in a binary is a key anyone can extract.
5. **Storage.** The key and the activation's instance id go in the **Keychain**, not
   `UserDefaults` — a plist in `~/Library/Preferences` is a file anyone can read,
   copy to another Mac, or hand-edit into "unlocked".
6. **Moving to another Mac.** A "Deactivate this Mac" button calls `deactivate` with
   the stored instance id, frees the seat under the activation limit, and clears the
   Keychain item. The buyer then activates on the new Mac.

## Two policies — the owner decides

Ask the owner which one; do not pick for them. Both are legitimate; they trade
different things.

**(a) Re-validate on launch.** On launch, unlock **optimistically** from the Keychain,
then call `validate` in the background. Lock **only on an explicit rejection from the
server** — a response that says `valid: false`, or names another product. Never lock
on a network failure, a timeout, a 5xx, or a body that is not JSON: a paying user on a
plane, behind a captive portal, or during the merchant's outage must keep the app they
paid for. What it buys: a refunded or disabled key stops working the next time the app
is online.

**(b) Activate-only.** One network call, at activation; after that the app never
contacts the licence server again. For apps that promise to work offline, or promise
never to phone home. What it costs: **a refunded or disabled key keeps working on a Mac
that already activated it** — the server's change never reaches the app. Write that
cost down where the owner will see it, and do not ship (b) by default.

## Rules

- **Match `meta.variant_id` strictly.** The licence API answers for every key in the
  **store**, not for one product: a key bought for another product in the same store
  activates successfully. The app compares `meta.variant_id` in the response to its
  own configured variant id and refuses on any mismatch — and if the server already
  counted an activation, deactivates it again so the buyer's seat is not wasted.
  (Several variants of one product — say a single-Mac and a family licence — mean a
  set of accepted ids, still compared exactly.)
- **Refuse to activate until the variant id is configured.** A build where the id is
  still the placeholder must say so and refuse, not skip the check — skipping it turns
  every key in the store into a key for this app.
- **The price lives on the checkout page, not in the binary.** The paywall says "Buy"
  and opens the checkout; it does not print "$19.99". A price in the binary is a price
  that is wrong the day it changes and stays wrong in every installed copy. (Where a
  price is written elsewhere — site, profile, store metadata — is `price-sync`'s
  business.)
- **Read `license_key.status`.** `active` and `inactive` (valid, no activations yet)
  are fine; `disabled` and `expired` are a rejection, whatever `activated`/`valid`
  says.
- **Validate before you activate.** `validate` without an instance id costs no seat;
  checking the variant and status there first means a wrong-product key never touches
  the activation count.

### The App Store build carries none of it

App Review Guideline 3.1.1 forbids unlocking features in an App Store app by any
mechanism other than in-app purchase, and **names licence keys explicitly**. So the
App Store build must contain **no checkout link, no licence-server URL, and no
licence code** — not dormant, not hidden behind a flag that is off. A reviewer, or a
`strings` run, that finds `lemonsqueezy.com` in an App Store binary has found a
reason to reject it.

Compile it into the Direct target only:

- **Swift / Xcode:** wrap it in `#if DIRECT` — the flag this skill's target already
  sets ([xcode-target.md](xcode-target.md#the-direct-flag-is-the-seam-for-more-than-sparkle)) —
  or keep it in a direct-only folder that only the Direct target compiles. The
  checkout URL and the variant id are inside the guard too, not in a shared constants
  file.
- **Tauri / Rust:** a Cargo feature (`direct`), with the licence module behind
  `#[cfg(feature = "direct")]`, and a `build.rs` that **fails** the App Store build if
  the feature is on — it reads `CARGO_FEATURE_DIRECT` and whatever marks the App Store
  build in your pipeline, and panics on the combination. The frontend counts as well:
  a checkout URL in the web bundle ships in the App Store app, so the paywall's
  strings come from the Rust side, behind the same feature.

Verify it on the built App Store product, the same way the Sparkle split is verified:

```bash
APP=/tmp/mas_check/Build/Products/Release/<Product>.app
strings -a "$APP/Contents/MacOS/<Product>" | grep -iE 'lemonsqueezy|licenses/(activate|validate)'
# expect: no output
```

## The owner's dashboard step (Lemon Squeezy)

The owner does this once, in the merchant's dashboard — the app cannot:

1. **Create the product** and its **variant** (or variants), with the price.
2. **Turn licence keys on** for the product, and set the **activation limit** — how
   many Macs one key may run on at a time — and the key's length (unlimited for a
   one-time purchase).
3. **Hand the app two values:** the **variant id** (`<VARIANT_ID>`) and the
   **checkout URL** (`https://<store>.lemonsqueezy.com/checkout/buy/<id>`). Nothing
   else from the dashboard belongs in the app — no store API key.

Test mode is a separate data set: a product moved from test mode to live mode can come
out with a different variant id. Check the configured id against the **live** product
before the release build.

## A compact Swift sketch

Direct target only. Form-encoded POST, `Accept: application/json`; the API answers
errors with a 4xx and a JSON body carrying `error`, so the body is parsed whatever the
status.

```swift
#if DIRECT
import Foundation
import Security

enum Licence {
    /// From the dashboard. Empty means "not configured" — activation refuses.
    static let variantIDs: Set<Int> = []                       // e.g. [<VARIANT_ID>]
    static let checkoutURL = URL(string: "https://<store>.lemonsqueezy.com/checkout/buy/<id>")!
    private static let api = URL(string: "https://api.lemonsqueezy.com/v1/licenses/")!

    struct Stored: Codable { let key: String; let instanceID: String }
    enum Failure: Error { case notConfigured, wrongProduct, rejected(String), offline }

    static func activate(_ key: String) async throws -> Stored {
        guard !variantIDs.isEmpty else { throw Failure.notConfigured }
        // 1. validate first: costs no seat, catches a wrong-product or disabled key
        let check = try await post("validate", ["license_key": key])
        try accept(check, flag: "valid")
        // 2. activate
        let json = try await post("activate", ["license_key": key,
                                               "instance_name": Host.current().localizedName ?? "Mac"])
        guard let instance = (json["instance"] as? [String: Any])?["id"] as? String else {
            throw Failure.rejected(json["error"] as? String ?? "not activated")
        }
        do { try accept(json, flag: "activated") } catch {
            _ = try? await post("deactivate", ["license_key": key, "instance_id": instance])  // give the seat back
            throw error
        }
        let stored = Stored(key: key, instanceID: instance)
        try Keychain.save(stored)
        return stored
    }

    static func deactivate(_ s: Stored) async throws {
        let json = try await post("deactivate", ["license_key": s.key, "instance_id": s.instanceID])
        guard json["deactivated"] as? Bool == true else {
            throw Failure.rejected(json["error"] as? String ?? "not deactivated")
        }
        Keychain.clear()
    }

    /// Policy (a), in the background after an optimistic unlock.
    /// false only when the server explicitly says no — never for offline / 5xx / garbage.
    static func stillValid(_ s: Stored) async -> Bool {
        guard let json = try? await post("validate", ["license_key": s.key, "instance_id": s.instanceID]),
              json["valid"] is Bool else { return true }
        return (try? accept(json, flag: "valid")) != nil
    }

    private static func accept(_ json: [String: Any], flag: String) throws {
        guard json[flag] as? Bool == true else { throw Failure.rejected(json["error"] as? String ?? "rejected") }
        let status = (json["license_key"] as? [String: Any])?["status"] as? String
        guard status == "active" || status == "inactive" else { throw Failure.rejected(status ?? "no status") }
        guard let v = (json["meta"] as? [String: Any])?["variant_id"] as? Int, variantIDs.contains(v) else {
            throw Failure.wrongProduct
        }
    }

    private static func post(_ path: String, _ form: [String: String]) async throws -> [String: Any] {
        var req = URLRequest(url: api.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        var body = URLComponents()
        body.queryItems = form.map { URLQueryItem(name: $0.key, value: $0.value) }
        req.httpBody = body.percentEncodedQuery?.data(using: .utf8)   // keys are letters, digits, dashes
        guard let reply = try? await URLSession.shared.data(for: req),
              let json = try? JSONSerialization.jsonObject(with: reply.0) as? [String: Any]
        else { throw Failure.offline }                                 // no network, or a body that is not JSON
        return json
    }
}

enum Keychain {
    private static let base: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: (Bundle.main.bundleIdentifier ?? "app") + ".licence",
        kSecAttrAccount as String: "licence",
    ]
    static func save(_ s: Licence.Stored) throws {
        SecItemDelete(base as CFDictionary)
        var add = base
        add[kSecValueData as String] = try JSONEncoder().encode(s)
        let status = SecItemAdd(add as CFDictionary, nil)
        guard status == errSecSuccess else { throw NSError(domain: NSOSStatusErrorDomain, code: Int(status)) }
    }
    static func load() -> Licence.Stored? {
        var q = base
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var out: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let data = out as? Data else { return nil }
        return try? JSONDecoder().decode(Licence.Stored.self, from: data)
    }
    static func clear() { SecItemDelete(base as CFDictionary) }
}
#endif
```

On launch: `if let s = Keychain.load() { unlock(); Task { if await !Licence.stillValid(s) { Keychain.clear(); lock() } } }`
for policy (a); for policy (b), `Keychain.load() != nil` is the whole check and
`stillValid` is not called.

## Test checklist

Run each against the real API (test mode first, then once against live) before the
first release, and again whenever the licence code changes:

- [ ] **Valid key** — activates, unlocks, survives a relaunch; the dashboard shows one
      activation.
- [ ] **Key for another product in the same store** — refused with a wrong-product
      message; the dashboard shows **no** activation left behind on that key.
- [ ] **Disabled key** (disable it in the dashboard) — refused at activation. Under
      policy (a), an already-activated Mac locks on the next online launch; under (b)
      it does not, as documented.
- [ ] **Offline at activation** — a clear "can't reach the licence server" message;
      nothing written to the Keychain; the app stays locked and does not crash. Under
      policy (a), also: offline on a later launch keeps the app **unlocked**.
- [ ] **Deactivate** — the seat is freed in the dashboard, the Keychain item is gone,
      the app locks, and the same key then activates on a second Mac.
- [ ] **Variant id not configured** — activation refuses with a message, and never
      calls the API.
- [ ] **App Store build** — the `strings` check above prints nothing.
