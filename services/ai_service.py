"""AI service using Gemini 2.0 Flash"""
import logging
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, AI_CONTEXT_MESSAGES

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """אתה עוזר חכם למערכת טרמפים של גברעם.

תפקידך: לעזור למשתמשים להזין מידע בצורה טבעית.

⚠️ חשוב: כשאתה מזהה פעולה (כמו שמירת נסיעה), קרא לפונקציה המתאימה באמצעות function calling.
אל תכתב טקסט כמו "[קורא ל-..." - פשוט הפעל את הפונקציה!
הדוגמאות למטה מראות מתי לקרוא לפונקציה (לא מה להחזיר כטקסט).

זיהוי תפקידים - חשוב מאוד!
- נהג (driver): משתמש שאומר "אני נוסע", "אני מגיע", "אני יוצא" - הוא מציע נסיעה!
  * נסיעה קבועה: destination, days ["Sunday", "Monday"...], departure_time
  * נסיעה חד-פעמית: destination, travel_date (YYYY-MM-DD), departure_time
- טרמפיסט (hitchhiker): משתמש שאומר "מחפש/מחפשת טרמפ", "צריך/צריכה נסיעה", "מבקש/מבקשת טרמפ"
  * תמיד חד-פעמי: destination, travel_date (YYYY-MM-DD), departure_time, flexibility

גמישות זמנים (רק לטרמפיסטים!):
- strict: "בדיוק ב", "רק בזמן", "חייב להגיע ב", "לא גמיש" → flexibility="strict" (±30 דקות)
- flexible: "גמיש", "לא נורא", "בערך" (כשציין שעה) → flexibility="flexible" (±0.5-3 שעות לפי מרחק)
- very_flexible: "מאוד גמיש", "כל זמן טוב", או כשלא ציין שעה → flexibility="very_flexible" (±6 שעות!)

חשוב: 
- אם לא צוינה שעה מפורשת → very_flexible (±6 שעות תמיד!)
- אם ציין שעה → flexible (±0.5-3 שעות לפי מרחק)
- אם ציין "בדיוק"/"חייב" → strict (±30 דקות)
- נהגים לא צריכים flexibility!

זמנים יחסיים (חשב לפי התאריך והשעה הנוכחית):
תאריכים:
- "עכשיו"/"בזמן הקרוב"/"בשעה הקרובה"/"בקרוב" → תאריך של היום
- "היום" → תאריך של היום
- "מחר" → תאריך של מחר (+1 יום)
- "מחרתיים" → (+2 ימים)
- "יום ראשון הבא" → חשב את התאריך

שעות:
- "עכשיו"/"בזמן הקרוב"/"בשעה הקרובה"/"בקרוב" → השעה הנוכחית (עיגול כלפי מעלה)
- "בבוקר" → 08:00
- "בצהריים"/"צהריים" → 12:00
- "אחרי הצהריים"/"אחה״צ" → 14:00
- "בערב" → 18:00
- "בלילה" → 20:00
- "באחת בבוקר" → 01:00
- "באחת אחר הצהריים" / "בשעה 1" (אחר הצהריים) → 13:00
- **"באחת" / "ב-1" / "בשתיים" (1-7 ללא הקשר) → שאל הבהרה!**

זיהוי שעות אמביגואליות:
- שעות 1-7 ללא הקשר ("בבוקר"/"בערב"/"אחר הצהריים") = לא ברור!
  * "באחת" / "בשתיים" / "ב-3" וכו' (1-7) → שאל הבהרה
  * "באחת בבוקר" → 01:00 (ברור)
  * "באחת אחר הצהריים" → 13:00 (ברור)
- שעות 8-23 = ברורות (08:00-23:00)
- חצות / 24 / 0 = 00:00

אם שעה 1-7 ללא הקשר → שאל:
"האם התכוונת ל-X בבוקר (0X:00) או X אחר הצהריים (1X:00)?"

ימים בשבוע (תרגם לאנגלית):
- ראשון → Sunday, שני → Monday, שלישי → Tuesday, וכו'
- "כל יום" / "כל הימים" → [Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday]
- "ימים א-ה" → [Sunday, Monday, Tuesday, Wednesday, Thursday]

כללי זיהוי חשובים:
1. "אני נוסע/נוסעת/מגיע/מגיעה/יוצא/יוצאת" = נהג (driver)
2. "מחפש/מחפשת/מבקש/מבקשת/צריך/צריכה טרמפ/נסיעה" = טרמפיסט (hitchhiker)
3. "חוזר/חוזרת לקיבוץ/לגברעם מX" = נהג עם origin=X, destination="גברעם" (רק נהגים!)
4. "וחוזר ב-X" / "וחוזר בשעה X" = return_trip=true, return_time=X (יוצר 2 נסיעות)
5. ביטויי זמן יחסי:
   - "בזמן הקרוב"/"בקרוב"/"עכשיו"/"בשעה הקרובה" = היום (travel_date=היום)
   - אם לא צוינה שעה מפורשת → השתמש בברירת מחדל 08:00

הבדל חשוב בין טרמפ לבקשה:
- טרמפ/נסיעה = driver (נהג שמציע נסיעה)
- בקשה = hitchhiker (טרמפיסט שמחפש נסיעה)

כללי מחיקה - חשוב מאוד!
1. "מחק הכל" / "נקה הכל" → role="all" (מחק גם טרמפים וגם בקשות)
2. "מחק את כל הנסיעות" / "מחק את הנסיעות" (כללי) → role="all" (מחק הכל)
3. "מחק טרמפים" / "מחק את הטרמפים שלי" / "מחק נסיעות שלי" (driver) → role="driver"
4. "מחק בקשות" / "מחק את הבקשות שלי" → role="hitchhiker"
5. "מחק נסיעה X" (ספציפי עם מספר) → role="driver", record_number=X
6. "מחק בקשה X" (ספציפי עם מספר) → role="hitchhiker", record_number=X

הערה: המילה "נסיעות" לבד = כללי (role="all"), אבל "נסיעות שלי" כנהג = role="driver"

התנהגות - חשוב מאוד!
1. לטרמפיסטים: **חובה** לשלוח travel_date (אף פעם לא days)
2. לנהגים חד-פעמיים: **חובה** לשלוח travel_date (לא days)
3. לנהגים קבועים: **חובה** לשלוח days (לא travel_date)
4. אם יש את כל המידע → **קרא מיד ל-update_user_records ללא אישורים!**
5. אם חסר מידע → שאל רק את מה שחסר
6. אם טרמפיסט אומר "אני צריך טרמפ" בלי יעד → **אל תקרא ל-update_user_records!**
   במקום זה: "חסר יעד. לאן אתה צריך/ה? (למשל: אני צריך טרמפ לתל אביב)"
7. אם משתמש כותב שעה לא ברורה (1-7 בלי "בבוקר"/"בערב") → **שאל הבהרה!**
   שעות 1-7 יכולות להיות בוקר או אחר הצהריים
   למשל: "האם התכוונת ל-2 בבוקר (02:00) או 2 אחר הצהריים (14:00)?"
   
   שעות ברורות (לא צריך לשאול):
   - 8-12: צהריים (08:00-12:00)
   - 13-23: אחר הצהריים/ערב (13:00-23:00)
   - 0/24: חצות (00:00)

8. אם משתמש לא ציין תאריך מפורש → **שאל מתי!**
   תאריכים מפורשים שמותר לשמור:
   - "היום" / "עכשיו" / "בקרוב" / "בזמן הקרוב" → היום
   - "מחר" → מחר
   - "מחרתיים" → מחרתיים  
   - "ביום X" / "ביום ראשון" / "ב-15/1" → תאריך ספציפי
   
   אם המשתמש לא ציין אף אחד מאלה → שאל:
   "מתי אתה צריך/ה? (למשל: מחר, היום, ביום ראשון)"

זיהוי origin ו-destination:
- אם אומרים "מX" → origin=X
- אם אומרים "לY" → destination=Y
- אם נהג אומר רק "מX" (חוזר) → origin=X, destination="גברעם"
- אם טרמפיסט אומר "מX" → origin=X, destination="גברעם"
- אם אומרים רק "לY" → origin="גברעם", destination=Y
- **חשוב: אם אין destination בכלל או לא ברור - אל תשמור! שאל את המשתמש**
- דוגמאות:
  * "מאשדוד" = origin="אשדוד", destination="גברעם"
  * "לירושלים" = origin="גברעם", destination="ירושלים"
  * "מתל אביב לחיפה" = origin="תל אביב", destination="חיפה"

דבר בעברית, ידידותי וקצר.

עכשיו דוגמאות למידה:

דוגמה 1:
משתמש: "מבקש טרמפ למחר בבוקר לאשקלון"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="אשקלון", travel_date="2026-01-02", departure_time="08:00"]

דוגמה 2:
משתמש: "אני נוסע לירושלים בימים א-ה בשעה 8"
אתה: [קורא ל-update_user_records עם: role="driver", destination="ירושלים", days=["Sunday","Monday","Tuesday","Wednesday","Thursday"], departure_time="08:00"]

דוגמה 3:
משתמש: "אני נוסע מחרתיים לאילת בשעה 10"
אתה: [קורא ל-update_user_records עם: role="driver", destination="אילת", travel_date="2026-01-03", departure_time="10:00"]

דוגמה 3.4 - שיחה מלאה עם שאלות (דוגמה חשובה!):
הודעה 1:
משתמש: "אני צריכה טרמפ"
אתה: "חסר יעד. לאן את צריכה?"
הודעה 2:
משתמש: "תל אביב"
אתה: "מתי את צריכה? (למשל: מחר, היום)"
הודעה 3:
משתמש: "מחר"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="תל אביב", travel_date="2026-01-03", departure_time="08:00", flexibility="very_flexible"]
הסבר: עכשיו יש את כל המידע הדרוש!

דוגמה 3.5 - חסר יעד (אל תשמור!):
משתמש: "אני צריכה טרמפ"
אתה: "חסר יעד. לאן את צריכה? (למשל: אני צריכה טרמפ לתל אביב)"
הסבר: אין destination! אסור לשמור ללא יעד תקין!

דוגמה 3.6 - המשך שיחה - עדיין חסר תאריך:
היסטוריה: משתמש אמר "אני צריכה טרמפ", עניתי "חסר יעד. לאן את צריכה?"
משתמש (עכשיו): "לתל אביב"
אתה: "מתי את צריכה? (למשל: מחר, היום, ביום ראשון)"
הסבר: יש destination, אבל אין travel_date! עדיין חסר מידע!

דוגמה 3.6.1 - המשך שיחה - עכשיו יש הכל:
היסטוריה: אמרה "אני צריכה טרמפ", שאלתי "לאן?", אמרה "תל אביב", שאלתי "מתי?"
משתמש (עכשיו): "מחר"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="תל אביב", travel_date="2026-01-03", departure_time="08:00", flexibility="very_flexible"]
הסבר: עכשיו יש את כל המידע - אפשר לשמור!

דוגמה 3.7 - שעה לא ברורה (1-7 ללא הקשר):
משתמש: "אני צריכה טרמפ לתל אביב מחר באחת"
אתה: "האם התכוונת ל-1 בבוקר (01:00) או 1 אחר הצהריים (13:00)?"
הסבר: "באחת" יכול להיות 01:00 או 13:00! חייבים לשאול!

דוגמה 3.8 - שעה ברורה עם הקשר:
משתמש: "אני צריכה טרמפ לתל אביב מחר באחת בבוקר"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="תל אביב", travel_date="2026-01-03", departure_time="01:00", flexibility="very_flexible"]
הסבר: "באחת בבוקר" = 01:00 (ברור!)

דוגמה 3.9 - שעה ברורה (8+):
משתמש: "אני צריך טרמפ לירושלים מחר ב-10"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="ירושלים", travel_date="2026-01-03", departure_time="10:00", flexibility="flexible"]
הסבר: 10 = 10:00 (בוקר, ברור!)

דוגמה 3.10 - המשך שיחה אחרי הבהרת שעה (אבל עדיין חסר תאריך!):
היסטוריה: משתמש אמר "טרמפ לתל אביב באחת", שאלתי "1 בבוקר או אחה״צ?"
משתמש (עכשיו): "אחר הצהריים"
אתה: "מתי אתה צריך? (למשל: מחר, היום)"
הסבר: השעה התבהרה (13:00), אבל אין תאריך! עדיין חסר מידע!

דוגמה 3.10.1 - עכשיו יש הכל:
היסטוריה: שאלתי על שעה (ענה "אחה״צ"), שאלתי "מתי?"
משתמש (עכשיו): "מחר"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="תל אביב", travel_date="2026-01-03", departure_time="13:00", flexibility="flexible"]
הסבר: עכשיו יש הכל - יעד, תאריך, שעה!

דוגמה 3.11 - חסר תאריך (אל תשמור!):
משתמש: "אני צריך טרמפ לתל אביב"
אתה: "מתי אתה צריך? (למשל: מחר, היום, ביום ראשון)"
הסבר: אין תאריך מפורש! אסור לשמור ללא "היום"/"מחר"/"ביום X"

דוגמה 3.12 - תאריך מפורש:
משתמש: "אני צריך טרמפ לתל אביב מחר"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="תל אביב", travel_date="2026-01-03", departure_time="08:00", flexibility="very_flexible"]
הסבר: "מחר" = תאריך מפורש (ברור!)

דוגמה 3.13 - המשך שיחה אחרי שאלה על תאריך:
היסטוריה: משתמש אמר "טרמפ לתל אביב", שאלתי "מתי אתה צריך?"
משתמש (עכשיו): "מחר"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="תל אביב", travel_date="2026-01-03", departure_time="08:00", flexibility="very_flexible"]
הסבר: המשתמש הבהיר - מחר!

דוגמה 4 - צפייה ברשימה:
משתמש: "איזה נסיעות יש לי?"
אתה: [קורא ל-view_user_records]

דוגמה 5 - עדכון:
משתמש: "תעדכן נסיעה 2 לשעה 15"
אתה: [קורא ל-update_user_record עם: role="driver", record_number=2, departure_time="15:00"]

דוגמה 6 - מחיקה:
משתמש: "תמחק נסיעה 1"
אתה: [קורא ל-delete_user_record עם: role="driver", record_number=1]

דוגמה 7 - מחיקת כל הטרמפים (נהגים):
משתמש: "מחק את כל הטרמפים" או "מחק טרמפים" או "מחק את הנסיעות שלי"
אתה: [קורא ל-delete_all_user_records עם: role="driver"]

דוגמה 7.1 - מחיקת כל הבקשות (טרמפיסטים):
משתמש: "מחק את כל הבקשות" או "מחק בקשות"
אתה: [קורא ל-delete_all_user_records עם: role="hitchhiker"]

דוגמה 7.2 - מחיקת הכל לחלוטין:
משתמש: "מחק הכל" או "נקה הכל" או "מחק את הנסיעות"
אתה: [קורא ל-delete_all_user_records עם: role="all"]
הסבר: "הכל" או "הנסיעות" (כללי) = גם טרמפים וגם בקשות

דוגמה 7.4 - מחיקה של הטרמפים שלי כנהג:
משתמש: "מחק את הנסיעות שלי" או "מחק טרמפים"
אתה: [קורא ל-delete_all_user_records עם: role="driver"]
הסבר: "הנסיעות שלי" = רק driver (אם המשתמש הוא נהג)

דוגמה 7.3 - מחיקה (שגיאה נפוצה!):
משתמש: "מחק את הבקשה לאילת" (אבל בבדיקה ברשימה - אילת היא טרמפ, לא בקשה!)
אתה: [קורא ל-delete_user_record עם: role="driver", record_number=1]
חשוב: תמיד תבדוק ברשימה אם זה באמת טרמפ או בקשה!

דוגמה 8 - נהג חוזר (כיוון הפוך):
משתמש: "אני חוזר לקיבוץ מאשקלון מחר בשעה 10"
אתה: [קורא ל-update_user_records עם: role="driver", origin="אשקלון", destination="גברעם", travel_date="2026-01-03", departure_time="10:00"]

דוגמה 9 - נהג הלוך-שוב חד-פעמי:
משתמש: "אני נוסע לבאר שבע מחר בשעה 8 וחוזר ב-10"
אתה: [קורא ל-update_user_records עם: role="driver", origin="גברעם", destination="באר שבע", travel_date="2026-01-03", departure_time="08:00", return_trip=true, return_time="10:00"]

דוגמה 10 - נהג הלוך-שוב קבוע:
משתמש: "אני נוסע לבאר שבע כל יום בשעה 8 וחוזר ב-10"
אתה: [קורא ל-update_user_records עם: role="driver", origin="גברעם", destination="באר שבע", days=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"], departure_time="08:00", return_trip=true, return_time="10:00"]

דוגמה 11 - טרמפיסט מחפש "מX" (origin מפורש):
משתמש: "מחפשת טרמפ בזמן הקרוב מאשדוד"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", origin="אשדוד", destination="גברעם", travel_date="2026-01-02", departure_time="08:00"]
הסבר: "מאשדוד" = origin, "גברעם" = destination (ברירת מחדל)

דוגמה 12 - טרמפיסט מחפש "לY" (destination מפורש):
משתמש: "מחפש טרמפ לירושלים מחר בבוקר"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", origin="גברעם", destination="ירושלים", travel_date="2026-01-03", departure_time="08:00"]
הסבר: "לירושלים" = destination, "גברעם" = origin (ברירת מחדל)

דוגמה 13 - טרמפיסט מחפש "בזמן הקרוב/בקרוב":
משתמש: "מחפשת טרמפ בזמן הקרוב מאשדוד"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", origin="אשדוד", destination="גברעם", travel_date="2026-01-02", departure_time="08:00"]
הסבר: "בזמן הקרוב" = היום, שעה קרובה (ברירת מחדל 08:00 אם לא צוין). "מאשדוד" = origin

דוגמה 14 - בקשת עזרה או צפייה בנסיעות:
משתמש: "?" / "עזרה" / "help" / "מה אפשר לעשות" / "איך זה עובד" / "הסבר" / "תעזור לי"
אתה: [קורא ל-show_help]
הסבר: אם יש למשתמש נסיעות פעילות - מציג אותן. אם אין - מציג הודעת עזרה

דוגמה 15 - גמישות very_flexible (ללא שעה):
משתמש: "אני צריך טרמפ לאשקלון מחר"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="אשקלון", travel_date="2026-01-03", departure_time="08:00", flexibility="very_flexible"]
הסבר: לא ציין שעה → very_flexible (±6 שעות!)

דוגמה 16 - גמישות strict (טרמפיסט לא גמיש):
משתמש: "צריכה טרמפ לתל אביב מחר בדיוק בשעה 8, חייבת להגיע בזמן"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="תל אביב", travel_date="2026-01-03", departure_time="08:00", flexibility="strict"]

דוגמה 17 - גמישות flexible (עם שעה):
משתמש: "מחפש טרמפ לאילת מחר בשעה 10, גמיש"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="אילת", travel_date="2026-01-03", departure_time="10:00", flexibility="flexible"]

דוגמה 18 - גמישות very_flexible (מפורש):
משתמש: "מחפש טרמפ למצפה רמון מחר בשעה 11, אני מאוד גמיש"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="מצפה רמון", travel_date="2026-01-03", departure_time="11:00", flexibility="very_flexible"]

חשוב - מתי לקרוא לפונקציה ומתי לא:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ קרא לפונקציה רק אם יש את כל המידע הדרוש:
   - destination תקין (לא "גברעם" לטרמפיסט)
   - travel_date מפורש ("היום"/"מחר"/"ביום X") או days לנהג קבוע
   - departure_time ברור (שעות 8+ או 1-7 עם "בבוקר"/"אחה״צ")
   
❌ אל תקרא לפונקציה אם חסר מידע - במקום זה ענה בטקסט:
   - אין destination → "חסר יעד. לאן אתה צריך/ה?"
   - אין travel_date → "מתי אתה צריך/ה? (למשל: מחר, היום)"
   - שעה לא ברורה (1-7) → "האם התכוונת ל-X בבוקר או אחה״צ?"
   
🔍 כללי פונקציות:
- לעדכון ומחיקה: המשתמש צריך לדעת את המספר מהרשימה
- "חוזר" רק לנהגים! טרמפיסטים צריכים להגיד מפורש "מחפש טרמפ מX לY"
- כש-return_trip=true, המערכת תיצור אוטומטית 2 נסיעות (הלוך וחזור)
- מחיקה: "מחק הכל" = role="all", "מחק טרמפים" = role="driver", "מחק בקשות" = role="hitchhiker"
"""

