# AI Log Doctor 🩺

[English](README.md) | **עברית**

כלי Python שקורא קובצי לוג, מקבץ שגיאות חוזרות לפי "חתימה" משותפת, ושולח את הקבוצות הנפוצות ביותר ל־Google Gemini לניתוח. בסוף הוא מפיק דוח עם הסבר על סיבת השורש של כל שגיאה והצעה לתיקון.

אפשר להריץ אותו משורת הפקודה (CLI) או דרך ממשק גרפי (Tkinter).

## איך זה עובד

```
קובץ לוג ──► Parser ──► Grouper ──► LLM Client ──► Report
            (פירוק     (קיבוץ      (ניתוח עם      (Markdown /
             שורות)     שגיאות)     Gemini)         Text)
```

1. **פירוק (Parser)** – כל שורה מפורקת לזמן, רמה, רכיב והודעה. שורות שלא מתאימות לפורמט נספרות כ"שורות שדולגו".
2. **קיבוץ (Grouper)** – רק רשומות ברמת `ERROR`, `CRITICAL` או `FATAL` נכנסות לקיבוץ. ערכים שמשתנים בין מופע למופע (מספרים, כתובות IP, נתיבים, UUID, חותמות זמן, מחרוזות במירכאות, ערכי hex) מוחלפים בממלאי מקום, כך שהודעות כמו:
   ```
   User 812 not found
   User 1043 not found
   ```
   מקבלות את אותה חתימה: `api|User <INT> not found`. הקבוצות ממוינות לפי מספר המופעים.
3. **ניתוח AI (LLM Client)** – הקבוצות הנפוצות ביותר (ברירת מחדל: 5) נשלחות ל־Gemini עם עד 5 דוגמאות לכל קבוצה. המודל מחזיר JSON עם `root_cause` ו־`fix`. בשגיאות זמניות (timeout, ניתוק, HTTP 429/5xx) הבקשה נשלחת שוב עם המתנה שגדלה בכל ניסיון (exponential backoff).
4. **דוח (Report)** – סיכום כללי ואחריו פירוט לכל קבוצה: מספר מופעים, מתי הופיעה לראשונה ולאחרונה, הניתוח, ההצעה לתיקון ושורות לדוגמה.

## פורמט הלוג הנתמך

```
YYYY-MM-DD HH:MM:SS,mmm LEVEL [source] message
```

לדוגמה:

```
2026-11-14 10:01:15,442 ERROR [db] Connection timeout after 30s to host 10.0.0.12
```

- אפשר להפריד בין התאריך לשעה ברווח או ב־`T`, ולפני המילישניות אפשר לשים `,` או `.`.
- רמות נתמכות: `DEBUG`, `INFO`, `WARNING`/`WARN`, `ERROR`, `CRITICAL`, `FATAL`.

## דרישות

