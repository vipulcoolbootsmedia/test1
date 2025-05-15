from database import db
import json
from datetime import datetime
from auth import get_password_hash
import uuid
from typing import List, Dict, Optional

class UserCRUD:
    @staticmethod
    def create_user(user_data):
        with db.get_cursor() as (cursor, connection):
            # Check if username or email already exists
            cursor.execute("""
                SELECT userid FROM user_info 
                WHERE username = %s OR email = %s
            """, (user_data.username, user_data.email))
            
            if cursor.fetchone():
                return {"error": "Username or email already exists"}
            
            # Create new user
            cursor.execute("""
                INSERT INTO user_info 
                (username, email, hashpassword, trait_profile, game_played, game_history, is_active) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user_data.username,
                user_data.email,
                get_password_hash(user_data.password),
                json.dumps(user_data.trait_profile),  # This should now work
                0,
                json.dumps({}),
                True
            ))
            
            connection.commit()
            return {"userid": cursor.lastrowid, "message": "User created successfully"}
    
    @staticmethod
    def get_user(user_id: int):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT userid, username, email, trait_profile, game_played, 
                       game_history, created_at, is_active
                FROM user_info 
                WHERE userid = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            if user:
                user['trait_profile'] = json.loads(user['trait_profile']) if user['trait_profile'] else {}
                user['game_history'] = json.loads(user['game_history']) if user['game_history'] else {}
            return user
    
    @staticmethod
    def update_user(user_id: int, update_data):
        with db.get_cursor() as (cursor, connection):
            updates = []
            values = []
            
            if update_data.email:
                updates.append("email = %s")
                values.append(update_data.email)
            
            if update_data.trait_profile:
                updates.append("trait_profile = %s")
                values.append(json.dumps(update_data.trait_profile))
            
            if not updates:
                return {"message": "No updates provided"}
            
            values.append(user_id)
            query = f"UPDATE user_info SET {', '.join(updates)} WHERE userid = %s"
            cursor.execute(query, values)
            connection.commit()
            
            return {"message": "User updated successfully"}
    
    @staticmethod
    def delete_user(user_id: int):
        with db.get_cursor() as (cursor, connection):
            # Soft delete - just mark as inactive
            cursor.execute("""
                UPDATE user_info 
                SET is_active = FALSE 
                WHERE userid = %s
            """, (user_id,))
            connection.commit()
            return {"message": "User deleted successfully"}
    
    @staticmethod
    def get_all_users(skip: int = 0, limit: int = 100):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT userid, username, email, game_played, created_at, is_active
                FROM user_info 
                WHERE is_active = TRUE
                LIMIT %s OFFSET %s
            """, (limit, skip))
            return cursor.fetchall()

class SessionCRUD:
    @staticmethod
    def create_session(user_id: int, mode: str, scenario_id: Optional[int] = None):
        with db.get_cursor() as (cursor, connection):
            if mode == "learn" and scenario_id is None:
                return {"error": "scenario_id is required for learn mode"}
            
            cursor.execute("""
                INSERT INTO game_session (user_id, mode, scenario_id) 
                VALUES (%s, %s, %s)
            """, (user_id, mode, scenario_id))
            
            connection.commit()
            return {
                "session_id": cursor.lastrowid,
                "message": "Session created successfully"
            }
    
    @staticmethod
    def get_session(session_id: int):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT * FROM game_session 
                WHERE session_id = %s
            """, (session_id,))
            return cursor.fetchone()
    
    @staticmethod
    def update_session(session_id: int, ended_at: datetime, is_completed: bool):
        with db.get_cursor() as (cursor, connection):
            cursor.execute("""
                UPDATE game_session 
                SET ended_at = %s, is_completed = %s 
                WHERE session_id = %s
            """, (ended_at, is_completed, session_id))
            connection.commit()
            return {"message": "Session updated"}
    
    @staticmethod
    def get_user_sessions(user_id: int, mode: Optional[str] = None):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            query = "SELECT * FROM game_session WHERE user_id = %s"
            params = [user_id]
            
            if mode:
                query += " AND mode = %s"
                params.append(mode)
            
            query += " ORDER BY started_at DESC"
            cursor.execute(query, params)
            return cursor.fetchall()

class ChoiceCRUD:
    @staticmethod
    def record_choice(session_id: int, depth: int, choice_id: str, trait_impact: str):
        with db.get_cursor() as (cursor, connection):
            cursor.execute("""
                INSERT INTO user_choices (session_id, depth, choice_id, trait_impact)
                VALUES (%s, %s, %s, %s)
            """, (session_id, depth, choice_id, trait_impact))
            connection.commit()
            return {"message": "Choice recorded"}
    
    @staticmethod
    def get_session_choices(session_id: int):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT * FROM user_choices 
                WHERE session_id = %s 
                ORDER BY depth
            """, (session_id,))
            return cursor.fetchall()

