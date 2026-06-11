from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance — import this in routers to apply @limiter.limit()
# Uses client IP as the rate-limit key
limiter = Limiter(key_func=get_remote_address)
