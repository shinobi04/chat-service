from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models import Conversation
from app.schemas import ConversationResponse, ConversationHistoryResponse
from app.core.security import verify_session_jwt

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.get("", response_model=List[ConversationResponse])
def get_conversations(
    db: Session = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """Fetch all conversation threads for the current session."""
    conversations = db.query(Conversation).filter(Conversation.session_id == session_id).order_by(Conversation.created_at.desc()).all()
    return conversations

@router.get("/{conversation_id}/messages", response_model=ConversationHistoryResponse)
def get_conversation_messages(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """Fetch the history of a specific conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.session_id == session_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationHistoryResponse(
        conversation=conversation,
        messages=conversation.messages
    )
