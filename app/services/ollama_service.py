import ollama
from typing import List, Dict, Optional, AsyncIterator
from app.core.config import settings

# Initialize ollama AsyncClient pointing to the OLLAMA_BASE_URL
client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)

MODEL_NAME = "gemma3:1b"

async def generate_chat_response_stream(
    messages: List[Dict[str, str]], 
    image_base64: Optional[str] = None,
    model_name: str = MODEL_NAME
) -> AsyncIterator[str]:
    """
    Sends the conversation history to Ollama and yields the generated text chunks asynchronously.
    messages format: [{"role": "user", "content": "hello"}]
    """
    # If there's an image, attach it to the latest user message
    if image_base64 and len(messages) > 0:
        last_msg = messages[-1]
        if last_msg["role"] == "user":
            last_msg["images"] = [image_base64]

    # We add strict options to prevent the model from "blurting" or hallucinating.
    # Lower temperature = more focused and deterministic responses.
    response_stream = await client.chat(
        model=model_name, 
        messages=messages,
        stream=True,
        options={
            "temperature": 0.2,
            "top_p": 0.9
        }
    )
    
    async for chunk in response_stream:
        yield chunk['message']['content']
