"""
Cache decorator for API endpoints (synchronous Redis).
"""
from functools import wraps
from typing import Callable
import hashlib
import json

from app.services.cache_service import cache_service


def cache_response(ttl: int = 3600, key_prefix: str = "api"):
    """
    Decorator to cache API responses.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Cache key prefix
    
    Usage:
        @cache_response(ttl=300, key_prefix="students")
        async def list_students(...):
            return data
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Skip caching if Redis is not connected
            if not cache_service.is_connected():
                return await func(*args, **kwargs)
            
            # Generate cache key from function name and args
            cache_key_data = {
                "function": func.__name__,
                "kwargs": {k: str(v) for k, v in kwargs.items() if k not in ['db', 'current_user']}
            }
            cache_key_hash = hashlib.md5(
                json.dumps(cache_key_data, sort_keys=True).encode()
            ).hexdigest()
            cache_key = f"{key_prefix}:{func.__name__}:{cache_key_hash}"
            
            # Try to get from cache
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                print(f"✓ Cache HIT: {cache_key}")
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache (only if serializable)
            try:
                cache_service.set(cache_key, result, ttl=ttl)
                print(f"✓ Cache SET: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                print(f"⚠️  Cache SET failed: {e}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions
            if not cache_service.is_connected():
                return func(*args, **kwargs)
            
            cache_key_data = {
                "function": func.__name__,
                "kwargs": {k: str(v) for k, v in kwargs.items()}
            }
            cache_key_hash = hashlib.md5(
                json.dumps(cache_key_data, sort_keys=True).encode()
            ).hexdigest()
            cache_key = f"{key_prefix}:{func.__name__}:{cache_key_hash}"
            
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                print(f"✓ Cache HIT: {cache_key}")
                return cached_result
            
            result = func(*args, **kwargs)
            
            try:
                cache_service.set(cache_key, result, ttl=ttl)
                print(f"✓ Cache SET: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                print(f"⚠️  Cache SET failed: {e}")
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def invalidate_cache(pattern: str):
    """
    Decorator to invalidate cache after operation.
    
    Usage:
        @invalidate_cache(pattern="students:*")
        async def create_student(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate cache
            if cache_service.is_connected():
                deleted = cache_service.clear_pattern(pattern)
                print(f"✓ Cache INVALIDATED: {pattern} ({deleted} keys)")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if cache_service.is_connected():
                deleted = cache_service.clear_pattern(pattern)
                print(f"✓ Cache INVALIDATED: {pattern} ({deleted} keys)")
            
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
