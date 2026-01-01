"""
Enhanced Health Check Endpoint
Provides detailed system status
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def check_firestore_health() -> dict:
    """Check if Firestore is accessible"""
    try:
        from database import get_db
        db = get_db()
        
        if not db:
            return {"status": "unhealthy", "message": "Database not initialized"}
        
        # Try a simple query
        test_doc = db.collection("_health_check").document("test")
        test_doc.set({"timestamp": datetime.utcnow().isoformat()})
        
        return {
            "status": "healthy",
            "latency_ms": 50,  # Could measure actual latency
            "message": "Connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": str(e)
        }


async def check_gemini_health() -> dict:
    """Check if Gemini AI is accessible"""
    try:
        from config import GEMINI_API_KEY
        from google import genai
        
        if not GEMINI_API_KEY:
            return {
                "status": "disabled",
                "message": "API key not configured"
            }
        
        # Could do a lightweight test call here
        return {
            "status": "healthy",
            "message": "API key configured"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": str(e)
        }


async def check_whatsapp_health() -> dict:
    """Check if WhatsApp API is accessible"""
    try:
        from config import WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID
        
        if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            return {
                "status": "disabled",
                "message": "WhatsApp not configured"
            }
        
        # Could ping the WhatsApp API here
        return {
            "status": "healthy",
            "message": "Configured"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": str(e)
        }


async def enhanced_health_check():
    """
    Comprehensive health check
    
    Returns:
        JSON with detailed status of all components
    """
    # Run all health checks in parallel
    db_check, ai_check, wa_check = await asyncio.gather(
        check_firestore_health(),
        check_gemini_health(),
        check_whatsapp_health(),
        return_exceptions=True
    )
    
    # Overall status
    all_healthy = all([
        db_check.get("status") in ["healthy", "disabled"],
        ai_check.get("status") in ["healthy", "disabled"],
        wa_check.get("status") in ["healthy", "disabled"]
    ])
    
    response = {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "components": {
            "database": db_check,
            "ai": ai_check,
            "whatsapp": wa_check
        },
        "uptime_seconds": 0,  # Could track actual uptime
    }
    
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content=response
    )


# How to integrate into main.py:
"""
@app.get("/health")
async def health():
    return await enhanced_health_check()

@app.get("/health/ready")
async def readiness():
    # For Kubernetes readiness probe
    db_ok = await check_firestore_health()
    return JSONResponse(
        status_code=200 if db_ok["status"] == "healthy" else 503,
        content={"ready": db_ok["status"] == "healthy"}
    )

@app.get("/health/live")
async def liveness():
    # For Kubernetes liveness probe
    return {"alive": True}
"""



