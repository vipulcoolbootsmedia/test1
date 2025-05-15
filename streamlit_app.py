import streamlit as st
import requests
import json

# API base URL
API_URL = "http://localhost:8000"

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'current_path' not in st.session_state:
    st.session_state.current_path = ""
if 'current_scenario' not in st.session_state:
    st.session_state.current_scenario = None
if 'game_active' not in st.session_state:
    st.session_state.game_active = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = 1  # Default user
if 'scenario_id' not in st.session_state:
    st.session_state.scenario_id = 1  # Default scenario

st.title("🎭 Psychological Thriller - Learn Module Tester")
st.markdown("---")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.session_state.user_id = st.number_input("User ID", min_value=1, value=1)
    st.session_state.scenario_id = st.number_input("Scenario ID", min_value=1, value=1)
    
    if st.button("🚀 Start New Game"):
        # Start a new session
        response = requests.post(f"{API_URL}/session/start", json={
            "user_id": st.session_state.user_id,
            "mode": "learn",
            "scenario_id": st.session_state.scenario_id
        })
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.session_id = data['session_id']
            st.session_state.current_path = ""
            st.session_state.game_active = True
            st.success(f"Game started! Session ID: {st.session_state.session_id}")
            st.rerun()
        else:
            st.error(f"Error starting game: {response.json()}")
    
    if st.session_state.session_id:
        st.info(f"Current Session: {st.session_state.session_id}")
        st.info(f"Current Path: {st.session_state.current_path or 'Start'}")
    
    st.markdown("---")
    st.header("📊 Debug Info")
    if st.checkbox("Show Raw Scenario Data"):
        st.json(st.session_state.current_scenario)

# Main game area
if st.session_state.game_active and st.session_state.session_id:
    # Get current scenario
    if st.session_state.current_scenario is None:
        # Get starting scenario
        response = requests.get(f"{API_URL}/learn/scenario/{st.session_state.session_id}/start")
        if response.status_code == 200:
            st.session_state.current_scenario = response.json()
        else:
            st.error(f"Error loading scenario: {response.json()}")
            st.stop()
    
    # Display current scenario
    scenario = st.session_state.current_scenario
    
    # Scene header
    st.header(f"🎬 Scene {scenario.get('depth', 1)}")
    
    # Display narrative purpose
    if 'narrative_purpose' in scenario:
        st.caption(f"*{scenario['narrative_purpose']}*")
    
    # Display scene narrative
    if 'scene_narrative' in scenario:
        for narrative in scenario['scene_narrative']:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{narrative['text']}**")
            with col2:
                if narrative.get('sfx'):
                    st.caption(f"🔊 {narrative['sfx']}")
    
    # Display image prompt (if available)
    if 'image_gen_prompt' in scenario:
        with st.expander("🖼️ Scene Visualization"):
            st.info(scenario['image_gen_prompt'])
    
    # Check if game has ended
    if scenario.get('is_end', False):
        st.balloons()
        st.success("🎭 The End!")
        st.markdown("---")
        
        # Show final stats
        st.subheader("📊 Your Journey")
        st.write(f"Final Path: {st.session_state.current_path}")
        st.write(f"Depth Reached: {scenario.get('depth', 5)}")
        
        if st.button("🔄 Play Again"):
            st.session_state.session_id = None
            st.session_state.current_path = ""
            st.session_state.current_scenario = None
            st.session_state.game_active = False
            st.rerun()
    else:
        # Display choices
        st.markdown("---")
        st.subheader("🤔 What will you do?")
        
        choices = scenario.get('choices', [])
        
        # Create columns for choices
        cols = st.columns(len(choices))
        
        for idx, (choice, col) in enumerate(zip(choices, cols)):
            with col:
                # Show trait impact
                trait_info = choice.get('maps_to_trait_details', {})
                trait = trait_info.get('trait', 'unknown')
                degree = trait_info.get('degree', 'unknown')
                
                # Create styled button
                button_text = f"{choice['choice_id']}: {choice['choice_text']}"
                
                if st.button(button_text, key=f"choice_{idx}", 
                           help=f"Affects {trait} ({degree})"):
                    
                    # Record the choice
                    choice_response = requests.post(f"{API_URL}/learn/choice", json={
                        "session_id": st.session_state.session_id,
                        "depth": scenario['depth'],
                        "choice_id": choice['choice_id'],
                        "trait_impact": degree
                    })
                    
                    if choice_response.status_code == 200:
                        # Update path
                        st.session_state.current_path += choice['choice_id']
                        
                        # Get next scenario
                        path_response = requests.post(
                            f"{API_URL}/learn/scenario/{st.session_state.session_id}/by-path",
                            json={"path": st.session_state.current_path}
                        )
                        
                        if path_response.status_code == 200:
                            st.session_state.current_scenario = path_response.json()
                            st.rerun()
                        else:
                            st.error(f"Error getting next scenario: {path_response.json()}")
                    else:
                        st.error(f"Error recording choice: {choice_response.json()}")
                
                # Show hidden message in expander
                if 'short_hidden_message' in choice:
                    with st.expander(f"🔮 Hidden Insight ({choice['choice_id']})"):
                        st.caption(choice['short_hidden_message'])

else:
    # Welcome screen
    st.markdown("""
    ## 🎮 Welcome to the Learn Module Tester!
    
    This application allows you to play through the Learn module scenarios interactively.
    
    ### How to Play:
    1. Set your User ID and Scenario ID in the sidebar
    2. Click "Start New Game" to begin
    3. Read the scenario and make choices
    4. Continue until you reach the end
    
    ### Features:
    - 📖 Interactive story progression
    - 🎭 Character trait tracking
    - 🔮 Hidden insights for each choice
    - 📊 Debug information available
    
    **Click "Start New Game" in the sidebar to begin!**
    """)

# Footer
st.markdown("---")
st.caption("🎭 Psychological Thriller Game - Learn Module Tester v1.0")