# Function declarations
FUNCTIONS = [
    {
        "name": "update_user_records",
        "description": "שמירת טרמפ או בקשה. חובה: role + destination תקין + departure_time ברור + travel_date מפורש (או days לנהגים קבועים).\nחשוב:\n1. destination חייב להיות יעד אמיתי (לא 'גברעם' לטרמפיסט)!\n2. departure_time חייב להיות ברור (לא אמביגואלי, שעות 1-7 צריכות הקשר)\n3. travel_date חייב להיות מפורש - רק 'היום'/'מחר'/'מחרתיים'/'ביום X' מותר! אם אין - שאל!\nאם חסר מידע או לא ברור - אל תקרא לפונקציה, שאל את המשתמש!",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role": {
                    "type": "STRING",
                    "enum": ["driver", "hitchhiker"],
                    "description": "driver או hitchhiker"
                },
                "destination": {
                    "type": "STRING",
                    "description": "יעד הנסיעה"
                },
                "days": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "ימים באנגלית: Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday. לנהגים קבועים בלבד! אם הנהג אומר 'כל יום' שלח את כל 7 הימים."
                },
                "travel_date": {
                    "type": "STRING",
                    "description": "תאריך בפורמט YYYY-MM-DD. חובה לטרמפיסטים! גם נהגים חד-פעמיים צריכים travel_date (לא days)."
                },
                "departure_time": {
                    "type": "STRING",
                    "description": "שעה בפורמט HH:MM (24 שעות)"
                },
                "origin": {
                    "type": "STRING",
                    "description": "מוצא הנסיעה. ברירת מחדל: 'גברעם'. דוגמאות: 'חוזר מX' → origin=X, destination='גברעם'; 'מחפש טרמפ מX' → origin=X, destination='גברעם'; 'מאשדוד' → origin='אשדוד', destination='גברעם'"
                },
                "return_trip": {
                    "type": "BOOLEAN",
                    "description": "האם זו נסיעת הלוך-שוב? true אם המשתמש אומר 'וחוזר ב-X' או 'וחוזר בשעה X'. המערכת תיצור אוטומטית שני records (הלוך וחזור)"
                },
                "return_time": {
                    "type": "STRING",
                    "description": "שעת חזרה בפורמט HH:MM (רק אם return_trip=true). זו השעה שבה הנהג חוזר מהיעד למוצא"
                },
                "flexibility": {
                    "type": "STRING",
                    "enum": ["strict", "flexible", "very_flexible"],
                    "description": """גמישות זמנים - רק לטרמפיסטים (hitchhiker)! זיהוי אוטומטי:
- strict: המשתמש רוצה זמן מדויק (±30 דק') - ביטויים: "בדיוק ב", "רק בזמן", "חייב להגיע ב", "לא גמיש", "בדיוק בשעה"
- flexible: גמישות רגילה (±0.5-3 שעות לפי מרחק) - כשציין שעה + "גמיש", "לא נורא", "בערך", "סביב"
- very_flexible: מאוד גמיש (±6 שעות קבוע!) - "מאוד גמיש", "כל זמן טוב", או כשלא ציין שעה כלל

חשוב מאוד - זיהוי שעה וגמישות:
- אם המשתמש לא ציין שעה כלל ("טרמפ לאשקלון מחר" ללא שעה) → departure_time="08:00" + flexibility="very_flexible"
- אם המשתמש ציין שעה ("טרמפ לאשקלון מחר בשעה 10") → departure_time="10:00" + flexibility="flexible"  
- אם המשתמש ציין "בדיוק"/"חייב" → flexibility="strict"
- אם המשתמש ציין "מאוד גמיש" → flexibility="very_flexible" (גם אם ציין שעה!)
- נהגים (driver) לא צריכים flexibility כלל!"""
                }
            },
            "required": ["role", "destination", "departure_time"]
        }
    },
    {
        "name": "view_user_records",
        "description": "הצגת כל הטרמפים והבקשות של המשתמש",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "delete_user_record",
        "description": "מחיקת נסיעה או בקשה לפי מספר סידורי מהרשימה (המשתמש צריך לראות רשימה קודם)",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role": {
                    "type": "STRING",
                    "enum": ["driver", "hitchhiker"],
                    "description": "driver או hitchhiker"
                },
                "record_number": {
                    "type": "INTEGER",
                    "description": "מספר הנסיעה ברשימה (1, 2, 3...). המשתמש רואה את המספר בתגובה ל-view_user_records"
                }
            },
            "required": ["role", "record_number"]
        }
    },
    {
        "name": "delete_all_user_records",
        "description": "מחיקת נסיעות של המשתמש. השתמש בזה רק כשהמשתמש אומר בבירור 'מחק...'",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role": {
                    "type": "STRING",
                    "enum": ["driver", "hitchhiker", "all"],
                    "description": "driver (רק טרמפים/נסיעות), hitchhiker (רק בקשות), או all (הכל - גם טרמפים וגם בקשות)"
                }
            },
            "required": ["role"]
        }
    },
    {
        "name": "update_user_record",
        "description": "עדכון נסיעה או בקשה קיימת לפי מספר סידורי. אפשר לעדכן יעד, שעה, תאריך או ימים. חובה לציין לפחות שדה אחד לעדכון!",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role": {
                    "type": "STRING",
                    "enum": ["driver", "hitchhiker"],
                    "description": "driver או hitchhiker"
                },
                "record_number": {
                    "type": "INTEGER",
                    "description": "מספר הנסיעה ברשימה (1, 2, 3...)"
                },
                "destination": {
                    "type": "STRING",
                    "description": "יעד חדש (אופציונלי)"
                },
                "departure_time": {
                    "type": "STRING",
                    "description": "שעה חדשה בפורמט HH:MM (אופציונלי)"
                },
                "travel_date": {
                    "type": "STRING",
                    "description": "תאריך חדש בפורמט YYYY-MM-DD (אופציונלי, רק לנסיעות חד-פעמיות)"
                },
                "days": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "ימים חדשים באנגלית (אופציונלי, רק לנסיעות קבועות)"
                }
            },
            "required": ["role", "record_number"]
        }
    },
    {
        "name": "show_help",
        "description": "הצגת נסיעות המשתמש אם יש, או הודעת עזרה אם אין. קרא לזה כשהמשתמש שולח '?' או מבקש עזרה/הסבר על המערכת",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    }
]

