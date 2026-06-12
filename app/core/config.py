from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: str = ""
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # Comma-separated list of IPs allowed to access the API.
    # Empty string = allow all (development mode).
    # Example: "203.0.113.10,198.51.100.5,172.18.0.4"
    ALLOWED_IPS: str = ""

    # Database connection pool tuning
    DB_POOL_SIZE: int = 3
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # File processing limits
    MAX_FILE_SIZE_MB: int = 50              # Max upload size in MB
    MAX_PDF_PAGES: int = 20                 # Max pages to render from a PDF
    WHISPER_MODEL_SIZE: str = "base"        # faster-whisper model: tiny, base, small, medium, large

    # Maximum messages sent to Ollama for context (sliding window)
    MAX_CONTEXT_MESSAGES: int = 20

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

