"""
STEP 3: WhatsApp + Database + AI Integration
Full bot with Gemini AI, function calling, and smart data extraction
"""

import os
import logging
import json
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import requests
from dotenv import load_dotenv
from google.cloud import firestore
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Step 3 - WhatsApp + Database + AI")

# Environment variables
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_test_token_123")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# WhatsApp API URL
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

# Firestore client
db = None

# Welcome message in Hebrew
WELCOME_MESSAGE = """שלום וברוך הבא לאפליקצית הטרמפים של גברעם! 🚗

אם אתה מחפש טרמפ שלח לי הודעה בסגנון:
"אני מחפש טרמפ לתל אביב בשעה 12:00 מחר"

אם אתה נהג שרוצה לעזור:
"אני נוסע בימים א-ה לתל אביב בשעה 9 וחוזר ב-17:30"

איך אני יכול לעזור לך היום?"""

# System prompt for Gemini
SYSTEM_PROMPT = """אתה עוזר וירטואלי לקהילת הטרמפים של גברעם. תפקידך:

1. לזהות אם המשתמש הוא נהג (driver) או מחפש טרמפ (hitchhiker)
2. לאסוף מידע מובנה:
   - נהג: מוצא, יעד, ימים בשבוע, שעות נסיעה, מספר מקומות פנויים
   - מחפש טרמפ: מוצא, יעד, תאריך/זמן רצוי, גמישות
3. לעזור בהתאמה בין נהגים למחפשי טרמפ
4. לדבר בעברית בצורה ידידותית וברורה

כאשר יש לך מספיק מידע, השתמש בפונקציה update_user_records לשמור את הנתונים.

אם משהו לא ברור, שאל שאלות הבהרה.

הקשר הנוכחי:
- תאריך ושעה: {current_timestamp}
- יום בשבוע: {current_day_of_week}"""

# Function calling schema - will be created after genai.configure()
def get_function_tool():
    """Get the function calling tool for Gemini"""
    return genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="update_user_records",
                description="Update user role and structured data in the database. Use this when you have collected enough information about the user.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "role": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="User's role - either 'driver' or 'hitchhiker'",
                            enum=["driver", "hitchhiker"]
                        ),
                        "origin": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Starting location (e.g., 'גברעם', 'ירושלים')"
                        ),
                        "destination": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Destination location (e.g., 'תל אביב', 'חיפה')"
                        ),
                        "days": genai.protos.Schema(
                            type=genai.protos.Type.ARRAY,
                            description="Days of the week (for drivers)",
                            items=genai.protos.Schema(type=genai.protos.Type.STRING)
                        ),
                        "departure_time": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Departure time - e.g., '09:00', '17:30'"
                        ),
                        "return_time": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Return time (for drivers who make round trips)"
                        ),
                        "available_seats": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="Number of available seats (for drivers)"
                        ),
                        "travel_date": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Specific travel date for hitchhikers"
                        ),
                        "flexibility": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Time flexibility for hitchhikers"
                        ),
                        "notes": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Additional notes or preferences"
                        )
                    },
                    required=["role", "origin", "destination"]
                )
            )
        ]
    )


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db
    
    # Initialize Firestore
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            db = firestore.Client(project=project_id)
            logger.info(f"✅ Firestore initialized for project: {project_id}")
        else:
            db = firestore.Client()
            logger.info("✅ Firestore initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Firestore: {str(e)}")
        logger.warning("⚠️  Continuing without database...")
    
    # Initialize Gemini
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("✅ Gemini AI initialized successfully")
    else:
        logger.warning("⚠️  GEMINI_API_KEY not set - AI features disabled")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "step": "3 - WhatsApp + Database + AI",
        "database": "connected" if db else "disconnected",
        "ai": "enabled" if GEMINI_API_KEY else "disabled",
        "message": "Full AI-powered hitchhiking bot!"
    }


