from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from schemas import GameStats, LeaderboardEntry
from dependencies import get_current_active_user
from crud import AnalyticsCRUD, ChoiceCRUD
from typing import List

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/user/{user_id}/stats", response_model=dict)
async def get_user_stats(
    user_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed statistics for a user"""
    return AnalyticsCRUD.get_user_stats(user_id)

@router.get("/leaderboard", response_model=list)
async def get_leaderboard(limit: int = 10):
    """Get top players leaderboard"""
    return AnalyticsCRUD.get_leaderboard(limit)

@router.get("/choices/distribution", response_model=list)
async def get_choice_distribution(scenario_id: Optional[int] = None):
    """Get distribution of choices made by all users"""
    return AnalyticsCRUD.get_choice_analytics(scenario_id)

@router.get("/session/{session_id}/summary", response_model=dict)
async def get_session_summary(
    session_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get summary of a specific session"""
    choices = ChoiceCRUD.get_session_choices(session_id)
    
    # Calculate summary statistics
    trait_impacts = {"high": 0, "moderate": 0, "low": 0}
    choice_distribution = {"A": 0, "B": 0, "C": 0}
    
    for choice in choices:
        trait_impacts[choice["trait_impact"]] += 1
        choice_distribution[choice["choice_id"]] += 1
    
    return {
        "session_id": session_id,
        "total_choices": len(choices),
        "trait_impacts": trait_impacts,
        "choice_distribution": choice_distribution,
        "choices": choices
    }

@router.get("/traits/progression", response_model=dict)
async def get_trait_progression(
    user_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get trait progression over time for a user"""
    if current_user["userid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get all sessions for user
    sessions = SessionCRUD.get_user_sessions(user_id)
    
    progression = []
    for session in sessions:
        choices = ChoiceCRUD.get_session_choices(session["session_id"])
        
        # Calculate trait changes for this session
        trait_changes = {}
        for choice in choices:
            # This is simplified - in reality, you'd track specific traits
            impact_value = {"high": 3, "moderate": 2, "low": 1}.get(choice["trait_impact"], 0)
            trait_changes[choice["depth"]] = impact_value
        
        progression.append({
            "session_id": session["session_id"],
            "started_at": session["started_at"],
            "mode": session["mode"],
            "trait_changes": trait_changes
        })
    
    return {
        "user_id": user_id,
        "progression": progression
    }