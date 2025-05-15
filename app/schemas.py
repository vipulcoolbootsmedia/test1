from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List, Literal
from datetime import datetime

# Auth Schemas

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    trait_profile: Optional[Dict[str, int]] = {
        "focus": 50,
        "bravery": 50,
        "empathy": 50,
        "honesty": 50,
        "patience": 50,
        "curiosity": 50,
        "truthfulness": 50
    }

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserRegister):
    trait_profile: Optional[Dict[str, int]] = {
        "focus": 50,
        "bravery": 50,
        "empathy": 50,
        "honesty": 50,
        "patience": 50,
        "curiosity": 50,
        "truthfulness": 50
    }

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    trait_profile: Optional[Dict[str, int]] = None

class UserResponse(UserBase):
    userid: int
    trait_profile: Dict[str, int]
    game_played: int
    game_history: Dict
    created_at: datetime
    is_active: bool

# Session Schemas
class SessionCreate(BaseModel):
    mode: Literal["learn", "grow"]
    scenario_id: Optional[int] = None

class SessionResponse(BaseModel):
    session_id: int
    user_id: int
    mode: str
    scenario_id: Optional[int]
    started_at: datetime
    ended_at: Optional[datetime]
    is_completed: bool

# Learn Module Schemas
class PathRequest(BaseModel):
    path: str = ""

class ChoiceInput(BaseModel):
    depth: int
    choice_id: Literal["A", "B", "C"]
    trait_impact: Literal["high", "moderate", "low"]

# Grow Module Schemas
class GenerateScenarioRequest(BaseModel):
    depth: int
    previous_choices: Optional[List[str]] = []
    trait_focus: Optional[str] = "bravery"

class ScenarioResponse(BaseModel):
    depth: int
    scene_narrative: List[Dict]
    choices: List[Dict]
    is_end: bool

# Analytics Schemas
class GameStats(BaseModel):
    total_games: int
    completed_games: int
    mode_distribution: Dict[str, int]
    average_completion_time: Optional[float]
    trait_progression: Dict[str, float]

class LeaderboardEntry(BaseModel):
    userid: int
    username: str
    games_played: int
    total_score: float
    dominant_trait: str