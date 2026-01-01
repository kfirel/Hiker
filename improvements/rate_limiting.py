"""
Rate Limiting Implementation
Protects against spam and abuse
"""

from fastapi import Request, HTTPException
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # phone_number -> [timestamps]
        
        # Clean up old entries every minute
        asyncio.create_task(self._cleanup_task())
    
    async def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if request is within rate limit
        
        Args:
            identifier: User identifier (phone number or IP)
        
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Remove old timestamps
        self.requests[identifier] = [
            ts for ts in self.requests[identifier]
            if ts > cutoff
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[identifier].append(now)
        return True
    
    async def _cleanup_task(self):
        """Periodically clean up old entries"""
        while True:
            await asyncio.sleep(60)
            now = datetime.utcnow()
            cutoff = now - timedelta(seconds=self.window_seconds * 2)
            
            # Remove very old entries
            for identifier in list(self.requests.keys()):
                self.requests[identifier] = [
                    ts for ts in self.requests[identifier]
                    if ts > cutoff
                ]
                
                # Remove empty entries
                if not self.requests[identifier]:
                    del self.requests[identifier]


# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


async def check_rate_limit_middleware(request: Request, phone_number: str):
    """
    Middleware to check rate limits
    
    Usage in endpoint:
        @app.post("/webhook")
        async def handle_webhook(request: Request):
            phone = extract_phone(request)
            await check_rate_limit_middleware(request, phone)
            # ... process request
    """
    if not await rate_limiter.check_rate_limit(phone_number):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Too many requests",
                "message_hebrew": "שלחת יותר מדי הודעות. נסה שוב בעוד דקה.",
                "retry_after": 60
            }
        )



