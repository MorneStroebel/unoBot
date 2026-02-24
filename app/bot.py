import signal
import sys

from api.actions import get_room_id, join_room, is_player_in_room
from api.socket_listener import SocketListener
from core.state import load_state
from strategies.loader import load_strategy
from config.settings import ACTIVE_STRATEGY, ONLY_PLAYERS_MODE

# -----------------------------
# Graceful shutdown
# -----------------------------
listener = None


def handle_exit(sig, frame):
    print("\n🛑 Shutting down bot gracefully...")
    if listener:
        listener.disconnect()
    sys.exit(0)


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


# -----------------------------
# Main bot runner
# -----------------------------
def start_bot():
    global listener

    state = load_state()
    if state and is_player_in_room(state["roomId"], state["playerId"]):
        room_id = state["roomId"]
        player_id = state["playerId"]
        print("🔁 Player exists in room, reconnecting")
    else:
        print("🆕 Player not in room, joining again")
        room_id = get_room_id()
        player_id = join_room(room_id, ONLY_PLAYERS_MODE)

    # Load strategy from config
    print(f"🧠 Loading strategy: {ACTIVE_STRATEGY}")
    strategy = load_strategy(ACTIVE_STRATEGY)

    # Start socket listener
    listener = SocketListener(room_id, player_id, strategy)
    listener.connect()

    print("🤖 Bot active and waiting for game events...")

    # Block and wait for events
    listener.wait()
