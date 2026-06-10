import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import sessions, chat, conversations

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Chat Backend Service",
    description="Backend API for Gemma 3 powered chat app using zero-latency JWT sessions",
    version="1.0.0"
)

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(conversations.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "chat-backend"}
