import json
import os

STATE_FILE = "state.json"

def save_state(room_id, player_id):
    with open(STATE_FILE, "w") as f:
        json.dump({"roomId": room_id, "playerId": player_id}, f)

def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        return json.load(f)