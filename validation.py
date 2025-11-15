"""
Validation module for user input
Includes settlement validation and day validation
"""

import re
from difflib import SequenceMatcher
from typing import Optional, Tuple, List

# רשימת ישובים מרכזיים בישראל (ניתן להרחיב)
ISRAELI_SETTLEMENTS = {
    # ערים מרכזיות
    'ירושלים', 'תל אביב', 'תל אביב-יפו', 'חיפה', 'באר שבע', 'באר-שבע',
    'ראשון לציון', 'פתח תקווה', 'פתח-תקווה', 'אשדוד', 'נתניה', 'חולון',
    'בני ברק', 'רמת גן', 'רמת-גן', 'אשקלון', 'רחובות', 'בת ים', 'בת-ים',
    'כפר סבא', 'כפר-סבא', 'הרצליה', 'חדרה', 'מודיעין', 'מודיעין-מכבים-רעות',
    'נצרת', 'נצרת עילית', 'לוד', 'רמלה', 'עכו', 'עפולה', 'קריית אתא',
    'צפת', 'טבריה', 'ביתר עילית', 'קריית גת', 'קריית מוצקין', 'אור יהודה',
    'גבעתיים', 'קריית ביאליק', 'קריית ים', 'קריית שמונה', 'כרמיאל', 'יהוד',
    'דימונה', 'קריית מלאכי', 'זכרון יעקב', 'באקה אל-גרביה', 'אום אל-פחם',
    'בית שמש', 'רעננה', 'אריאל', 'מעלות-תרשיחא', 'קריית ארבע', 'צפת',
    
    # אזורים
    'צפון', 'דרום', 'מרכז', 'שפלה', 'ירושלים והסביבה', 'גוש דן', 'השרון',
    'עמק יזרעאל', 'הגליל', 'הגליל העליון', 'הגליל התחתון', 'הנגב', 'ערבה',
    'בקעת הירדן', 'עמק הירדן', 'הכרמל', 'גליל מערבי', 'עמק חפר',
    
    # ערים נוספות
    'תל מונד', 'יבנה', 'גדרה', 'שוהם', 'מזכרת בתיה', 'נס ציונה', 'נס-ציונה',
    'רמת השרון', 'רמת-השרון', 'הוד השרון', 'הוד-השרון', 'רעות', 'אלעד',
    'כוכב יעקב', 'בית שאן', 'מגדל העמק', 'מגדל-העמק', 'יקנעם', 'אופקים',
    'נהריה', 'טייבה', 'שפרעם', 'ערערה', 'עראבה', 'טמרה',
    'דאלית אל-כרמל', 'שדרות', 'ערד', 'אילת', 'מעלה אדומים', 'בית אריה',
    'גני תקווה', 'קדומים', 'עמנואל', 'אלפי מנשה', 'אבן יהודה', 'אבן-יהודה',
    
    # ישובים נוספים בגוש דן ומרכז
    'יהוד-מונוסון', 'אזור', 'קריית אונו', 'קריית-אונו', 'סביון', 'צהלה',
    'רמת אפעל', 'רמת-אפעל', 'גבעת שמואל', 'גבעת-שמואל', 'אור עקיבא', 'אור-עקיבא',
    
    # יישובים בדרום
    'נתיבות', 'אשכול', 'מטולה', 'קרית שמונה', 'רהט', 'תל שבע', 'לקיה', 'חורה',
    
    # יישובים באזור ירושלים
    'מעלה אדומים', 'מעלה-אדומים', 'גבעת זאב', 'גבעת-זאב', 'בית אל', 'בית-אל',
    'פסגת זאב', 'רמות', 'גילה', 'ניווה יעקב', 'פסגות', 'עפרה',
    
    # קיבוצים ומושבים מרכזיים
    'יפתח', 'עין גדי', 'עין-גדי', 'נחשולים', 'שדות ים', 'מעגן מיכאל', 'מעגן-מיכאל',
    'עין גב', 'עין-גב', 'דגניה', 'דגניה א', "דגניה ב'",
}

# הוספת וריאציות שכתוב של כל ישוב
SETTLEMENT_VARIATIONS = {}
for settlement in list(ISRAELI_SETTLEMENTS):
    # הוספה ללא מקפים
    without_dash = settlement.replace('-', ' ')
    SETTLEMENT_VARIATIONS[without_dash.lower()] = settlement
    SETTLEMENT_VARIATIONS[settlement.lower()] = settlement
    
    # הוספה ללא רווחים (חיפה -> חיפה, תל אביב -> תלאביב)
    without_space = settlement.replace(' ', '')
    SETTLEMENT_VARIATIONS[without_space.lower()] = settlement


