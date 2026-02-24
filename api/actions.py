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


def join_room(room_id, only_players=None):
    """Join a specific room.

    Args:
        room_id: The room ID to join
        only_players: If True, no system bots will be added. If None, uses ONLY_PLAYERS_MODE

    Returns:
        player_id if successful, None otherwise
    """
    # Use global setting if only_players not specified
    if only_players is None:
        only_players = ONLY_PLAYERS_MODE

    payload = {
        "firstName": BOT_FIRST_NAME,
        "lastName": BOT_LAST_NAME,
        "MAC": MAC_ADDRESS,
        "isSandbox": IS_SANDBOX_MODE,
        "onlyPlayers": only_players
    }

    resp = post(f"/rooms/{room_id}/join", payload)
    if resp.status_code != 200:
        error = resp.json().get("error", "Unknown error")
        print(f"❌ Joining room failed: {error}")
        return None
    player_id = resp.json()["playerId"]
    save_state(room_id, player_id)
    print(f"✅ Joined room {room_id} as {player_id}")
    return player_id


def find_and_join_room(player_name, only_players=None):
    """Find a room by player name and join it (sandbox only).

    Args:
        player_name: Name of player to search for (string) or list of players
        only_players: If True, no system bots will be added. If None, uses ONLY_PLAYERS_MODE

    Returns:
        Dict with result containing roomId and playerId, or error
    """
    # Handle list of players - use first player for search
    if isinstance(player_name, list):
        if not player_name:
            raise ValueError("player_name list cannot be empty")
        player_name = player_name[0]

    # Use global setting if only_players not specified
    if only_players is None:
        only_players = ONLY_PLAYERS_MODE

    payload = {
        "playerName": player_name,
        "isSandbox": True,
        "firstName": BOT_FIRST_NAME,
        "lastName": BOT_LAST_NAME,
        "MAC": MAC_ADDRESS,
        "onlyPlayers": only_players
    }

    resp = post("/rooms/find-join", payload)
    result = resp.json()

    if resp.status_code != 200:
        print(f"❌ Find and join failed: {result.get('error', 'Unknown error')}")
        return result

    if result.get("roomId") and result.get("playerId"):
        save_state(result["roomId"], result["playerId"])
        print(f"✅ Found and joined room {result['roomId']} as {result['playerId']}")

    return result


def leave_room(room_id, player_id):
    """Leave a room.

    Args:
        room_id: The room ID to leave
        player_id: Your player ID

    Returns:
        Result dict if successful, None otherwise

    Note:
        Can only leave rooms in WAITING or ENDED status.
        Cannot leave during active games.
    """
    payload = {
        "playerId": player_id
    }

    resp = post(f"/rooms/{room_id}/leave", payload)
    result = resp.json()

    if resp.status_code != 200:
        error = result.get("error", "Unknown error")
        print(f"❌ Leave room failed: {error}")
        return None

    print(f"✅ Left room {room_id}")
    return result


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
    """Check if a player is in a specific room."""
    try:
        room_state = get_room_state(room_id, player_id)
        if room_state and room_state.get("result"):
            players = room_state["result"].get("players", [])
            return any(p.get("id") == player_id for p in players)
    except Exception:
        pass
    return False


def get_leaderboard(sandbox=True):
    """Get the leaderboard.

    Args:
        sandbox: If True, get sandbox leaderboard. If False, get competitive leaderboard.

    Returns:
        Response dict with leaderboard data
    """
    endpoint = "/leaderboard"
    if sandbox:
        endpoint += "?sandbox=true"

    resp = get(endpoint)
    return resp.json()


# -----------------------------
# Game actions
# -----------------------------
def play_card(room_id, player_id, card_index, wild_color=None):
    """Play a card from your hand.

    Args:
        room_id: The room ID
        player_id: Your player ID
        card_index: Index of card in your hand to play
        wild_color: If playing a wild card, specify color (RED, BLUE, GREEN, YELLOW)

    Returns:
        Response dict with result or error
    """
    payload = {
        "playerId": player_id,
        "cardIndex": card_index
    }
    if wild_color:
        payload["wildColor"] = wild_color

    resp = post(f"/rooms/{room_id}/play", payload)
    return resp.json()


def draw_card(room_id, player_id):
    """Draw a card from the deck.

    Args:
        room_id: The room ID
        player_id: Your player ID

    Returns:
        Response dict with drawn card or error
    """
    payload = {"playerId": player_id}
    resp = post(f"/rooms/{room_id}/draw", payload)
    return resp.json()


def pass_turn(room_id, player_id):
    """Pass your turn after drawing a card.

    Args:
        room_id: The room ID
        player_id: Your player ID

    Returns:
        Response dict with result or error

    Note:
        Can only pass after drawing a card that cannot be played.
    """
    payload = {"playerId": player_id}
    resp = post(f"/rooms/{room_id}/pass", payload)
    return resp.json()


def call_uno(room_id, player_id):
    """Call UNO when you have one card left.

    Args:
        room_id: The room ID
        player_id: Your player ID

    Returns:
        Response dict with result or error
    """
    payload = {"playerId": player_id}
    resp = post(f"/rooms/{room_id}/uno", payload)
    return resp.json()


def catchout(room_id, challenger_id, target_id):
    """Challenge another player for not calling UNO.

    Args:
        room_id: The room ID
        challenger_id: Your player ID (the one issuing the challenge)
        target_id: The player ID to challenge

    Returns:
        Response dict with result or error

    Note:
        If successful, target draws 2 cards.
        If unsuccessful (they did call UNO), you draw 2 cards.
    """
    payload = {
        "challengerId": challenger_id,
        "targetId": target_id
    }
    resp = post(f"/rooms/{room_id}/catchout", payload)
    return resp.json()