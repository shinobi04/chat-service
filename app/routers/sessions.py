import uuid
from fastapi import APIRouter
from app.schemas import SessionResponse
from app.core.security import create_session_jwt

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionResponse)
def create_session():
    """Generates a new stateless session UUID and returns a signed JWT."""
    session_id = str(uuid.uuid4())
    token = create_session_jwt(session_id)
    return SessionResponse(session_id=session_id, access_token=token)
