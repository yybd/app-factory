*[English](keys.md) · עברית*

# `$KEYS_ROOT` — מה סקילי השליחה צריכים, ומה הם לעולם לא עושים עם זה

כל סקיל שחותם או מעלה צריך סוד שאסור שיהיה בריפו. הם נקובים כ-`$KEYS_ROOT/…` ובשום
מקום כנתיב, כך שהתיקייה יכולה להיקרא בכל שם ולשבת בכל מקום — דיסק חיצוני, כספת
מחוברת — אבל היא חייבת **להתקיים**, ועל מכונה חדשה היא לא. הפער הזה נהג לצוץ באמצע
שחרור, כ-file-not-found על מפתח.

```bash
python3 factory/init_keys.py            # מה יש, מה חסר
python3 factory/init_keys.py --create   # ליצור
python3 factory/init_keys.py --point ~/vault/studio-keys   # להשתמש באחת שכבר יש
```

---

## המבנה

```
$KEYS_ROOT/
├── .gitignore              מסרב להכול, נכתב ראשון
├── credentials.json        איפה כל אישור — מזהים ונתיבים בלבד
├── APPLE.md                אופציונלי — המפה של חשבון אפל, apple-credentials כותב אותה
├── signing/                מה שחותם
│   ├── android/<app>/      keystore.properties וה-.jks שלו — מפתח העלאה אחד לכל אפליקציה
│   ├── apple/              גיבויי <type>-<YYYY-MM-DD>.p12 ו-p12-password.txt
│   └── sparkle/            sparkle_private_key.txt — המפתח של עדכוני Mac
├── store-api/              מה שמדבר עם חנות
│   ├── appstoreconnect/<name>/   api_key.json ו-private_keys/AuthKey_<KEYID>.p8,
│   │                             תיקייה לכל שימוש (העלאות, notarytool, …)
│   ├── googleplay/<service-account>.json   Google Play
│   └── appleads/           אופציונלי — Apple Ads API: api_key.json + private-key.pem
│                           (aso-keywords קורא ממנו פופולריות חיפוש; שום דבר לא תלוי בו)
├── services/               שירותים אחרים: google/, ai/<provider>/, <name>/
├── projects/<name>/        סודות של פרויקט אחד
└── accounts/               קודי שחזור, הערות חשבון
```

ה-`.gitignore` נכתב **לפני** שאפשר לשים משהו בתיקייה, ומסרב להכול חוץ מעצמו ומה-README.
הסדר הוא העיקר: תיקייה שהפכה מוגנת אחרי שהמפתח הראשון כבר בתוכה הייתה לא מוגנת ברגע
היחיד שבו זה חשוב.

## `credentials.json` — הקובץ האחד שאומר איפה הדברים

הוא מחזיק **מזהים ונתיבים. לעולם לא סוד.** נתיב יכול להיות מוחלט או יחסי לתיקייה.

```json
{
  "appstoreconnect": { "issuer_id": "<uuid>", "key_id": "<10 תווים>",
                       "p8": "store-api/appstoreconnect/<name>/private_keys/AuthKey_<KEYID>.p8" },
  "notary":          { "keychain_profile": "<שם שבחרת>" },
                  /* או: { "key_id": "<10 תווים>", "p8": "store-api/appstoreconnect/notarytool/…/AuthKey_<KEYID>.p8" } */
  "googleplay":      { "service_account": "store-api/googleplay/<file>.json",
                       "keystores": { "<app>": "signing/android/<app>/keystore.properties" } }
}
```

**למה הקובץ הזה קיים בכלל.** שלושה מנגנונים ענו על "איפה האישור" לפניו, והם לא
הסכימו: אחד שלף issuer id מתוך **פרוזה מסומנת** בקובץ markdown בריפו אחר, אחד חיפש
בתיקייה קבועה, ואחד עשה grep לכותרת. את הראשון אי אפשר לבקש מאף אחד אחר — זו מוסכמה
במסמך של סטודיו אחד.

## איפה כל מסלול מחפש, לפי הסדר

כל מסלול פותר את האישורים של עצמו — אפל לא צריכה כלום מגוגל. הסדר זהה בשניהם, וכל אחד
אומר איזה מקור ענה:

