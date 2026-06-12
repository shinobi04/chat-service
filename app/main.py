import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    description="Backend API for Gemma 3 powered chat app using zero-latency JWT sessions",
    version="1.0.0"
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — configurable via CORS_ORIGINS env var
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# IP Whitelisting — configurable via ALLOWED_IPS env var
app.add_middleware(IPWhitelistMiddleware)

# Include routers
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(conversations.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "chat-backend"}

