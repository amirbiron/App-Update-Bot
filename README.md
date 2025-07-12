# 📱 Telegram App Updates Monitor Bot

**בוט טלגרם למעקב אחר עדכוני אפליקציות פופולריות**

מקבל התראות מיידיות כשיוצאים עדכונים חדשים ל-WhatsApp, Telegram, Instagram ועוד!

## ✨ תכונות עיקריות

- 🔍 **מעקב אוטומטי** אחר עדכוני אפליקציות פופולריות
- 📨 **התראות מיידיות** בטלגרם על עדכונים חדשים
- 🌐 **מקורות מהימנים** - שימוש ב-RSS feeds של APKMirror
- ☁️ **רצה בענן 24/7** ללא צורך בתחזוקה
- 🇮🇱 **תמיכה מלאה בעברית** - הודעות וממשק

## 📱 אפליקציות במעקב

- **WhatsApp** 💬 - אפליקציית ההודעות הפופולרית
- **Telegram** ✈️ - אפליקציית הודעות מתקדמת
- **Instagram** 📸 - רשת חברתית לתמונות ווידאו

*קל להוסיף אפליקציות נוספות!*

## 🚀 התקנה מהירה (5 דקות)

### שלב 1: יצירת בוט בטלגרם
1. פתח שיחה עם [@BotFather](https://t.me/BotFather)
2. שלח `/newbot`
3. בחר שם לבוט (לדוגמה: "App Updates Monitor")
4. בחר שם משתמש לבוט (חייב להסתיים ב-`bot`)
5. **שמור את הטוקן שתקבל!** 🔑

### שלב 2: קבלת Chat ID
1. הוסף את הבוט לקבוצה/ערוץ שבו תרצה לקבל עדכונים
2. שלח הודעה כלשהי בקבוצה/ערוץ
3. בקר בכתובת: `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates`
4. חפש בתוצאה את `"chat":{"id": מספר}` ושמור את המספר

### שלב 3: העלאה ל-GitHub
```bash
# צור ריפו חדש בגיטהאב, ואז:
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# העתק את כל הקבצים לתיקייה
# ואז:
git add .
git commit -m "Initial commit - Telegram App Monitor Bot"
git push origin main
```

### שלב 4: Deploy ל-Render (חינמי!)
1. הירשם ל-[Render.com](https://render.com)
2. לחץ "New" → "Background Worker"
3. חבר את הריפו מ-GitHub
4. **הגדר משתני סביבה:**
   - `BOT_TOKEN`: הטוקן שקיבלת מ-BotFather
   - `CHAT_ID`: מזהה הצ'אט שמצאת
5. לחץ "Create Background Worker"

**זהו! הבוט יתחיל לעבוד תוך דקות ספורות** 🎉

## 🔧 התאמות אישיות

### הוספת אפליקציות נוספות
ערוך את הקובץ `main.py` והוסף לרשימת `rss_feeds`:

```python
self.rss_feeds = {
    'WhatsApp': 'https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/',
    'Telegram': 'https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/',
    'Instagram': 'https://www.apkmirror.com/apk/instagram/instagram-instagram/feed/',
    # הוסף כאן:
    'YouTube': 'https://www.apkmirror.com/apk/google-inc/youtube/feed/',
    'Facebook': 'https://www.apkmirror.com/apk/facebook-2/facebook/feed/',
    'TikTok': 'https://www.apkmirror.com/apk/tiktok-pte-ltd/tik-tok/feed/',
}
```

### שינוי תדירות הבדיקות
```python
# במקום שעה (3600), בדוק כל 30 דקות:
await asyncio.sleep(1800)  # 30 * 60 = 1800 שניות
```

### התאמת פורמט ההודעות
ערוך את הפונקציה `send_update_notification` לשנות את מבנה ההודעה.

## 📋 מבנה הפרויקט

```
telegram-app-monitor/
├── main.py              # 🤖 קוד הבוט הראשי
├── test.py              # 🧪 script לבדיקות מקומיות
├── requirements.txt     # 📦 רשימת ספריות
├── render.yaml         # ☁️ הגדרות Render
├── .gitignore          # 🔒 קבצים שלא יועלו לגיט
└── README.md           # 📖 התיעוד הזה
```

## � תיקונים אחרונים

### שיפורים שבוצעו:
- ✅ **תיקון שם קובץ** - `.gitignore` במקום `gitignore.`
- ✅ **הוספת MONGO_URI** ל-`render.yaml` - נדרש לפעולת הבוט
- ✅ **שיפור טיפול בשגיאות** - הוספת try-catch blocks בכל הפונקציות
- ✅ **בדיקת חיבור MongoDB** - וידוא שהחיבור עובד לפני הפעלת הבוט
- ✅ **שיפור לוגים** - הוספת הודעות debug ו-info מפורטות יותר
- ✅ **טיפול טוב יותר בשגיאות רקע** - retry mechanism בלולאת הבדיקות
- ✅ **הוספת health check endpoint** - לבדיקת תקינות השירות
- ✅ **שיפור startup script** - בדיקת dependencies ו-environment variables
- ✅ **הוספת בדיקות MongoDB** לקובץ test.py

### קבצים חדשים שנוספו:
- `app.py` - שילוב של Flask health check ו-Telegram bot
- `startup.py` - script לבדיקת סביבה לפני הפעלת הבוט

## �🛠️ פיתוח מקומי

אם תרצה לבדוק את הבוט במחשב שלך לפני העלאה לענן:

```bash
# שכפול הפרויקט
git clone https://github.com/yourusername/telegram-app-monitor.git
cd telegram-app-monitor

# יצירת סביבה וירטואלית
python -m venv venv

# הפעלת הסביבה הוירטואלית
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# התקנת ספריות
pip install -r requirements.txt

# הגדרת משתני סביבה
export BOT_TOKEN="your_bot_token_here"
export CHAT_ID="your_chat_id_here"

# בדיקת המערכת
python test.py

# הרצת הבוט
python main.py
```

## 📊 מעקב ו-Logs

הבוט כולל מערכת logging מפורטת:

- ✅ **עדכונים חדשים** - יירשם כל עדכון שנמצא
- ⚠️ **שגיאות RSS** - בעיות בקריאת מקורות המידע
- 📨 **סטטוס הודעות** - האם ההודעות נשלחו בהצלחה
- 🔄 **מחזורי בדיקה** - כל בדיקה שמתבצעת

### צפייה ב-Logs ב-Render:
1. כנס לדשבורד של Render
2. בחר את השירות שלך
3. לחץ על "Logs"
4. ראה את הפעילות בזמן אמת

## 🎯 הרחבות מתוכננות

- [ ] **סיכום עדכונים בעברית** עם בינה מלאכותית
- [ ] **בחירת אפליקציות** דרך הבוט עצמו
- [ ] **שמירת היסטוריה** של כל העדכונים
- [ ] **תמיכה במקורות נוספים** מעבר ל-APKMirror
- [ ] **כפתורי הורדה מהירים** בהודעות
- [ ] **התראות מותאמות אישית** לכל משתמש

## 🆘 פתרון בעיות נפוצות

### הבוט לא שולח הודעות
1. ✅ בדוק שהטוקן נכון ב-Render
2. ✅ בדוק שה-Chat ID נכון
3. ✅ ודא שהבוט הוסף לקבוצה/ערוץ
4. ✅ בדוק את הלוגים ב-Render

### בעיות ב-RSS feeds
1. ✅ בדוק חיבור לאינטרנט
2. ✅ ודא שאתרי APKMirror פעילים
3. ✅ בדוק תקינות קישורי ה-RSS

### הבוט מפסיק לעבוד
1. ✅ בדוק את הלוגים לשגיאות
2. ✅ עשה Redeploy ב-Render
3. ✅ ודא שהמשתני סביבה נכונים

## 📞 תמיכה ויצירת קשר

נתקלת בבעיה או יש לך רעיון לשיפור?

1. 🐛 **באג או בעיה טכנית** - פתח Issue בגיטהאב
2. 💡 **רעיון לשיפור** - צור Pull Request
3. ❓ **שאלות כלליות** - צור Discussion

## 🤝 תרומה לפרויקט

הפרויקט פתוח לתרומות!

1. עשה Fork לפרויקט
2. צור Branch חדש לשינוי שלך
3. בצע את השינויים
4. שלח Pull Request

## ⭐ תן כוכב!

אם הבוט עזר לך, אל תשכח לתת כוכב ⭐ לפרויקט בגיטהאב!

## 📜 רישיון

MIT License - חופשי לשימוש, שינוי והפצה.

---

<div dir="rtl">

**נוצר באהבה בישראל** 🇮🇱

*בוט שמרכז את כל עדכוני האפליקציות החשובות במקום אחד!*

</div>

---

### סטטיסטיקות

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Telegram](https://img.shields.io/badge/telegram-bot-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)