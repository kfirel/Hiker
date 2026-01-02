"""
Logging Middleware
Automatically log errors and activities to Firestore
"""

import logging
import traceback
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from database import get_db
from database.logging import log_error, log_activity

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log errors and activities to Firestore
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and log any errors
        """
        try:
            response = await call_next(request)
            
            # Log 4xx and 5xx responses
            if response.status_code >= 400:
                db = get_db()
                if db:
                    severity = "error" if response.status_code >= 500 else "warning"
                    await log_error(
                        db=db,
                        severity=severity,
                        message=f"{request.method} {request.url.path} returned {response.status_code}",
                        context={
                            "method": request.method,
                            "path": str(request.url.path),
                            "status_code": response.status_code,
                            "client_host": request.client.host if request.client else None
                        }
                    )
            
            return response
        
        except Exception as e:
            # Log the exception
            db = get_db()
            if db:
                await log_error(
                    db=db,
                    severity="error",
                    message=f"Unhandled exception: {str(e)}",
                    stack_trace=traceback.format_exc(),
                    context={
                        "method": request.method,
                        "path": str(request.url.path),
                        "client_host": request.client.host if request.client else None
                    }
                )
            
            # Re-raise the exception
            raise

