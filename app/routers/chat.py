from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
import base64
import json

from app.database import get_db
from app.models import Conversation, Message, RoleEnum
from app.core.security import verify_session_jwt
from app.services.ollama_service import generate_chat_response_stream

router = APIRouter(prefix="/chat", tags=["chat"])

def _process_chat_request(
    content: str,
    image: Optional[UploadFile],
    conversation_id: Optional[UUID],
    db: Session,
    session_id: str,
    model_name: str
):
    if conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.session_id == session_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        title = content[:30] + "..." if len(content) > 30 else content
        conversation = Conversation(session_id=session_id, title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    image_base64 = None
    if image:
        image_bytes = image.file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    user_message = Message(
        conversation_id=conversation.id,
        role=RoleEnum.user,
        content=content,
        image_path=image.filename if image else None 
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    history = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()).all()
    ollama_messages = [{"role": msg.role.value, "content": msg.content} for msg in history]

    def stream_generator():
        full_response = []
        try:
            for chunk in generate_chat_response_stream(
                messages=ollama_messages, 
                image_base64=image_base64, 
                model_name=model_name
            ):
                full_response.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        final_text = "".join(full_response)
        ai_message = Message(
            conversation_id=conversation.id,
            role=RoleEnum.assistant,
            content=final_text
        )
        db.add(ai_message)
        db.commit()

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.post("")
def handle_chat(
    content: str = Form(..., description="The text message for the AI"),
    image: Optional[UploadFile] = File(None, description="Optional image file to upload"),
    conversation_id: Optional[UUID] = Query(None, description="Provide this to continue an existing conversation"),
    db: Session = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """
    Standard endpoint for chat using the fast gemma3:1b model.
    """
    return _process_chat_request(content, image, conversation_id, db, session_id, "gemma3:1b")


@router.post("/gemma4")
def handle_chat_gemma4(
    content: str = Form(..., description="The text message for the AI"),
    image: Optional[UploadFile] = File(None, description="Optional image file to upload"),
    conversation_id: Optional[UUID] = Query(None, description="Provide this to continue an existing conversation"),
    db: Session = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """
    Dedicated endpoint for heavy image-processing using the gemma4:26b model.
    """
    return _process_chat_request(content, image, conversation_id, db, session_id, "gemma4:26b")
