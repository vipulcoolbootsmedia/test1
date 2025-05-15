from fastapi import APIRouter, Depends, HTTPException
from schemas import GenerateScenarioRequest, ScenarioResponse, ChoiceInput
from dependencies import get_current_active_user
from crud import SessionCRUD, GeneratedScenarioCRUD, ChoiceCRUD, UserCRUD
from database import db
import os
import json
from typing import List
import random

# Only import OpenAI if available
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_AVAILABLE = True
except Exception as e:
    print(f"OpenAI not available: {e}")
    OPENAI_AVAILABLE = False

router = APIRouter(prefix="/grow", tags=["grow"])

def generate_scenario_with_ai(depth: int, trait_focus: str, previous_choices: list):
    """Generate scenario using OpenAI with enhanced prompting"""
    
    # Create a more detailed context based on previous choices
    choice_context = ""
    if previous_choices:
        choice_context = f"Previous actions: {', '.join(previous_choices)}. Build upon these choices."
    
    prompt = f"""
    Create a unique psychological thriller scenario for depth {depth}/5.
    
    Requirements:
    1. Create a UNIQUE situation different from generic crossroads
    2. Make it dark, psychological, and tense
    3. Trait focus: {trait_focus}
    4. {choice_context}
    5. Choices should test {trait_focus} in different ways
    6. Each choice should reveal something about the character's psychology
    
    Return ONLY valid JSON in this exact format:
    {{
        "depth": {depth},
        "scene_narrative": [
            {{"text": "First descriptive sentence about the unique situation", "sfx": "appropriate_sound"}},
            {{"text": "Second sentence building tension", "sfx": "another_sound"}}
        ],
        "narrative_purpose": "What psychological aspect this tests",
        "choices": [
            {{
                "choice_id": "A",
                "choice_text": "First option (tests {trait_focus} highly)",
                "maps_to_trait_details": {{
                    "trait": "{trait_focus}",
                    "degree": "high"
                }},
                "short_hidden_message": "What this reveals about the player"
            }},
            {{
                "choice_id": "B",
                "choice_text": "Second option (moderate {trait_focus})",
                "maps_to_trait_details": {{
                    "trait": "{trait_focus}",
                    "degree": "moderate"
                }},
                "short_hidden_message": "What this reveals about the player"
            }},
            {{
                "choice_id": "C",
                "choice_text": "Third option (low {trait_focus})",
                "maps_to_trait_details": {{
                    "trait": "{trait_focus}",
                    "degree": "low"
                }},
                "short_hidden_message": "What this reveals about the player"
            }}
        ],
        "is_end": {"true" if depth == 5 else "false"}
    }}
    """
    
    try:
        if OPENAI_AVAILABLE:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a creative writer for psychological thriller games. Return only valid JSON in the exact format requested."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=1500
            )
            
            # Get the response content
            output_text = response.choices[0].message.content
            
            # Remove markdown code block if present
            if output_text.startswith("```json"):
                output_text = output_text[7:]  # Remove ```json
            if output_text.startswith("```"):
                output_text = output_text[3:]  # Remove ```
            if output_text.endswith("```"):
                output_text = output_text[:-3]  # Remove trailing ```
                
            # Extract JSON from response
            json_start = output_text.find('{')
            json_end = output_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_text = output_text[json_start:json_end]
                scenario_json = json.loads(json_text)
            else:
                # Try parsing the entire response as JSON
                scenario_json = json.loads(output_text.strip())
            
            # Validate the structure
            required_keys = ["depth", "scene_narrative", "choices", "is_end"]
            if all(key in scenario_json for key in required_keys):
                print(f"Successfully generated scenario for depth {depth}")
                return scenario_json
            else:
                raise ValueError(f"Invalid scenario structure. Missing keys: {[key for key in required_keys if key not in scenario_json]}")
        else:
            print("OpenAI not available, using fallback")
            return get_fallback_scenario(depth, trait_focus)
            
    except Exception as e:
        print(f"AI generation error: {e}")
        # Enhanced fallback scenarios based on depth
        return get_fallback_scenario(depth, trait_focus)

