from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from schemas import SessionCreate, SessionResponse
from dependencies import get_current_active_user
from crud import SessionCRUD
from datetime import datetime

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/", response_model=dict)
async def create_session(
    session: SessionCreate,
    current_user: dict = Depends(get_current_active_user)
):
    result = SessionCRUD.create_session(
        current_user["userid"], 
        session.mode, 
        session.scenario_id
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: int):
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.patch("/{session_id}/end", response_model=dict)
async def end_session(
    session_id: int,
    is_completed: bool = True,
    current_user: dict = Depends(get_current_active_user)
):
    # Verify session belongs to user
    session = SessionCRUD.get_session(session_id)
    if not session or session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = SessionCRUD.update_session(
        session_id, 
        datetime.utcnow(), 
        is_completed
    )
    return result

@router.get("/user/{user_id}", response_model=List[SessionResponse])
async def get_user_sessions(
    user_id: int,
    mode: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    if current_user["userid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return SessionCRUD.get_user_sessions(user_id, mode)