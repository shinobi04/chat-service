from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from app.database import get_db
from app.models import Conversation
from app.schemas import ConversationResponse, ConversationDetailResponse
from app.core.security import verify_session_jwt
from app.core.rate_limit import limiter

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.get("", response_model=List[ConversationResponse])
@limiter.limit("30/minute")
async def get_conversations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """Fetch all conversation threads for the current session."""
    result = await db.execute(select(Conversation).filter(Conversation.session_id == session_id).order_by(Conversation.created_at.desc()))
    conversations = result.scalars().all()
    return conversations

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
@limiter.limit("30/minute")
async def get_conversation(
    request: Request,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """Fetch the history of a specific conversation."""
    result = await db.execute(select(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.session_id == session_id
    ))
    conversation = result.scalars().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation
