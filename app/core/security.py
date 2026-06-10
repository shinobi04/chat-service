import jwt
from datetime import datetime, timezone
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer()

def create_session_jwt(session_id: str) -> str:
    """Creates a signed JWT containing the session UUID."""
    payload = {
        "session_id": session_id,
        "iat": datetime.now(timezone.utc)
    }
    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_session_jwt(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verifies the JWT and returns the session_id."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        session_id: str = payload.get("session_id")
        if session_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return session_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
