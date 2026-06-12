import logging
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limit import limiter
from app.core.config import settings
from app.core.ip_whitelist import IPWhitelistMiddleware
from app.routers import sessions, chat, conversations

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Chat Backend Service",
    description="Backend-to-backend API for Gemma 3 powered chat app using zero-latency JWT sessions",
    version="1.0.0"
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# IP Whitelisting — configurable via ALLOWED_IPS env var
app.add_middleware(IPWhitelistMiddleware)

# Include routers
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(conversations.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "chat-backend"}

