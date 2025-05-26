from fastapi import APIRouter, Depends, HTTPException
from schemas import GenerateScenarioRequest, ScenarioResponse, ChoiceInput
from dependencies import get_current_active_user
from crud import SessionCRUD, GeneratedScenarioCRUD, ChoiceCRUD
from openai import OpenAI
import os
import json
from typing import List
from dotenv import load_dotenv

import agenta as ag
from agenta.sdk.types import PromptTemplate

# Load environment variables
load_dotenv()

# Set environment variables for Agenta and OpenAI
os.environ["AGENTA_API_KEY"] = os.getenv("AGENTA_API_KEY")
os.environ["AGENTA_HOST"] = os.getenv("AGENTA_HOST", "https://cloud.agenta.ai:443")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Get Agenta configuration from environment
AGENTA_APP_SLUG = os.getenv("AGENTA_APP_SLUG", "test1")
AGENTA_ENVIRONMENT_SLUG = os.getenv("AGENTA_ENVIRONMENT_SLUG", "development")

# Initialize Agenta SDK
ag.init()

# Fetch prompt config from the registry for your app and variant
config_dict = ag.ConfigManager.get_from_registry(
    app_slug=AGENTA_APP_SLUG,
    environment_slug=AGENTA_ENVIRONMENT_SLUG
)

# Build PromptTemplate object
prompt_template = PromptTemplate(**config_dict['prompt'])

router = APIRouter(prefix="/grow", tags=["grow"])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Constants
MAX_DEPTH = 5

def generate_scenario_with_ai(depth: int, trait_focus: str, previous_choices: list, user_data: dict):
    trait_profile = user_data.get("trait_profile", {})
    game_history = user_data.get("game_history", {})
    game_played = user_data.get("game_played", 0)

    # Trait analysis
    trait_analysis = ""
    if trait_profile:
        strongest_trait = max(trait_profile.items(), key=lambda x: x[1])
        weakest_trait = min(trait_profile.items(), key=lambda x: x[1])
        trait_analysis = f"""
        Strongest: {strongest_trait[0]} ({strongest_trait[1]})
        Weakest: {weakest_trait[0]} ({weakest_trait[1]})
        Focus Level: {trait_profile.get(trait_focus, 50)}
        All Traits: {trait_profile}
        """

    # Get prompt template from Agenta
    config_dict = ag.ConfigManager.get_from_registry(
        app_slug=AGENTA_APP_SLUG,
        environment_slug=AGENTA_ENVIRONMENT_SLUG
    )
    prompt_template = PromptTemplate(**config_dict['prompt'])

    # Format Agenta prompt with your dynamic context
    formatted_prompt = prompt_template.format(
        depth=depth,
        trait_focus=trait_focus,
        previous_choices=previous_choices,
        game_played=game_played,
        trait_analysis=trait_analysis,
    )

    # Call OpenAI with the structured prompt
    client = OpenAI()
    kwargs = formatted_prompt.to_openai_kwargs()
    kwargs.pop("response_format", None)

    try:
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        scenario_json = json.loads(content)

        # Force is_end to True if we're at max depth
        if depth >= MAX_DEPTH:
            scenario_json["is_end"] = True

        # Basic structure check
        required_keys = ["depth", "scene_narrative", "choices", "is_end"]
        if all(key in scenario_json for key in required_keys):
            print(f"Generated scenario (depth {depth}, trait {trait_focus})")
            return scenario_json
        else:
            raise ValueError("Missing required keys in AI response")

    except Exception as e:
        print(f"Fallback due to error: {e}")
        return {
            "depth": depth,
            "scene_narrative": [
                {"text": f"You face a challenge that tests your {trait_focus}.", "sfx": "tension"},
                {"text": "Your next move will shape your fate.", "sfx": "heartbeat"}
            ],
            "narrative_purpose": "Test fallback due to AI error",
            "personalization_notes": "Fallback generation due to error",
            "choices": [
                {"choice_id": "A", "choice_text": "Act boldly", "maps_to_trait_details": {"trait": trait_focus, "degree": "high"}, "short_hidden_message": "Bold move"},
                {"choice_id": "B", "choice_text": "Choose balance", "maps_to_trait_details": {"trait": trait_focus, "degree": "moderate"}, "short_hidden_message": "Balanced move"},
                {"choice_id": "C", "choice_text": "Play safe", "maps_to_trait_details": {"trait": trait_focus, "degree": "low"}, "short_hidden_message": "Safe move"}
            ],
            "is_end": depth >= MAX_DEPTH
        }

