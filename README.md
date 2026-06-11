# Group Similarity Search

כלי לאיתור קבוצות בעלות מאפיינים דומים בנתוני תקשורת סלולרית, איכון וסייבר.

## דרישות מוקדמות

- Python 3.10+
- PostgreSQL רץ עם דאטהבייס בשם `groupsearch`

## התקנה

```bash
pip install -r requirements.txt
```

## הגדרת מסד הנתונים

```bash
# ברירת מחדל: postgresql://postgres:postgres@localhost:5432/groupsearch
# ניתן לשנות באמצעות משתנה סביבה:
export DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

## הרצה ראשונה (עם נתוני דמו)

```bash
cd /path/to/first
python -m app.seed           # יוצר 300 אנשים עם נתונים סינטטיים
uvicorn app.main:app --reload
```

פתח דפדפן בכתובת: http://localhost:8000

## שימוש

1. בחר קבוצת אנשים מהרשימה או הקלד IDs ידנית
2. לחץ "חפש קבוצות דומות"
3. הכלי מחזיר את 10 הקבוצות הדומות ביותר עם ציון דמיון ופרופיל מאפיינים

## API

- `POST /api/search` — `{"person_ids": [1, 2, 3]}` → 10 קבוצות דומות
- `GET /api/persons` — רשימת כל האנשים
- `POST /api/recompute-features` — חישוב מחדש של וקטורי המאפיינים
