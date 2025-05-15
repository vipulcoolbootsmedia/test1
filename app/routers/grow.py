from fastapi import APIRouter, Depends, HTTPException
from schemas import GenerateScenarioRequest, ScenarioResponse, ChoiceInput
from dependencies import get_current_active_user
from crud import SessionCRUD, GeneratedScenarioCRUD, ChoiceCRUD
import openai
import os
import json
from typing import List

router = APIRouter(prefix="/grow", tags=["grow"])

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_scenario_with_ai(depth: int, trait_focus: str, previous_choices: list):
    """Generate scenario using OpenAI"""
    prompt = f"""
    You are creating a psychological thriller scenario.
    Depth: {depth}/5
    Trait Focus: {trait_focus}
    Previous Choices: {previous_choices}
    
    Generate a scenario with:
    1. A dark, psychological narrative (2-3 sentences)
    2. Three choices (A, B, C) that test {trait_focus}
    3. Each choice should have different trait impact (high, moderate, low)
    
    Return as JSON in this format:
    {{
        "depth": {depth},
        "scene_narrative": [
            {{"text": "First sentence", "sfx": "sound_effect"}},
            {{"text": "Second sentence", "sfx": "sound_effect"}}
        ],
        "narrative_purpose": "Brief purpose",
        "choices": [
            {{
                "choice_id": "A",
                "choice_text": "Choice description",
                "maps_to_trait_details": {{
                    "trait": "{trait_focus}",
                    "degree": "high"
                }},
                "short_hidden_message": "Hidden psychological insight"
            }},
            // ... B and C choices
        ],
        "is_end": {str(depth == 5).lower()}
    }}
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a psychological thriller game writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1000
        )
        
        scenario_json = json.loads(response.choices[0].message.content)
        return scenario_json
    except Exception as e:
        # Fallback scenario if AI fails
        return {
            "depth": depth,
            "scene_narrative": [
                {"text": f"You find yourself at a crossroads. (Depth {depth})", "sfx": "ambient"},
                {"text": "Three paths lie before you.", "sfx": "wind"}
            ],
            "narrative_purpose": f"Test {trait_focus} at depth {depth}",
            "choices": [
                {
                    "choice_id": "A",
                    "choice_text": "Take the dangerous path",
                    "maps_to_trait_details": {"trait": trait_focus, "degree": "high"},
                    "short_hidden_message": "You embrace risk."
                },
                {
                    "choice_id": "B",
                    "choice_text": "Take the safe path",
                    "maps_to_trait_details": {"trait": trait_focus, "degree": "moderate"},
                    "short_hidden_message": "You prefer caution."
                },
                {
                    "choice_id": "C",
                    "choice_text": "Turn back",
                    "maps_to_trait_details": {"trait": trait_focus, "degree": "low"},
                    "short_hidden_message": "You avoid challenges."
                }
            ],
            "is_end": depth == 5
        }

@router.post("/scenario/{session_id}/generate", response_model=dict)
async def generate_scenario(
    session_id: int,
    request: GenerateScenarioRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Generate a new scenario for grow mode"""
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if session["mode"] != "grow":
        raise HTTPException(status_code=400, detail="Not a grow session")
    
    # Generate scenario using AI
    scenario = generate_scenario_with_ai(
        request.depth,
        request.trait_focus,
        request.previous_choices
    )
    
    # Save to database
    result = GeneratedScenarioCRUD.save_generated_scenario(
        session_id,
        request.depth,
        scenario
    )
    
    return {
        "id": result["id"],
        "scenario": scenario
    }

@router.get("/scenario/{session_id}/{depth}", response_model=dict)
async def get_scenario(
    session_id: int,
    depth: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get generated scenario by depth"""
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    scenario = GeneratedScenarioCRUD.get_generated_scenario(session_id, depth)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return scenario

@router.post("/choice/{session_id}", response_model=dict)
async def record_choice(
    session_id: int,
    choice: ChoiceInput,
    current_user: dict = Depends(get_current_active_user)
):
    """Record a user's choice in grow mode"""
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
    
    return result

@router.get("/scenarios/{session_id}", response_model=list)
async def get_all_scenarios(
    session_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all generated scenarios for a session"""
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return GeneratedScenarioCRUD.get_all_generated_scenarios(session_id)