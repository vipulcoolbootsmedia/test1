from fastapi import APIRouter, Depends, HTTPException
from schemas import GenerateScenarioRequest, ScenarioResponse, ChoiceInput
from dependencies import get_current_active_user
from crud import SessionCRUD, GeneratedScenarioCRUD, ChoiceCRUD
from openai import OpenAI
import os
import json
from typing import List

router = APIRouter(prefix="/grow", tags=["grow"])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_scenario_with_ai(depth: int, trait_focus: str, previous_choices: list, user_data: dict):
    """Generate scenario using OpenAI with enhanced user context"""
    
    # Extract user information
    trait_profile = user_data.get("trait_profile", {})
    game_history = user_data.get("game_history", {})
    game_played = user_data.get("game_played", 0)
    
    # Create trait analysis for the prompt
    trait_analysis = ""
    if trait_profile:
        strongest_trait = max(trait_profile.items(), key=lambda x: x[1])
        weakest_trait = min(trait_profile.items(), key=lambda x: x[1])
        
        trait_analysis = f"""
        Player's Trait Profile:
        - Strongest trait: {strongest_trait[0]} ({strongest_trait[1]}/100)
        - Weakest trait: {weakest_trait[0]} ({weakest_trait[1]}/100)
        - Current {trait_focus}: {trait_profile.get(trait_focus, 50)}/100
        - Overall traits: {dict(sorted(trait_profile.items(), key=lambda x: x[1], reverse=True))}
        """
    
    # Analyze game history patterns
    history_analysis = ""
    # if game_history:
    #     choice_patterns = {"A": 0, "B": 0, "C": 0}
    #     common_endings = []
        
    #     for session_key, session_data in game_history.items():
    #         if isinstance(session_data, dict):
    #             for depth_key, depth_data in session_data.items():
    #                 if depth_key.startswith("depth") and isinstance(depth_data, dict):
    #                     choice = depth_data.get("choice_taken", "")
    #                     if choice in choice_patterns:
    #                         choice_patterns[choice] += 1
                
    #             if "results" in session_data:
    #                 ending = session_data["results"].get("ending_achieved", "")
    #                 if ending:
    #                     common_endings.append(ending)
        
    #     most_common_choice = max(choice_patterns.items(), key=lambda x: x[1])
    #     choice_tendency = ""
    #     if most_common_choice[0] == "A":
    #         choice_tendency = "tends to choose bold, direct actions"
    #     elif most_common_choice[0] == "B":
    #         choice_tendency = "tends to choose balanced, moderate approaches"
    #     elif most_common_choice[0] == "C":
    #         choice_tendency = "tends to choose cautious, safe options"
        
    #     history_analysis = f"""
    #     Player's Gaming History:
    #     - Total games played: {game_played}
    #     - Choice pattern: {choice_patterns} (player {choice_tendency})
    #     - Recent endings achieved: {list(set(common_endings))[-3:] if common_endings else "None"}
    #     - Experience level: {"Experienced" if game_played > 5 else "Intermediate" if game_played > 2 else "Beginner"}
    #     """

    prompt = f"""
    You are creating a personalized psychological thriller scenario for a specific player.
    
    PLAYER CONTEXT:
    {trait_analysis}
    {history_analysis}
    
    CURRENT SESSION:
    Depth: {depth}/5
    Trait Focus: {trait_focus}
    Previous Choices in This Session: {previous_choices}
    
    PERSONALIZATION GUIDELINES:
    1. Consider the player's trait profile when crafting the scenario intensity
    2. If this trait ({trait_focus}) is their weakness, create a gentler introduction
    3. If this trait is their strength, challenge them with more complex moral dilemmas
    4. Reference their choice patterns - if they're always cautious, present scenarios that reward boldness
    5. Adapt difficulty based on their experience level ({game_played} games played)
    6. Create narrative callbacks to their previous gaming patterns when appropriate
    
    Generate a scenario with:
    1. A dark, psychological narrative (2-3 sentences) tailored to their experience level
    2. Three choices (A, B, C) that test {trait_focus} at appropriate difficulty
    3. Each choice should have different trait impact (high, moderate, low)
    4. Consider their playing history - challenge their typical patterns
    
    Return ONLY valid JSON in this exact format:
    {{
        "depth": {depth},
        "scene_narrative": [
            {{"text": "First sentence adapted to player's profile", "sfx": "sound_effect"}},
            {{"text": "Second sentence that challenges their patterns", "sfx": "sound_effect"}}
        ],
        "narrative_purpose": "Why this scenario fits this specific player",
        "personalization_notes": "How this scenario is tailored to their profile",
        "choices": [
            {{
                "choice_id": "A",
                "choice_text": "Choice description (consider their typical patterns)",
                "maps_to_trait_details": {{
                    "trait": "{trait_focus}",
                    "degree": "high"
                }},
                "short_hidden_message": "Psychological insight based on their profile"
            }},
            {{
                "choice_id": "B", 
                "choice_text": "Moderate choice adapted to their experience",
                "maps_to_trait_details": {{
                    "trait": "{trait_focus}",
                    "degree": "moderate"
                }},
                "short_hidden_message": "Insight reflecting their gaming history"
            }},
            {{
                "choice_id": "C",
                "choice_text": "Choice that challenges their usual pattern",
                "maps_to_trait_details": {{
                    "trait": "{trait_focus}",
                    "degree": "low"
                }},
                "short_hidden_message": "Counter to their typical behavior"
            }}
        ],
        "is_end": {str(depth == 5).lower()}
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert psychological thriller writer who creates personalized gaming experiences. Always return valid JSON only."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1500
        )
        
        scenario_json = json.loads(response.choices[0].message.content)
        
        # Validate the structure
        required_keys = ["depth", "scene_narrative", "choices", "is_end"]
        if all(key in scenario_json for key in required_keys):
            print(f"Generated personalized scenario for depth {depth}, trait: {trait_focus}")
            return scenario_json
        else:
            raise ValueError("Invalid scenario structure from AI")
            
    except Exception as e:
        print(f"AI generation error: {e}")
        # Simple fallback scenario
        return {
            "depth": depth,
            "scene_narrative": [
                {"text": f"You face a challenging situation that tests your {trait_focus}.", "sfx": "tension"},
                {"text": "The choice you make will reveal something important about yourself.", "sfx": "heartbeat"}
            ],
            "narrative_purpose": f"Testing {trait_focus} for an experienced player",
            "personalization_notes": f"Adapted for {game_played} games played",
            "choices": [
                {
                    "choice_id": "A",
                    "choice_text": f"Face the challenge head-on",
                    "maps_to_trait_details": {"trait": trait_focus, "degree": "high"},
                    "short_hidden_message": f"You push your {trait_focus} to its limits"
                },
                {
                    "choice_id": "B",
                    "choice_text": f"Take a measured approach",
                    "maps_to_trait_details": {"trait": trait_focus, "degree": "moderate"},
                    "short_hidden_message": f"You balance {trait_focus} with wisdom"
                },
                {
                    "choice_id": "C",
                    "choice_text": f"Choose the safer option",
                    "maps_to_trait_details": {"trait": trait_focus, "degree": "low"},
                    "short_hidden_message": f"You prioritize safety over {trait_focus}"
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
    """Generate a personalized scenario for grow mode"""
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if session["mode"] != "grow":
        raise HTTPException(status_code=400, detail="Not a grow session")
    
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