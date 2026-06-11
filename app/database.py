import re
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Safely replace postgresql:// with postgresql+asyncpg:// if needed
# NeonDB connection strings usually start with postgresql://
async_db_url = settings.DATABASE_URL
if async_db_url.startswith("postgresql://"):
    async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# asyncpg requires 'ssl=' instead of 'sslmode='
if "sslmode=" in async_db_url:
    async_db_url = async_db_url.replace("sslmode=", "ssl=")

# asyncpg does not accept 'channel_binding'
async_db_url = re.sub(r"&?channel_binding=[^&]*", "", async_db_url)
async_db_url = async_db_url.replace("?&", "?").rstrip("?").rstrip("&")

# Create the SQLAlchemy async engine
# pool_pre_ping=True helps handle disconnects gracefully
engine = create_async_engine(async_db_url, pool_pre_ping=True)

# Create a configured "AsyncSession" class
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for declarative models
Base = declarative_base()

# Dependency for FastAPI to get DB async sessions
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db
