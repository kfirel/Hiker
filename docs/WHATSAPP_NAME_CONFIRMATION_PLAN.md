# תוכנית יישום: אישור שם מ-WhatsApp

## סקירה כללית

המטרה היא לשפר את חוויית המשתמש בהודעה הראשונה על ידי:
1. הצגת שם המשתמש מ-WhatsApp בהודעה הראשונה
2. שאלת המשתמש אם להשתמש בשם מ-WhatsApp או להקליד שם אחר

## המצב הנוכחי

### זרימה נוכחית:
```
initial (condition: user_not_registered)
  ↓
ask_full_name (שואל את השם)
  ↓
ask_user_type (ממשיך לשאול על סוג משתמש)
```

### איך שם מ-WhatsApp נשלף כרגע:
- ב-`app.py` ב-`process_message()`:
  - מנסה לקבל שם מ-webhook data (`value['contacts']`)
  - אם לא נמצא, קורא ל-`whatsapp_client.get_user_profile_name()`
  - שומר את השם ב-`whatsapp_name` (וגם ב-`full_name` אם אין שם אחר)

### בעיות במצב הנוכחי:
1. ההודעה הראשונה לא משתמשת בשם מ-WhatsApp
2. המשתמש צריך להקליד את השם גם אם יש שם ב-WhatsApp
3. אין אפשרות לבחור בין שם מ-WhatsApp לשם אחר

## התוכנית המוצעת

### זרימה חדשה:
```
initial (condition: user_not_registered)
  ↓
  [בדיקה: יש שם מ-WhatsApp?]
  ├─ כן → confirm_whatsapp_name (שואל אם להשתמש בשם)
  │         ├─ כן → שמור שם מ-WhatsApp → ask_user_type
  │         └─ לא → ask_full_name → ask_user_type
  └─ לא → ask_full_name → ask_user_type
```

### מצבים חדשים/משונים:

#### 1. `confirm_whatsapp_name` (חדש)
- **תפקיד**: לשאול את המשתמש אם להשתמש בשם מ-WhatsApp
- **הודעה**: 
  ```
  היי {whatsapp_name}! 👋 ברוכים הבאים להייקר 🚗✨
  
  הבוט החכם של ישוב גברעם שיעזור לך למצוא טרמפים או לתת טרמפים! 😄
  
  בואו נכיר! מצאתי את השם שלך ב-WhatsApp: *{whatsapp_name}*
  
  האם להשתמש בשם הזה או להקליד שם אחר?
  
  1. ✅ כן, להשתמש ב-{whatsapp_name}
  2. ✏️ לא, להקליד שם אחר
  ```
- **קלט צפוי**: choice
- **אפשרויות**:
  - `1` → שמור `whatsapp_name` כ-`full_name` → `ask_user_type`
  - `2` → `ask_full_name`

#### 2. `ask_full_name` (משונה)
- **שינוי**: להוסיף שם מ-WhatsApp בהודעה אם קיים
- **הודעה חדשה**:
  ```
  היי {whatsapp_name}! 👋 ברוכים הבאים להייקר 🚗✨
  
  הבוט החכם של ישוב גברעם שיעזור לך למצוא טרמפים או לתת טרמפים! 😄
  
  בואו נכיר! מה השם המלא שלך?
  (השם יעזור לנהגים וטרמפיסטים לזהות אותך) 🎭
  ```
- **הערה**: אם אין `whatsapp_name`, ההודעה תהיה כמו קודם (בלי שם)

#### 3. `initial` (משונה)
- **שינוי**: לבדוק אם יש שם מ-WhatsApp ולכוון למצב המתאים
- **לוגיקה**: 
  - אם יש `whatsapp_name` → `confirm_whatsapp_name`
  - אחרת → `ask_full_name`

## שינויים בקוד הנדרשים

### 1. `conversation_flow.yml`

