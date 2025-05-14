from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

class UserCreate(BaseModel):
    username: str

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
