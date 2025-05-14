from pydantic import BaseModel, EmailStr
from typing import Optional, Dict,List, Literal
from datetime import datetime

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


class ScenarioResponse(BaseModel):
    depth: int
    narrative: str
    choices: List[str]

class ChoiceInput(BaseModel):
    session_id: int
    depth: int
    choice_id: Literal["A", "B", "C"]
    trait_impact: Literal["high", "moderate", "low"]

class StartSession(BaseModel):
    user_id: int
    mode: Literal["learn", "grow"]

class UpdateTraits(BaseModel):
    user_id: int
    trait_profile: dict

class GenerateScenarioInput(BaseModel):
    session_id: int
    depth: int
    narrative: str
    choices: List[str]