class ScenarioCRUD:
    @staticmethod
    def get_scenario(scenario_id: int):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT * FROM scenario 
                WHERE scenario_id = %s
            """, (scenario_id,))
            
            result = cursor.fetchone()
            if result:
                result['info'] = json.loads(result['info']) if result['info'] else {}
            return result
    
    @staticmethod
    def create_scenario(scenario_data):
        with db.get_cursor() as (cursor, connection):
            cursor.execute("""
                INSERT INTO scenario (info) 
                VALUES (%s)
            """, (json.dumps(scenario_data),))
            connection.commit()
            return {"scenario_id": cursor.lastrowid}
    
    @staticmethod
    def update_scenario(scenario_id: int, scenario_data):
        with db.get_cursor() as (cursor, connection):
            cursor.execute("""
                UPDATE scenario 
                SET info = %s 
                WHERE scenario_id = %s
            """, (json.dumps(scenario_data), scenario_id))
            connection.commit()
            return {"message": "Scenario updated"}
    
    @staticmethod
    def delete_scenario(scenario_id: int):
        with db.get_cursor() as (cursor, connection):
            cursor.execute("""
                DELETE FROM scenario 
                WHERE scenario_id = %s
            """, (scenario_id,))
            connection.commit()
            return {"message": "Scenario deleted"}
    
    @staticmethod
    def list_scenarios():
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("SELECT scenario_id FROM scenario")
            return cursor.fetchall()

class GeneratedScenarioCRUD:
    @staticmethod
    def save_generated_scenario(session_id: int, depth: int, scenario_json: dict):
        with db.get_cursor() as (cursor, connection):
            cursor.execute("""
                INSERT INTO generated_scenarios (session_id, depth, scenario_json)
                VALUES (%s, %s, %s)
            """, (session_id, depth, json.dumps(scenario_json)))
            connection.commit()
            return {"id": cursor.lastrowid}
    
    @staticmethod
    def get_generated_scenario(session_id: int, depth: int):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT * FROM generated_scenarios
                WHERE session_id = %s AND depth = %s
            """, (session_id, depth))
            
            result = cursor.fetchone()
            # Make sure to fetch all results to avoid "Unread result found" error
            cursor.fetchall()  # Consume any remaining results
            
            if result:
                result['scenario_json'] = json.loads(result['scenario_json'])
            return result
    
    @staticmethod
    def get_all_generated_scenarios(session_id: int):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT * FROM generated_scenarios
                WHERE session_id = %s
                ORDER BY depth
            """, (session_id,))
            
            scenarios = cursor.fetchall()
            for scenario in scenarios:
                scenario['scenario_json'] = json.loads(scenario['scenario_json'])
            return scenarios

class AnalyticsCRUD:
    @staticmethod
    def get_user_stats(user_id: int):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            # Get user data
            cursor.execute("""
                SELECT game_played, trait_profile 
                FROM user_info 
                WHERE userid = %s
            """, (user_id,))
            user_data = cursor.fetchone()
            
            # Get session stats
            cursor.execute("""
                SELECT mode, COUNT(*) as count, 
                       SUM(is_completed) as completed,
                       AVG(TIMESTAMPDIFF(MINUTE, started_at, ended_at)) as avg_duration
                FROM game_session 
                WHERE user_id = %s 
                GROUP BY mode
            """, (user_id,))
            session_stats = cursor.fetchall()
            
            # Get trait progression
            cursor.execute("""
                SELECT uc.trait_impact, COUNT(*) as count
                FROM user_choices uc
                JOIN game_session gs ON uc.session_id = gs.session_id
                WHERE gs.user_id = %s
                GROUP BY uc.trait_impact
            """, (user_id,))
            trait_impacts = cursor.fetchall()
            
            return {
                "user_data": user_data,
                "session_stats": session_stats,
                "trait_impacts": trait_impacts
            }
    
    @staticmethod
    def get_leaderboard(limit: int = 10):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT u.userid, u.username, u.game_played,
                       COUNT(DISTINCT gs.session_id) as total_sessions,
                       SUM(gs.is_completed) as completed_sessions,
                       u.trait_profile
                FROM user_info u
                LEFT JOIN game_session gs ON u.userid = gs.user_id
                WHERE u.is_active = TRUE
                GROUP BY u.userid
                ORDER BY u.game_played DESC, completed_sessions DESC
                LIMIT %s
            """, (limit,))
            
            leaderboard = cursor.fetchall()
            for entry in leaderboard:
                if entry['trait_profile']:
                    trait_profile = json.loads(entry['trait_profile'])
                    # Find dominant trait
                    if trait_profile:
                        dominant_trait = max(trait_profile.items(), key=lambda x: x[1])
                        entry['dominant_trait'] = dominant_trait[0]
                        entry['dominant_trait_value'] = dominant_trait[1]
                del entry['trait_profile']
            
            return leaderboard
    
    @staticmethod
    def get_choice_analytics(scenario_id: Optional[int] = None):
        with db.get_cursor(dictionary=True) as (cursor, connection):
            query = """
                SELECT uc.depth, uc.choice_id, uc.trait_impact, COUNT(*) as count
                FROM user_choices uc
                JOIN game_session gs ON uc.session_id = gs.session_id
            """
            params = []
            
            if scenario_id:
                query += " WHERE gs.scenario_id = %s"
                params.append(scenario_id)
            
            query += " GROUP BY uc.depth, uc.choice_id, uc.trait_impact"
            query += " ORDER BY uc.depth, uc.choice_id"
            
            cursor.execute(query, params)
            return cursor.fetchall()