import asyncio
import ollama
from typing import List, Dict, Optional, AsyncIterator
from app.core.config import settings

# Initialize ollama AsyncClient pointing to the OLLAMA_BASE_URL
client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)

MODEL_NAME = "gemma3:1b"

# Max 2 concurrent inferences per worker. With 8 workers, this allows 16 concurrent
# calls to Ollama. The rest wait safely in line without crashing the API or Ollama.
inference_semaphore = asyncio.Semaphore(2)

async def generate_chat_response_stream(
    messages: List[Dict[str, str]], 
    images_base64: Optional[List[str]] = None,
    model_name: str = MODEL_NAME,
    system_prompt: Optional[str] = None
) -> AsyncIterator[str]:
    """
    Sends the conversation history to Ollama and yields the generated text chunks asynchronously.
    messages format: [{"role": "user", "content": "hello"}]
    """
    # If there are images (single image or multi-page PDF), attach to the latest user message
    if images_base64 and len(messages) > 0:
        last_msg = messages[-1]
        if last_msg["role"] == "user":
            last_msg["images"] = images_base64

    # Prepend system prompt if provided by the calling backend
    full_messages = messages
    if system_prompt:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
    async with inference_semaphore:
        response_stream = await client.chat(
            model=model_name, 
            messages=full_messages,
            stream=True,
            options={
                "temperature": 0.2,
                "top_p": 0.9
            }
        )
        
        async for chunk in response_stream:
            yield chunk['message']['content']

async def generate_chat_response(
    messages: List[Dict[str, str]], 
    images_base64: Optional[List[str]] = None,
    model_name: str = MODEL_NAME,
    system_prompt: Optional[str] = None
) -> str:
    """
    Sends the conversation history to Ollama and returns the complete generated text asynchronously.
    """
    if images_base64 and len(messages) > 0:
        last_msg = messages[-1]
        if last_msg["role"] == "user":
            last_msg["images"] = images_base64

    full_messages = messages
    if system_prompt:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
    async with inference_semaphore:
        response = await client.chat(
            model=model_name, 
            messages=full_messages,
            stream=False,
            options={
                "temperature": 0.2,
                "top_p": 0.9
            }
        )
        
        return response['message']['content']
