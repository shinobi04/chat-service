import uuid
from fastapi import APIRouter, Request
from app.schemas import SessionResponse
from app.core.security import create_session_jwt
from app.core.rate_limit import limiter

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionResponse)
@limiter.limit("10/minute")
def create_session(request: Request):
    """Generates a new stateless session UUID and returns a signed JWT."""
    session_id = str(uuid.uuid4())
    token = create_session_jwt(session_id)
    return SessionResponse(session_id=session_id, access_token=token)

