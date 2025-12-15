"""
Redis caching service using Redis Cloud.
"""
import redis
import json
from typing import Optional, Any

from app.config import settings  # Import settings


class CacheService:
    """Redis cache service for performance optimization."""
    
    def __init__(self):
        # Redis Cloud configuration from settings
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
            username=settings.REDIS_USERNAME,
            password=settings.REDIS_PASSWORD,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        self.default_ttl = 3600  # 1 hour default
        self._connected = False
    
    def connect(self) -> bool:
        """Test Redis connection."""
        try:
            self.client.ping()
            self._connected = True
            print("✓ Connected to Redis Cloud")
            return True
        except Exception as e:
            print(f"✗ Redis connection failed: {e}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if not self._connected:
                self.connect()
            
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache GET error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL."""
        try:
            if not self._connected:
                self.connect()
            
            serialized = json.dumps(value, default=str)  # default=str handles datetime, UUID
            ttl = ttl or self.default_ttl
            
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Cache SET error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if not self._connected:
                self.connect()
            
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"Cache DELETE error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            if not self._connected:
                self.connect()
            
            return self.client.exists(key) > 0
        except Exception as e:
            print(f"Cache EXISTS error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            if not self._connected:
                self.connect()
            
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache CLEAR error: {e}")
            return 0
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        try:
            if not self._connected:
                self.connect()
            
            return self.client.incr(key, amount)
        except Exception as e:
            print(f"Cache INCR error: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            if not self._connected:
                self.connect()
            
            info = self.client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            print(f"Cache STATS error: {e}")
            return {}


# Global instance
cache_service = CacheService()

# Test connection on import
cache_service.connect()
