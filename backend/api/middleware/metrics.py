import time
from fastapi import Request
from typing import Dict, Any

# Simple in-memory metrics store
METRICS: Dict[str, Any] = {
    "total_requests": 0,
    "total_latency_ms": 0.0,
    "errors": 0,
    "endpoints": {}
}

async def metrics_middleware(request: Request, call_next):
    METRICS["total_requests"] += 1
    path = request.url.path
    if path not in METRICS["endpoints"]:
        METRICS["endpoints"][path] = {"count": 0, "latency": 0.0}
    
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            METRICS["errors"] += 1
        return response
    except Exception:
        METRICS["errors"] += 1
        raise
    finally:
        latency = (time.perf_counter() - start_time) * 1000
        METRICS["total_latency_ms"] += latency
        METRICS["endpoints"][path]["count"] += 1
        METRICS["endpoints"][path]["latency"] += latency

def get_metrics():
    return METRICS
