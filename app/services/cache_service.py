import json
import redis
from app.core.config import settings

# Initialize Redis connection pool
# decode_responses=True automatically decodes bytes to strings
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

# 1 Hour TTL for inactive conversations to free up memory
CACHE_TTL = 3600 

def get_from_cache(conversation_id):
    """Fetch conversation history from Redis."""
    data = redis_client.get(str(conversation_id))
    if data:
        return json.loads(data)
    return None

def add_to_cache(conversation_id, messages):
    """Store conversation history in Redis with a TTL."""
    redis_client.setex(
        str(conversation_id),
        CACHE_TTL,
        json.dumps(messages)
    )

def append_to_cache_message(conversation_id, message_dict):
    """Append a single message to an existing conversation in Redis."""
    data = redis_client.get(str(conversation_id))
    if data:
        messages = json.loads(data)
        messages.append(message_dict)
        redis_client.setex(
            str(conversation_id),
            CACHE_TTL,
            json.dumps(messages)
        )
