import asyncio, json, hashlib
from functools import wraps
from typing import Any, Callable
import aioredis
from backend.utils.logger import get_logger

log = get_logger("RateLimit")

# Simple in-memory cache as Redis fallback
_memory_cache = {}
_memory_timestamps = {}

class CacheManager:
    def __init__(self, redis_url: str = None):
        self.redis = None
        self.redis_url = redis_url or "redis://localhost:6379"
        
    async def _init_redis(self):
        """Initialize Redis connection (graceful fallback to memory)"""
        if self.redis is None:
            try:
                self.redis = await aioredis.from_url(self.redis_url)
                await self.redis.ping()
                log.info("Redis connected")
            except Exception as e:
                log.warning(f"Redis unavailable, using memory cache: {e}")
                self.redis = False  # Mark as unavailable
    
    async def get(self, key: str) -> Any:
        """Get from cache (Redis or memory)"""
        await self._init_redis()
        
        if self.redis and self.redis is not False:
            try:
                value = await self.redis.get(key)
                return json.loads(value) if value else None
            except:
                pass
        
        # Memory fallback
        return _memory_cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set in cache with TTL"""
        await self._init_redis()
        
        if self.redis and self.redis is not False:
            try:
                await self.redis.setex(key, ttl, json.dumps(value))
                return
            except:
                pass
        
        # Memory fallback
        _memory_cache[key] = value
        # Simple TTL simulation
        _memory_timestamps[key] = asyncio.get_event_loop().time() + ttl
        
        # Cleanup old entries
        now = asyncio.get_event_loop().time()
        expired_keys = [k for k, exp_time in _memory_timestamps.items() if now > exp_time]
        for k in expired_keys:
            _memory_cache.pop(k, None)
            _memory_timestamps.pop(k, None)

# Global cache instance
cache = CacheManager()

def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Optional prefix for cache key
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                log.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            log.debug(f"Cached result for {func.__name__} (TTL: {ttl}s)")
            
            return result
        return wrapper
    return decorator

def throttle(calls_per_minute: int = 60):
    """Decorator for rate limiting function calls"""
    def decorator(func: Callable):
        call_times = []
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = asyncio.get_event_loop().time()
            
            # Remove calls older than 1 minute
            call_times[:] = [t for t in call_times if now - t < 60]
            
            # Check if we've exceeded the rate limit
            if len(call_times) >= calls_per_minute:
                wait_time = 60 - (now - call_times[0])
                log.warning(f"Rate limit hit for {func.__name__}, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                call_times.pop(0)
            
            # Record this call
            call_times.append(now)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator