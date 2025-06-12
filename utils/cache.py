from flask import session, request, current_app as app
from flask_caching import Cache
from functools import wraps

# Cache instance
cache = Cache()

def session_cache_key(*args, **kwargs):
    """Generate a cache key that includes the session ID for authenticated users."""
    if session.get('user_id'):
        # For authenticated users, include session ID in the key
        return f"session_{session['user_id']}_{request.path}"
    # For non-authenticated users, use a regular cache key
    return f"public_{request.path}"

def clear_user_cache(user_id):
    """Clear all cache entries for a specific user."""
    if user_id:
        # Get all cache keys
        keys = list(cache.cache._cache.keys())
        # Delete keys that match the user's session pattern
        for key in keys:
            if key.startswith(f"session_{user_id}_"):
                cache.delete(key)

def clear_page_cache(path):
    """Clear all cache entries for a specific page."""
    keys = list(cache.cache._cache.keys())
    for key in keys:
        # Clear both public and session-specific caches for the path
        if key.startswith(f"view/{path}") or (key.startswith("session_") and key.endswith(path)):
            cache.delete(key)

def caching(timeout=300, key_prefix='view/%s'):
    """Custom cache decorator that uses session-based caching for authenticated users."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('user_id'):
                # For authenticated users, use session-based caching
                cache_key = session_cache_key()
                rv = cache.get(cache_key)
                if rv is not None:
                    return rv
                rv = f(*args, **kwargs)
                cache.set(cache_key, rv, timeout=timeout)
                return rv
            else:
                # For non-authenticated users, use regular caching
                return cache.cached(timeout=timeout, key_prefix=key_prefix)(f)(*args, **kwargs)
        return decorated_function
    return decorator