@app.get("/webhook")
async def verify_webhook(request: Request):
    """Webhook verification endpoint for WhatsApp"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    logger.info(f"Webhook verification request - mode: {mode}")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ Webhook verified successfully!")
        return Response(content=challenge, media_type="text/plain")
    
    logger.warning("❌ Webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle incoming WhatsApp messages with AI processing"""
    try:
        body = await request.json()
        logger.info(f"📥 Received webhook")
        
        if not body.get("entry"):
            return JSONResponse(content={"status": "ok"})
        
        for entry in body["entry"]:
            changes = entry.get("changes", [])
            
            for change in changes:
                value = change.get("value", {})
                
                if "messages" not in value:
                    continue
                
                messages = value["messages"]
                
                for message in messages:
                    from_number = message.get("from")
                    message_type = message.get("type")
                    
                    logger.info(f"📨 Message from: {from_number}, type: {message_type}")
                    
                    if message_type == "text":
                        message_text = message["text"]["body"]
                        logger.info(f"   Content: {message_text}")
                        
                        # Get or create user
                        user_data = await get_or_create_user(from_number)
                        is_new_user = len(user_data.get("chat_history", [])) == 0
                        
                        # Send welcome message to new users
                        if is_new_user:
                            await send_whatsapp_message(from_number, WELCOME_MESSAGE)
                            await add_message_to_history(from_number, "assistant", WELCOME_MESSAGE)
                        
                        # Process with AI
                        await process_message_with_ai(from_number, message_text, user_data)
                    
                    else:
                        await send_whatsapp_message(
                            from_number,
                            "אני יכול להגיב רק להודעות טקסט כרגע 📝"
                        )
        
        return JSONResponse(content={"status": "ok"})
    
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}", exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)})


async def process_message_with_ai(phone_number: str, message: str, user_data: dict):
    """Process user message with Gemini AI"""
    try:
        if not GEMINI_API_KEY:
            # Fallback without AI
            response = f"קיבלתי: {message}\n(AI לא מופעל)"
            await send_whatsapp_message(phone_number, response)
            return
        
        # Add user message to history
        await add_message_to_history(phone_number, "user", message)
        
        # Get current context
        now = datetime.utcnow()
        current_timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
        current_day_of_week = now.strftime("%A")
        
        # Build system prompt with context
        system_prompt = SYSTEM_PROMPT.format(
            current_timestamp=current_timestamp,
            current_day_of_week=current_day_of_week
        )
        
        # Build conversation history
        chat_history = user_data.get("chat_history", [])
        conversation = []
        
        for msg in chat_history[-4:]:  # Last 4 messages
            if msg["role"] == "user":
                conversation.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                conversation.append({"role": "model", "parts": [msg["content"]]})
        
        # Initialize model with function calling
        model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            tools=get_function_tool(),
            system_instruction=system_prompt
        )
        
        # Start chat
        chat = model.start_chat(history=conversation[:-1])
        
        # Send message
        response = chat.send_message(message)
        
        # Check for function calls
        if response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    function_name = function_call.name
                    function_args = dict(function_call.args)
                    
                    logger.info(f"🤖 AI called function: {function_name}")
                    logger.info(f"   Args: {json.dumps(function_args, ensure_ascii=False)}")
                    
                    # Execute function
                    result = await execute_function_call(function_name, function_args, phone_number)
                    
                    # Send result back to AI
                    response = chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=function_name,
                                    response={"result": result}
                                )
                            )]
                        )
                    )
        
        # Get final text response
        ai_response = response.text
        logger.info(f"🤖 AI response: {ai_response[:100]}...")
        
        # Send to user
        await send_whatsapp_message(phone_number, ai_response)
        
        # Add to history
        await add_message_to_history(phone_number, "assistant", ai_response)
    
    except Exception as e:
        logger.error(f"❌ Error in AI processing: {str(e)}", exc_info=True)
        error_msg = "סליחה, נתקלתי בבעיה. אנא נסה שוב. 🙏"
        await send_whatsapp_message(phone_number, error_msg)