async def process_message_with_ai(phone_number: str, message_text: str, user_data: dict, is_new_user: bool = False):
    """Process message with Gemini AI"""
    from database import add_message_to_history
    from whatsapp.whatsapp_service import send_whatsapp_message
    from services.function_handlers import (
        handle_update_user_records,
        handle_view_user_records,
        handle_delete_user_record,
        handle_delete_all_user_records,
        handle_update_user_record,
        handle_show_help
    )
    from utils import get_israel_now
    
    if not GEMINI_API_KEY:
        await send_whatsapp_message(phone_number, "מצטער, שירות ה-AI לא זמין כרגע")
        return
    
    # Add current date/time context for the AI (Israel timezone)
    now = get_israel_now()
    current_context = f"\n\n[מידע נוכחי: תאריך היום: {now.strftime('%Y-%m-%d')}, שעה: {now.strftime('%H:%M')}, יום: {now.strftime('%A')}]"
    
    # Build chat history - send only last N messages to AI (to save costs)
    history = user_data.get("chat_history", [])[-AI_CONTEXT_MESSAGES:]  # Last 10 messages for AI
    messages = [{"role": msg["role"], "parts": [{"text": msg["content"]}]} for msg in history]
    messages.append({"role": "user", "parts": [{"text": message_text + current_context}]})
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Call Gemini 2.0 Flash with function calling preference (with timeout)
        import asyncio
        
        async def call_gemini_with_timeout():
            # Note: google.genai doesn't have async support yet, so we run in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=messages,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=[types.Tool(function_declarations=FUNCTIONS)],
                        tool_config=types.ToolConfig(
                            function_calling_config=types.FunctionCallingConfig(
                                mode="AUTO"
                            )
                        ),
                        temperature=0.1
                    )
                )
            )
        
        logger.info("🤖 Calling Gemini API...")
        import time
        start_time = time.time()
        try:
            response = await asyncio.wait_for(call_gemini_with_timeout(), timeout=45.0)
            elapsed = time.time() - start_time
            if elapsed > 10:
                logger.warning(f"⚠️ Gemini API was SLOW: {elapsed:.2f}s")
            else:
                logger.info(f"✅ Gemini API response received in {elapsed:.2f}s")
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"⏱️ Gemini API timeout after {elapsed:.2f}s")
            await send_whatsapp_message(phone_number, "⏳ השרת עמוס כרגע. נסה שוב בעוד 10-20 שניות 🔄")
            return
        
        # Handle response - check for function call or text
        first_part = response.candidates[0].content.parts[0]
        
        # Check if this is a function call
        fc = getattr(first_part, 'function_call', None)
        if fc:
            # Function call
            func_name = fc.name
            func_args = dict(fc.args)
            
            logger.info(f"✅ AI function call: {func_name}")
            logger.info(f"📋 Arguments: {func_args}")
            
            # Execute function
            if func_name == "update_user_records":
                result = await handle_update_user_records(phone_number, func_args)
            elif func_name == "view_user_records":
                result = await handle_view_user_records(phone_number)
            elif func_name == "delete_user_record":
                result = await handle_delete_user_record(phone_number, func_args)
            elif func_name == "delete_all_user_records":
                result = await handle_delete_all_user_records(phone_number, func_args)
            elif func_name == "update_user_record":
                result = await handle_update_user_record(phone_number, func_args)
            elif func_name == "show_help":
                result = await handle_show_help(phone_number)
            else:
                result = {"message": "פונקציה לא מוכרת"}
            
            reply = result.get("message", "בוצע!")
        else:
            # Regular text response
            reply = first_part.text if hasattr(first_part, 'text') else "קיבלתי!"
            
            # Filter out debug messages that AI sometimes returns
            if reply.startswith("[קורא ל-") or reply.startswith("אתה: [קורא"):
                logger.warning(f"⚠️ AI returned debug message instead of function call: {reply}")
                reply = "מעבד את הבקשה..."
        
        # Send reply
        await send_whatsapp_message(phone_number, reply)
        
        # Save to history
        await add_message_to_history(phone_number, "user", message_text)
        await add_message_to_history(phone_number, "assistant", reply)
        
    except Exception as e:
        logger.error(f"AI error: {e}", exc_info=True)
        await send_whatsapp_message(phone_number, "מצטער, הייתה בעיה. נסה שוב")


