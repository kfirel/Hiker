# שיפור מבנה Content ל-AI 📋

## 🎯 **הבעיה**

הקוד שבנה את ה-content ל-Gemini היה **מבולגן ולא ברור**:

```python
# לפני - מבולגן:
history = []
for msg in conversation[:-1]:
    history.append(types.Content(
        role=msg["role"],
        parts=[types.Part(text=msg["parts"][0])]
    ))

history.append(types.Content(
    role="user",
    parts=[types.Part(text=message)]
))

response = client.models.generate_content(
    model=GEMINI_MODEL,
    contents=history,
    config=config
)
```

**בעיות:**
1. ❌ קשה לקרוא
2. ❌ לא ברור מה `msg["parts"][0]` עושה
3. ❌ קוד חוזר על עצמו
4. ❌ קשה לדבג

---

## ✅ **הפתרון**

### **1. Helper Functions - פשוטות וברורות**

```python
def build_message_content(role: str, text: str) -> types.Content:
    """Build a single message for Gemini"""
    return types.Content(
        role=role,
        parts=[types.Part(text=text)]
    )


def build_conversation_history(
    chat_history: List[Dict[str, Any]],
    current_message: str,
    max_messages: int = 20
) -> List[types.Content]:
    """Build full conversation for Gemini API"""
    contents = []
    
    # Add previous messages
    for msg in chat_history[-max_messages:]:
        if msg["role"] == "user":
            contents.append(build_message_content("user", msg["content"]))
        elif msg["role"] == "assistant":
            contents.append(build_message_content("model", msg["content"]))
    
    # Add current message
    contents.append(build_message_content("user", current_message))
    
    return contents


def check_if_loop_detected(chat_history: List[Dict[str, Any]]) -> bool:
    """Check if AI stuck repeating same question"""
    if len(chat_history) < 3:
        return False
    
    last_assistant = [
        msg["content"] 
        for msg in chat_history[-3:] 
        if msg["role"] == "assistant"
    ]
    
    # If last 2 messages identical → loop!
    return len(last_assistant) >= 2 and last_assistant[-1] == last_assistant[-2]
```

---

### **2. קוד ראשי - פשוט וקריא**

```python
# אחרי - ברור ופשוט:

# Step 1: Check for loop
chat_history = user_data.get("chat_history", [])

if check_if_loop_detected(chat_history):
    logger.warning("⚠️ AI loop detected! Clearing history")
    chat_history = []

# Step 2: Build conversation
contents = build_conversation_history(
    chat_history=chat_history,
    current_message=message,
    max_messages=MAX_CONVERSATION_CONTEXT
)

# Step 3: Build config
client = genai.Client(api_key=GEMINI_API_KEY)

config = types.GenerateContentConfig(
    system_instruction=system_prompt,
    tools=[get_function_tool()],
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(mode="AUTO")
    ),
    temperature=0.1
)

# Step 4: Log (readable)
logger.info(f"🤖 ═══ SENDING TO GEMINI ═══")
logger.info(f"📱 User: {phone_number}")
logger.info(f"💬 Message: {message}")
logger.info(f"📚 History: {len(contents)-1} messages")

# Step 5: Call API
response = client.models.generate_content(
    model=GEMINI_MODEL,
    contents=contents,
    config=config
)
```

---

## 📊 **השוואה: לפני ואחרי**

| אספקט | לפני | אחרי |
|-------|------|------|
| **קריאות** | נמוכה | גבוהה ✅ |
| **מספר שורות** | 50+ | 30 ✅ |
| **מורכבות** | גבוהה | נמוכה ✅ |
| **ניתן לבדיקה** | קשה | קל ✅ |
| **תיעוד** | חסר | מלא ✅ |
| **שימוש חוזר** | אין | יש ✅ |

---

## 🔍 **מבנה ה-Content שנשלח ל-Gemini**

### **פורמט פשוט:**