#### להוסיף מצב חדש `confirm_whatsapp_name`:
```yaml
confirm_whatsapp_name:
  id: confirm_whatsapp_name
  message: 'היי {whatsapp_name}! 👋 ברוכים הבאים להייקר 🚗✨
  
  
    הבוט החכם של ישוב גברעם שיעזור לך למצוא טרמפים או לתת טרמפים! 😄
    
    
    בואו נכיר! מצאתי את השם שלך ב-WhatsApp: *{whatsapp_name}*
    
    האם להשתמש בשם הזה או להקליד שם אחר?
    
    
    1. ✅ כן, להשתמש ב-{whatsapp_name}
    
    2. ✏️ לא, להקליד שם אחר'
  expected_input: choice
  options:
    '1':
      label: ✅ כן, להשתמש בשם מ-WhatsApp
      value: 'use_whatsapp_name'
      action: save_whatsapp_name_as_full_name
      next_state: ask_user_type
    '2':
      label: ✏️ לא, להקליד שם אחר
      value: 'enter_different_name'
      next_state: ask_full_name
```

#### לשנות את `ask_full_name`:
```yaml
ask_full_name:
  id: ask_full_name
  message: 'היי {whatsapp_name}! 👋 ברוכים הבאים להייקר 🚗✨
  
  
    הבוט החכם של ישוב גברעם שיעזור לך למצוא טרמפים או לתת טרמפים! 😄
    
    
    בואו נכיר! מה השם המלא שלך?
    (השם יעזור לנהגים וטרמפיסטים לזהות אותך) 🎭'
  expected_input: text
  save_to: full_name
  action: set_gevaram_as_home
  next_state: ask_user_type
```

#### לשנות את `initial`:
```yaml
initial:
  id: initial
  condition: user_not_registered
  # next_state יקבע דינמית לפי האם יש שם מ-WhatsApp
  # זה יטופל ב-conversation_engine.py
```

### 2. `conversation_engine.py`

#### להוסיף לוגיקה ב-`_process_state` לטיפול ב-`initial`:
```python
# ב-_process_state, אחרי בדיקת idle state:
if state.get('id') == 'initial':
    # בדוק אם יש שם מ-WhatsApp
    user = self.user_db.get_user(phone_number)
    whatsapp_name = None
    if user:
        profile = user.get('profile', {})
        whatsapp_name = profile.get('whatsapp_name') or user.get('whatsapp_name')
    
    if whatsapp_name:
        # יש שם מ-WhatsApp - עבור ל-confirm_whatsapp_name
        next_state = 'confirm_whatsapp_name'
        self.user_db.set_user_state(phone_number, next_state, {'last_state': next_state})
        confirm_state = self.flow['states'].get(next_state)
        if confirm_state:
            message = self._get_state_message(phone_number, confirm_state)
            buttons = self._build_buttons(confirm_state)
            return message, next_state, buttons
    else:
        # אין שם מ-WhatsApp - עבור ל-ask_full_name
        next_state = 'ask_full_name'
        self.user_db.set_user_state(phone_number, next_state, {'last_state': next_state})
        ask_name_state = self.flow['states'].get(next_state)
        if ask_name_state:
            message = self._get_state_message(phone_number, ask_name_state)
            buttons = self._build_buttons(ask_name_state)
            return message, next_state, buttons
```

### 3. `action_executor.py`

#### להוסיף action חדש `save_whatsapp_name_as_full_name`:
```python
def _execute_save_whatsapp_name_as_full_name(self, phone_number: str, data: Dict[str, Any]):
    """Save WhatsApp name as full_name"""
    user = self.user_db.get_user(phone_number)
    if not user:
        logger.error(f"User not found: {phone_number}")
        return
    
    # Get WhatsApp name
    profile = user.get('profile', {})
    whatsapp_name = profile.get('whatsapp_name') or user.get('whatsapp_name')
    
    if whatsapp_name:
        # Save WhatsApp name as full_name
        self.user_db.save_to_profile(phone_number, 'full_name', whatsapp_name)
        logger.info(f"Saved WhatsApp name '{whatsapp_name}' as full_name for {phone_number}")
    else:
        logger.warning(f"No WhatsApp name found for {phone_number}")
```

### 4. `message_formatter.py`

#### להוסיף תמיכה במשתנה `{whatsapp_name}`:
```python
# ב-format_message, אחרי הטיפול ב-full_name:
elif var == 'whatsapp_name':
    # Get WhatsApp name from user document
    user = self.user_db.get_user(phone_number)
    if user:
        profile = user.get('profile', {})
        value = profile.get('whatsapp_name') or user.get('whatsapp_name') or ''
    else:
        value = ''
    message = message.replace(f'{{{var}}}', str(value))
```

### 5. `app.py`

#### לשנות את הלוגיקה של שמירת שם מ-WhatsApp:
```python
# ב-process_message, אחרי קבלת profile_name:
if profile_name:
    # Ensure user exists
    if not user_db.user_exists(from_number):
        user_db.create_user(from_number)
    
    # Save WhatsApp name BUT DON'T save as full_name yet
    # Wait for user confirmation in confirm_whatsapp_name state
    if not user_db.get_profile_value(from_number, 'whatsapp_name'):
        user_db.save_to_profile(from_number, 'whatsapp_name', profile_name)
        logger.info(f"Saved WhatsApp name '{profile_name}' for {from_number}")
    
    # Only save as full_name if user already confirmed or if no full_name exists
    # This allows the confirmation flow to work properly
    if not user_db.get_profile_value(from_number, 'full_name'):
        # Don't auto-save as full_name - let user confirm first
        pass
```

## סיכונים ופתרונות

### סיכון 1: משתמשים קיימים עם שם מ-WhatsApp שכבר נשמר
**פתרון**: 
- לבדוק אם יש `full_name` קיים
- אם יש, לא לעבור ל-`confirm_whatsapp_name` אלא ישירות ל-`ask_user_type` או `ask_full_name` (תלוי אם רשום)

### סיכון 2: שם מ-WhatsApp לא זמין (API נכשל)
**פתרון**: 
- אם אין שם מ-WhatsApp, פשוט לעבור ל-`ask_full_name` כמו קודם
- ההודעה ב-`ask_full_name` תתמוך גם בלי שם (תשתמש ב-`{whatsapp_name}` רק אם קיים)

### סיכון 3: משתמשים שמעדכנים שם (לא רישום ראשון)
**פתרון**: 
- ב-`text_handler.py` יש כבר בדיקה: `if state_id == 'ask_full_name' and self.user_db.is_registered(phone_number)`
- זה ימשיך לעבוד - משתמש רשום שמעדכן שם לא יעבור דרך `confirm_whatsapp_name`

### סיכון 4: ביצועים (קריאה ל-API בכל הודעה)
**פתרון**: 
- שם מ-WhatsApp נשלף רק פעם אחת ב-`process_message` ונשמר
- לא צריך קריאה נוספת ל-API

## בדיקות נדרשות

1. **תרחיש 1**: משתמש חדש עם שם ב-WhatsApp
   - אמור לראות הודעה עם השם
   - אמור לקבל אפשרות לאשר או להקליד שם אחר

2. **תרחיש 2**: משתמש חדש בלי שם ב-WhatsApp
   - אמור לראות הודעה רגילה (בלי שם)
   - אמור להקליד שם

3. **תרחיש 3**: משתמש קיים שמעדכן שם
   - אמור לעבור ישירות ל-`ask_full_name` (לא דרך `confirm_whatsapp_name`)

4. **תרחיש 4**: משתמש שבוחר להשתמש בשם מ-WhatsApp
   - אמור לשמור את השם ולהמשיך ל-`ask_user_type`

5. **תרחיש 5**: משתמש שבוחר להקליד שם אחר
   - אמור לעבור ל-`ask_full_name` ולהקליד שם

## סדר יישום מומלץ

1. **שלב 1**: הוספת מצב `confirm_whatsapp_name` ל-`conversation_flow.yml`
2. **שלב 2**: הוספת action `save_whatsapp_name_as_full_name` ל-`action_executor.py`
3. **שלב 3**: הוספת תמיכה ב-`{whatsapp_name}` ב-`message_formatter.py`
4. **שלב 4**: שינוי לוגיקת `initial` ב-`conversation_engine.py`
5. **שלב 5**: שינוי `ask_full_name` ב-`conversation_flow.yml`
6. **שלב 6**: שינוי לוגיקת שמירת שם ב-`app.py`
7. **שלב 7**: בדיקות מקיפות

## הערות חשובות

1. **תאימות לאחור**: השינוי צריך לעבוד גם עם משתמשים קיימים
2. **ביצועים**: לא להוסיף קריאות נוספות ל-API
3. **UX**: ההודעה צריכה להיות ברורה ונוחה
4. **לוגיקה**: לא לפגוע בלוגיקה הקיימת של עדכון שם למשתמשים רשומים










