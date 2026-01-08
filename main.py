"""
Main FastAPI Application
Hitchhiking bot for Gvar'am community with AI-powered matching
"""

import logging
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

# Import configuration
from config import VERIFY_TOKEN, GEMINI_API_KEY, PORT

# Import modules
import admin
from database import initialize_db, get_db, get_or_create_user
from webhooks import handle_whatsapp_message
from middleware.logging_middleware import LoggingMiddleware

# Configure logging for Cloud Run
import json
import sys
import os

class CloudRunFormatter(logging.Formatter):
    """Format logs as JSON for Cloud Run"""
    def format(self, record):
        log_obj = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
            "logger": record.name,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)

# Check if running in Cloud Run (has K_SERVICE env var)
IS_CLOUD_RUN = os.getenv("K_SERVICE") is not None

# Configure logging
handler = logging.StreamHandler(sys.stdout)

if IS_CLOUD_RUN:
    # Production: JSON format for Cloud Run
    handler.setFormatter(CloudRunFormatter())
else:
    # Development: Human-readable format
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)
logger = logging.getLogger(__name__)

# Disable uvicorn access logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").propagate = False

# Log configuration diagnostics
root_logger = logging.getLogger()
logger.info(f"🔧 Logger configuration:")
logger.info(f"   Environment: {'Cloud Run (Production)' if IS_CLOUD_RUN else 'Local (Development)'}")
logger.info(f"   Root level: {logging.getLevelName(root_logger.level)}")
logger.info(f"   Handlers: {len(root_logger.handlers)}")
for h in root_logger.handlers:
    logger.info(f"   - {h.__class__.__name__}: {logging.getLevelName(h.level)}")

# Initialize FastAPI app
app = FastAPI(
    title="Gvar'am Hitchhiking Bot",
    description="AI-powered WhatsApp bot for hitchhiking coordination",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Include admin router
app.include_router(admin.router)

# Serve React admin dashboard (if built)
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
frontend_index = os.path.join(frontend_dist, "index.html")

# Custom middleware to add cache-busting headers
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    
    # For admin static files
    if request.url.path.startswith("/admin"):
        # index.html - always revalidate
        if request.url.path.endswith(".html") or request.url.path == "/admin" or request.url.path == "/admin/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        # JS/CSS assets with hash - cache forever
        elif "/assets/" in request.url.path and (request.url.path.endswith(".js") or request.url.path.endswith(".css")):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        # Other static files - moderate caching
        else:
            response.headers["Cache-Control"] = "public, max-age=3600"
    
    return response

if os.path.exists(frontend_dist):
    # Mount entire dist directory as static files under /admin
    # This handles all assets, vite.svg, etc.
    app.mount("/admin", StaticFiles(directory=frontend_dist, html=True), name="admin_static")
    logger.info("✅ Admin dashboard available at /admin")
else:
    logger.warning("⚠️  Admin dashboard not built - run 'cd frontend && npm run build'")


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
        
        if not body.get("entry"):
            return JSONResponse(content={"status": "ok"})
        
        # Process each entry and change
        for entry in body["entry"]:
            changes = entry.get("changes", [])
            
            for change in changes:
                value = change.get("value", {})
                
                if "messages" not in value:
                    continue
                
                # Extract contact information (includes user's name)
                contacts = value.get("contacts", [])
                contact_map = {contact.get("wa_id"): contact for contact in contacts}
                
                messages = value["messages"]
                
                # Handle each message
                for message in messages:
                    # Attach contact info to message if available
                    from_number = message.get("from")
                    if from_number in contact_map:
                        contact_profile = contact_map[from_number].get("profile", {})
                        message["_contact_name"] = contact_profile.get("name")
                    
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
            driver_rides = user_data.get("driver_rides", [])
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            users.append({
                "phone_number": user_data.get("phone_number"),
                "name": user_data.get("name"),
                "active_driver_rides": len([r for r in driver_rides if r.get("active", True)]),
                "active_hitchhiker_requests": len([r for r in hitchhiker_requests if r.get("active", True)]),
                "message_count": len(user_data.get("chat_history", [])),
                "last_seen": user_data.get("last_seen")
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


# Note: StaticFiles with html=True handles all /admin/* routes automatically
# including React Router navigation and serving index.html as fallback


if __name__ == "__main__":
    import subprocess
    import sys
    import atexit
    
    logger.info("🚀 Starting Gvar'am Hitchhiking Bot v2.0")
    logger.info(f"   VERIFY_TOKEN: {'✅' if VERIFY_TOKEN else '❌'}")
    logger.info(f"   GEMINI_API_KEY: {'✅' if GEMINI_API_KEY else '❌'}")
    
    # Check if running in development (K_SERVICE is only set in Cloud Run)
    is_dev = os.getenv("K_SERVICE") is None
    
    # Start frontend in development mode (unless explicitly disabled)
    start_frontend = is_dev and "--no-frontend" not in sys.argv
    vite_process = None
    
    if start_frontend:
        frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
        if os.path.exists(frontend_dir):
            try:
                logger.info("🎨 Starting Frontend dev server...")
                vite_process = subprocess.Popen(
                    ["/opt/homebrew/bin/npm", "run", "dev"],
                    cwd=frontend_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                def cleanup():
                    if vite_process:
                        logger.info("🛑 Stopping frontend dev server...")
                        vite_process.terminate()
                        try:
                            vite_process.wait(timeout=5)
                        except:
                            vite_process.kill()
                
                atexit.register(cleanup)
                logger.info("✅ Frontend dev server starting on http://localhost:3000")
            except Exception as e:
                logger.warning(f"⚠️  Could not start frontend: {e}")
    
    # Disable uvicorn access logs (HTTP request logs)
    if is_dev and os.getenv("ENABLE_RELOAD", "true").lower() == "true":
        # Use import string for reload mode
        uvicorn.run(
            "main:app",  # Import string for reload
            host="0.0.0.0", 
            port=PORT,
            access_log=False,
            log_level="warning",
            reload=True
        )
    else:
        # Production mode - use app object directly
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=PORT,
            access_log=False,
            log_level="warning"
        )

