import time
from fastapi import Request
from core.logger import get_logger

log = get_logger("api.middleware.logging")

async def logging_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    log.info(
        f"{request.method} {request.url.path} | "
        f"status={response.status_code} | "
        f"latency={process_time:.2f}ms"
    )
    return response
