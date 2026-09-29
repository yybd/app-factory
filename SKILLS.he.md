*[English](SKILLS.md) · עברית*

# סקילים ומסלולים במפעל האפליקציות

הכלל שקובע היכן סקיל יושב הוא: **סקיל שנדרש תוך כדי עבודה על אפליקציה יושב במפעל (בתוך מסלול רלוונטי); סקיל שנדרש רק כשעומדים בתוך פרויקט מסוים יושב בתוכו.**

למידע נוסף על מנגנון הטעינה והפריסה, ראו את [HOW-IT-WORKS.he.md](HOW-IT-WORKS.he.md).

---

## החלוקה בפועל (Tracks)

הסקילים במפעל מקובצים ל"מסלולים" (Tracks). איזה repo מקבל איזה מסלול נקבע תחת ה-`tracks` ברישום של grove — `$GROVE/tools/registry.json`.

**המעקות אינם כאן.** `grove` הוא marketplace נפרד, והוא **אופציונלי**. הוא מכריע איפה נטענים המסלולים מתוך רישום מרכזי אחד, וזו התשובה הנכונה ברגע שעובדים על כמה ריפואים. בלעדיו, `factory/enable.py` מדליק את המסלולים לפי ריפו.

| מסלול | כמות סקילים | לאיזה פרויקטים מיועד |
|---|---|---|
| `apple-track` | 16 | Repo של אפליקציה |
| `android-track` | 9 | Repo של אפליקציה |
| `shared-track` | 7 | Repo של אפליקציה **וגם** ההאב |
| `web-track` | 4 | האתר (Web) |
| `capacitor-track` | 2 | Repo של אפליקציה |
| `design-track` | 1 | אפליקציה והאתר כאחד |
| `factory-setup` | 1 | **בכל מקום** — ראו למטה |

*המספרים נספרו מהדיסק, ונבדקים: `factory/check_skills.py` נכשל ברגע שמספר שכתוב כאן מפסיק להתאים למה שיושב בפועל. מספרים שהועתקו ממסמך אחר יצאו שגויים שוב ושוב, ולכן הם כבר לא נסמכים על זיכרונו של אדם.*

---

### מסלול אפל (Apple Track)
כולל 16 סקילים: `ship-apple-app` · `app-store-deliver` · `app-store-metadata` · `app-store-review-compliance` · `app-store-reviews-responder` · `apple-credentials` · `code-signing-provisioning` · `apple-app-store-screenshots` · `appstore-media` · `apple-bug-flow-review` · `apple-hig-design-review` · `notarize-and-distribute` · `macos-direct-distribution` · `app-icon-generator` · `aso-keywords` · `localization-i18n`.

**הערה:** למרות שחלקם נראים גנריים (כמו מחולל אייקונים או לוקליזציה), הם ספציפיים למערכת של אפל (למשל מתעסקים עם `.xcstrings` או שדות ASO שקיימים רק שם).

### מסלול אנדרואיד (Android Track)
כולל 9 סקילים: `play-store-ship` · `android-credentials` · `play-store-compliance` · `play-store-metadata` · `play-store-media` · `android-icon-generator` · `play-store-deliver` · `play-store-reviews-responder` · `android-run-device`.

### חוצי-חנויות ומשותפים (Shared Track)
כולל 7 סקילים: 
* **כלים כלליים:** `prepare-app-release` (המתזמר הראשי) · `launch-app` (השקה ראשונה) · `app-identity` (החלטת השם לשתי החנויות) · `copy-edit`.
* **סקילי האב:** `app-profile` · `store-metadata-writer` · `price-sync`. 
אלה מופעלים תוך כדי עבודה על האפליקציה, אך כותבים נתונים הישר ל-Hub ולכן הם חייבים להיות משותפים ולא לשבת באחד משני המקומות.

### מסלול עיצוב (Design Track)
כולל סקיל 1: `frontend-design`. גנרי לחלוטין ונדרש בכל מקום שבו נבנה ממשק משתמש (HTML/CSS ב-Capacitor או באתר).

