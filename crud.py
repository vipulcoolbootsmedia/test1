from database import get_connection
from datetime import datetime
import json


def create_user_in_db(user):
    conn = get_connection()
    cursor = conn.cursor()

    # Default trait profile
    default_traits = {
        "focus": 50,
        "bravery": 50,
        "empathy": 50,
        "honesty": 50,
        "patience": 50,
        "curiosity": 50,
        "truthfulness": 50
    }

    # Use default traits if not provided
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
    cursor.close()
    conn.close()
    return {"message": "User created"}


def update_user_traits(user_id: int, traits: dict):
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch current traits
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