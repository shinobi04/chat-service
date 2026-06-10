from cachetools import LRUCache

# Global LRU Cache mapping conversation_id (UUID) -> List[Dict[str, str]] (Ollama messages format)
# Max size 1000 ensures memory safety for active conversations
conversation_cache = LRUCache(maxsize=1000)
