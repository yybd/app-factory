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
   here, because its licence API covers the whole flow from the app alone; what other
   providers offer, and what to build when one falls short, is in
   [the provider contract](#the-provider-contract).
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

## The provider contract

The app needs five things from whoever issues the keys. Check a provider against them
**before** choosing it — a missing one is either a feature the app drops or a server
the owner has to run.

1. **Check a key without spending an activation** — so a wrong-product or revoked key
   is refused before it counts against the buyer's limit.
2. **Activate this Mac**, returning a per-Mac handle (an instance or machine id) that
   the later calls name.
3. **Deactivate that handle with the key alone** — the buyer moves to a new Mac
   without writing to support.
4. **Name the product** in every answer, so the app can compare it to its own.
5. **Say why a key is no good** — revoked, refunded, expired — distinctly from "I could
   not answer", which is what lets policy (a) below lock on the one and never on the
   other.

All five must work **with the licence key as the only credential**. An endpoint that
needs the seller's API key or OAuth token cannot be called from the app; it needs a
small server the owner runs — the app calls the server, the server holds the secret
and calls the provider.

| | Lemon Squeezy | Keygen | Gumroad | Paddle Billing |
|---|---|---|---|---|
| 1. Check, no seat | `validate` without `instance_id` | `licenses/actions/validate-key`, no auth | `licenses/verify` with `increment_uses_count=false` | — |
| 2. Activate, per-Mac handle | `activate` → `instance.id`; limit set per product | `POST machines` with a fingerprint, `Authorization: License <key>` → machine id | `verify` with the counter on: a **count**, no handle; the app compares `uses` to its own limit | — |
| 3. Deactivate with the key | `deactivate` with `instance_id` | `DELETE machines/<id>`, same licence-key auth | **No** — `decrement_uses_count` needs the seller's token: a server, or support resets it | — |
| 4. Product to match | `meta.variant_id` (or `meta.product_id`) | `meta.scope.product` in the request: another product's key fails validation | `product_id` in the request: another product's key gets a 404 | — |
| 5. Why it is no good | `license_key.status` `disabled` / `expired` | `meta.code` (`SUSPENDED`, `EXPIRED`, …) | `purchase.refunded`, `purchase.chargebacked`, `subscription_*_at` — separate fields: **`success` alone is not the answer**; the app reads them | — |
| Notes | 60 requests a minute | Licence-key auth only when the policy's authentication strategy is `LICENSE` or `MIXED`; a free self-hosted edition (CE) exists | Older products may need `product_permalink` instead of `product_id` | **No licence keys** — Paddle Classic had them; Billing does not. Generate keys on the `transaction.completed` webhook into Keygen or your own server, then follow that column |

The table was checked against each provider's API documentation on 2026-10-21.
Providers change their APIs; read the current page before relying on a row.

## Two policies — the owner decides

Ask the owner which one; do not pick for them. Both are legitimate; they trade
different things.

**(a) Re-validate on launch.** On launch, unlock **optimistically** from the Keychain,
then re-check in the background (contract item 5). Lock **only on an explicit rejection
from the server** — a response that says the key is no good, or names another product.
Never lock
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

- **Match the product strictly.** A licence API answers for every key in the
  **store** or **account**, not for one product: on Lemon Squeezy a key bought for
  another product in the same store activates successfully. The app compares the
  product its provider names — Lemon Squeezy's `meta.variant_id` — to its own
  configured id and refuses on any mismatch, and if the server already counted an
  activation, deactivates it again so the buyer's seat is not wasted. Where the
  provider takes the product in the request instead (Keygen, Gumroad), always send it.
  (Several variants of one product — say a single-Mac and a family licence — mean a
  set of accepted ids, still compared exactly.)
- **Refuse to activate until the product id is configured.** A build where the id is
  still the placeholder must say so and refuse, not skip the check — skipping it turns
  every key in the store into a key for this app.
- **The price lives on the checkout page, not in the binary.** The paywall says "Buy"
  and opens the checkout; it does not print "$19.99". A price in the binary is a price
  that is wrong the day it changes and stays wrong in every installed copy. (Where a
  price is written elsewhere — site, profile, store metadata — is `price-sync`'s
  business.)
- **Read the reason, not only the yes.** A successful call can still describe a key
  that must not unlock: Lemon Squeezy's `license_key.status` `disabled` / `expired`,
  Gumroad's `refunded` and `chargebacked`, which `success` does not fold in. Contract item 5, per provider, in the
  table.
- **Check before you activate** (contract item 1). Checking product and status on a
  call that costs no seat means a wrong-product key never touches the activation count.

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
  checkout URL and the product id are inside the guard too, not in a shared constants
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

Other providers have the same three steps under other names — Keygen's product,
policy (with its machine limit and authentication strategy) and the account id; Gumroad's
product id and the limit the app enforces itself.

Test mode is a separate data set: a product moved from test mode to live mode can come
out with a different variant id. Check the configured id against the **live** product
before the release build.

## A compact Swift sketch

Direct target only. Three parts: `LicenceProvider` is the [contract](#the-provider-contract)
as a protocol; `Licence` is the app's side — the ordering, the Keychain and the policy —
written once against it; and one type per provider. Lemon Squeezy, Keygen and Gumroad
are below — pick one, delete the others. Another provider is another conforming type
(in Rust, a trait of the same shape), and nothing in `Licence` changes.

The three implementations follow the request and response shapes in each provider's
documentation (checked on 2026-10-21) and are typechecked; they have not been run
against the live services. Run the [test checklist](#test-checklist) on the one you
keep.

### The contract and the app's side

```swift
#if DIRECT
import Foundation
import Security

enum LicenceFailure: Error { case notConfigured, wrongProduct, rejected(String), offline }

/// The provider contract. One conforming type per provider.
protocol LicenceProvider {
    /// The product id this build accepts is set. Until it is, nothing is activated.
    var isConfigured: Bool { get }
    /// Contract 1, 4, 5: is this key good for this product — without spending an activation.
    func check(_ key: String) async throws
    /// Contract 2: activate this Mac; returns the per-Mac handle ("" if the provider has none).
    func activate(_ key: String) async throws -> String
    /// Contract 3.
    func deactivate(_ key: String, handle: String) async throws
    /// Contract 5, later: false = the server said no; nil = no answer (offline, 5xx, garbage).
    func verdict(_ key: String, handle: String) async -> Bool?
}

/// The app's side, provider-neutral.
struct Licence {
    struct Stored: Codable { let key: String; let handle: String }
    let provider: any LicenceProvider

    func activate(_ key: String) async throws -> Stored {
        guard provider.isConfigured else { throw LicenceFailure.notConfigured }
        try await provider.check(key)                       // a wrong product never spends a seat
        let stored = Stored(key: key, handle: try await provider.activate(key))
        try Keychain.save(stored)
        return stored
    }

    func deactivate(_ s: Stored) async throws {
        try await provider.deactivate(s.key, handle: s.handle)
        Keychain.clear()
    }

    /// Policy (a), in the background after an optimistic unlock: only an explicit no locks.
    func stillValid(_ s: Stored) async -> Bool {
        await provider.verdict(s.key, handle: s.handle) ?? true
    }
}

/// One request, one answer. A 4xx with a JSON body is an answer — the server said
/// something; no network, a 5xx, or a body that is not JSON is `.offline`, which is
/// what keeps policy (a) from locking a paying user out during an outage.
enum LicenceHTTP {
    static func form(_ url: URL, _ fields: [String: String]) -> URLRequest {
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        var body = URLComponents()
        body.queryItems = fields.map { URLQueryItem(name: $0.key, value: $0.value) }
        req.httpBody = body.percentEncodedQuery?.data(using: .utf8)   // keys are letters, digits, dashes
        return req
    }

    static func send(_ req: URLRequest) async throws -> (status: Int, json: [String: Any]) {
        guard let (data, response) = try? await URLSession.shared.data(for: req),
              let status = (response as? HTTPURLResponse)?.statusCode, status < 500
        else { throw LicenceFailure.offline }
        if data.isEmpty, (200..<300).contains(status) { return (status, [:]) }   // 204 No Content
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw LicenceFailure.offline                    // a captive portal's HTML page
        }
        return (status, json)
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

On launch, with `let licence = Licence(provider: <one of the types below>)`:
`if let s = Keychain.load() { unlock(); Task { if await !licence.stillValid(s) { Keychain.clear(); lock() } } }`
for policy (a); for policy (b), `Keychain.load() != nil` is the whole check and
`stillValid` is not called.

### Lemon Squeezy

```swift
#if DIRECT
/// Lemon Squeezy's public licence API — the key is the only credential.
struct LemonSqueezy: LicenceProvider {
    /// From the dashboard, e.g. [<VARIANT_ID>]. Empty means not configured.
    let variantIDs: Set<Int>
    static let checkoutURL = URL(string: "https://<store>.lemonsqueezy.com/checkout/buy/<id>")!
    private let api = URL(string: "https://api.lemonsqueezy.com/v1/licenses/")!

    var isConfigured: Bool { !variantIDs.isEmpty }

    func check(_ key: String) async throws {
        try accept(try await post("validate", ["license_key": key]), flag: "valid")
    }

    func activate(_ key: String) async throws -> String {
        let json = try await post("activate", ["license_key": key,
                                               "instance_name": Host.current().localizedName ?? "Mac"])
        guard let instance = (json["instance"] as? [String: Any])?["id"] as? String else {
            throw LicenceFailure.rejected(json["error"] as? String ?? "not activated")
        }
        do { try accept(json, flag: "activated") } catch {
            try? await deactivate(key, handle: instance)    // give the seat back
            throw error
        }
        return instance
    }

    func deactivate(_ key: String, handle: String) async throws {
        let json = try await post("deactivate", ["license_key": key, "instance_id": handle])
        guard json["deactivated"] as? Bool == true else {
            throw LicenceFailure.rejected(json["error"] as? String ?? "not deactivated")
        }
    }

    func verdict(_ key: String, handle: String) async -> Bool? {
        guard let json = try? await post("validate", ["license_key": key, "instance_id": handle]),
              json["valid"] is Bool else { return nil }
        return (try? accept(json, flag: "valid")) != nil
    }

    private func accept(_ json: [String: Any], flag: String) throws {
        guard json[flag] as? Bool == true else {
            throw LicenceFailure.rejected(json["error"] as? String ?? "rejected")
        }
        let status = (json["license_key"] as? [String: Any])?["status"] as? String
        guard status == "active" || status == "inactive" else {
            throw LicenceFailure.rejected(status ?? "no status")
        }
        guard let v = (json["meta"] as? [String: Any])?["variant_id"] as? Int, variantIDs.contains(v) else {
            throw LicenceFailure.wrongProduct
        }
    }

    /// Errors come back as a 4xx with a JSON body carrying `error`: read whatever the status.
    private func post(_ path: String, _ form: [String: String]) async throws -> [String: Any] {
        try await LicenceHTTP.send(LicenceHTTP.form(api.appendingPathComponent(path), form)).json
    }
}
#endif
```

### Keygen

The policy's authentication strategy must be `LICENSE` or `MIXED`, or the machine calls
are refused. The handle is the machine id; the fingerprint is a SHA-256 of the Mac's
hardware UUID, so the raw identifier never leaves the Mac.

```swift
#if DIRECT
import CryptoKit
import IOKit

/// Keygen — validate-key needs no auth; machines are created and deleted under the key itself.
struct Keygen: LicenceProvider {
    let account: String                                     // <ACCOUNT_ID>, public
    let product: String                                     // <PRODUCT_ID>; empty means not configured
    var isConfigured: Bool { !product.isEmpty && !account.isEmpty }
    private var api: URL { URL(string: "https://api.keygen.sh/v1/accounts/\(account)/")! }

    /// Before activation a node-locked licence answers NO_MACHINE: that is a good key.
    private static let unactivated: Set<String> = ["VALID", "NO_MACHINE", "NO_MACHINES"]

    func check(_ key: String) async throws { _ = try await licenceID(key) }

    func activate(_ key: String) async throws -> String {
        let body: [String: Any] = ["data": [
            "type": "machines",
            "attributes": ["fingerprint": Self.fingerprint, "platform": "macOS",
                           "name": Host.current().localizedName ?? "Mac"],
            "relationships": ["license": ["data": ["type": "licenses", "id": try await licenceID(key)]]],
        ]]
        var req = request("machines", method: "POST", key: key)
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (status, json) = try await LicenceHTTP.send(req)
        if status == 201, let id = (json["data"] as? [String: Any])?["id"] as? String { return id }
        if errorCode(json) == "FINGERPRINT_TAKEN" { return Self.fingerprint }   // already active on this Mac
        throw LicenceFailure.rejected(errorDetail(json) ?? "not activated")
    }

    func deactivate(_ key: String, handle: String) async throws {
        let (status, json) = try await LicenceHTTP.send(request("machines/\(handle)", method: "DELETE", key: key))
        guard status == 204 else { throw LicenceFailure.rejected(errorDetail(json) ?? "not deactivated") }
    }

    func verdict(_ key: String, handle: String) async -> Bool? {
        guard let json = try? await validate(key, fingerprint: true),
              let valid = (json["meta"] as? [String: Any])?["valid"] as? Bool else { return nil }
        return valid
    }

    /// Contract 1, 4, 5 in one call: the licence id, or why not.
    private func licenceID(_ key: String) async throws -> String {
        let json = try await validate(key, fingerprint: false)
        let code = (json["meta"] as? [String: Any])?["code"] as? String ?? errorCode(json) ?? "no answer"
        if code == "PRODUCT_SCOPE_MISMATCH" { throw LicenceFailure.wrongProduct }
        guard Self.unactivated.contains(code), let id = (json["data"] as? [String: Any])?["id"] as? String else {
            throw LicenceFailure.rejected(code)              // NOT_FOUND, SUSPENDED, EXPIRED, TOO_MANY_MACHINES…
        }
        return id
    }

    private func validate(_ key: String, fingerprint: Bool) async throws -> [String: Any] {
        var scope = ["product": product]
        if fingerprint { scope["fingerprint"] = Self.fingerprint }
        var req = request("licenses/actions/validate-key", method: "POST", key: nil)
        req.httpBody = try JSONSerialization.data(withJSONObject: ["meta": ["key": key, "scope": scope]])
        return try await LicenceHTTP.send(req).json
    }

    private func request(_ path: String, method: String, key: String?) -> URLRequest {
        var req = URLRequest(url: api.appendingPathComponent(path))
        req.httpMethod = method
        req.setValue("application/vnd.api+json", forHTTPHeaderField: "Accept")
        req.setValue("application/vnd.api+json", forHTTPHeaderField: "Content-Type")
        if let key { req.setValue("License \(key)", forHTTPHeaderField: "Authorization") }
        return req
    }

    private func firstError(_ json: [String: Any]) -> [String: Any]? { (json["errors"] as? [[String: Any]])?.first }
    private func errorCode(_ json: [String: Any]) -> String? { firstError(json)?["code"] as? String }
    private func errorDetail(_ json: [String: Any]) -> String? { firstError(json)?["detail"] as? String }

    /// SHA-256 of IOPlatformUUID, hex: stable per Mac, URL-safe, and not the raw hardware id.
    static let fingerprint: String = {
        let service = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("IOPlatformExpertDevice"))
        defer { IOObjectRelease(service) }
        let uuid = IORegistryEntryCreateCFProperty(service, "IOPlatformUUID" as CFString, kCFAllocatorDefault, 0)?
            .takeRetainedValue() as? String ?? Host.current().localizedName ?? "unknown"
        return SHA256.hash(data: Data(uuid.utf8)).map { String(format: "%02x", $0) }.joined()
    }()
}
#endif
```

### Gumroad

Gumroad keeps a **count** of verifications, not a list of Macs, and lowering the count
needs the seller's token. So the activation limit is the app's own (`maxActivations`),
every call except `activate` turns the counter **off**, and deactivation goes through a
server the owner runs (`deactivationServer`, which calls `decrement_uses_count` with the
token) — or, without one, only clears this Mac and leaves the count for support to
reset. Say which in the UI.

```swift
#if DIRECT
/// Gumroad — licences/verify needs no auth; the key and the product id are the whole request.
struct Gumroad: LicenceProvider {
    let productID: String                                   // <PRODUCT_ID>; empty means not configured
    let maxActivations: Int                                 // the app's own limit
    /// The owner's server that decrements the count, e.g. https://<your-server>/licence/deactivate.
    /// nil: deactivating clears this Mac only, and the count stays until support resets it.
    let deactivationServer: URL?
    private let verify = URL(string: "https://api.gumroad.com/v2/licenses/verify")!

    var isConfigured: Bool { !productID.isEmpty && maxActivations > 0 }

    func check(_ key: String) async throws {
        let json = try accept(try await call(key, count: false))
        guard (json["uses"] as? Int ?? 0) < maxActivations else {
            throw LicenceFailure.rejected("activation limit reached — deactivate another Mac first")
        }
    }

    func activate(_ key: String) async throws -> String {
        let json = try accept(try await call(key, count: true))   // the one counted call
        guard (json["uses"] as? Int ?? 0) <= maxActivations else {
            throw LicenceFailure.rejected("activation limit reached")
        }
        return ""                                           // Gumroad has no per-Mac handle
    }

    func deactivate(_ key: String, handle: String) async throws {
        guard let server = deactivationServer else { return }  // local only — see above
        let (status, _) = try await LicenceHTTP.send(LicenceHTTP.form(server, ["license_key": key,
                                                                                 "product_id": productID]))
        guard (200..<300).contains(status) else { throw LicenceFailure.rejected("not deactivated") }
    }

    func verdict(_ key: String, handle: String) async -> Bool? {
        guard let reply = try? await call(key, count: false), reply.json["success"] is Bool else { return nil }
        return (try? accept(reply)) != nil
    }

    private func call(_ key: String, count: Bool) async throws -> (status: Int, json: [String: Any]) {
        try await LicenceHTTP.send(LicenceHTTP.form(verify, ["product_id": productID, "license_key": key,
                                                             "increment_uses_count": count ? "true" : "false"]))
    }

    /// The product is matched by the request: another product's key, or a disabled one, is a
    /// 404 with success:false. success:true
    /// alone does not say the purchase still stands — refunds and chargebacks are separate fields.
    @discardableResult
    private func accept(_ reply: (status: Int, json: [String: Any])) throws -> [String: Any] {
        let json = reply.json
        guard json["success"] as? Bool == true, let purchase = json["purchase"] as? [String: Any] else {
            throw LicenceFailure.rejected(json["message"] as? String ?? "not valid for this product")
        }
        if purchase["refunded"] as? Bool == true || purchase["chargebacked"] as? Bool == true {
            throw LicenceFailure.rejected("the purchase was refunded")
        }
        if let ended = purchase["subscription_ended_at"], !(ended is NSNull) {
            throw LicenceFailure.rejected("the subscription has ended")
        }
        return json
    }
}
#endif
```

**Paddle Billing, or keys you issue yourself** — the provider is your server (or Keygen
behind the `transaction.completed` webhook), and `LicenceProvider` is the API that
server has to offer: write its type against your own endpoints, the same way.

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
- [ ] **Relaunch a few times online** — the activation count in the dashboard does not
      move: re-validation spends no seat (on Gumroad, the counter is off).
- [ ] **Product id not configured** — activation refuses with a message, and never
      calls the API.
- [ ] **App Store build** — the `strings` check above prints nothing.