def get_fallback_scenario(depth: int, trait_focus: str):
    """Get unique fallback scenarios for each depth"""
    scenarios = {
        1: {
            "scene": "You wake up in a dimly lit room with no memory of how you got here. The walls seem to breathe, and somewhere in the darkness, a clock ticks irregularly.",
            "sfx": ["heartbeat", "dripping_water"],
            "choices": [
                ("Search for a way out immediately", "Your {trait} drives you to act quickly"),
                ("Examine the room carefully first", "Your measured approach shows moderate {trait}"),
                ("Call out for help", "You prefer to rely on others rather than your own {trait}")
            ]
        },
        2: {
            "scene": "A stranger approaches you with an urgent message about your past. Their face shifts and changes as they speak, never quite settling on one form.",
            "sfx": ["footsteps", "whisper"],
            "choices": [
                ("Confront them directly about what they know", "Your {trait} compels you to face the truth"),
                ("Listen cautiously while planning escape", "You balance {trait} with caution"),
                ("Refuse to engage and walk away", "You avoid situations that test your {trait}")
            ]
        },
        3: {
            "scene": "You discover a hidden journal with disturbing entries in your handwriting. The pages turn themselves, revealing truths you don't remember writing.",
            "sfx": ["page_turning", "clock_ticking"],
            "choices": [
                ("Read every entry despite the horror", "Your {trait} drives you to know everything"),
                ("Read selected pages carefully", "You approach with moderate {trait}"),
                ("Burn the journal immediately", "You reject challenges to your {trait}")
            ]
        },
        4: {
            "scene": "Three doors appear before you, each showing a different version of your future. The visions shift and writhe, each more disturbing than the last.",
            "sfx": ["door_creak", "echoing_voices"],
            "choices": [
                ("Enter the door showing greatest challenge", "Maximum {trait} guides your choice"),
                ("Choose the balanced middle path", "You moderate your {trait}"),
                ("Select the safest looking option", "You minimize the need for {trait}")
            ]
        },
        5: {
            "scene": "The truth about everything is finally revealed in a shocking confrontation. Reality itself seems to fracture as you face your deepest fears.",
            "sfx": ["dramatic_music", "revelation"],
            "choices": [
                ("Face the complete truth head-on", "Your {trait} defines who you are"),
                ("Accept parts while questioning others", "You've learned to balance {trait}"),
                ("Reject the revelation entirely", "You choose comfort over {trait}")
            ]
        }
    }
    
    scenario_data = scenarios.get(depth, scenarios[1])
    scene_parts = scenario_data["scene"].split(". ")
    
    return {
        "depth": depth,
        "scene_narrative": [
            {"text": scene_parts[0] + ".", "sfx": scenario_data["sfx"][0]},
            {"text": scene_parts[1] if len(scene_parts) > 1 else "The tension builds.", "sfx": scenario_data["sfx"][1]}
        ],
        "narrative_purpose": f"Testing {trait_focus} through increasingly complex moral choices",
        "choices": [
            {
                "choice_id": chr(65 + i),  # A, B, C
                "choice_text": choice[0],
                "maps_to_trait_details": {
                    "trait": trait_focus,
                    "degree": ["high", "moderate", "low"][i]
                },
                "short_hidden_message": choice[1].format(trait=trait_focus)
            }
            for i, choice in enumerate(scenario_data["choices"])
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
    
    # Get user's trait profile to potentially influence generation
    user_traits = current_user.get("trait_profile", {})
    
    # You could vary trait focus based on user's lowest traits
    if not request.trait_focus:
        if user_traits:
            # Find the lowest trait
            lowest_trait = min(user_traits.items(), key=lambda x: x[1])[0]
            request.trait_focus = lowest_trait
        else:
            request.trait_focus = "bravery"
    
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
    
    # Get the scenario to find which trait was being tested
    scenario = GeneratedScenarioCRUD.get_generated_scenario(session_id, choice.depth)
    if scenario and scenario.get('scenario_json'):
        # Extract trait from the scenario's choices
        for scenario_choice in scenario['scenario_json'].get('choices', []):
            if scenario_choice['choice_id'] == choice.choice_id:
                trait_name = scenario_choice['maps_to_trait_details']['trait']
                _update_user_traits(current_user["userid"], trait_name, choice.trait_impact)
                break
    
    return result

def _update_user_traits(user_id: int, trait_name: str, impact: str):
    """Update specific user trait based on choice"""
    impact_values = {
        "high": 8,
        "moderate": 4,
        "low": 1
    }
    
    with db.get_cursor() as (cursor, connection):
        # Get current trait profile
        cursor.execute("SELECT trait_profile FROM user_info WHERE userid = %s", (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            trait_profile = json.loads(result[0])
            
            # Update specific trait
            if trait_name in trait_profile:
                current_value = trait_profile[trait_name]
                new_value = min(100, current_value + impact_values.get(impact, 0))
                trait_profile[trait_name] = new_value
            
            # Update in database
            cursor.execute("""
                UPDATE user_info 
                SET trait_profile = %s 
                WHERE userid = %s
            """, (json.dumps(trait_profile), user_id))
            connection.commit()

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