def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings (0-1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def validate_settlement(settlement_input: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    """
    Validate if settlement exists in Israel
    
    Args:
        settlement_input: The settlement name entered by user
    
    Returns:
        Tuple of (is_valid, exact_match_or_none, list_of_suggestions)
    """
    settlement_input = settlement_input.strip()
    settlement_lower = settlement_input.lower()
    
    # חיפוש התאמה מדויקת (case insensitive)
    if settlement_lower in SETTLEMENT_VARIATIONS:
        return True, SETTLEMENT_VARIATIONS[settlement_lower], None
    
    # אם לא נמצא התאמה מדויקת, נחפש התאמות דומות
    suggestions = []
    for settlement in ISRAELI_SETTLEMENTS:
        sim = similarity(settlement_input, settlement)
        if sim > 0.6:  # דמיון של 60% ומעלה
            suggestions.append((settlement, sim))
    
    # מיון לפי רמת דמיון (הגבוה ביותר ראשון)
    suggestions.sort(key=lambda x: x[1], reverse=True)
    
    # נחזיר את 3 ההצעות הטובות ביותר
    top_suggestions = [s[0] for s in suggestions[:3]]
    
    if top_suggestions:
        return False, None, top_suggestions
    
    # אם אין הצעות טובות, נחזיר False ללא הצעות
    return False, None, None


def validate_days(days_input: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate day format input
    
    Args:
        days_input: Days input from user (e.g., "א-ה", "א,ג,ה", "כל יום")
    
    Returns:
        Tuple of (is_valid, normalized_format or None, error_message or None)
    """
    days_input = days_input.strip()
    
    # דפוסים תקינים
    valid_patterns = [
        r'^[א-ו]{1}-[א-ו]{1}$',  # א-ה, א-ו
        r'^[א-ו]{1},[א-ו]{1}(,[א-ו]{1})*$',  # א,ג,ה
        r'^כל יום$',
        r'^כל הימים$',
        r'^יומי$',
        r'^(ראשון|שני|שלישי|רביעי|חמישי|שישי|שבת)( ו)?(ראשון|שני|שלישי|רביעי|חמישי|שישי|שבת)?$',
        r'^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)',
    ]
    
    # בדיקה אם התבנית תקינה
    for pattern in valid_patterns:
        if re.match(pattern, days_input, re.IGNORECASE):
            return True, days_input, None
    
    # בדיקה אם יש רווחים מיותרים
    days_no_spaces = days_input.replace(' ', '')
    for pattern in valid_patterns:
        if re.match(pattern, days_no_spaces):
            return True, days_no_spaces, None
    
    # אם לא תקין, נחזיר הודעת שגיאה
    error_message = """
פורמט לא תקין! 😅

דוגמאות נכונות:
• א-ה (ראשון עד חמישי)
• א,ג,ה (ימים ספציפיים)
• כל יום
• ראשון ושלישי

נסה שוב! 😊
""".strip()
    
    return False, None, error_message


def validate_time(time_input: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate time format input
    
    Args:
        time_input: Time input from user (e.g., "08:00", "14:30")
    
    Returns:
        Tuple of (is_valid, normalized_format or None, error_message or None)
    """
    time_input = time_input.strip()
    
    # דפוסים תקינים
    # HH:MM או H:MM
    time_pattern = r'^([0-9]{1,2}):([0-9]{2})$'
    
    match = re.match(time_pattern, time_input)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            # נרמול - הוספת 0 בהתחלה אם צריך
            normalized = f"{hours:02d}:{minutes:02d}"
            return True, normalized, None
    
    error_message = """
פורמט שעה לא תקין! ⏰

דוגמאות נכונות:
• 08:00
• 14:30
• 7:00 (זה גם בסדר!)

נסה שוב! 😊
""".strip()
    
    return False, None, error_message


def validate_time_range(time_range_input: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate time range format input
    
    Args:
        time_range_input: Time range input from user (e.g., "08:00-10:00")
    
    Returns:
        Tuple of (is_valid, normalized_format or None, error_message or None)
    """
    time_range_input = time_range_input.strip()
    
    # דפוס: HH:MM-HH:MM
    time_range_pattern = r'^([0-9]{1,2}):([0-9]{2})\s*-\s*([0-9]{1,2}):([0-9]{2})$'
    
    match = re.match(time_range_pattern, time_range_input)
    if match:
        start_hours = int(match.group(1))
        start_minutes = int(match.group(2))
        end_hours = int(match.group(3))
        end_minutes = int(match.group(4))
        
        # בדיקת תקינות שעות ודקות
        if (0 <= start_hours <= 23 and 0 <= start_minutes <= 59 and
            0 <= end_hours <= 23 and 0 <= end_minutes <= 59):
            
            # בדיקה ששעת הסיום אחרי שעת ההתחלה
            start_total = start_hours * 60 + start_minutes
            end_total = end_hours * 60 + end_minutes
            
            if end_total > start_total:
                # נרמול
                normalized = f"{start_hours:02d}:{start_minutes:02d}-{end_hours:02d}:{end_minutes:02d}"
                return True, normalized, None
            else:
                error_message = "שעת הסיום צריכה להיות אחרי שעת ההתחלה! 😅"
                return False, None, error_message
    
    error_message = """
פורמט טווח שעות לא תקין! ⏰

דוגמאות נכונות:
• 08:00-10:00
• 14:30-17:00
• 7:00-9:30 (זה גם בסדר!)

נסה שוב! 😊
""".strip()
    
    return False, None, error_message

