from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form, BackgroundTasks
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
from app.services.cache_service import conversation_cache

router = APIRouter(prefix="/chat", tags=["chat"])

def save_message_to_db(db: Session, conversation_id: UUID, role: RoleEnum, content: str, image_path: Optional[str] = None):
    """Background task to save a message to the database."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        image_path=image_path
    )
    db.add(message)
    db.commit()


def _process_chat_request(
    content: str,
    image: Optional[UploadFile],
    conversation_id: Optional[UUID],
    db: Session,
    session_id: str,
    model_name: str,
    background_tasks: BackgroundTasks
):
    if conversation_id:
        # Validate conversation ownership
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.session_id == session_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create a new conversation
        title = content[:30] + "..." if len(content) > 30 else content
        conversation = Conversation(session_id=session_id, title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 1. Fast Read: Check LRU Cache
    if conversation.id in conversation_cache:
        ollama_messages = conversation_cache[conversation.id]
    else:
        # Cache Miss: Load from DB once and store in cache
        history = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()).all()
        ollama_messages = [{"role": msg.role.value, "content": msg.content} for msg in history]
        conversation_cache[conversation.id] = ollama_messages

    # 2. Instant Append User Message
    ollama_messages.append({"role": RoleEnum.user.value, "content": content})
    
    # Process image temporarily for this request only (not saved in LRUCache)
    image_base64 = None
    image_filename = None
    if image:
        image_bytes = image.file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        image_filename = image.filename

    # 3. Background DB Write (User)
    background_tasks.add_task(save_message_to_db, db, conversation.id, RoleEnum.user, content, image_filename)

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
        
        # 4. Instant Append AI Message to Cache
        ollama_messages.append({"role": RoleEnum.assistant.value, "content": final_text})
        
        # 5. Background DB Write (AI)
        # Note: StreamingResponse consumes the generator after the main thread returns, 
        # so we can't use the standard background_tasks.add_task here easily.
        # But wait, FastAPI BackgroundTasks run AFTER the response completes. 
        # Inside a StreamingResponse generator, we can just execute the DB call directly 
        # at the end of the generator without blocking the user!
        # Because the stream is already finished yielding chunks.
        save_message_to_db(db, conversation.id, RoleEnum.assistant, final_text)

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.post("")
def handle_chat(
    background_tasks: BackgroundTasks,
    content: str = Form(..., description="The text message for the AI"),
    image: Optional[UploadFile] = File(None, description="Optional image file to upload"),
    conversation_id: Optional[UUID] = Query(None, description="Provide this to continue an existing conversation"),
    db: Session = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """
    Standard endpoint for chat using the fast gemma3:1b model.
    """
    return _process_chat_request(content, image, conversation_id, db, session_id, "gemma3:1b", background_tasks)


@router.post("/gemma4")
def handle_chat_gemma4(
    background_tasks: BackgroundTasks,
    content: str = Form(..., description="The text message for the AI"),
    image: Optional[UploadFile] = File(None, description="Optional image file to upload"),
    conversation_id: Optional[UUID] = Query(None, description="Provide this to continue an existing conversation"),
    db: Session = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """
    Dedicated endpoint for heavy image-processing using the gemma4:26b model.
    """
    return _process_chat_request(content, image, conversation_id, db, session_id, "gemma4:26b", background_tasks)
