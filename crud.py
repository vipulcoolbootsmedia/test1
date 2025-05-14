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
