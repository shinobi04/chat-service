from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import Optional, List
import json

from app.database import get_db, AsyncSessionLocal
from app.models import Conversation, Message, RoleEnum
from app.core.security import verify_session_jwt
from app.core.config import settings
from app.services.ollama_service import generate_chat_response_stream, generate_chat_response
from app.services.cache_service import get_from_cache, add_to_cache, append_to_cache_message, get_conversation_lock
from app.services.file_processor import process_file, ProcessedFile
from app.core.rate_limit import limiter

router = APIRouter(prefix="/chat", tags=["chat"])

async def save_message_to_db(conversation_id: UUID, role: RoleEnum, content: str, image_path: Optional[str] = None):
    """Background task to save a message to the database."""
    async with AsyncSessionLocal() as db:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            image_path=image_path
        )
        db.add(message)
        await db.commit()
        print(f"✅ [Background Task] Successfully saved '{role.value}' message to NeonDB!")


async def _process_chat_request(
    content: str,
    file: Optional[UploadFile],
    conversation_id: Optional[UUID],
    db: AsyncSession,
    session_id: str,
    model_name: str,
    background_tasks: BackgroundTasks,
    system_prompt: Optional[str] = None,
    stream: bool = True
):
    # --- Process the uploaded file (if any) ---
    images_base64: List[str] = []
    file_label: Optional[str] = None

    if file:
        processed: ProcessedFile = await process_file(file)
        file_label = processed.original_filename

        if processed.images_base64:
            images_base64 = processed.images_base64

        if processed.extracted_text:
            # Prepend extracted text (audio transcript / markdown) to the user's message
            content = f"{processed.extracted_text}\n\n{content}"

    if conversation_id:
        # Validate conversation ownership
        result = await db.execute(select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.session_id == session_id
        ))
        conversation = result.scalars().first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create a new conversation
        title = content[:30] + "..." if len(content) > 30 else content
        conversation = Conversation(session_id=session_id, title=title)
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    # Acquire distributed lock so concurrent requests for the SAME conversation wait in line
    lock = get_conversation_lock(conversation.id)
    await lock.acquire()

    try:
        # 1. Fast Read: Check Redis Cache
        cached_messages = await get_from_cache(conversation.id)
        if cached_messages is not None:
            ollama_messages = cached_messages
        else:
            # Cache Miss: Load from DB once and store in cache
            result = await db.execute(select(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()))
            history = result.scalars().all()
            ollama_messages = [{"role": msg.role.value, "content": msg.content} for msg in history]
            await add_to_cache(conversation.id, ollama_messages)

        # 2. Instant Append User Message
        user_message = {"role": RoleEnum.user.value, "content": content}
        ollama_messages.append(user_message)
        await append_to_cache_message(conversation.id, user_message)

        # 3. Background DB Write (User)
        print("🚀 [API] Passing user message to BackgroundTasks to save later...", flush=True)
        background_tasks.add_task(save_message_to_db, conversation.id, RoleEnum.user, content, file_label)

        if stream:
            async def stream_generator():
                try:
                    # Instantly send the conversation_id back to the calling service
                    yield f"data: {json.dumps({'conversation_id': str(conversation.id), 'title': conversation.title})}\n\n"
                    
                    full_response = []
                    try:
                        # Sliding window: only send the last N messages to Ollama
                        # Full history stays in cache/DB for the conversations API
                        context_messages = ollama_messages[-settings.MAX_CONTEXT_MESSAGES:]

                        async for chunk in generate_chat_response_stream(
                            messages=context_messages, 
                            images_base64=images_base64 or None,
                            model_name=model_name,
                            system_prompt=system_prompt
                        ):
                            full_response.append(chunk)
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                        return

                    final_text = "".join(full_response)
                    
                    # 4. Instant Append AI Message to Cache
                    ai_message = {"role": RoleEnum.assistant.value, "content": final_text}
                    ollama_messages.append(ai_message)
                    await append_to_cache_message(conversation.id, ai_message)
                    
                    # 5. Background DB Write (AI)
                    print("🚀 [API] Sending AI response to BackgroundTasks to save to NeonDB...", flush=True)
                    background_tasks.add_task(save_message_to_db, conversation.id, RoleEnum.assistant, final_text)

                finally:
                    # 6. Release lock when the stream finishes or disconnects
                    if await lock.owned():
                        await lock.release()

            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        
        else:
            try:
                context_messages = ollama_messages[-settings.MAX_CONTEXT_MESSAGES:]
                final_text = await generate_chat_response(
                    messages=context_messages, 
                    images_base64=images_base64 or None,
                    model_name=model_name,
                    system_prompt=system_prompt
                )
                
                # 4. Instant Append AI Message to Cache
                ai_message = {"role": RoleEnum.assistant.value, "content": final_text}
                ollama_messages.append(ai_message)
                await append_to_cache_message(conversation.id, ai_message)
                
                # 5. Background DB Write (AI)
                print("🚀 [API] Sending AI response to BackgroundTasks to save to NeonDB...", flush=True)
                background_tasks.add_task(save_message_to_db, conversation.id, RoleEnum.assistant, final_text)
                
                return JSONResponse(content={
                    "conversation_id": str(conversation.id),
                    "title": conversation.title,
                    "content": final_text
                })
            finally:
                if await lock.owned():
                    await lock.release()

    except Exception as e:
        # If anything fails before we even return the stream, release the lock
        if await lock.owned():
            await lock.release()
        raise e


@router.post("")
@limiter.limit("20/minute")
async def handle_chat(
    request: Request,
    background_tasks: BackgroundTasks,
    content: str = Form(..., description="The text message for the AI"),
    system_prompt: Optional[str] = Form(None, description="System prompt to set the AI persona for this request"),
    stream: bool = Form(True, description="Whether to stream the response or return a single JSON object"),
    conversation_id: Optional[UUID] = Query(None, description="Provide this to continue an existing conversation"),
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """
    Standard endpoint for chat using the fast gemma3:1b model.
    """
    return await _process_chat_request(content, None, conversation_id, db, session_id, "gemma3:1b", background_tasks, system_prompt, stream)


@router.post("/gemma4")
@limiter.limit("5/minute")
async def handle_chat_gemma4(
    request: Request,
    background_tasks: BackgroundTasks,
    content: str = Form(..., description="The text message for the AI"),
    system_prompt: Optional[str] = Form(None, description="System prompt to set the AI persona for this request"),
    stream: bool = Form(True, description="Whether to stream the response or return a single JSON object"),
    file: Optional[UploadFile] = File(None, description="File to process: image, PDF, audio (mp3/wav/ogg), or text/markdown"),
    conversation_id: Optional[UUID] = Query(None, description="Provide this to continue an existing conversation"),
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(verify_session_jwt)
):
    """
    Dedicated endpoint for heavy processing using the gemma4:26b model.
    Supports images, multi-page PDFs, audio files, and markdown/text files.
    """
    return await _process_chat_request(content, file, conversation_id, db, session_id, "gemma4:26b", background_tasks, system_prompt, stream)

