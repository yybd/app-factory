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
├── appstoreconnect/
│   ├── AuthKey_<KEYID>.p8  the App Store Connect API key
│   └── notarytool/         the notarisation profile, when one is kept as a file
└── android/
    ├── api-fastlane-supply/<service-account>.json    Google Play
    └── <app>-keystore/keystore.properties           one upload key per app
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
                       "p8": "appstoreconnect/AuthKey_<KEYID>.p8" },
  "notary":          { "keychain_profile": "<a name you chose>" },
  "googleplay":      { "service_account": "android/api-fastlane-supply/<file>.json",
                       "keystores": { "<app>": "android/<app>-keystore/keystore.properties" } }
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
   in `android/api-fastlane-supply/` is an answer; none or several is not, because the
   filename is issued by the Play Console and guessing which account a release goes out
   under is the one mistake that cannot be undone.
4. **A data repo's `DATA.md`**, for an installation that predates this file. Still read,
   so nothing breaks — and reported as legacy, because a fallback nobody is told about
   becomes the real mechanism.

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

Two fallbacks exist for a tree that has grove: `keys_root` in its registry, relative to
the tree's base, and failing that a `keys` folder beside the other repos —
`factory/deploy.py` then writes the variable into the machine's settings so a shell has
it too. Neither is required, and nothing here fails for want of grove.

## What this does not protect against

A credential pasted into a chat. A key committed before any of this was installed. A
machine someone else has. Rotation — nothing here tracks the age of a key, and an App
Store Connect key that is revoked in the console keeps working here until it does not.
None of that is in this project's power to fix, and saying so is more useful than
implying otherwise.