- **Python 3.12 ומעלה** (הקוד משתמש בתחביר f-string שנתמך רק מגרסה 3.12)
- מפתח API של Google Gemini. אפשר להוציא אחד ב־[Google AI Studio](https://aistudio.google.com/apikey). בלי מפתח עדיין אפשר לעבוד עם `--no-ai`.

## התקנה

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

## הגדרה

מעתיקים את `.env.example` לקובץ בשם `.env` וממלאים את הערכים:

```env
GEMINI_API_KEY=המפתח_שלך_כאן
GEMINI_MODEL=gemini-flash-lite-latest
```

| משתנה | חובה | תיאור |
|-------|------|-------|
| `GEMINI_API_KEY` | כן (חוץ מהרצה עם `--no-ai`) | מפתח ה־API של Gemini |
| `GEMINI_MODEL` | לא | שם המודל. ברירת המחדל היא `gemini-flash-lite-latest` |

כדי לראות אילו מודלים זמינים למפתח שלך:

```bash
python sample_logs/ex.py
```

## שימוש

### שורת פקודה

```bash
# ניתוח מלא עם AI, הדוח נשמר ב־report.md
python main.py sample_logs/app.log

# רק פירוק וקיבוץ, בלי לפנות ל־AI
python main.py sample_logs/app.log --no-ai

# לנתח את 3 הקבוצות הנפוצות ביותר ולשמור דוח טקסט
python main.py sample_logs/app.log --top 3 --format text --output report.txt
```

| פרמטר | ברירת מחדל | תיאור |
|-------|-------------|-------|
| `log_file` | — | נתיב לקובץ הלוג (לא צריך עם `--gui`) |
| `--top N` | `5` | כמה מהקבוצות הנפוצות ביותר יישלחו ל־AI ויופיעו בדוח |
| `--no-ai` | כבוי | לדלג על ניתוח ה־AI |
| `--format` | `markdown` | פורמט הדוח: `markdown` או `text` |
| `--output` | `report.md` | איפה לשמור את הדוח |
| `--gui` | כבוי | לפתוח את הממשק הגרפי |

### ממשק גרפי

```bash
python main.py --gui
# או
python -m log_doctor.gui
```

1. **Open Log File…** – בוחרים קובץ לוג.
2. **Analyse** – מריצים פירוק, קיבוץ וניתוח AI על 5 הקבוצות המובילות. אם לא הוגדר מפתח API, מוצגות תוצאות בלי ניתוח AI.
3. לוחצים על קבוצה ברשימה משמאל כדי לראות את הפרטים, הניתוח ושורות לדוגמה.
4. **Save Report…** – שומרים את הדוח כקובץ `.md` או `.txt`.

## דוגמת פלט

הרצה על [sample_logs/app.log](sample_logs/app.log) מפיקה דוח כזה (מקוצר):

```markdown
## Summary
- **Total log entries:** 13
- **Error entries:** 10
- **Error groups:** 4
- **Skipped lines:** 1

## Group 1: `db|Connection timeout after <INT>s to host <IP>`
- **Occurrences:** 4
- **First seen:** 2026-11-14 10:01:15
- **Last seen:** 2026-11-14 10:10:20

### Analysis
The application is experiencing intermittent database connection timeouts...

### Suggested Fix
Investigate the network path and firewall configurations...
```

הדוח המלא נמצא ב־[report.md](report.md).

## מבנה הפרויקט

```
ai-log-doctor/
├── main.py               # נקודת הכניסה ל־CLI
├── requirements.txt
├── .env.example          # תבנית למשתני הסביבה
├── log_doctor/
│   ├── models.py         # LogEntry, ErrorGroup (dataclasses)
│   ├── parser.py         # LogParser: פירוק שורות לוג
│   ├── grouper.py        # ErrorGrouper: קיבוץ שגיאות לפי חתימה
│   ├── llm_client.py     # LLMClient: פנייה ל־Gemini וניסיונות חוזרים
│   ├── report.py         # ReportGenerator: דוח Markdown / Text
│   └── gui.py            # ממשק גרפי ב־Tkinter
└── sample_logs/
    ├── app.log           # לוג לדוגמה
    └── ex.py             # סקריפט שמציג את המודלים הזמינים ב־Gemini
```

## שימוש כספרייה

```python
from dotenv import load_dotenv
from log_doctor import LogParser, ErrorGrouper, LLMClient, ReportGenerator

load_dotenv()

parser = LogParser()
entries = parser.parse_file("sample_logs/app.log")
groups = ErrorGrouper().top_n(entries, n=5)

LLMClient().analyse_groups(groups)

gen = ReportGenerator()
report = gen.to_markdown(groups, len(entries), parser.skipped_lines)
gen.save(report, "report.md")
```

## הערות

- הקריאות ל־Gemini נשלחות אחת אחרי השנייה, עם השהיה של שנייה ביניהן, כדי לא לחרוג ממגבלות הקצב.
- אם הניתוח של קבוצה מסוימת נכשל, הכישלון נרשם בדוח וההרצה ממשיכה לשאר הקבוצות.
- שורות הלוג נשלחות כמו שהן ל־API של Google. אל תריצו את הכלי עם ניתוח AI על לוגים שיש בהם מידע רגיש.
