from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from schemas import UserResponse, UserUpdate
from dependencies import get_current_active_user
from crud import UserCRUD

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    return current_user

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(user_id: int):
    user = UserCRUD.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=dict)
async def update_user(
    user_id: int, 
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    if current_user["userid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")
    result = UserCRUD.update_user(user_id, user_update)
    return result

@router.delete("/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    if current_user["userid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")
    result = UserCRUD.delete_user(user_id)
    return result

@router.get("/", response_model=List[dict])
async def list_users(skip: int = 0, limit: int = 100):
    return UserCRUD.get_all_users(skip, limit)