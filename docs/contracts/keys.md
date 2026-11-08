*English · [עברית](keys.he.md)*

# `$KEYS_ROOT` — what the shipping skills need, and what they never do with it

Every skill that signs or uploads needs a secret that must never be in a repo. They are
named as `$KEYS_ROOT/…` and nowhere as a path, so the folder can be called anything and
live anywhere — an external disk, a mounted vault — but it has to **exist**, and on a
fresh machine it does not. That gap used to surface halfway through a release, as a
file-not-found on a key.

```bash
python3 factory/init_keys.py            # what is there, what is missing
python3 factory/init_keys.py --create   # make it
python3 factory/init_keys.py --point ~/vault/studio-keys   # use one you already have
```

---

## The shape

```
$KEYS_ROOT/
├── .gitignore              refuses everything, written FIRST
├── credentials.json        where each credential is — identifiers and PATHS only
├── APPLE.md                OPTIONAL — the Apple account's map, written by apple-credentials
├── signing/                what signs
│   ├── android/<app>/      keystore.properties + its .jks — one upload key per app
│   ├── apple/              <type>-<YYYY-MM-DD>.p12 backups + p12-password.txt
│   └── sparkle/            sparkle_private_key.txt — the Mac update key
├── store-api/              what talks to a store
│   ├── appstoreconnect/<name>/   api_key.json + private_keys/AuthKey_<KEYID>.p8,
│   │                             one folder per purpose (uploads, notarytool, …)
│   ├── googleplay/<service-account>.json   Google Play
│   └── appleads/           OPTIONAL — Apple Ads API: api_key.json + private-key.pem
│                           (aso-keywords reads search popularity; nothing needs it)
├── services/               other services: google/, ai/<provider>/, <name>/
├── projects/<name>/        secrets that belong to one project
└── accounts/               recovery codes, account notes
```

`.gitignore` is written before anything can be put in the folder, and refuses everything
except itself and the README. That order is the point: a folder that becomes protected
after the first key is in it was unprotected at the only moment that mattered.

## `credentials.json` — the one file that says where things are

It holds **identifiers and paths. Never a secret.** A path may be absolute or relative
to the folder.

```json
{
  "appstoreconnect": { "issuer_id": "<uuid>", "key_id": "<10 chars>",
                       "p8": "store-api/appstoreconnect/<name>/private_keys/AuthKey_<KEYID>.p8" },
  "notary":          { "keychain_profile": "<a name you chose>" },
                  /* or: { "key_id": "<10 chars>", "p8": "store-api/appstoreconnect/notarytool/…/AuthKey_<KEYID>.p8" } */
  "googleplay":      { "service_account": "store-api/googleplay/<file>.json",
                       "keystores": { "<app>": "signing/android/<app>/keystore.properties" } }
}
```

**Why this file exists at all.** Three mechanisms answered "where is the credential"
before it, and they disagreed: one read an issuer id out of labelled prose in a markdown
file in another repo, one looked in a fixed folder, one grepped a heading. The first
cannot be asked of anyone else — it is a convention in one studio's document.

## Where each track looks, in order

Each track resolves its own credentials — Apple needs none of Google's. The order is the
same in both, and each says which source answered:

1. **The environment.** `ASC_KEY_ID` / `ASC_ISSUER_ID` / `ASC_KEY_PATH`,
   `PLAY_SERVICE_ACCOUNT`, `NOTARY_PROFILE`. CI sets variables; it does not keep a file.
2. **`$KEYS_ROOT/credentials.json`.** The documented answer.
3. **The folder convention**, where it is unambiguous. Exactly one service-account JSON
   in `store-api/googleplay/` is an answer; none or several is not, because the
   filename is issued by the Play Console and guessing which account a release goes out
   under is the one mistake that cannot be undone.
   The upload keystore of an app is looked for in `signing/android/<app>/`.
4. **The legacy layout's folders**, last — see below.
5. **A data repo's `DATA.md`**, for an installation that predates this file. Still read,
   so nothing breaks — and reported as legacy, because a fallback nobody is told about
   becomes the real mechanism.

## The legacy layout

Until 2026-11 the folders sat at the top level. The resolvers
(`plugins/*/shared/credentials.py`, `LAYOUT`) still read them, **as the last fallback**,
and say so when that is where the answer came from; `init_keys.py` reports them and
never creates them.

| legacy | current |
|---|---|
| `android/<app>-keystore/` | `signing/android/<app>/` |
| `android/api-fastlane-supply/` | `store-api/googleplay/` |
| `appstoreconnect/` | `store-api/appstoreconnect/` |
| `appleads/` | `store-api/appleads/` |
| `apple-certificates/` | `signing/apple/` |
| `Sparkle/` | `signing/sparkle/` |

A `credentials.json` that names a legacy path keeps working while the file is there —
it is a path like any other. Move the files, then update the paths in it.

## What the skills do, and do not do

- They read the files **in place** and hand the path to the tool that needs it.
- **Nothing prints** a key, a password, a token or a `.p8`'s contents.
- **Nothing copies** a credential into a repo, and nothing commits one.
- A notary credential is not a file this holds at all: `notarytool store-credentials`
  puts it in the login keychain, and the skills use the profile **name**.

## Where `$KEYS_ROOT` is decided

**`KEYS_ROOT` in the environment is the answer**, and for most installations it is the
only one: set it in your shell, or in `~/.claude/settings.json` under `env`, and every
resolver and every tool here reads it. `factory/init_keys.py --create` makes the folder
and tells you what to set.

Two fallbacks exist for a tree that has RepoGuards: `keys_root` in its registry, relative to
the tree's base, and failing that a `keys` folder beside the other repos —
`factory/deploy.py` then writes the variable into the machine's settings so a shell has
it too. Neither is required, and nothing here fails for want of RepoGuards.

## What this does not protect against

A credential pasted into a chat. A key committed before any of this was installed. A
machine someone else has. Rotation — nothing here tracks the age of a key, and an App
Store Connect key that is revoked in the console keeps working here until it does not.
None of that is in this project's power to fix, and saying so is more useful than
implying otherwise.
