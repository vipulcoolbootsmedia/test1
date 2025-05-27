import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API URL from environment variables, with fallback to localhost
API_URL = os.getenv("API_URL", "http://localhost:8000")

def make_request(method, endpoint, data=None, token=None):
    """Make request to API with improved debugging and error handling"""
    url = f"{API_URL}{endpoint}"
    
    print(f"Making {method} request to: {url}")  # Debug print
    
    headers = {}
    if token:
        # Ensure token has the Bearer prefix
        if not token.startswith("Bearer "):
            headers["Authorization"] = f"Bearer {token}"
        else:
            headers["Authorization"] = token
        # Print first 10 chars of token for debugging
        print(f"Using token: {headers['Authorization'][:15]}...")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            st.error(f"Unsupported method: {method}")
            return None
        
        # Debug response info
        print(f"Response status: {response.status_code}")
        
        # Log detailed info for non-200 responses
        if response.status_code >= 400:
            print(f"Error response: {response.text[:200]}...")
            
            # Handle common errors with user-friendly messages
            if response.status_code == 401:
                st.warning("Your session has expired. Please log in again.")
                # Clear token on 401 to force re-login
                if 'token' in st.session_state:
                    del st.session_state.token
            elif response.status_code == 403:
                st.error("You don't have permission to access this resource.")
            elif response.status_code == 404:
                st.error("The requested resource was not found.")
            elif response.status_code == 422:
                st.error("Validation error - please check your input.")
            elif response.status_code >= 500:
                st.error("Server error. Please try again later.")
        
        return response
        
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error details: {str(e)}")  # Detailed logging
        st.error(f"Failed to connect to API at {url}. Please make sure the API server is running.")
        return None
    except requests.exceptions.Timeout as e:
        print(f"Timeout error details: {str(e)}")  # Detailed logging
        st.error("API request timed out. The server may be experiencing high load.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error details: {str(e)}")  # Detailed logging
        st.error(f"Request error: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Detailed logging
        st.error(f"Unexpected error: {str(e)}")
        return None
    
# Initialize session state
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'current_path' not in st.session_state:
    st.session_state.current_path = ""
if 'current_scenario' not in st.session_state:
    st.session_state.current_scenario = None
if 'game_mode' not in st.session_state:
    st.session_state.game_mode = None


def login_page():
    """Login/Register page"""
    st.title("🎭 Psychological Thriller Game")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login"):
                # Fixed: Using the correct API format for token login
                response = requests.post(
                    f"{API_URL}/auth/login",
                    # For OAuth2, the correct format is form data, not JSON
                    data={
                        "username": username, 
                        "password": password
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Store the token properly
                    st.session_state.token = data["access_token"]
                    print(f"Token received and stored: {data['access_token'][:10]}...")
                    
                    # Get user info with the token
                    user_response = make_request(
                        "GET", 
                        "/users/me",
                        token=data["access_token"]  # Pass token explicitly
                    )
                    
                    if user_response and user_response.status_code == 200:
                        st.session_state.user = user_response.json()
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Could not retrieve user profile.")
                else:
                    error_msg = "Invalid credentials"
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            error_msg = error_data["detail"]
                    except:
                        pass
                    st.error(error_msg)
    
    with tab2:
        with st.form("register_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Register"):
                if password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    response = make_request("POST", "/auth/register", {
                        "username": username,
                        "email": email,
                        "password": password
                    })
                    
                    if response and response.status_code == 200:
                        st.success("Registration successful! Please login.")
                    else:
                        # Better error handling
                        try:
                            error_detail = response.json().get("detail", "Registration failed")
                            st.error(error_detail)
                        except:
                            st.error(f"Registration failed: {response.status_code if response else 'Connection error'}")

def game_selection_page():
    """Game mode selection page"""
    st.title("🎮 Select Game Mode")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📚 Learn Mode")
        st.write("Play through carefully crafted scenarios designed to test specific traits.")
        
        # Get available scenarios
        scenarios_response = make_request("GET", "/learn/scenarios", token=st.session_state.token)
        if scenarios_response and scenarios_response.status_code == 200:
            scenarios = scenarios_response.json()
            scenario_id = st.selectbox(
                "Select Scenario",
                options=[s["scenario_id"] for s in scenarios],
                format_func=lambda x: f"Scenario {x}"
            )
            
            if st.button("Start Learn Mode"):
                # Create session
                session_response = make_request(
                    "POST", 
                    "/sessions/", 
                    {
                        "mode": "learn",
                        "scenario_id": scenario_id
                    },
                    token=st.session_state.token
                )
                
                if session_response and session_response.status_code == 200:
                    st.session_state.session_id = session_response.json()["session_id"]
                    st.session_state.game_mode = "learn"
                    st.session_state.current_path = ""
                    st.rerun()
    
    with col2:
        st.subheader("🌱 Grow Mode")
        st.write("Experience dynamically generated scenarios powered by AI.")
        
        trait_focus = st.selectbox(
            "Select Trait Focus",
            ["bravery", "honesty", "curiosity", "empathy", "patience"]
        )
        
        if st.button("Start Grow Mode"):
            # Create session
            session_response = make_request(
                "POST", 
                "/sessions/", 
                {
                    "mode": "grow"
                },
                token=st.session_state.token
            )
            
            if session_response and session_response.status_code == 200:
                st.session_state.session_id = session_response.json()["session_id"]
                st.session_state.game_mode = "grow"
                st.session_state.trait_focus = trait_focus
                st.rerun()

def learn_game_page():
    """Learn mode gameplay"""
    st.title("📚 Learn Mode")
    
    if st.session_state.current_scenario is None:
        # Get starting scenario
        response = make_request(
            "GET",
            f"/learn/scenario/{st.session_state.session_id}/start",
            token=st.session_state.token
        )
        
        if response and response.status_code == 200:
            st.session_state.current_scenario = response.json()
        else:
            st.error("Failed to load scenario")
            return
    
    scenario = st.session_state.current_scenario
    
    # Display scenario
    st.header(f"Depth {scenario.get('depth', 1)}")
    
    # Scene narrative
    for narrative in scenario.get("scene_narrative", []):
        st.markdown(f"**{narrative['text']}**")
        if narrative.get("sfx"):
            st.caption(f"🔊 {narrative['sfx']}")
    
    # Check if game ended
    if scenario.get("is_end", False):
        st.balloons()
        st.success("🎭 The End!")
        
        # End session - Add this line to properly record game history
        end_response = make_request(
            "PATCH", 
            f"/sessions/{st.session_state.session_id}/end", 
            {"is_completed": True},
            token=st.session_state.token
        )
        
        # Optionally show a toast if you'd like to confirm session was saved
        if end_response and end_response.status_code == 200:
            st.toast("Session completed and saved!", icon="🎮")
        
        if st.button("Return to Menu"):
            st.session_state.session_id = None
            st.session_state.current_scenario = None
            st.session_state.game_mode = None
            st.rerun()
    else:
        # Display choices
        st.markdown("---")
        choices = scenario.get("choices", [])
        
        for choice in choices:
            trait_info = choice.get("maps_to_trait_details", {})
            
            if st.button(
                f"{choice['choice_id']}: {choice['choice_text']}",
                help=f"Affects {trait_info.get('trait', 'unknown')} ({trait_info.get('degree', 'unknown')})"
            ):
                # Record choice
                make_request(
                    "POST",
                    f"/learn/choice/{st.session_state.session_id}",
                    {
                        "depth": scenario["depth"],
                        "choice_id": choice["choice_id"],
                        "trait_impact": trait_info.get("degree", "moderate")
                    },
                    token=st.session_state.token
                )
                
                # Update path and get next scenario
                st.session_state.current_path += choice["choice_id"]
                
                response = make_request(
                    "POST",
                    f"/learn/scenario/{st.session_state.session_id}/by-path",
                    {"path": st.session_state.current_path},
                    token=st.session_state.token
                )
                
                if response and response.status_code == 200:
                    st.session_state.current_scenario = response.json()
                    st.rerun()

def grow_game_page():
    """Grow mode gameplay"""
    st.title("🌱 Grow Mode")
    
    depth = st.session_state.get("current_depth", 1)
    
    if st.session_state.current_scenario is None:
        # Generate first scenario
        with st.spinner("Generating scenario..."):
            response = make_request(
                "POST",
                f"/grow/scenario/{st.session_state.session_id}/generate",
                {
                    "depth": depth,
                    "trait_focus": st.session_state.get("trait_focus", "bravery"),
                    "previous_choices": st.session_state.get("previous_choices", [])
                },
                token=st.session_state.token
            )
            
            if response and response.status_code == 200:
                data = response.json()
                st.session_state.current_scenario = data["scenario"]
            else:
                st.error("Failed to generate scenario")
                return
    
    scenario = st.session_state.current_scenario
    
    # Display scenario
    st.header(f"Depth {scenario.get('depth', depth)}")
    
    # Scene narrative
    for narrative in scenario.get("scene_narrative", []):
        st.markdown(f"**{narrative['text']}**")
        if narrative.get("sfx"):
            st.caption(f"🔊 {narrative['sfx']}")
    
    # Check if game ended
    if scenario.get("is_end", False):
        st.balloons()
        st.success("🎭 The End!")
        
        # End session
        make_request(
            "PATCH", 
            f"/sessions/{st.session_state.session_id}/end", 
            {"is_completed": True},
            token=st.session_state.token
        )
        
        if st.button("Return to Menu"):
            st.session_state.session_id = None
            st.session_state.current_scenario = None
            st.session_state.game_mode = None
            st.rerun()
    else:
        # Display choices
        st.markdown("---")
        choices = scenario.get("choices", [])
        
        for choice in choices:
            trait_info = choice.get("maps_to_trait_details", {})
            
            if st.button(
                f"{choice['choice_id']}: {choice['choice_text']}",
                help=f"Affects {trait_info.get('trait', 'unknown')} ({trait_info.get('degree', 'unknown')})"
            ):
                # Record choice
                make_request(
                    "POST",
                    f"/grow/choice/{st.session_state.session_id}",
                    {
                        "depth": scenario["depth"],
                        "choice_id": choice["choice_id"],
                        "trait_impact": trait_info.get("degree", "moderate")
                    },
                    token=st.session_state.token
                )
                
                # Update state for next scenario
                if "previous_choices" not in st.session_state:
                    st.session_state.previous_choices = []
                st.session_state.previous_choices.append(choice["choice_id"])
                st.session_state.current_depth = depth + 1
                st.session_state.current_scenario = None
                st.rerun()

# Helper function to create a preview of game history
def create_history_preview(game_history, session_id):
    """Create a preview of game history for a session"""
    import json
    
    session_key = f"session_{session_id}"
    if session_key in game_history:
        session_data = game_history[session_key]
        
        # Create a simplified preview
        preview = {}
        
        # Add session info if available
        if "session_info" in session_data:
            info = session_data["session_info"]
            preview["duration"] = info.get("total_duration", "unknown")
        
        # Add choices summary
        depth_keys = [k for k in session_data.keys() if k.startswith("depth")]
        if depth_keys:
            choices = []
            for dk in sorted(depth_keys):
                choice = session_data[dk].get("choice_taken", "")
                if choice:
                    choices.append(choice)
            
            preview["choices"] = "→".join(choices)
        
        # Add results if available
        if "results" in session_data:
            results = session_data["results"]
            preview["score"] = results.get("session_score", 0)
            preview["ending"] = results.get("ending_achieved", "unknown")
        
        return json.dumps(preview, indent=None)
    
    return "No history available"

def display_recent_game_story():
    """Display the most recent game story in the profile"""
    user_response = make_request("GET", "/users/me", token=st.session_state.token)
    
    if user_response and user_response.status_code == 200:
        user_data = user_response.json()
        game_history = user_data.get("game_history", {})
        
        if game_history:
            # Get most recent session
            session_keys = sorted(
                [k for k in game_history.keys() if k.startswith("session_")],
                key=lambda x: game_history[x].get("session_info", {}).get("started_at", ""),
                reverse=True
            )
            
            if session_keys:
                recent_session = game_history[session_keys[0]]
                results = recent_session.get("results", {})
                
                if results.get("game_summary"):
                    st.subheader("📖 Your Latest Story")
                    st.markdown(f"*{results['game_summary']}*")
                    
                    # Show ending achieved
                    if results.get("ending_achieved"):
                        st.success(f"🏆 Latest Achievement: {results['ending_achieved']}")

def analytics_page():
    """Analytics dashboard with enhanced game summary display"""
    st.title("📊 Analytics Dashboard")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Personal Stats", "Game Stories", "Leaderboard", "Game Analytics"])
    
    with tab1:
        # Get user stats
        stats_response = make_request(
            "GET",
            f"/analytics/user/{st.session_state.user['userid']}/stats",
            token=st.session_state.token
        )
        
        if stats_response and stats_response.status_code == 200:
            stats = stats_response.json()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Games Played", stats["user_data"]["game_played"])
            
            with col2:
                st.metric("Sessions", len(stats.get("session_stats", [])))
            
            with col3:
                # Calculate average trait
                traits = stats["user_data"]["trait_profile"]
                
                # Parse JSON if it's a string
                if isinstance(traits, str):
                    import json
                    traits = json.loads(traits)
                
                avg_trait = sum(traits.values()) / len(traits) if traits else 0
                st.metric("Average Trait Score", f"{avg_trait:.1f}")
            
            # Trait profile chart
            if traits:  # Now 'traits' is guaranteed to be a dict
                traits_df = pd.DataFrame(
                    list(traits.items()),
                    columns=["Trait", "Value"]
                )
                
                fig = px.bar(
                    traits_df,
                    x="Trait",
                    y="Value",
                    title="Trait Profile",
                    color="Value",
                    color_continuous_scale="Blues"
                )
                st.plotly_chart(fig)
        
        # Session history
        st.subheader("Recent Sessions")
        
        # Get user's full profile with game history
        user_response = make_request("GET", "/users/me", token=st.session_state.token)
        
        # Get sessions list
        sessions_response = make_request(
            "GET",
            f"/sessions/user/{st.session_state.user['userid']}",
            token=st.session_state.token
        )
        
        if sessions_response and sessions_response.status_code == 200 and user_response and user_response.status_code == 200:
            sessions = sessions_response.json()
            user_data = user_response.json()
            game_history = user_data.get("game_history", {})
            
            if sessions:
                # Create a dataframe for sessions
                sessions_df = pd.DataFrame(sessions)
                sessions_df["started_at"] = pd.to_datetime(sessions_df["started_at"])
                
                # Add full game history JSON column
                sessions_df["game_history"] = sessions_df["session_id"].apply(
                    lambda sid: json.dumps(game_history.get(f"session_{sid}", {}), indent=2)
                )
                
                # Display the dataframe with the new column
                st.dataframe(
                    sessions_df[["session_id", "mode", "started_at", "is_completed", "game_history"]],
                    use_container_width=True
                )
    
    with tab2:
        # NEW TAB: Game Stories - Display AI-generated summaries
        st.subheader("🎭 Your Psychological Journey Stories")
        st.write("AI-generated narratives of your gameplay sessions")
        
        # Get user's full profile with game history
        user_response = make_request("GET", "/users/me", token=st.session_state.token)
        
        if user_response and user_response.status_code == 200:
            user_data = user_response.json()
            game_history = user_data.get("game_history", {})
            
            if game_history:
                # Sort sessions by most recent first
                session_keys = sorted(
                    [k for k in game_history.keys() if k.startswith("session_")],
                    key=lambda x: game_history[x].get("session_info", {}).get("started_at", ""),
                    reverse=True
                )
                
                for session_key in session_keys:
                    session_data = game_history[session_key]
                    session_info = session_data.get("session_info", {})
                    results = session_data.get("results", {})
                    
                    # Create an expandable section for each session
                    with st.expander(
                        f"🎮 {session_info.get('mode', 'Unknown').title()} Session - {results.get('ending_achieved', 'Unknown Ending')} ({session_info.get('total_duration', 'Unknown duration')})",
                        expanded=False
                    ):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            # Display AI-generated game summary
                            if results.get("game_summary"):
                                st.markdown("### 📖 Your Story")
                                st.markdown(f"*{results['game_summary']}*")
                            else:
                                st.info("No AI summary available for this session")
                        
                        with col2:
                            # Display session stats
                            st.markdown("### 📊 Session Stats")
                            st.metric("Score", results.get("session_score", 0))
                            st.metric("Duration", session_info.get("total_duration", "Unknown"))
                            
                            # Trait changes
                            trait_changes = results.get("trait_changes", {})
                            if trait_changes:
                                st.markdown("**Trait Changes:**")
                                for trait, change in trait_changes.items():
                                    st.write(f"• {trait.capitalize()}: {change}")
                        
                        # Show choice progression
                        st.markdown("### 🎯 Choice Progression")
                        depth_keys = sorted([k for k in session_data.keys() if k.startswith("depth")])
                        
                        choice_summary = []
                        for depth_key in depth_keys:
                            depth_data = session_data[depth_key]
                            choice_taken = depth_data.get("choice_taken")
                            if choice_taken:
                                # Find the choice details
                                chosen_choice = None
                                for choice in depth_data.get("choices", []):
                                    if choice["choice_id"] == choice_taken:
                                        chosen_choice = choice
                                        break
                                
                                if chosen_choice:
                                    choice_summary.append({
                                        "depth": depth_key.replace("depth", "Depth "),
                                        "choice": f"{choice_taken}: {chosen_choice['choice_text'][:60]}...",
                                        "impact": chosen_choice.get("maps_to_trait_details", {}).get("degree", "unknown")
                                    })
                        
                        if choice_summary:
                            choice_df = pd.DataFrame(choice_summary)
                            st.dataframe(choice_df, use_container_width=True, hide_index=True)
                        
                        st.markdown("---")
            else:
                st.info("No game sessions found. Play some games to see your stories here!")
    
    with tab3:
        # Leaderboard
        leaderboard_response = make_request("GET", "/analytics/leaderboard", token=st.session_state.token)
        
        if leaderboard_response and leaderboard_response.status_code == 200:
            leaderboard = leaderboard_response.json()
            
            if leaderboard:
                df = pd.DataFrame(leaderboard)
                
                # Create ranking chart
                fig = go.Figure(data=[
                    go.Bar(
                        x=df["username"],
                        y=df["game_played"],
                        text=df.get("dominant_trait", ""),
                        textposition="auto",
                        marker_color='lightblue'
                    )
                ])
                
                fig.update_layout(
                    title="Top Players by Games Played",
                    xaxis_title="Player",
                    yaxis_title="Games Played",
                    showlegend=False
                )
                
                st.plotly_chart(fig)
                
                # Detailed leaderboard table
                columns_to_show = ["username", "game_played", "completed_sessions"]
                if "dominant_trait" in df.columns:
                    columns_to_show.append("dominant_trait")
                st.dataframe(df[columns_to_show])
    
    with tab4:
        # Choice analytics
        st.subheader("Choice Distribution")
        
        choices_response = make_request("GET", "/analytics/choices/distribution", token=st.session_state.token)
        
        if choices_response and choices_response.status_code == 200:
            choices = choices_response.json()
            
            if choices:
                df = pd.DataFrame(choices)
                
                # Group by depth and choice
                if not df.empty and "depth" in df.columns and "choice_id" in df.columns:
                    depth_choices = df.groupby(["depth", "choice_id"])["count"].sum().reset_index()
                    
                    fig = px.bar(
                        depth_choices,
                        x="depth",
                        y="count",
                        color="choice_id",
                        title="Choices by Depth",
                        labels={"count": "Number of Times Chosen", "depth": "Story Depth"}
                    )
                    
                    st.plotly_chart(fig)
                
                # Trait impact distribution
                if "trait_impact" in df.columns:
                    trait_impact = df.groupby("trait_impact")["count"].sum().reset_index()
                    
                    fig2 = px.pie(
                        trait_impact,
                        values="count",
                        names="trait_impact",
                        title="Trait Impact Distribution"
                    )
                    
                    st.plotly_chart(fig2)

def profile_page():
    """User profile page with recent game story"""
    st.title("👤 Profile")
    
    user = st.session_state.user
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("User Information")
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Joined:** {user['created_at']}")
        st.write(f"**Games Played:** {user['game_played']}")
    
    with col2:
        st.subheader("Trait Profile")
        if user.get("trait_profile"):
            for trait, value in user["trait_profile"].items():
                st.progress(value / 100, text=f"{trait.capitalize()}: {value}")
    
    # Display recent game story
    st.markdown("---")
    display_recent_game_story()
    
    # Update profile section
    st.markdown("---")
    st.subheader("Update Profile")
    
    with st.form("update_profile"):
        new_email = st.text_input("Email", value=user["email"])
        
        if st.form_submit_button("Update"):
            response = make_request(
                "PATCH",
                f"/users/{user['userid']}",
                {"email": new_email},
                token=st.session_state.token
            )
            
            if response and response.status_code == 200:
                st.success("Profile updated successfully")
                # Refresh user data
                user_response = make_request("GET", "/users/me", token=st.session_state.token)
                if user_response and user_response.status_code == 200:
                    st.session_state.user = user_response.json()
                    st.rerun()

def main():
    """Main application"""
    st.set_page_config(
        page_title="Psychological Thriller Game",
        page_icon="🎭",
        layout="wide"
    )
    
    # Check authentication
    if not st.session_state.token:
        login_page()
        return
    
    # Get user info if we have token but no user data
    if st.session_state.token and not st.session_state.user:
        user_response = make_request("GET", "/users/me", token=st.session_state.token)
        if user_response and user_response.status_code == 200:
            st.session_state.user = user_response.json()
        else:
            # Token is invalid or expired, clear it and show login page
            st.session_state.token = None
            login_page()
            return
    
    # Sidebar navigation
    with st.sidebar:
        st.title(f"Welcome, {st.session_state.user['username']}!")
        
        if st.session_state.game_mode:
            # In-game navigation
            page = st.selectbox(
                "Navigation",
                ["Game", "Analytics", "Profile", "End Game"]
            )
            
            if page == "End Game":
                if st.button("Confirm End Game"):
                    # End current session
                    if st.session_state.session_id:
                        make_request(
                            "PATCH",
                            f"/sessions/{st.session_state.session_id}/end",
                            {"is_completed": False},
                            token=st.session_state.token
                        )
                    
                    # Reset game state
                    st.session_state.session_id = None
                    st.session_state.current_scenario = None
                    st.session_state.game_mode = None
                    st.session_state.current_path = ""
                    if "current_depth" in st.session_state:
                        st.session_state.current_depth = 1
                    if "previous_choices" in st.session_state:
                        st.session_state.previous_choices = []
                    st.rerun()
        else:
            # Main menu navigation
            page = st.selectbox(
                "Navigation",
                ["Play Game", "Analytics", "Profile", "Logout"]
            )
            
            if page == "Logout":
                if st.button("Confirm Logout"):
                    # Clear all session state
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
    
    # Route to appropriate page
    if st.session_state.game_mode == "learn":
        if page == "Game":
            learn_game_page()
        elif page == "Analytics":
            analytics_page()
        elif page == "Profile":
            profile_page()
    elif st.session_state.game_mode == "grow":
        if page == "Game":
            grow_game_page()
        elif page == "Analytics":
            analytics_page()
        elif page == "Profile":
            profile_page()
    else:
        if page == "Play Game":
            game_selection_page()
        elif page == "Analytics":
            analytics_page()
        elif page == "Profile":
            profile_page()

if __name__ == "__main__":
    main()