### מסלול אתרים (Web Track)
כולל 4 סקילים: `page-builder` · `web-design-guidelines` · `web-seo` · `content-site-structure`. מיועדים למבנה דף, SEO וביקורות של אתרים — ובנוסף פריסת המבנה של אתר תוכן רב-לשוני, שהוא הסקיל היחיד כאן שרץ **רק כשמבקשים אותו בשם**: הוא כותב עץ תוכן שלם לריפו, ולכן אסור לו להתחיל רק מפני שהוזכר אתר.

### `factory-setup`
סקיל אחד ו-hook אחד של `SessionStart`. **זה המסלול היחיד שדולק בכל מקום**, וזה בדיוק מה שהוא נועד לו: ריפו שבו איש לא הפעיל מסלול לא טוען סקילים, ונראה זהה לריפו שבו הסקילים החליטו שהם לא רלוונטיים. שניהם שתיקה. ה-hook אומר זאת פעם אחת לריפו, והסקיל מדליק את המסלולים הנכונים.

כש-grove מותקן, הסקילים `register-project` ו-`deploy` שלו עושים את אותה עבודה מרישום מרכזי, למי שעובד על הרבה ריפואים. אף אחד מהשניים אינו נדרש.

### סקילים מקומיים
לפרויקט יכולים להיות סקילים משלו, ב-`.claude/skills/` שלו. ריפו של אתר עשוי להחזיק את `add-app-to-site`, `translate-site`, `reference-page` — כל אחד מהם עורך אך ורק את הנכסים של אותו אתר, ולכן אין שום סיבה שייטענו במפעל או באפליקציה.

סקיל מקומי צריך להצהיר על מה שבבעלותו ב-`.claude/owns.json` של אותו ריפו, כדי שסשן שעומד במקום אחר ייחסם במקום לעקוף אותו בשקט. המפעל מדווח על כל סקיל מקומי שאין הצהרה שמכסה אותו.


---

## אפל ↔ אנדרואיד: מה משוקף ומה לא

| תפקיד | Apple | Android |
|---|---|---|
| בנייה והעלאה | `ship-apple-app` | `play-store-ship` |
| תעודות וחתימה | `apple-credentials` + `code-signing-provisioning` | `android-credentials` — אחד בלבד, כי באנדרואיד אין provisioning profiles |
| מדיניות החנות | `app-store-review-compliance` | `play-store-compliance` |
| קובצי הליסטינג | `app-store-metadata` | `play-store-metadata` |
| מסירת הליסטינג | `app-store-deliver` | `play-store-deliver` |
| מדיה | `appstore-media` (ייצור) + `apple-app-store-screenshots` (התאמת תמונה בודדת) | `play-store-media` — אחד בלבד, כי ל-Play אין טבלת גדלים לפי מכשיר |
| אייקונים | `app-icon-generator` | `android-icon-generator` |
| ביקורות משתמשים | `app-store-reviews-responder` | `play-store-reviews-responder` |
| ASO | `aso-keywords` — שדה 100 התווים הנסתר | **בתוך** `play-store-metadata`: ל-Play אין שדה מילות מפתח, ולכן הדירוג שלו קורא את הטקסט הגלוי |
| העלאת בילד למכשיר | — | `android-run-device` |
| ביקורת עיצוב | `apple-hig-design-review` | **פער.** אין כאן ביקורת Material או ביקורת נגישות לאנדרואיד |
| ביקורת באגים וזרימה | `apple-bug-flow-review` | `capacitor-bug-flow-review` מכסה מעטפת web; **אנדרואיד נייטיב הוא פער** |
| לוקליזציה בתוך האפליקציה | `localization-i18n` | `capacitor-localization` מכסה JS ו-HTML; **`strings.xml` הוא פער** |

