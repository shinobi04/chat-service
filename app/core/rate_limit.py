from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

def smart_rate_limit_key(request: Request) -> str:
    """
    Extract conversation_id from query or path parameters for conversation-based rate limiting.
    If not present, fallback to the client's IP address.
    """
    # 1. Try to get from query params (e.g. POST /chat?conversation_id=...)
    conversation_id = request.query_params.get("conversation_id")
    
    # 2. Try to get from path params (e.g. GET /conversations/{conversation_id})
    if not conversation_id and hasattr(request, 'path_params'):
        conversation_id = request.path_params.get("conversation_id")
        
    if conversation_id:
        return f"conv:{conversation_id}"
        
    # 3. Fallback to IP address
    return f"ip:{get_remote_address(request)}"

# Shared limiter instance — import this in routers to apply @limiter.limit()
# Uses conversation_id if present, otherwise falls back to client IP
limiter = Limiter(key_func=smart_rate_limit_key)
