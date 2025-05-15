from database import get_connection
import json
from datetime import datetime
from fastapi import HTTPException

# User CRUD Operations
def create_user_in_db(user):
    conn = get_connection()
    cursor = conn.cursor()

    default_traits = {
        "focus": 50,
        "bravery": 50,
        "empathy": 50,
        "honesty": 50,
        "patience": 50,
        "curiosity": 50,
        "truthfulness": 50
    }

    trait_profile = user.trait_profile if user.trait_profile else default_traits
    game_history = user.game_history if user.game_history else {}
    game_played = user.game_played if user.game_played is not None else 0

    cursor.execute("""
        INSERT INTO user_info 
        (username, email, hashpassword, trait_profile, game_played, game_history) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        user.username,
        user.email,
        user.hashpassword,
        json.dumps(trait_profile),
        game_played,
        json.dumps(game_history)
    ))

    conn.commit()
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return {"message": "User created", "user_id": user_id}

def get_user_by_id(user_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM user_info WHERE userid = %s", (user_id,))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not user:
        return None
    
    # Parse JSON fields
    if user.get("game_history"):
        user["game_history"] = json.loads(user["game_history"])
    if user.get("trait_profile"):
        user["trait_profile"] = json.loads(user["trait_profile"])
    
    # Remove password from response
    user.pop("hashpassword", None)
    
    return user

def update_user_traits(user_id: int, traits: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT trait_profile FROM user_info WHERE userid = %s", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {"error": "User not found"}

    current_traits = json.loads(result[0])
    current_traits.update(traits)

    cursor.execute("""
        UPDATE user_info SET trait_profile = %s WHERE userid = %s
    """, (json.dumps(current_traits), user_id))

    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Trait profile updated", "updated_traits": current_traits}

def add_game_to_user(user_id: int, game_id: str, game_data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT game_history, game_played FROM user_info WHERE userid = %s", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {"error": "User not found"}

    game_history = json.loads(result[0]) if result[0] else {}
    game_played = result[1] if result[1] else 0

    game_history[game_id] = game_data
    game_played += 1

    cursor.execute("""
        UPDATE user_info SET game_history = %s, game_played = %s WHERE userid = %s
    """, (json.dumps(game_history), game_played, user_id))

    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Game data added", "game_history": game_history, "game_played": game_played}

# Session CRUD Operations
def start_game_session(user_id: int, mode: str, scenario_id: int = None):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT userid FROM user_info WHERE userid = %s", (user_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return {"error": "User not found"}
    
    # For learn mode, scenario_id is required
    if mode == "learn" and scenario_id is None:
        cursor.close()
        conn.close()
        return {"error": "scenario_id is required for learn mode"}
    
    # Insert new session
    cursor.execute("""
        INSERT INTO game_session (user_id, mode, scenario_id) 
        VALUES (%s, %s, %s)
    """, (user_id, mode, scenario_id))
    
    session_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        "message": "Session started successfully",
        "session_id": session_id,
        "user_id": user_id,
        "mode": mode,
        "scenario_id": scenario_id
    }

def get_session_details(session_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT session_id, user_id, mode, scenario_id, started_at 
        FROM game_session 
        WHERE session_id = %s
    """, (session_id,))
    
    session = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not session:
        return {"error": "Session not found"}
    
    session['started_at'] = str(session['started_at'])
    return session

