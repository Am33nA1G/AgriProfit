"""
Request Timing Middleware

Measures detailed timing for each request phase to identify performance bottlenecks.
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to measure and log request timing details"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start overall timer
        start_time = time.time()
        
        # Store timing data in request state
        request.state.timing = {
            'start': start_time,
            'middleware_start': start_time
        }
        
        # Call the next middleware/endpoint
        middleware_end = time.time()
        request.state.timing['middleware_duration'] = (middleware_end - start_time) * 1000
        
        response = await call_next(request)
        
        # Calculate total duration
        end_time = time.time()
        total_duration = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Log timing details
        logger.info(
            f"Request timing: {request.method} {request.url.path} | "
            f"Total: {total_duration:.2f}ms | "
            f"Status: {response.status_code}"
        )
        
        # Add timing header for debugging
        response.headers["X-Process-Time"] = f"{total_duration:.2f}ms"
        
        # Log slow requests
        if total_duration > 500:
            logger.warning(
                f"SLOW REQUEST DETECTED: {request.method} {request.url.path} | "
                f"Duration: {total_duration:.2f}ms | "
                f"Status: {response.status_code}"
            )
        
        return response
