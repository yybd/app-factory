*English · [עברית](hub.he.md)*

# The hub contract

**What the hub is.** One repository holding the *data* of every app you ship — its
profile, its store listings in every language, its media, its prices. Not code, and not a
website: the things the shipping skills read from and write to.

**Why it exists as a separate repo.** The same facts are needed in several places at once
— an app's description belongs in the App Store, in Google Play, and on its web page — and
each of those lives in a different repo with a different release rhythm. Keeping the facts
in any one of them makes the other two copies. Keeping them in the hub makes all three
derived.

**Why this document exists.** **32 of the 39 skills can read `$APP_HUB`, and every one of them works
without it.** A hub is what makes several apps share one source of truth; with one app
it is overhead, and the skills detect its absence rather than assuming it.

For those who want one, the structure they rely on existed only as a convention among
them — dozens of references to `DATA.md` and not one page saying what it must contain.
This is that page.

> `python3 factory/init_hub.py --create` builds the skeleton described here.
> `python3 factory/init_hub.py` reports what is present and what is missing.

---

## The shape

```
<hub>/
├── DATA.md                    studio-wide facts every app shares
├── PRODUCT.md                 the product voice — the master any site inherits from
├── prices.json                every app's price, in one file          [price-sync]
├── scripts/
│   └── verify_prices.py       asks the stores whether they still agree  [optional]
└── <slug>/                    one directory per app
    ├── profile.md             THE source of truth for all copy
    ├── profile.<lang>.md      a read-only translation for the owner   [app-profile]
    ├── README.md              where the launch STANDS — blockers, gaps, open
    │                          decisions. Volatile, and written by `launch-app`.
    ├── store/
    │   ├── apple/
    │   │   ├── metadata/<locale>/           name, subtitle, description, keywords…
    │   │   ├── metadata/review_information/ contact details, demo credentials
    │   │   ├── release-notes/<version>/<locale>.txt   "What's New", per version
    │   │   └── iap/<product-id>/            per-locale display name, description, price
    │   └── play/
    │       ├── metadata/<locale>/           title, short and full description
    │       ├── changelogs/<versionCode>/<locale>.txt
    │       └── iap/<product-id>/
    └── media/
        ├── apple/<App>/<locale>/{screenshots,app-preview,iap,raw}/
        └── play/<locale>/images/phoneScreenshots/   (+ icon-512.png)
```

**`<slug>` is the app's name in the hub**, and the same slug is used by the site (in a
privacy-policy path) and by the registry (`hub_slug`). One name across three places is
what lets a skill move between them without being told.

---

## `DATA.md` — the studio's shared facts

Read by **35 references across the skills**, more than any other file here. It holds what
every app shares, so that no skill has to ask you or invent it.

| Key | Who reads it | What breaks without it |
|---|---|---|
| **Contact** — name, email, phone | `app-store-metadata`, `store-metadata-writer` | the App Store review-information block cannot be filled; submission is rejected |
| **Copyright** — e.g. `2026 <Studio Name>` | `app-store-metadata` | `copyright.txt` is missing from the listing |
| **Default URLs** — marketing / support / privacy, with `{app-slug}` substituted | `app-profile`, `store-metadata-writer` | every app is asked for its URLs by hand, and they drift apart |
| **App Store Connect API key** — issuer id, key id, and the **path** to the `.p8` | `app-store-deliver`, `ship-apple-app` | nothing can be uploaded to App Store Connect |
| **Play service account** — the path to its JSON | `play-store-deliver`, `play-store-ship` | nothing can be uploaded to Google Play |
| **`conversational language`** *(optional)* | every skill | nothing breaks — without it, skills answer in the language you write in |

> **The keys themselves are never here, and never in any repo.** `DATA.md` holds
> **identifiers and paths**; the secret files live under `$KEYS_ROOT`, which is not a git
> directory. See [`factory/init_keys.py`](../../factory/init_keys.py).

---

## `PRODUCT.md` — the voice

The master description of how the product sounds: what it says, what it never says, the
words it uses and the words it refuses. Every skill that writes customer-facing text reads
it, and `copy-edit` enforces it.

A site repo may carry its own `PRODUCT.md` that **inherits** from this one and overrides
only site-specific presentation. If you have no website, this file alone is enough.

**Without it** the skills still work — they simply have no shared voice to hold to, and
each piece of copy sounds like whoever wrote it.

---

## `<slug>/profile.md` — the source of truth for all copy

**The single most important file in the hub**, and the only one whose absence stops work
rather than degrading it: no store copy is written before the profile exists, and no skill
invents what is not in it.

Written by `app-profile`, which reads the app's source and interviews you. Read by
`store-metadata-writer`, `app-store-metadata`, `aso-keywords`, `play-store-metadata`,
`appstore-media` (for screen order and captions), and the site skills.

Its sections, as the template defines them: what the app is · positioning · platforms and
distribution · links · key features · advantages · market context · target users · voice
notes · a reusable "derived copy" block.

**Without it:** every copy skill stops and asks for it. That is deliberate — copy invented
per surface is how an app ends up described three different ways in three places.

---

## `prices.json` — one price, one file

Read and reconciled by `price-sync`, whose whole job is that a price lives in **eight
places** and they drift. This file is the hub's answer to the question "what should it be",
and `$APP_HUB/scripts/verify_prices.py` — if you have it — is the answer to "what is it actually",
asked live of the stores.

**Without it** `price-sync` has nothing to reconcile against, and the other seven places
are simply seven independent opinions.

---

## What is required, and what is optional

**Nothing here is required to install the factory.** The mechanics — the registry, the
guards, `close.py`, the checks — know nothing about a hub.

For the **store tracks**, the order in which things start to matter:

| | Needed for |
|---|---|
| `<slug>/profile.md` | any copy work at all — this is the floor |
| `DATA.md` contact + copyright | submitting to the App Store |
| `DATA.md` API key path | uploading to either store |
| `<slug>/store/…` | it is created by the skills; you do not author it by hand |
| `<slug>/media/…` | screenshots — created by `appstore-media` |
| `PRODUCT.md` | a consistent voice across apps |
| `prices.json` | reconciling a price across places |

---

## Two rules that come from measurement, not taste

**The hub is the source of truth; `fastlane/` is derived.** The app repo's `fastlane/`
directory is written **only** by the deliver skills' sync, at deliver time, with
`rsync --delete`. Anything written there by hand disappears on the next run. Text belongs
in the hub; `fastlane/` is how it reaches the store.

**And the store can be ahead of the hub.** Somebody edits a listing in the console, and
from that moment the hub is stale without anything saying so. Both deliver skills therefore
run a mandatory *pull and compare* before uploading: `in sync` continues, `hub adds` is
safe, and a **conflict stops** — you look at it, and back-port into the hub what you want to
keep. "The hub is the SoT" is not a licence to overwrite what somebody wrote somewhere else.
