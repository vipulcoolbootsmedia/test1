from fastapi import APIRouter, Depends, HTTPException
from schemas import PathRequest, ChoiceInput, ScenarioResponse
from dependencies import get_current_active_user
from crud import ScenarioCRUD, SessionCRUD, ChoiceCRUD
import json
from typing import List
from database import db
router = APIRouter(prefix="/learn", tags=["learn"])

def traverse_scenario_tree(scenario_info: dict, path: str):
    """Navigate through nested scenario tree based on path"""
    current = scenario_info
    
    for choice in path:
        found = False
        for c in current.get('choices', []):
            if c['choice_id'] == choice:
                if 'next_scenario' in c:
                    current = c['next_scenario']
                    found = True
                    break
        if not found:
            raise HTTPException(status_code=400, detail=f"Invalid path: {path}")
    
    return current

@router.get("/scenarios", response_model=List[dict])
async def list_scenarios():
    """List all available learn scenarios"""
    return ScenarioCRUD.list_scenarios()

@router.get("/scenario/{session_id}/start", response_model=dict)
async def get_start_scenario(
    session_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get starting scenario for a session"""
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if session["mode"] != "learn":
        raise HTTPException(status_code=400, detail="Not a learn session")
    
    scenario = ScenarioCRUD.get_scenario(session["scenario_id"])
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return {
        "session_id": session_id,
        "current_path": "",
        **scenario["info"]
    }

@router.post("/scenario/{session_id}/by-path", response_model=dict)
async def get_scenario_by_path(
    session_id: int,
    path_req: PathRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Get scenario at specific path"""
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    scenario = ScenarioCRUD.get_scenario(session["scenario_id"])
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    current_scenario = traverse_scenario_tree(scenario["info"], path_req.path)
    
    return {
        "session_id": session_id,
        "current_path": path_req.path,
        **current_scenario
   }

@router.post("/choice/{session_id}", response_model=dict)
async def record_choice(
   session_id: int,
   choice: ChoiceInput,
   current_user: dict = Depends(get_current_active_user)
):
   """Record a user's choice"""
   session = SessionCRUD.get_session(session_id)
   if not session:
       raise HTTPException(status_code=404, detail="Session not found")
   
   if session["user_id"] != current_user["userid"]:
       raise HTTPException(status_code=403, detail="Not authorized")
   
   result = ChoiceCRUD.record_choice(
       session_id,
       choice.depth,
       choice.choice_id,
       choice.trait_impact
   )
   
   # Update user traits based on choice
   _update_user_traits(current_user["userid"], choice.trait_impact)
   
   return result

def _update_user_traits(user_id: int, trait_impact: str):
    """Update user traits based on choice impact"""
    from database import db
    import json
    
    impact_values = {
        "high": 10,
        "moderate": 5,
        "low": 2
    }
    
    with db.get_cursor() as (cursor, connection):
        # Get current trait profile
        cursor.execute("SELECT trait_profile FROM user_info WHERE userid = %s", (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            trait_profile = json.loads(result[0])
            
            # Update all traits by the impact value (simplified)
            # In real implementation, you'd update specific traits based on the scenario
            for trait in trait_profile:
                trait_profile[trait] = min(100, trait_profile[trait] + impact_values.get(trait_impact, 0))
            
            # Update the trait profile
            cursor.execute("""
                UPDATE user_info 
                SET trait_profile = %s 
                WHERE userid = %s
            """, (json.dumps(trait_profile), user_id))
            connection.commit()