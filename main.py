from fastapi import FastAPI, HTTPException
from schemas import *
from crud import *

app = FastAPI(title="Psychological Thriller Game API")

# User Endpoints
@app.post("/user/create", response_model=dict)
def create_user(user: UserCreate):
    return create_user_in_db(user)

@app.get("/user/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.patch("/user/{user_id}/update-traits", response_model=dict)
def update_traits(user_id: int, traits: UpdateTraitProfile):
    result = update_user_traits(user_id, traits.trait_profile)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.patch("/user/{user_id}/add-game", response_model=dict)
def add_game(user_id: int, game_data: AddGameData):
    result = add_game_to_user(user_id, game_data.game_id, game_data.game_data)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

# Session Endpoints
@app.post("/session/start", response_model=SessionResponse)
def start_session(session: SessionStart):
    result = start_game_session(session.user_id, session.mode, session.scenario_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/session/{session_id}", response_model=dict)
def get_session(session_id: int):
    result = get_session_details(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

# Learn Module Endpoints
@app.get("/learn/scenario/{session_id}/start", response_model=dict)
def get_learn_start(session_id: int):
    """Get starting scenario for a learn session"""
    result = get_scenario_for_session(session_id, "")
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.post("/learn/scenario/{session_id}/by-path", response_model=dict)
def get_scenario_by_path(session_id: int, request: PathRequest):
    """Get scenario at specific path for this session"""
    result = get_scenario_for_session(session_id, request.path)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.post("/learn/choice", response_model=dict)
def make_learn_choice(choice: LearnChoice):
    """Record user's choice in learn mode"""
    result = record_choice(choice)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

# Grow Module Endpoints
@app.post("/grow/scenario/generate", response_model=dict)
def generate_grow_scenario(data: GenerateScenarioInput):
    """Generate and store a new scenario"""
    result = generate_scenario_in_db(data)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/grow/scenario/{session_id}/{depth}", response_model=dict)
def get_generated(session_id: int, depth: int):
    """Get a generated scenario by session and depth"""
    result = get_generated_scenario(session_id, depth)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.post("/grow/choice", response_model=dict)
def submit_grow_choice(choice: GrowChoice):
    """Record user's choice in grow mode"""
    result = record_choice(choice)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

# Analytics Endpoints
@app.get("/user/{user_id}/history", response_model=list)
def get_user_game_history(user_id: int):
    """Get all sessions played by a user"""
    return get_user_history(user_id)

@app.get("/session/{session_id}/choices", response_model=list)
def get_session_choice_history(session_id: int):
    """Get all choices made in a session"""
    return get_session_choices(session_id)

@app.get("/grow/scenarios/{session_id}", response_model=list)
def get_all_generated_scenarios(session_id: int):
    """Get all generated scenarios for a grow session"""
    return get_session_generated_scenarios(session_id)

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Psychological Thriller Game API",
        "version": "1.0",
        "modules": ["learn", "grow", "analytics"]
    }