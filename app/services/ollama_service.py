import ollama
from typing import List, Dict, Optional
from app.core.config import settings

# Initialize ollama client pointing to the OLLAMA_BASE_URL
client = ollama.Client(host=settings.OLLAMA_BASE_URL)

MODEL_NAME = "gemma3:1b"

def generate_chat_response(messages: List[Dict[str, str]], image_base64: Optional[str] = None) -> str:
    """
    Sends the conversation history to Ollama and returns the generated text.
    messages format: [{"role": "user", "content": "hello"}]
    """
    # If there's an image, attach it to the latest user message
    if image_base64 and len(messages) > 0:
        last_msg = messages[-1]
        if last_msg["role"] == "user":
            last_msg["images"] = [image_base64]

    # We add strict options to prevent the model from "blurting" or hallucinating.
    # Lower temperature = more focused and deterministic responses.
    response = client.chat(
        model=MODEL_NAME, 
        messages=messages,
        options={
            "temperature": 0.2,
            "top_p": 0.9
        }
    )
    return response['message']['content']
