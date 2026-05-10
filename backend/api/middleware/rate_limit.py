import time
from fastapi import Request, HTTPException
from typing import Dict

# Simple memory-based rate limiter
RATE_LIMITS: Dict[str, float] = {}
REQUEST_WINDOW = 60.0 # 1 minute
MAX_REQUESTS = 100

async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    now = time.time()
    
    # Very basic window cleanup (in production use Redis)
    if client_ip not in RATE_LIMITS:
        RATE_LIMITS[client_ip] = []
    
    # Filter requests in the current window
    RATE_LIMITS[client_ip] = [t for t in RATE_LIMITS[client_ip] if now - t < REQUEST_WINDOW]
    
    if len(RATE_LIMITS[client_ip]) >= MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests")
    
    RATE_LIMITS[client_ip].append(now)
    return await call_next(request)
