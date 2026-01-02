# 🛠️ Scripts Directory

סקריפטים עזר של פרויקט Hiker

## 📁 קבצים

### `deploy.sh` 🚀

**סקריפט deployment ל-Google Cloud**

שימוש:
```bash
./scripts/deploy.sh
```

מה הסקריפט עושה:
1. בודק תלויות
2. מריץ בדיקות
3. בונה Docker image
4. מעלה ל-Cloud Run

---

### `test_webhook.sh` 🔗

**בדיקת webhook של WhatsApp**

שימוש:
```bash
./scripts/test_webhook.sh
```

בודק:
- ✅ Verification endpoint
- ✅ Message webhook
- ✅ Status webhook

---

### `test_logs.sh` 📊

**סקריפט לבדיקת logs ומעקב**

שימוש:
```bash
./scripts/test_logs.sh
```

מה הסקריפט עושה:
1. מציג logs אחרונים
2. מסנן לפי severity
3. מחפש שגיאות
4. מציג סטטיסטיקות

---

## 🔧 הרצת סקריפט

### הפיכת סקריפט להרצה:
```bash
chmod +x scripts/<script_name>.sh
```

### הרצה:
```bash
./scripts/<script_name>.sh
```

או:
```bash
bash scripts/<script_name>.sh
```

---

## 📝 יצירת סקריפט חדש

תבנית לסקריפט bash:

```bash
#!/bin/bash
# Description: מה הסקריפט עושה

set -e  # יציאה בשגיאה

# Constants
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Main logic
main() {
    echo "Starting..."
    # Your code here
    echo "Done!"
}

main "$@"
```

---

## 🎯 סקריפטים מומלצים להוסיף:

- [ ] `setup.sh` - התקנה ראשונית
- [ ] `test_all.sh` - הרצת כל הבדיקות
- [ ] `backup.sh` - גיבוי נתונים
- [ ] `monitor.sh` - ניטור מערכת
- [ ] `update_deps.sh` - עדכון תלויות

