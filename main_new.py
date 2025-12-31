"""
Main FastAPI Application
Hitchhiking bot for Gvar'am community with AI-powered matching
"""

import logging
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
import uvicorn

# Import configuration
from config import VERIFY_TOKEN, GEMINI_API_KEY, PORT

# Import modules
import admin
from database import initialize_db, get_db, get_or_create_user
from webhooks import handle_whatsapp_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Gvar'am Hitchhiking Bot",
    description="AI-powered WhatsApp bot for hitchhiking coordination",
    version="2.0.0"
)

# Include admin router
app.include_router(admin.router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    
    # Initialize Firestore
    db = initialize_db()
    
    # Log Gemini status
    if GEMINI_API_KEY:
        logger.info("✅ Gemini API key configured")
    else:
        logger.warning("⚠️  GEMINI_API_KEY not set - AI features disabled")
    
    # Log admin status
    logger.info(f"🔧 Admin status: {admin.get_admin_status_message()}")
    
    logger.info("🚀 Application started successfully!")


@app.get("/")
async def root():
    """Health check endpoint"""
    db = get_db()
    return {
        "status": "healthy",
        "service": "Gvar'am Hitchhiking Bot",
        "version": "2.0.0",
        "database": "connected" if db else "disconnected",
        "ai": "enabled" if GEMINI_API_KEY else "disabled",
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
    """Handle incoming WhatsApp messages"""
    try:
        body = await request.json()
        logger.info(f"📥 Received webhook")
        
        if not body.get("entry"):
            return JSONResponse(content={"status": "ok"})
        
        # Process each entry and change
        for entry in body["entry"]:
            changes = entry.get("changes", [])
            
            for change in changes:
                value = change.get("value", {})
                
                if "messages" not in value:
                    continue
                
                messages = value["messages"]
                
                # Handle each message
                for message in messages:
                    await handle_whatsapp_message(message)
        
        return JSONResponse(content={"status": "ok"})
    
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}", exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)})


@app.get("/users", dependencies=[Depends(admin.verify_admin_token)])
async def list_users():
    """List all users in database (requires admin token)"""
    db = get_db()
    if not db:
        return {"error": "Database not available"}
    
    try:
        users = []
        docs = db.collection("users").stream()
        
        for doc in docs:
            user_data = doc.to_dict()
            users.append({
                "phone_number": user_data.get("phone_number"),
                "role": user_data.get("role"),
                "message_count": len(user_data.get("chat_history", [])),
                "last_seen": user_data.get("last_seen"),
                "driver_data": user_data.get("driver_data", {}),
                "hitchhiker_data": user_data.get("hitchhiker_data", {})
            })
        
        return {"users": users, "count": len(users)}
    
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return {"error": str(e)}


@app.get("/user/{phone_number}", dependencies=[Depends(admin.verify_admin_token)])
async def get_user_details(phone_number: str):
    """Get specific user data (requires admin token)"""
    db = get_db()
    if not db:
        return {"error": "Database not available"}
    
    try:
        doc_ref = db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            return {"error": "User not found"}
    
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    logger.info("🚀 Starting Gvar'am Hitchhiking Bot v2.0")
    logger.info(f"   VERIFY_TOKEN: {'✅' if VERIFY_TOKEN else '❌'}")
    logger.info(f"   GEMINI_API_KEY: {'✅' if GEMINI_API_KEY else '❌'}")
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)

