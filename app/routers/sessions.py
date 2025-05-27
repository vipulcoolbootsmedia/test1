from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from schemas import SessionCreate, SessionResponse
from dependencies import get_current_active_user
from crud import SessionCRUD, ChoiceCRUD, GeneratedScenarioCRUD, ScenarioCRUD
from database import db
from datetime import datetime
import json
import time
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Initialize OpenAI client for game summaries
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_game_summary(session_data: dict, user_data: dict) -> dict:
    """
    Generate an AI-powered breakdown summary of the entire gameplay session
    Returns: dict with story_summary, trait_summary, genre, and genre_description
    """
    try:
        # Extract key information from session data
        mode = session_data["session_info"]["mode"]
        duration = session_data["session_info"]["total_duration"]
        trait_changes = session_data["results"]["trait_changes"]
        ending = session_data["results"]["ending_achieved"]
        
        # Build choice progression narrative
        choice_progression = []
        trait_impacts = {"high": 0, "moderate": 0, "low": 0}
        depth_keys = sorted([k for k in session_data.keys() if k.startswith("depth")])
        
        for depth_key in depth_keys:
            depth_data = session_data[depth_key]
            if depth_data.get("choice_taken"):
                choice_id = depth_data["choice_taken"]
                
                # Find the chosen option details
                chosen_choice = None
                for choice in depth_data.get("choices", []):
                    if choice["choice_id"] == choice_id:
                        chosen_choice = choice
                        break
                
                if chosen_choice:
                    trait_impact_degree = chosen_choice["maps_to_trait_details"].get("degree", "moderate")
                    trait_impacts[trait_impact_degree] += 1
                    
                    choice_progression.append({
                        "depth": depth_key,
                        "scenario": depth_data["scene_narrative"][0]["text"][:80] + "..." if depth_data.get("scene_narrative") else "",
                        "choice": chosen_choice["choice_text"][:60] + "...",
                        "trait_impact": chosen_choice["maps_to_trait_details"],
                        "hidden_message": chosen_choice.get("short_hidden_message", "")
                    })
        
        # Determine average choice pattern
        total_choices = sum(trait_impacts.values())
        if total_choices > 0:
            high_percent = (trait_impacts["high"] / total_choices) * 100
            moderate_percent = (trait_impacts["moderate"] / total_choices) * 100
            low_percent = (trait_impacts["low"] / total_choices) * 100
            
            if high_percent >= 50:
                avg_choice_trait = "Bold Risk-Taker"
            elif moderate_percent >= 50:
                avg_choice_trait = "Balanced Decision-Maker"
            elif low_percent >= 50:
                avg_choice_trait = "Cautious Strategist"
            else:
                avg_choice_trait = "Adaptive Player"
        else:
            avg_choice_trait = "Unknown Pattern"
        
        # Create the prompt for OpenAI
        prompt = f"""
You are a psychological game analyst. Create a structured breakdown of this player's session.

GAME DATA:
- Mode: {mode.title()}
- Duration: {duration}
- Ending: {ending}
- Username: {user_data.get('username', 'Player')}
- Choice Pattern: {avg_choice_trait}
- High Impact Choices: {trait_impacts['high']}/{total_choices}
- Moderate Impact Choices: {trait_impacts['moderate']}/{total_choices}
- Low Impact Choices: {trait_impacts['low']}/{total_choices}

CHOICE SUMMARY:
"""
        
        for i, choice_data in enumerate(choice_progression, 1):
            prompt += f"Depth {i}: {choice_data['choice']} (Impact: {choice_data['trait_impact']['degree']})\n"
        
        prompt += f"""

Return EXACTLY this JSON format (no additional text):
{{
  "story_summary": "80-word dramatic narrative of the player's journey through the scenarios",
  "trait_summary": "Analysis of their {avg_choice_trait} pattern and what it reveals about their personality",
  "genre": "One of: Psychological Horror, Mystery Thriller, Supernatural Drama, Dark Fantasy, or Suspense",
  "genre_description": "Brief explanation of why this session fits that genre"
}}

Requirements:
- story_summary: Exactly 80 words, dramatic tone, third person
- trait_summary: Focus on their choice pattern and psychological insights
- genre: Pick the most fitting genre based on scenarios
- genre_description: 1-2 sentences explaining the genre choice
"""
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a psychological game analyst who creates structured breakdowns of gameplay sessions. Always return valid JSON format exactly as requested."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        # Parse the JSON response
        response_text = response.choices[0].message.content.strip()
        
        # Clean up the response to ensure it's valid JSON
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        game_summary = json.loads(response_text)
        print(f"Generated structured game summary for user {user_data.get('username', 'Unknown')}")
        return game_summary
        
    except Exception as e:
        print(f"Error generating game summary: {str(e)}")
        # Fallback structured summary if AI fails
        return {
            "story_summary": f"In this {session_data['session_info']['mode']} mode session lasting {session_data['session_info']['total_duration']}, the player navigated through psychological challenges and achieved the '{session_data['results']['ending_achieved']}' ending, revealing key insights into their decision-making patterns and personality traits.",
            "trait_summary": f"Player demonstrated a {avg_choice_trait} approach with {trait_impacts['high']} high-impact, {trait_impacts['moderate']} moderate, and {trait_impacts['low']} low-impact choices.",
            "genre": "Psychological Thriller",
            "genre_description": "A psychological thriller focusing on the mental and emotional states of characters facing internal conflicts and moral dilemmas."
        }

