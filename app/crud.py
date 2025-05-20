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
                json.dumps(user_data.trait_profile),
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
    def update_user_game_history(user_id: int, game_history_data: dict):
        """Update user's game history JSON field"""
        with db.get_cursor() as (cursor, connection):
            cursor.execute("""
                UPDATE user_info
                SET game_history = %s
                WHERE userid = %s
            """, (json.dumps(game_history_data), user_id))
            connection.commit()
            return {"message": "Game history updated successfully"}
    
    @staticmethod
    def update_user_traits(user_id: int, trait_updates: dict):
        """Update specific user traits based on choices"""
        with db.get_cursor() as (cursor, connection):
            # Get current trait profile
            cursor.execute("SELECT trait_profile FROM user_info WHERE userid = %s", (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                trait_profile = json.loads(result[0])
                
                # Update traits
                for trait, change in trait_updates.items():
                    if trait in trait_profile:
                        # Ensure trait values stay within bounds (0-100)
                        trait_profile[trait] = max(0, min(100, trait_profile[trait] + change))
                
                # Update in database
                cursor.execute("""
                    UPDATE user_info 
                    SET trait_profile = %s 
                    WHERE userid = %s
                """, (json.dumps(trait_profile), user_id))
                connection.commit()
                return {"message": "Traits updated successfully"}
            return {"error": "User not found or trait profile is empty"}
    
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
    
    @staticmethod
    def increment_games_played(user_id: int):
        """Increment the games_played counter for a user"""
        with db.get_cursor() as (cursor, connection):
            cursor.execute("""
                UPDATE user_info
                SET game_played = game_played + 1
                WHERE userid = %s
            """, (user_id,))
            connection.commit()
            return {"message": "Games played counter incremented"}

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
    
    @staticmethod
    def get_session_with_details(session_id: int):
        """Get session with all related details for game history"""
        with db.get_cursor(dictionary=True) as (cursor, connection):
            # Get session info
            cursor.execute("""
                SELECT gs.*, u.username 
                FROM game_session gs
                JOIN user_info u ON gs.user_id = u.userid
                WHERE gs.session_id = %s
            """, (session_id,))
            
            session = cursor.fetchone()
            if not session:
                return None
            
            # Get choices
            cursor.execute("""
                SELECT * FROM user_choices
                WHERE session_id = %s
                ORDER BY depth, created_at
            """, (session_id,))
            
            session['choices'] = cursor.fetchall()
            
            return session

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
    
    @staticmethod
    def get_choice_details(session_id: int, depth: int):
        """Get detailed information about a specific choice"""
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT * FROM user_choices 
                WHERE session_id = %s AND depth = %s
            """, (session_id, depth))
            return cursor.fetchone()
    
    @staticmethod
    def get_choice_impacts(session_id: int):
        """Get trait impacts from all choices in a session"""
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT trait_impact, COUNT(*) as count
                FROM user_choices 
                WHERE session_id = %s
                GROUP BY trait_impact
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
    
    @staticmethod
    def get_scenario_metadata(scenario_id: int):
        """Get the metadata for a scenario"""
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT * FROM scenario_metadata
                WHERE scenario_id = %s
            """, (scenario_id,))
            return cursor.fetchone()

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
    
    @staticmethod
    def record_session_analytics(session_id: int, analytics_data: dict):
        """Record analytics for a completed session"""
        with db.get_cursor() as (cursor, connection):
            cursor.execute("""
                INSERT INTO session_analytics 
                (session_id, total_choices, average_response_time, trait_focus, trait_changes, session_score)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                session_id,
                analytics_data.get("total_choices", 0),
                analytics_data.get("average_response_time", 0),
                analytics_data.get("trait_focus", ""),
                json.dumps(analytics_data.get("trait_changes", {})),
                analytics_data.get("session_score", 0)
            ))
            connection.commit()
            return {"id": cursor.lastrowid}
    
    @staticmethod
    def get_user_progress_over_time(user_id: int):
        """Get user trait progress over time through multiple sessions"""
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT gs.session_id, gs.started_at, gs.ended_at, 
                       JSON_EXTRACT(u.game_history, CONCAT('$.session_', gs.session_id, '.results.trait_changes')) as trait_changes
                FROM game_session gs
                JOIN user_info u ON gs.user_id = u.userid
                WHERE gs.user_id = %s AND gs.is_completed = TRUE
                ORDER BY gs.started_at
            """, (user_id,))
            
            return cursor.fetchall()

class AchievementCRUD:
    @staticmethod
    def list_achievements():
        """List all available achievements"""
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("SELECT * FROM achievements")
            return cursor.fetchall()
    
    @staticmethod
    def get_user_achievements(user_id: int):
        """Get all achievements for a user"""
        with db.get_cursor(dictionary=True) as (cursor, connection):
            cursor.execute("""
                SELECT a.*, ua.unlocked_at
                FROM achievements a
                JOIN user_achievements ua ON a.achievement_id = ua.achievement_id
                WHERE ua.user_id = %s
                ORDER BY ua.unlocked_at
            """, (user_id,))
            return cursor.fetchall()
    
    @staticmethod
    def unlock_achievement(user_id: int, achievement_id: int):
        """Unlock an achievement for a user"""
        with db.get_cursor() as (cursor, connection):
            # Check if already unlocked
            cursor.execute("""
                SELECT * FROM user_achievements
                WHERE user_id = %s AND achievement_id = %s
            """, (user_id, achievement_id))
            
            if cursor.fetchone():
                return {"message": "Achievement already unlocked"}
            
            # Unlock achievement
            cursor.execute("""
                INSERT INTO user_achievements (user_id, achievement_id)
                VALUES (%s, %s)
            """, (user_id, achievement_id))
            connection.commit()
            return {"message": "Achievement unlocked"}
    
    @staticmethod
    def check_achievement_eligibility(user_id: int):
        """Check if user is eligible for any new achievements"""
        with db.get_cursor(dictionary=True) as (cursor, connection):
            # Get user stats
            cursor.execute("""
                SELECT game_played, trait_profile FROM user_info
                WHERE userid = %s
            """, (user_id,))
            
            user_stats = cursor.fetchone()
            if not user_stats:
                return {"eligible_achievements": []}
            
            # Get completed sessions
            cursor.execute("""
                SELECT COUNT(*) as completed_sessions FROM game_session
                WHERE user_id = %s AND is_completed = TRUE
            """, (user_id,))
            
            session_stats = cursor.fetchone()
            
            # Get already unlocked achievements
            cursor.execute("""
                SELECT achievement_id FROM user_achievements
                WHERE user_id = %s
            """, (user_id,))
            
            unlocked = [row["achievement_id"] for row in cursor.fetchall()]
            
            # Check achievements based on criteria
            cursor.execute("""
                SELECT * FROM achievements
                WHERE achievement_id NOT IN (%s)
            """, (",".join(map(str, unlocked)) if unlocked else "0"))
            
            eligible = []
            for achievement in cursor.fetchall():
                # This is where you'd implement logic for checking eligibility
                # based on achievement criteria and user stats
                pass
            
            return {"eligible_achievements": eligible}