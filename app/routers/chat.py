from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.models import Conversation, Message, RoleEnum
from app.schemas import ChatRequest, ChatResponse
from app.core.security import verify_session_jwt
from app.services.ollama_service import generate_chat_response

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
def handle_chat(
    request: ChatRequest,
    conversation_id: Optional[UUID] = Query(None, description="Provide this to continue an existing conversation"),
    db: Session = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """
    Main endpoint for chat.
    If conversation_id is not provided, it creates a new conversation.
    """
    if conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.session_id == session_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create a new conversation
        title = request.content[:30] + "..." if len(request.content) > 30 else request.content
        conversation = Conversation(session_id=session_id, title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role=RoleEnum.user,
        content=request.content,
        image_path=None 
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Prepare message history for Ollama
    history = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()).all()
    
    ollama_messages = [{"role": msg.role.value, "content": msg.content} for msg in history]

    try:
        ai_response_text = generate_chat_response(messages=ollama_messages, image_base64=request.image_base64)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

    # Save AI message
    ai_message = Message(
        conversation_id=conversation.id,
        role=RoleEnum.assistant,
        content=ai_response_text
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)

    return ChatResponse(
        message_id=ai_message.id,
        conversation_id=conversation.id,
        role=ai_message.role.value,
        content=ai_message.content,
        created_at=ai_message.created_at
    )