```python
contents = [
    # Message 1 (from history)
    Content(
        role="user",
        parts=[Part(text="אני נוסעת לאשקלון")]
    ),
    
    # Message 2 (from history)
    Content(
        role="model",
        parts=[Part(text="באיזה שעה?")]
    ),
    
    # Message 3 (current)
    Content(
        role="user",
        parts=[Part(text="בשעה 8")]
    )
]
```

**פשוט!** כל הודעה היא `Content` עם `role` ו-`parts`.

---

## 🎯 **יתרונות**

### **1. קריאות**
```python
# לפני:
history.append(types.Content(role=msg["role"], parts=[types.Part(text=msg["parts"][0])]))

# אחרי:
contents.append(build_message_content("user", msg["content"]))
```

### **2. שימוש חוזר**
```python
# אפשר להשתמש בפונקציות בכל מקום:
def send_to_ai(message: str):
    contents = build_conversation_history([], message)
    # ...
```

### **3. בדיקות**
```python
# קל לבדוק:
def test_build_message():
    content = build_message_content("user", "שלום")
    assert content.role == "user"
    assert content.parts[0].text == "שלום"
```

### **4. דיבוג**
```python
# קל לדבג:
contents = build_conversation_history(history, message)
print(f"Sending {len(contents)} messages to AI")
for i, c in enumerate(contents):
    print(f"[{i}] {c.role}: {c.parts[0].text[:30]}...")
```

---

## 📝 **דוגמה מלאה**

```python
# Input: chat history from DB
chat_history = [
    {"role": "user", "content": "אני נוסעת לאשקלון"},
    {"role": "assistant", "content": "באיזה שעה?"}
]
current_message = "בשעה 8"

# Step 1: Check loop
if check_if_loop_detected(chat_history):
    chat_history = []

# Step 2: Build contents
contents = build_conversation_history(
    chat_history=chat_history,
    current_message=current_message
)

# Result:
# contents = [
#   Content(role="user", parts=[Part(text="אני נוסעת לאשקלון")]),
#   Content(role="model", parts=[Part(text="באיזה שעה?")]),
#   Content(role="user", parts=[Part(text="בשעה 8")])
# ]

# Step 3: Send to AI
response = client.models.generate_content(
    model="gemini-2.0-flash-exp",
    contents=contents,
    config=config
)
```

---

## 🧪 **בדיקות**

### **Test 1: Build single message**
```python
content = build_message_content("user", "שלום")
assert content.role == "user"
assert len(content.parts) == 1
assert content.parts[0].text == "שלום"
```

### **Test 2: Build conversation**
```python
history = [
    {"role": "user", "content": "היי"},
    {"role": "assistant", "content": "שלום"}
]
contents = build_conversation_history(history, "מה קורה?")
assert len(contents) == 3
assert contents[0].role == "user"
assert contents[1].role == "model"
assert contents[2].parts[0].text == "מה קורה?"
```

### **Test 3: Loop detection**
```python
history = [
    {"role": "assistant", "content": "באיזה שעה?"},
    {"role": "user", "content": "כן"},
    {"role": "assistant", "content": "באיזה שעה?"}  # Same!
]
assert check_if_loop_detected(history) == True
```

---

## 🎓 **עקרונות שיפור**

1. **DRY (Don't Repeat Yourself)**
   - קוד חוזר → פונקציה

2. **Single Responsibility**
   - כל פונקציה עושה דבר אחד

3. **Clear Naming**
   - `build_message_content` ברור מ-`append(types.Content(...))`

4. **Type Hints**
   - `-> types.Content` עוזר ל-IDE ולדיבוג

5. **Documentation**
   - Docstrings מסבירים מה כל פונקציה עושה

---

## 📋 **סיכום**

**שיפרנו:**
- ✅ קריאות הקוד
- ✅ ניתנות לתחזוקה
- ✅ ניתנות לבדיקה
- ✅ שימוש חוזר
- ✅ דיבוג קל

**התוצאה:**
קוד פשוט, ברור, וקל לעבודה! 🎉

---

**הקוד עכשיו מוכן לכל שינוי עתידי בקלות!** 🚀

