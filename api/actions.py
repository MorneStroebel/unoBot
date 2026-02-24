from api.client import get, post
from core.state import save_state
from config.settings import BOT_FIRST_NAME, BOT_LAST_NAME, IS_SANDBOX_MODE, MAC_ADDRESS, PLAYER_NAME, ONLY_PLAYERS_MODE


# -----------------------------
# Room actions
# -----------------------------
def get_room_id():
    """Get the first available room or create a new sandbox room."""
    resp = get("/rooms/list")
    rooms = resp.json()
    if rooms:
        return rooms[0]["id"]
    # Fallback: create sandbox
    resp = post("/rooms", {"isSandbox": IS_SANDBOX_MODE})
    room_id = resp.json().get("roomId")
    return room_id


def join_room(room_id, only_players=False):
    """Join a specific room.
    
    Args:
        room_id: The room ID to join
        only_players: If True (and sandbox), no system bots will be added
    """
    payload = {
        "firstName": BOT_FIRST_NAME,
        "lastName": BOT_LAST_NAME,
        "MAC": MAC_ADDRESS,
        "isSandbox": IS_SANDBOX_MODE,
        "onlyPlayers": ONLY_PLAYERS_MODE
    }
    if only_players:
        payload["onlyPlayers"] = True

    resp = post(f"/rooms/{room_id}/join", payload)
    if resp.status_code != 200:
        print("Joining room failed: ", resp.json()["error"])
        return None
    player_id = resp.json()["playerId"]
    save_state(room_id, player_id)
    print(f"✅ Joined room {room_id} as {player_id}")
    return player_id


def find_and_join_room(player_name, only_players=False):
    """Find a room by player name and join it (sandbox only).
    
    Args:
        player_name: Name of player to search for
        only_players: If True, no system bots will be added
    """
    payload = {
        "playerName": player_name,
        "isSandbox": True,
        "firstName": BOT_FIRST_NAME,
        "lastName": BOT_LAST_NAME,
        "MAC": MAC_ADDRESS
    }
    if only_players:
        payload["onlyPlayers"] = True

    resp = post("/rooms/find-join", payload)
    result = resp.json()
    save_state(result["roomId"], result["playerId"])
    print(f"✅ Found and joined room {result['roomId']} as {result['playerId']}")
    return result["roomId"], result["playerId"]


def get_room_state(room_id, player_id=None):
    """Get the current state of a room.
    
    Args:
        room_id: The room ID
        player_id: Optional player ID to include your hand in response
    """
    endpoint = f"/rooms/{room_id}"
    if player_id:
        endpoint += f"?playerId={player_id}"
    resp = get(endpoint)
    return resp.json()


def is_player_in_room(room_id, player_id):
    """Check if a player is still in a room."""
    resp = get(f"/rooms/{room_id}")
    if resp.status_code != 200:
        return False
    players = resp.json().get("players", [])
    return any(p["id"] == player_id for p in players)


def leave_room(room_id, player_id):
    """Leave a room (only allowed in WAITING or ENDED status)."""
    payload = {"playerId": player_id}
    resp = post(f"/rooms/{room_id}/leave", payload)
    return resp.json()


def get_leaderboard(sandbox=False):
    """Get the leaderboard.
    
    Args:
        sandbox: If True, get sandbox leaderboard
    """
    endpoint = "/leaderboard"
    if sandbox:
        endpoint += "?sandbox=true"
    resp = get(endpoint)
    return resp.json()


# -----------------------------
# Gameplay actions
# -----------------------------
def play_card(room_id, player_id, card_index, wild_color=None):
    """Play a card from your hand.
    
    Args:
        room_id: The room ID
        player_id: Your player ID
        card_index: Index of card in hand to play
        wild_color: Required for wild cards (RED, BLUE, GREEN, YELLOW)
    """
    payload = {"playerId": player_id, "cardIndex": card_index}
    if wild_color:
        payload["wildColor"] = wild_color
    resp = post(f"/rooms/{room_id}/play", payload)
    return resp.json()


def draw_card(room_id, player_id):
    """Draw a card from the deck."""
    payload = {"playerId": player_id}
    resp = post(f"/rooms/{room_id}/draw", payload)
    return resp.json()


def call_uno(room_id, player_id):
    """Call UNO! Must be done before playing second-to-last card."""
    payload = {"playerId": player_id}
    resp = post(f"/rooms/{room_id}/uno", payload)
    return resp.json()


def pass_turn(room_id, player_id):
    """Pass your turn (only possible after drawing a card)."""
    payload = {"playerId": player_id}
    resp = post(f"/rooms/{room_id}/pass", payload)
    return resp.json()


def catchout(room_id, challenger_id, target_id):
    """Challenge a player who didn't call UNO.
    
    Args:
        room_id: The room ID
        challenger_id: Your player ID
        target_id: The player ID you're challenging
    """
    payload = {"challengerId": challenger_id, "targetId": target_id}
    resp = post(f"/rooms/{room_id}/catchout", payload)
    return resp.json()
