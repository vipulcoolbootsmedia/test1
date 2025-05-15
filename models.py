# This file is for SQLAlchemy models if you decide to use ORM later
# For now, we're using direct SQL queries, so this can be empty or contain:

from datetime import datetime

class UserInfo:
    def __init__(self, userid, username, email, hashpassword, 
                 game_history, trait_profile, created_at, game_played):
        self.userid = userid
        self.username = username
        self.email = email
        self.hashpassword = hashpassword
        self.game_history = game_history
        self.trait_profile = trait_profile
        self.created_at = created_at
        self.game_played = game_played

class GameSession:
    def __init__(self, session_id, user_id, mode, scenario_id, started_at):
        self.session_id = session_id
        self.user_id = user_id
        self.mode = mode
        self.scenario_id = scenario_id
        self.started_at = started_at