async def execute_function_call(function_name: str, function_args: dict, phone_number: str) -> dict:
    """Execute AI function call"""
    try:
        if function_name == "update_user_records":
            role = function_args.get("role")
            
            # Build role data
            role_data = {}
            if role == "driver":
                role_data = {
                    "origin": function_args.get("origin"),
                    "destination": function_args.get("destination"),
                    "days": function_args.get("days", []),
                    "departure_time": function_args.get("departure_time"),
                    "return_time": function_args.get("return_time"),
                    "available_seats": function_args.get("available_seats", 1),
                    "notes": function_args.get("notes", "")
                }
            elif role == "hitchhiker":
                role_data = {
                    "origin": function_args.get("origin"),
                    "destination": function_args.get("destination"),
                    "travel_date": function_args.get("travel_date"),
                    "departure_time": function_args.get("departure_time"),
                    "flexibility": function_args.get("flexibility", "flexible"),
                    "notes": function_args.get("notes", "")
                }
            
            # Update database
            success = await update_user_role_and_data(phone_number, role, role_data)
            
            return {
                "success": success,
                "message": f"User registered as {role}",
                "role": role,
                "data": role_data
            }
        
        return {"success": False, "message": f"Unknown function: {function_name}"}
    
    except Exception as e:
        logger.error(f"❌ Error executing function: {str(e)}")
        return {"success": False, "message": str(e)}


# Database functions (same as Step 2)
async def get_or_create_user(phone_number: str) -> dict:
    """Get user from Firestore or create if doesn't exist"""
    if not db:
        return {"phone_number": phone_number, "chat_history": []}
    
    try:
        doc_ref = db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            user_data = {
                "phone_number": phone_number,
                "role": None,
                "notification_level": "all",
                "driver_data": {},
                "hitchhiker_data": {},
                "created_at": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat(),
                "chat_history": []
            }
            doc_ref.set(user_data)
            logger.info(f"✅ Created new user: {phone_number}")
            return user_data
    except Exception as e:
        logger.error(f"❌ Error getting user: {str(e)}")
        return {"phone_number": phone_number, "chat_history": []}


async def add_message_to_history(phone_number: str, role: str, content: str) -> bool:
    """Add message to chat history (keep last 5)"""
    if not db:
        return False
    
    try:
        doc_ref = db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if not doc.exists:
            return False
        
        user_data = doc.to_dict()
        chat_history = user_data.get("chat_history", [])
        
        chat_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        chat_history = chat_history[-5:]
        
        doc_ref.update({
            "chat_history": chat_history,
            "last_seen": datetime.utcnow().isoformat()
        })
        
        return True
    except Exception as e:
        logger.error(f"❌ Error adding to history: {str(e)}")
        return False


async def update_user_role_and_data(phone_number: str, role: str, role_data: dict) -> bool:
    """Update user role and data"""
    if not db:
        return False
    
    try:
        doc_ref = db.collection("users").document(phone_number)
        
        update_data = {
            "role": role,
            "last_seen": datetime.utcnow().isoformat()
        }
        
        if role == "driver":
            update_data["driver_data"] = role_data
        elif role == "hitchhiker":
            update_data["hitchhiker_data"] = role_data
        
        doc_ref.set(update_data, merge=True)
        logger.info(f"✅ Updated {phone_number} as {role}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error updating role: {str(e)}")
        return False


async def send_whatsapp_message(phone_number: str, message: str) -> bool:
    """Send WhatsApp message"""
    try:
        if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            return False
        
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message}
        }
        
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        logger.info(f"✅ Message sent to {phone_number}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error sending message: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("🚀 Starting AI-Powered Hitchhiking Bot (Step 3)")
    logger.info(f"   VERIFY_TOKEN: {'✅' if VERIFY_TOKEN else '❌'}")
    logger.info(f"   WHATSAPP_TOKEN: {'✅' if WHATSAPP_TOKEN else '❌'}")
    logger.info(f"   GEMINI_API_KEY: {'✅' if GEMINI_API_KEY else '❌'}")
    
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

