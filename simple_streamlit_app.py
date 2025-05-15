import streamlit as st
import requests

API_URL = "http://localhost:8000"

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'path' not in st.session_state:
    st.session_state.path = ""
if 'scenario' not in st.session_state:
    st.session_state.scenario = None

st.title("🎭 Learn Module - Story Player")

# Start game button
if not st.session_state.session_id:
    user_id = st.number_input("User ID", value=1)
    scenario_id = st.number_input("Scenario ID", value=1)
    
    if st.button("Start Game"):
        response = requests.post(f"{API_URL}/session/start", json={
            "user_id": user_id,
            "mode": "learn",
            "scenario_id": scenario_id
        })
        
        if response.status_code == 200:
            st.session_state.session_id = response.json()['session_id']
            st.rerun()

# Game play area
if st.session_state.session_id:
    # Get scenario
    if st.session_state.scenario is None:
        response = requests.get(f"{API_URL}/learn/scenario/{st.session_state.session_id}/start")
        st.session_state.scenario = response.json()
    
    scenario = st.session_state.scenario
    
    # Display scene
    st.header(f"Scene {scenario.get('depth', 1)}")
    
    # Show narrative
    for narrative in scenario.get('scene_narrative', []):
        st.write(f"**{narrative['text']}** *({narrative.get('sfx', '')})*")
    
    # Check if ended
    if scenario.get('is_end', False):
        st.success("The End!")
        if st.button("Play Again"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
    else:
        # Show choices
        st.write("---")
        for choice in scenario.get('choices', []):
            if st.button(f"{choice['choice_id']}: {choice['choice_text']}"):
                # Record choice
                requests.post(f"{API_URL}/learn/choice", json={
                    "session_id": st.session_state.session_id,
                    "depth": scenario['depth'],
                    "choice_id": choice['choice_id'],
                    "trait_impact": choice['maps_to_trait_details']['degree']
                })
                
                # Update path and get next scenario
                st.session_state.path += choice['choice_id']
                response = requests.post(
                    f"{API_URL}/learn/scenario/{st.session_state.session_id}/by-path",
                    json={"path": st.session_state.path}
                )
                
                st.session_state.scenario = response.json()
                st.rerun()