1. **הסביבה.** `ASC_KEY_ID` / `ASC_ISSUER_ID` / `ASC_KEY_PATH`, `PLAY_SERVICE_ACCOUNT`,
   `NOTARY_PROFILE`. CI מגדיר משתנים; הוא לא מחזיק קובץ.
2. **`$KEYS_ROOT/credentials.json`.** התשובה המתועדת.
3. **מוסכמת התיקייה**, כשהיא חד-משמעית. קובץ JSON אחד בדיוק ב-`store-api/googleplay/`
   הוא תשובה; אפס או כמה אינם, כי שם הקובץ מונפק על ידי ה-Play Console, וניחוש תחת
   איזה חשבון יוצא שחרור הוא הטעות היחידה שאי אפשר לבטל.
   את מפתח ההעלאה של אפליקציה מחפשים ב-`signing/android/<app>/`.
4. **התיקיות של המבנה הישן**, אחרונות — ראו למטה.
5. **`DATA.md` של ריפו נתונים**, להתקנה שקדמה לקובץ הזה. עדיין נקרא, כדי ששום דבר לא
   יישבר — ומדווח כ-legacy, כי fallback שאיש לא סופר עליו הופך למנגנון האמיתי.

## המבנה הישן (legacy)

עד 2026-11 התיקיות ישבו ברמה העליונה. ה-resolvers
(`plugins/*/shared/credentials.py`, ‏`LAYOUT`) עדיין קוראים אותן, **כ-fallback האחרון**,
ואומרים כשהתשובה הגיעה משם; `init_keys.py` מדווח עליהן ולא יוצר אותן.

| ישן | נוכחי |
|---|---|
| `android/<app>-keystore/` | `signing/android/<app>/` |
| `android/api-fastlane-supply/` | `store-api/googleplay/` |
| `appstoreconnect/` | `store-api/appstoreconnect/` |
| `appleads/` | `store-api/appleads/` |
| `apple-certificates/` | `signing/apple/` |
| `Sparkle/` | `signing/sparkle/` |

`credentials.json` שנוקב בנתיב ישן ממשיך לעבוד כל עוד הקובץ שם — זה נתיב כמו כל נתיב.
מעבירים את הקבצים, ואז מעדכנים בו את הנתיבים.

## מה הסקילים עושים, ומה לא

- הם קוראים את הקבצים **במקומם** ומוסרים את הנתיב לכלי שצריך אותו.
- **שום דבר לא מדפיס** מפתח, סיסמה, טוקן או את תוכן ה-`.p8`.
- **שום דבר לא מעתיק** אישור לתוך ריפו, ושום דבר לא מקמט אחד.
- אישור נוטריזציה אינו קובץ שהתיקייה מחזיקה בכלל: `notarytool store-credentials` שם
  אותו ב-login keychain, והסקילים משתמשים ב**שם** הפרופיל.

## איפה `$KEYS_ROOT` נקבע

`KEYS_ROOT` בסביבה מנצח — זו דלת המילוט לכספת מחוץ לעץ שלך. אחרת זה `keys_root` ברישום
של RepoGuards, יחסית לבסיס העץ, ואם לא אז תיקיית `keys` ליד שאר הריפואים. שתי הנפילות
האחרונות קיימות רק לעץ שיש בו RepoGuards; `KEYS_ROOT` בסביבה הוא התשובה, ולרוב ההתקנות
הוא היחידה — הגדירו אותו במעטפת או ב-`~/.claude/settings.json` תחת `env`, ושום דבר
כאן לא נכשל בהיעדר RepoGuards.
`factory/deploy.py` כותב את המשתנה להגדרות של המכונה כדי שגם למעטפת יהיה.

## מפני מה זה לא מגן

אישור שהודבק לתוך צ'אט. מפתח שקומט לפני שכל זה הותקן. מכונה שיש למישהו אחר גישה
אליה. **החלפה תקופתית** — שום דבר כאן לא עוקב אחרי גיל של מפתח, ומפתח App Store
Connect שבוטל בקונסולה ממשיך לעבוד כאן עד שלא. אף אחד מאלה אינו בכוחו של הפרויקט הזה
לתקן, ולומר זאת מועיל יותר מלרמוז אחרת.