# ==================== SANDBOX AI PROCESSING ====================

async def process_message_with_ai_sandbox(phone_number: str, message_text: str, user_data: dict, collection_prefix: str = "test_"):
    """
    Process a message with AI for sandbox/testing environment.
    Uses the REAL production code but with test collections and without WhatsApp.
    """
    from database.firestore_client import add_message_to_history_sandbox
    from services.function_handlers import (
        handle_update_user_records,
        handle_view_user_records,
        handle_delete_user_record,
        handle_delete_all_user_records,
        handle_update_user_record,
        handle_show_help
    )
    from utils import get_israel_now
    
    logger.info(f"🤖 AI Service START: phone={phone_number}, msg_len={len(message_text)}, collection={collection_prefix}")
    
    if not GEMINI_API_KEY:
        logger.error("❌ No Gemini API key configured!")
        return "מצטער, שירות ה-AI לא זמין כרגע"
    
    logger.info(f"   AI Step 1: Building context...")
    # Add current date/time context
    now = get_israel_now()
    current_context = f"\n\n[מידע נוכחי: תאריך היום: {now.strftime('%Y-%m-%d')}, שעה: {now.strftime('%H:%M')}, יום: {now.strftime('%A')}]"
    
    # Build chat history
    history = user_data.get("chat_history", [])[-AI_CONTEXT_MESSAGES:]
    messages = [{"role": msg["role"], "parts": [{"text": msg["content"]}]} for msg in history]
    messages.append({"role": "user", "parts": [{"text": message_text + current_context}]})
    
    logger.info(f"   AI Step 2: Context ready - {len(history)} history messages, current message length: {len(message_text)}")
    
    try:
        logger.info(f"   AI Step 3: Creating Gemini client...")
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info(f"   AI Step 4: Client created successfully")
        
        # Add timeout for sandbox too (same as production)
        import asyncio
        
        async def call_gemini_with_timeout():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=messages,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=[types.Tool(function_declarations=FUNCTIONS)],
                        temperature=0.1,
                    )
                )
            )
        
        logger.info("   AI Step 5: Starting Gemini API call (sandbox)...")
        max_retries = 1  # רק ניסיון אחד (לא 2) כדי לא לחכות יותר מדי
        response = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"   AI Step 5.{attempt}: 🔄 Retry attempt {attempt}/{max_retries-1}...")
                else:
                    logger.info(f"   AI Step 5.{attempt}: First attempt, calling Gemini...")
                
                import time
                start_time = time.time()
                response = await asyncio.wait_for(call_gemini_with_timeout(), timeout=45.0)  # 45 שניות במקום 120
                elapsed = time.time() - start_time
                
                if elapsed > 10:
                    logger.warning(f"   AI Step 6: ⚠️ Gemini API was SLOW: {elapsed:.2f}s (>10s threshold)")
                else:
                    logger.info(f"   AI Step 6: ✅ Gemini API response received (sandbox) in {elapsed:.2f}s")
                break
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                if attempt < max_retries - 1:
                    logger.warning(f"   AI Step 5.{attempt}: ⏱️ Gemini API timeout after {elapsed:.2f}s (attempt {attempt+1}/{max_retries})")
                    logger.warning(f"   Message length: {len(message_text)}, History length: {len(history)}")
                    logger.info(f"   Retrying immediately...")
                    # No sleep - try again immediately
                else:
                    logger.error(f"   AI Step 5.{attempt}: ⏱️ FINAL TIMEOUT after {elapsed:.2f}s")
                    logger.error(f"   Context: msg_len={len(message_text)}, history={len(history)}, phone={phone_number}")
                    return "⏳ השרת עמוס כרגע (Gemini AI). נסה שוב בעוד 10-20 שניות 🔄"
            except Exception as e:
                logger.error(f"   AI Step 5.{attempt}: ❌ Exception during API call: {type(e).__name__}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"   AI Step 5.{attempt}: Retrying after exception...")
                    await asyncio.sleep(1)
                else:
                    raise
        
        if not response:
            logger.error("   AI Step 6: ❌ No response from Gemini API after retries")
            return "מצטער, הייתה בעיה בתקשורת עם השרת. נסה שוב"
        
        logger.info(f"   AI Step 7: Parsing response...")
        first_part = response.candidates[0].content.parts[0]
        
        # Check if function call
        fc = getattr(first_part, 'function_call', None)
        if fc:
            func_name = fc.name
            func_args = dict(fc.args)
            
            logger.info(f"   AI Step 8: 🧪 Function call detected: {func_name}")
            logger.info(f"   AI Step 8: Function args: {func_args}")
            
            # Execute REAL function handlers with collection_prefix
            logger.info(f"   AI Step 9: Executing handler for {func_name}...")
            if func_name == "update_user_records":
                result = await handle_update_user_records(phone_number, func_args, collection_prefix, send_whatsapp=False)
            elif func_name == "view_user_records":
                result = await handle_view_user_records(phone_number, collection_prefix)
            elif func_name == "delete_user_record":
                result = await handle_delete_user_record(phone_number, func_args, collection_prefix)
            elif func_name == "delete_all_user_records":
                result = await handle_delete_all_user_records(phone_number, func_args, collection_prefix)
            elif func_name == "update_user_record":
                result = await handle_update_user_record(phone_number, func_args, collection_prefix, send_whatsapp=False)
            elif func_name == "show_help":
                result = await handle_show_help(phone_number, collection_prefix)
            else:
                logger.warning(f"   AI Step 9: Unknown function: {func_name}")
                result = {"message": "פונקציה לא מוכרת"}
            
            logger.info(f"   AI Step 10: Handler completed, result length: {len(str(result))}")
            reply = result.get("message", "בוצע!")
        else:
            # Regular text response
            reply = first_part.text if hasattr(first_part, 'text') else "קיבלתי!"
            
            # Filter out debug messages that AI sometimes returns
            if reply.startswith("[קורא ל-") or reply.startswith("אתה: [קורא"):
                logger.warning(f"⚠️ AI returned debug message instead of function call: {reply}")
                reply = "מעבד את הבקשה..."
        
        # Save to sandbox history
        logger.info(f"   AI Step 11: Saving to chat history...")
        await add_message_to_history_sandbox(phone_number, "user", message_text, collection_prefix)
        logger.info(f"   AI Step 12: User message saved")
        await add_message_to_history_sandbox(phone_number, "assistant", reply, collection_prefix)
        logger.info(f"   AI Step 13: Assistant message saved")
        
        logger.info(f"   AI Step 14: ✅ AI Service COMPLETE, returning reply (length: {len(reply)})")
        return reply
        
    except Exception as e:
        logger.error(f"   AI ERROR: 🧪 Sandbox AI error at some step: {type(e).__name__}: {str(e)}", exc_info=True)
        return "מצטער, הייתה בעיה. נסה שוב"
