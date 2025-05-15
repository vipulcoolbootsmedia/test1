from datetime import datetime
from typing import Optional, Dict, List

class User:
    def __init__(self, userid: int, username: str, email: str, hashpassword: str,
                 trait_profile: Dict, game_history: Dict, game_played: int,
                 created_at: datetime, is_active: bool = True):
        self.userid = userid
        self.username = username
        self.email = email
        self.hashpassword = hashpassword
        self.trait_profile = trait_profile
        self.game_history = game_history
        self.game_played = game_played
        self.created_at = created_at
        self.is_active = is_active

class Session:
    def __init__(self, session_id: int, user_id: int, mode: str,
                 scenario_id: Optional[int], started_at: datetime,
                 ended_at: Optional[datetime] = None, is_completed: bool = False):
        self.session_id = session_id
        self.user_id = user_id
        self.mode = mode
        self.scenario_id = scenario_id
        self.started_at = started_at
        self.ended_at = ended_at
        self.is_completed = is_completed