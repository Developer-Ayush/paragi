from fastapi import Request, HTTPException
from core.config import Settings

async def auth_middleware(request: Request, call_next):
    # Skip health check
    if request.url.path == "/health":
        return await call_next(request)
        
    settings = Settings.from_env()
    api_key = request.headers.get("X-API-Key")
    
    if settings.api_key_required and api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    return await call_next(request)