@router.post("/scenario/{session_id}/generate", response_model=dict)
async def generate_scenario(
    session_id: int,
    request: GenerateScenarioRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Generate a personalized scenario for grow mode"""
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if session["mode"] != "grow":
        raise HTTPException(status_code=400, detail="Not a grow session")
    
    # Validate depth - prevent going beyond max depth
    if request.depth > MAX_DEPTH:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum depth exceeded. Game ends at depth {MAX_DEPTH}"
        )
    
    # Check if session is already completed
    if session.get("is_completed"):
        raise HTTPException(
            status_code=400,
            detail="Session is already completed"
        )
    
    # Check if previous depth scenarios exist and if depth 5 was already reached
    existing_scenarios = GeneratedScenarioCRUD.get_all_generated_scenarios(session_id)
    if existing_scenarios:
        max_existing_depth = max(s["depth"] for s in existing_scenarios)
        if max_existing_depth >= MAX_DEPTH:
            # Check if the max depth scenario has is_end = True
            final_scenario = next((s for s in existing_scenarios if s["depth"] == MAX_DEPTH), None)
            if final_scenario and final_scenario.get("scenario_json", {}).get("is_end"):
                raise HTTPException(
                    status_code=400,
                    detail="Game has already ended. Cannot generate more scenarios."
                )
    
    # Prepare user data for personalization
    user_data = {
        "trait_profile": current_user.get("trait_profile", {}),
        "game_history": current_user.get("game_history", {}),
        "game_played": current_user.get("game_played", 0),
        "username": current_user.get("username", "Player")
    }
    
    print(f"Generating personalized scenario for {user_data['username']} - Game #{user_data['game_played'] + 1}")
    
    # Generate personalized scenario using AI
    scenario = generate_scenario_with_ai(
        request.depth,
        request.trait_focus,
        request.previous_choices,
        user_data
    )
    
    # Save to database
    result = GeneratedScenarioCRUD.save_generated_scenario(
        session_id,
        request.depth,
        scenario
    )
    
    # If this is the final scenario, mark the session as completed
    if scenario.get("is_end") or request.depth >= MAX_DEPTH:
        from datetime import datetime
        SessionCRUD.update_session(session_id, datetime.utcnow(), True)
        print(f"Session {session_id} marked as completed at depth {request.depth}")
    
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
    
    # Validate depth
    if depth > MAX_DEPTH:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid depth. Maximum depth is {MAX_DEPTH}"
        )
    
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
    
    # Check if session is completed
    if session.get("is_completed"):
        raise HTTPException(
            status_code=400,
            detail="Cannot record choice for completed session"
        )
    
    # Validate depth
    if choice.depth > MAX_DEPTH:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid depth. Maximum depth is {MAX_DEPTH}"
        )
    
    result = ChoiceCRUD.record_choice(
        session_id,
        choice.depth,
        choice.choice_id,
        choice.trait_impact
    )
    
    print(f"Recorded choice {choice.choice_id} for user {current_user['username']} at depth {choice.depth}")
    
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

@router.get("/session/{session_id}/status", response_model=dict)
async def get_session_status(
    session_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get session status including completion state"""
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    scenarios = GeneratedScenarioCRUD.get_all_generated_scenarios(session_id)
    current_depth = len(scenarios)
    max_depth_reached = max([s["depth"] for s in scenarios]) if scenarios else 0
    
    is_game_ended = False
    if scenarios:
        final_scenario = next((s for s in scenarios if s["depth"] == max_depth_reached), None)
        if final_scenario:
            is_game_ended = final_scenario.get("scenario_json", {}).get("is_end", False)
    
    return {
        "session_id": session_id,
        "is_completed": session.get("is_completed", False),
        "current_depth": current_depth,
        "max_depth_reached": max_depth_reached,
        "max_possible_depth": MAX_DEPTH,
        "is_game_ended": is_game_ended,
        "can_continue": not is_game_ended and max_depth_reached < MAX_DEPTH
    }