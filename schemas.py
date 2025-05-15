from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List, Literal
from datetime import datetime

# User Schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    hashpassword: str
    trait_profile: Optional[Dict[str, int]] = {
        "focus": 50,
        "bravery": 50,
        "empathy": 50,
        "honesty": 50,
        "patience": 50,
        "curiosity": 50,
        "truthfulness": 50
    }
    game_played: Optional[int] = 0
    game_history: Optional[dict] = {}

class UserResponse(BaseModel):
    userid: int
    username: str
    email: str
    trait_profile: dict
    game_played: int
    game_history: dict
    created_at: str

# Session Schemas
class SessionStart(BaseModel):
    user_id: int
    mode: Literal["learn", "grow"]
    scenario_id: Optional[int] = None  # Required for learn, optional for grow

class SessionResponse(BaseModel):
    session_id: int
    user_id: int
    mode: str
    scenario_id: Optional[int]
    message: str

# Learn Module Schemas
class PathRequest(BaseModel):
    path: str = ""

class LearnChoice(BaseModel):
    session_id: int
    depth: int
    choice_id: Literal["A", "B", "C"]
    trait_impact: Literal["high", "moderate", "low"]

# Grow Module Schemas
class GenerateScenarioInput(BaseModel):
    session_id: int
    depth: int
    scenario_json: dict

class GrowChoice(BaseModel):
    session_id: int
    depth: int
    choice_id: Literal["A", "B", "C"]
    trait_impact: Literal["high", "moderate", "low"]

# Update Schemas
class UpdateTraitProfile(BaseModel):
    trait_profile: Dict[str, int]

class AddGameData(BaseModel):
    game_id: str
    game_data: Dict[str, str]