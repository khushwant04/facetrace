"""
Performance monitoring middleware.
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Monitor endpoint performance."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests
        if process_time > 1.0:
            print(f"⚠️  SLOW REQUEST: {request.method} {request.url.path} took {process_time:.2f}s")
        
        return response