@router.post("/", response_model=dict)
async def create_session(
    session: SessionCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new game session"""
    result = SessionCRUD.create_session(
        current_user["userid"], 
        session.mode, 
        session.scenario_id
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: int):
    """Get details for a specific session"""
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.patch("/{session_id}/end", response_model=dict)
async def end_session(
    session_id: int,
    is_completed: bool = True,
    current_user: dict = Depends(get_current_active_user)
):
    """End a session and record comprehensive game history with AI-generated summary"""
    # Verify session belongs to user
    session = SessionCRUD.get_session(session_id)
    if not session or session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # End the session
    end_time = datetime.utcnow()
    result = SessionCRUD.update_session(
        session_id, 
        end_time, 
        is_completed
    )
    
    # If the session was completed, update game history with comprehensive data including AI summary
    if is_completed:
        try:
            # Calculate session duration
            start_time = session["started_at"]
            duration_seconds = (end_time - start_time).total_seconds()
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            duration_str = f"{minutes}m {seconds}s"
            
            # Create session info
            session_info = {
                "mode": session["mode"],
                "started_at": start_time.isoformat(),
                "ended_at": end_time.isoformat(),
                "is_completed": is_completed,
                "total_duration": duration_str
            }
            
            # Add scenario_id if in learn mode
            if session["mode"] == "learn":
                session_info["scenario_id"] = session["scenario_id"]
            
            # Get all choices and scenarios based on session mode
            detailed_history = {}
            
            if session["mode"] == "learn":
                detailed_history = build_learn_mode_history(session_id, session["scenario_id"])
            else:  # grow mode
                detailed_history = build_grow_mode_history(session_id)
            
            # Add session info to the detailed history
            detailed_history["session_info"] = session_info
            
            # Calculate result summary based on choices
            results = calculate_session_results(session_id, current_user["userid"])
            detailed_history["results"] = results
            
            # Update user's game history (this will also generate the AI summary)
            update_user_game_history(current_user["userid"], session_id, detailed_history)
            
        except Exception as e:
            # Log the error but still return success for the session update
            print(f"Error updating game history with AI summary: {str(e)}")
    
    return result

@router.get("/user/{user_id}", response_model=List[SessionResponse])
async def get_user_sessions(
    user_id: int,
    mode: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all sessions for a user, optionally filtered by mode"""
    if current_user["userid"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return SessionCRUD.get_user_sessions(user_id, mode)

# Helper functions for building detailed game history

def build_learn_mode_history(session_id: int, scenario_id: int):
    """Build detailed history for a learn mode session"""
    history = {}
    
    # Get all choices made in this session
    choices = ChoiceCRUD.get_session_choices(session_id)
    
    # Get the full scenario data
    scenario_data = ScenarioCRUD.get_scenario(scenario_id)
    if not scenario_data or not scenario_data["info"]:
        return history
    
    scenario_info = scenario_data["info"]
    
    # Track the path through scenario tree
    current_scenario = scenario_info
    path = ""
    
    # Process each choice to build the full history
    for i, choice in enumerate(sorted(choices, key=lambda x: x["depth"])):
        depth = choice["depth"]
        choice_id = choice["choice_id"]
        
        # Add to path for navigating scenario tree
        path += choice_id
        
        # Create depth entry if first choice
        if i == 0:
            history[f"depth{depth}"] = {
                "scene_narrative": current_scenario.get("scene_narrative", []),
                "narrative_purpose": current_scenario.get("narrative_purpose", ""),
                "image_gen_prompt": current_scenario.get("image_gen_prompt", ""),
                "choices": current_scenario.get("choices", []),
                "choice_taken": choice_id,
                "choice_timestamp": choice.get("recorded_at", "").isoformat() if choice.get("recorded_at") else "",
            }
        else:
            # Navigate to next scenario based on previous choice
            for c in current_scenario.get("choices", []):
                if c["choice_id"] == path[-2]:  # previous choice
                    if "next_scenario" in c:
                        current_scenario = c["next_scenario"]
                        break
            
            # Add this depth to history
            history[f"depth{depth}"] = {
                "scene_narrative": current_scenario.get("scene_narrative", []),
                "narrative_purpose": current_scenario.get("narrative_purpose", ""),
                "image_gen_prompt": current_scenario.get("image_gen_prompt", ""),
                "choices": current_scenario.get("choices", []),
                "choice_taken": choice_id,
                "choice_timestamp": choice.get("recorded_at", "").isoformat() if choice.get("recorded_at") else "",
            }
    
    return history

def build_grow_mode_history(session_id: int):
    """Build detailed history for a grow mode session"""
    history = {}
    
    # Get all generated scenarios for this session
    scenarios = GeneratedScenarioCRUD.get_all_generated_scenarios(session_id)
    
    # Get all choices made in this session
    choices = ChoiceCRUD.get_session_choices(session_id)
    
    # Create mapping of choice by depth for easier lookup
    choice_map = {choice["depth"]: choice for choice in choices}
    
    # Process each scenario to build the full history
    for scenario in scenarios:
        depth = scenario["depth"]
        scenario_json = scenario["scenario_json"]
        
        # Find the choice made at this depth
        choice_taken = ""
        choice_timestamp = ""
        if depth in choice_map:
            choice_taken = choice_map[depth]["choice_id"]
            if choice_map[depth].get("recorded_at"):
                choice_timestamp = choice_map[depth]["recorded_at"].isoformat()
        
        # Add to history
        history[f"depth{depth}"] = {
            "scene_narrative": scenario_json.get("scene_narrative", []),
            "narrative_purpose": scenario_json.get("narrative_purpose", ""),
            "image_gen_prompt": scenario_json.get("image_gen_prompt", ""),
            "choices": scenario_json.get("choices", []),
            "choice_taken": choice_taken,
            "choice_timestamp": choice_timestamp
        }
    
    return history

def calculate_session_results(session_id: int, user_id: int):
    """Calculate result summary for the session - Enhanced with AI game summary"""
    # Get all choices made
    choices = ChoiceCRUD.get_session_choices(session_id)
    
    # Track trait changes
    trait_changes = {}
    
    # Calculate impact levels
    impact_values = {"high": 8, "moderate": 4, "low": 1}
    
    # Process each choice to determine trait impacts
    for choice in choices:
        trait_impact = choice["trait_impact"]
        
        # In a real implementation, you'd determine which trait was affected
        # Here we're using placeholder logic
        trait = "bravery"  # Default
        
        # Update the trait change
        if trait not in trait_changes:
            trait_changes[trait] = 0
        
        trait_changes[trait] += impact_values.get(trait_impact, 0)
    
    # Format trait changes for display
    formatted_trait_changes = {k: f"+{v}" if v > 0 else str(v) for k, v in trait_changes.items()}
    
    # Calculate score based on choices
    score = sum(impact_values.get(choice["trait_impact"], 0) * 10 for choice in choices)
    
    # Determine ending based on choices
    high_choices = sum(1 for choice in choices if choice["trait_impact"] == "high")
    moderate_choices = sum(1 for choice in choices if choice["trait_impact"] == "moderate")
    low_choices = sum(1 for choice in choices if choice["trait_impact"] == "low")
    
    ending = "Neutral Explorer"
    ending_message = "You completed your journey with a balanced approach."
    
    if high_choices > moderate_choices and high_choices > low_choices:
        ending = "Brave Conqueror"
        ending_message = "You faced your fears and conquered them, proving your courage in the face of both physical and psychological threats."
    elif moderate_choices > high_choices and moderate_choices > low_choices:
        ending = "Thoughtful Navigator"
        ending_message = "You approached challenges with careful consideration, finding balanced solutions to complex problems."
    elif low_choices > high_choices and low_choices > moderate_choices:
        ending = "Cautious Survivor"
        ending_message = "You prioritized safety and careful planning, demonstrating that sometimes wisdom is knowing when not to act."
    
    return {
        "trait_changes": formatted_trait_changes,
        "ending_achieved": ending,
        "ending_message": ending_message,
        "session_score": score,
        # Note: game_summary will be added after the session data is built
        "game_summary": None  # Placeholder - will be filled in update_user_game_history
    }

def update_user_game_history(user_id: int, session_id: int, detailed_history: dict):
    """Update the user's game history with detailed session data - Enhanced with AI game summary"""
    try:
        with db.get_cursor() as (cursor, connection):
            # Get current game history
            cursor.execute("SELECT game_history FROM user_info WHERE userid = %s", (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                try:
                    game_history = json.loads(result[0])
                except Exception as e:
                    print(f"Error parsing existing game history: {str(e)}")
                    game_history = {}
            else:
                game_history = {}
            
            # Get user data for AI summary generation
            cursor.execute("""
                SELECT username, trait_profile, game_played 
                FROM user_info 
                WHERE userid = %s
            """, (user_id,))
            user_result = cursor.fetchone()
            
            if user_result:
                user_data = {
                    "username": user_result[0],
                    "trait_profile": json.loads(user_result[1]) if user_result[1] else {},
                    "game_played": user_result[2]
                }
                
                # Generate AI-powered game summary
                print(f"Generating AI game summary for session {session_id}...")
                game_summary = generate_game_summary(detailed_history, user_data)
                
                # Add the game summary to results
                detailed_history["results"]["game_summary"] = game_summary
                print(f"Added game summary to session {session_id}")
            
            # Add new session data
            game_history[f"session_{session_id}"] = detailed_history
            
            # Update in database
            cursor.execute("""
                UPDATE user_info 
                SET game_history = %s, game_played = game_played + 1
                WHERE userid = %s
            """, (json.dumps(game_history), user_id))
            connection.commit()
            
            return True
    except Exception as e:
        print(f"Error updating game history: {str(e)}")
        return False
    
@router.get("/{session_id}/history", response_model=dict)
async def get_session_history(
    session_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed history for a specific session"""
    # Verify session belongs to user
    session = SessionCRUD.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["userid"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get user's game history
    with db.get_cursor() as (cursor, connection):
        cursor.execute("SELECT game_history FROM user_info WHERE userid = %s", 
                      (current_user["userid"],))
        result = cursor.fetchone()
        
        if result and result[0]:
            try:
                game_history = json.loads(result[0])
                session_key = f"session_{session_id}"
                
                if session_key in game_history:
                    return {"history": game_history[session_key]}
                else:
                    return {"history": None, "message": "No history found for this session"}
            except:
                pass
    
    return {"history": None, "message": "Failed to retrieve session history"}