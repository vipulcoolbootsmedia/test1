from fastapi import FastAPI, HTTPException
from schemas import *
from crud import *
from fastapi import Path

app = FastAPI()

# 1. Create user
@app.post("/user/create")
def create_user(user: UserCreate):
    return create_user_in_db(user)

@app.get("/user/{userid}")
def get_user(userid: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_info WHERE userid = %s", (userid,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# 2. Start session
@app.post("/session/start")
def start_session(data: StartSession):
    return start_game_session(data)

# 3. Get static scenario
@app.get("/learn/scenario/{depth}")
def get_scenario(depth: int):
    return get_static_scenario(depth)

# 4. Submit choice in learn
@app.post("/learn/choice")
def make_choice(choice: ChoiceInput):
    return record_choice(choice)

# 5. Generate scenario (grow)
@app.post("/grow/scenario/generate")
def generate_grow_scenario(data: GenerateScenarioInput):
    return generate_scenario_in_db(data)

# 6. Get grow scenario
@app.get("/grow/scenario/{session_id}/{depth}")
def get_generated(session_id: int, depth: int):
    return get_generated_scenario(session_id, depth)

# 7. Submit choice in grow
@app.post("/grow/choice")
def submit_grow_choice(choice: ChoiceInput):
    return record_choice(choice)

# 8. Update user trait profile
@app.patch("/user/{user_id}/update-traits")
def update_traits(user_id: int = Path(...), traits: UpdateTraitProfile = ...):
    return update_user_traits(user_id, traits.trait_profile)

# 9. Increment games played
@app.patch("/user/{user_id}/add-game")
def add_game(user_id: int, game_data: AddGameData):
    return add_game_to_user(user_id, game_data.game_id, game_data.game_data)

# 10. Get game history
@app.get("/user/{user_id}/games")
def get_user_history(user_id: int):
    return get_user_game_history(user_id)

# 11. Get session details
@app.get("/session/{session_id}/info")
def get_session_info(session_id: int):
    return get_session_data(session_id)
