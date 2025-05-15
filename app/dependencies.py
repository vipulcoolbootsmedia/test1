from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from auth import get_current_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_active_user(token: str = Depends(oauth2_scheme)):
    user = get_current_user(token)
    if not user.get('is_active', True):
        raise HTTPException(status_code=400, detail="Inactive user")
    return user