# Learn Module CRUD Operations
def get_scenario_for_session(session_id: int, path: str = ""):
    """Get scenario based on session's scenario_id and current path"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get the scenario_id from the session
    cursor.execute("""
        SELECT scenario_id, mode FROM game_session 
        WHERE session_id = %s
    """, (session_id,))
    
    session = cursor.fetchone()
    if not session:
        cursor.close()
        conn.close()
        return {"error": "Session not found"}
    
    if session['mode'] != 'learn':
        cursor.close()
        conn.close()
        return {"error": "This session is not in learn mode"}
    
    scenario_id = session['scenario_id']
    
    # Get the scenario content
    cursor.execute("SELECT info FROM scenario WHERE scenario_id = %s", (scenario_id,))
    result = cursor.fetchone()
    
    if not result:
        cursor.close()
        conn.close()
        return {"error": f"Scenario {scenario_id} not found"}
    
    # Parse and traverse the JSON tree
    current_scenario = json.loads(result['info'])
    
    # Traverse the path
    for choice_letter in path:
        found = False
        for choice in current_scenario.get('choices', []):
            if choice['choice_id'] == choice_letter:
                if 'next_scenario' in choice:
                    current_scenario = choice['next_scenario']
                    found = True
                    break
        
        if not found:
            cursor.close()
            conn.close()
            return {"error": f"Invalid path: {path}"}
    
    cursor.close()
    conn.close()
    
    # Add metadata
    current_scenario['current_path'] = path
    current_scenario['session_id'] = session_id
    current_scenario['scenario_id'] = scenario_id
    
    return current_scenario

def record_choice(choice_data):
    """Record a user's choice for both learn and grow modes"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verify session exists
    cursor.execute("SELECT session_id FROM game_session WHERE session_id = %s", 
                   (choice_data.session_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return {"error": "Session not found"}
    
    # Insert choice
    cursor.execute("""
        INSERT INTO user_choices (session_id, depth, choice_id, trait_impact)
        VALUES (%s, %s, %s, %s)
    """, (
        choice_data.session_id,
        choice_data.depth,
        choice_data.choice_id,
        choice_data.trait_impact
    ))
    
    conn.commit()
    choice_id = cursor.lastrowid
    cursor.close()
    conn.close()
    
    return {
        "message": "Choice recorded successfully",
        "choice_id": choice_id
    }

# Grow Module CRUD Operations
def generate_scenario_in_db(data):
    """Store a generated scenario in the database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verify session exists and is in grow mode
    cursor.execute("""
        SELECT session_id, mode FROM game_session 
        WHERE session_id = %s
    """, (data.session_id,))
    
    session = cursor.fetchone()
    if not session:
        cursor.close()
        conn.close()
        return {"error": "Session not found"}
    
    if session[1] != 'grow':
        cursor.close()
        conn.close()
        return {"error": "Session is not in grow mode"}
    
    # Insert generated scenario
    cursor.execute("""
        INSERT INTO generated_scenarios (session_id, depth, scenario_json)
        VALUES (%s, %s, %s)
    """, (
        data.session_id,
        data.depth,
        json.dumps(data.scenario_json)
    ))
    
    conn.commit()
    scenario_id = cursor.lastrowid
    cursor.close()
    conn.close()
    
    return {
        "message": "Scenario generated successfully",
        "scenario_id": scenario_id
    }

def get_generated_scenario(session_id: int, depth: int):
    """Retrieve a generated scenario"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, session_id, depth, scenario_json, generated_at
        FROM generated_scenarios
        WHERE session_id = %s AND depth = %s
    """, (session_id, depth))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not result:
        return {"error": "Scenario not found"}
    
    scenario = {
        "id": result['id'],
        "session_id": result['session_id'],
        "depth": result['depth'],
        "generated_at": str(result['generated_at']),
        "scenario": json.loads(result['scenario_json'])
    }
    
    return scenario

# Analytics CRUD Operations
def get_user_history(user_id: int):
    """Get all sessions for a user"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT session_id, mode, scenario_id, started_at
        FROM game_session
        WHERE user_id = %s
        ORDER BY started_at DESC
    """, (user_id,))
    
    sessions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convert datetime to string
    for session in sessions:
        session['started_at'] = str(session['started_at'])
    
    return sessions

def get_session_choices(session_id: int):
    """Get all choices made in a session"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, depth, choice_id, trait_impact, recorded_at
        FROM user_choices
        WHERE session_id = %s
        ORDER BY depth
    """, (session_id,))
    
    choices = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convert datetime to string
    for choice in choices:
        choice['recorded_at'] = str(choice['recorded_at'])
    
    return choices

def get_session_generated_scenarios(session_id: int):
    """Get all generated scenarios for a grow session"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, depth, scenario_json, generated_at
        FROM generated_scenarios
        WHERE session_id = %s
        ORDER BY depth
    """, (session_id,))
    
    scenarios = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Parse JSON and convert datetime
    for scenario in scenarios:
        scenario['scenario_json'] = json.loads(scenario['scenario_json'])
        scenario['generated_at'] = str(scenario['generated_at'])
    
    return scenarios