# Restart Button - User Guide

## What is the Restart Button?

The restart button (🔄 התחל מחדש) is a convenient feature that allows you to restart your conversation with the chatbot at any time, without needing to remember or type any commands.

## Where Does It Appear?

The restart button appears in **every interactive message** that has choice options. This includes:

- ✅ User type selection (טרמפיסט/נהג/שניהם)
- ✅ Yes/No questions
- ✅ Ride request questions
- ✅ Time selection options
- ✅ Routine questions
- ✅ Registered user menu
- ✅ Alert preference settings
- ✅ All other choice-based questions

## How It Looks

### Example 1: User Type Question
```
🤖 מה אתה?

┌──────────────────────────┐
│ 1️⃣ טרמפיסט ונהג           │
│ 2️⃣ טרמפיסט                │
│ 3️⃣ נהג                    │
│ 🔄 התחל מחדש              │  ← Restart button
└──────────────────────────┘
```

### Example 2: Yes/No Question
```
🤖 האם אתה מחפש כרגע טרמפ?

┌──────────────────────────┐
│ 1️⃣ כן                     │
│ 2️⃣ לא                     │
│ 🔄 התחל מחדש              │  ← Restart button
└──────────────────────────┘
```

### Example 3: Registered User Menu
```
🤖 היי כפיר! 👋
   מה תרצה לעשות?

┌──────────────────────────┐
│ 1️⃣ מחפש טרמפ              │
│ 2️⃣ מתכנן יציאה            │
│ 3️⃣ עדכון שגרה             │
│ 4️⃣ עדכון פרטים           │
│ 🔄 התחל מחדש              │  ← Restart button
└──────────────────────────┘
```

## What Happens When You Click It?

When you click the restart button:

1. **All your data is deleted**
   - Your name
   - Your settlement
   - Your user type
   - Your ride requests
   - Your routines
   - Everything!

2. **You start fresh**
   - You'll see the welcome message again
   - You'll be asked for your name
   - You'll go through registration from scratch

3. **No confirmation required**
   - One click and you're restarted
   - No "Are you sure?" dialog
   - Instant reset

## When to Use It

### Good Reasons to Restart:
- ✅ You made a mistake during registration
- ✅ You want to register with different information
- ✅ You accidentally selected wrong user type
- ✅ You want to test the bot from the beginning
- ✅ You're registering for someone else

### Not Recommended:
- ❌ If you just want to go back one step (use "חזור" command instead)
- ❌ If you just want to update one field (use the update menu instead)
- ❌ If you accidentally click it (you'll lose all your data!)

## Alternative: Text Commands

You can still use text commands if you prefer:

- **"חדש"** - Same as restart button (full reset)
- **"חזור"** - Go back one step (doesn't delete data)
- **"תפריט"** - Return to main menu (for registered users)
- **"מחק"** - Delete all your data
- **"עזרה"** - Show help message

## Technical Details

### Button ID
- Internal ID: `restart_button`
- This is what gets sent to the bot when you click it

### Button Text
- Hebrew: "🔄 התחל מחדש"
- English translation: "🔄 Start Over"

### Button Description (for lists)
- When there are 4+ options, lists show a description
- Description: "חזור להתחלה" (Return to start)

### Implementation
- Automatically added to all choice questions
- No need to manually add it to conversation flow
- Always appears as the last option

## For Developers

If you're modifying the conversation flow:

1. **You don't need to add the restart button manually**
   - It's automatically added by `_build_buttons()` method

2. **It respects WhatsApp limits**
   - Max 3 reply buttons → becomes list with restart
   - Max 10 list items → restart is item #10

3. **It works with any state**
   - As long as `expected_input` is `"choice"`
   - As long as there are `options` defined

4. **Handler location**
   - Handled in `_handle_choice_input()` method
   - Calls `_handle_restart()` which does full user reset

## Examples of Use Cases

### Use Case 1: Registration Mistake
```
User: [Starting registration]
Bot: מה השם המלא שלך?
User: כפיר
Bot: באיזה ישוב אתה גר?
User: תל אביב
Bot: מה אתה?

[User realizes they should register as driver, not hitchhiker]

User: [Clicks 🔄 התחל מחדש]
Bot: היי בורך הבא להייקר הצ'אט בוט לטרמפיסט...
User: [Starts fresh with correct info]
```

### Use Case 2: Testing
```
Developer: [Testing the bot]
[Goes through entire registration]
Bot: מעולה! ההרשמה הושלמה בהצלחה.

[Developer wants to test again]

Developer: "שלום"
Bot: [Shows menu with buttons]
Developer: [Clicks 🔄 התחל מחדש]
Bot: היי בורך הבא... [Fresh start for testing]
```

### Use Case 3: Multiple Users
```
User A: [Completes registration on shared device]
User B: [Picks up same phone]
User B: "היי"
Bot: היי כפיר! 👋 [Shows User A's name]
User B: [Clicks 🔄 התחל מחדש]
Bot: היי בורך הבא... [Fresh registration for User B]
```

## FAQs

### Q: Is the restart permanent?
**A**: Yes, it deletes all your data. There's no undo.

### Q: Can I go back after restarting?
**A**: No, your previous data is permanently deleted.

### Q: Do I need to confirm the restart?
**A**: No, it happens immediately when you click the button.

### Q: What if I click it by accident?
**A**: You'll need to re-register. Be careful!

### Q: Can I restart by typing?
**A**: Yes, type "חדש" to restart.

### Q: Does it work for registered users?
**A**: Yes, but it will delete your entire profile!

### Q: Is there a "back" button instead?
**A**: Yes, type "חזור" to go back one step without deleting data.

---

## Visual Flow Diagram

```
Any Interactive Message
         │
         ├── Regular option selected
         │   └──> Continue conversation
         │
         └── 🔄 התחל מחדש selected
             │
             ├──> Delete all user data
             ├──> Create fresh user
             └──> Show welcome message
                  └──> Ask for name (start over)
```

---

**Remember**: The restart button is powerful and convenient, but use it carefully as it permanently deletes all your data! 🔄

