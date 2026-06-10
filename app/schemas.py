from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from uuid import UUID

# Sessions
class SessionResponse(BaseModel):
    session_id: str
    access_token: str
    token_type: str = "bearer"

# Chat
class ChatRequest(BaseModel):
    content: str
    image_base64: Optional[str] = None

class ChatResponse(BaseModel):
    message_id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

# Conversations
class ConversationResponse(BaseModel):
    id: UUID
    session_id: str
    title: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    image_path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationHistoryResponse(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]