**שלושת הפערים אמיתיים, והם נקובים בשמם בכוונה.** טבלת שיקוף שהייתה משמיטה אותם בשקט הייתה נקראת כשלמות. במקום שבו סקיל קיים רק בצד אחד, הסקיל של אותו צד אומר זאת בפרק ה-Boundaries שלו.

**למה חלק מהתפקידים הם סקיל אחד וחלק שניים.** כל פיצול הוכרע מתוך מה שהעבודה באמת היא, ולא מתוך סימטריה. לאפל יש שני סקילי תעודות כי יצירת תעודה ואבחון בילד שמסרב להיחתם הן שתי עבודות שונות עם קלטים שונים; לאנדרואיד יש אחד כי יש שם ארטיפקט אחד. לאפל יש שני סקילי מדיה כי ייצור של סט שלם והתאמה של תמונה בודדת הם שני סדרי גודל של עבודה.

## מי הבעלים של מה

נושא אחד, בעלים אחד. כל השאר נשענים עליו. זו הטבלה שמכריעה לאיזה סקיל לפנות כששניים נראים סבירים — וכל סקיל אומר את אותו הדבר מצדו שלו, בפרק ה-`Boundaries` שלו.

| נושא | הבעלים | מי נשען עליו |
|---|---|---|
| שם האפליקציה, כותרת המשנה ובלוק הזהות ב-README | `app-identity` | כל סקילי המטא-דאטה, ה-ASO והמדיה; רץ לפני כולם |
| פרופיל המוצר שממנו נכתב הכול | `app-profile` | `store-metadata-writer`, וכל סקיל של האתר |
| טקסט הליסטינג לשתי החנויות, מסונכרן ביניהן | `store-metadata-writer` | שני סקילי המטא-דאטה של החנויות |
| הקבצים, המגבלות והוולידציה של כל חנות | `app-store-metadata` · `play-store-metadata` | שני סקילי המסירה קוראים את מה שהם מייצרים |
| העלאת ליסטינג | `app-store-deliver` · `play-store-deliver` | אף אחד — הם משטח השליחה |
| בנייה, חתימה והעלאה של בינארי | `ship-apple-app` · `play-store-ship` | אף אחד |
| עץ המדיה הקנוני | `appstore-media` | `apple-app-store-screenshots` כותב לתוכו; סקילי המסירה מרכיבים ממנו |
| שדה מילות המפתח בן 100 התווים | `aso-keywords` | `app-store-metadata` כותב את מה שהוא מכריע |
| תעודות ופרטי גישה | `apple-credentials` · `android-credentials` | כל סקיל שחותם או מעלה |
| מחיר, בכל מקום שבו הוא מופיע | `price-sync` | אף אחד — והוא לעולם לא משנה מחיר |
| כל משפט שמופנה ללקוח | `copy-edit` | מורץ על כל דבר לפני שהוא יוצא |
| הסדר שבו שחרור גרסה מתרחש | `prepare-app-release` (עדכון) · `launch-app` (השקה ראשונה) | הם מניעים את כל השאר |

---

## נתיב מיוחד: Capacitor

אפליקציות Capacitor הן אפליקציות web בתוך מעטפת נייטיב, וסקילי האיכות הסטנדרטיים של אפל — שמחפשים קבצי `.strings` וממשק נייטיב — פשוט לא חלים עליהן. מכאן המסלול הייעודי:

* **`capacitor-localization`** — בודק מחרוזות ב-JavaScript ובתבניות ה-HTML, מזהה שגיאות תרגום אילמות (כמו מפתח עברית שמוצג למשתמש אנגלי) ובודק אחאות של תבניות שפה ולא סתם קרבה.
* **`capacitor-bug-flow-review`** — ה-QA של התפר שבין ה-Web למעטפת המובייל, מכיל קטלוג של מלכודות Capacitor מוכרות (למשל היעדר Web Share ב-Android WebView או צווארי בקבוק מוכרים של ביצועים) וכולל הנחיות כיצד לבדוק את ה-WebView דרך דפדפן שולחני.
