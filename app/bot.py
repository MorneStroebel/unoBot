import signal
import sys
import threading
import time
import atexit

from api.socket_listener import SocketListener
from core.room_manager import RoomManager
from core.state import save_state
from strategies.loader import load_strategy
from stats.tracker import StatsTracker
from app.prompts import (
    display_startup_banner,
    prompt_room_mode,
    prompt_post_game_action,
    prompt_continue_after_game,
    prompt_strategy_change,
    display_game_summary
)
from config.settings import (
    ACTIVE_STRATEGY,
    AUTO_REJOIN,
    REJOIN_DELAY,
    DEBUG_MODE,
    get_strategy_setting,
    set_setting,
)

# -----------------------------
# Global state
# -----------------------------
listener = None
stats_tracker = None
room_manager = None

should_exit = False
exit_lock = threading.Lock()
already_exiting = False


# -----------------------------
# Cleanup
# -----------------------------
def cleanup_and_exit():
    """Cleanup function called once on shutdown."""
    global already_exiting, room_manager, stats_tracker, listener

    with exit_lock:
        if already_exiting:
            return
        already_exiting = True

    print("\n\n🛑 Shutting down bot gracefully...")

    # Leave room
    if room_manager:
        try:
            if room_manager.current_room_id and room_manager.current_player_id:
                print("🚪 Leaving room...")
                room_manager.leave_current_room()
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Error leaving room: {e}")

    # Print final stats
    if stats_tracker:
        try:
            print("\n📊 Final Statistics:")
            stats_tracker.print_summary()
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Error printing stats: {e}")

    # Disconnect socket
    if listener:
        try:
            listener.disconnect()
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Error disconnecting socket: {e}")

    print("\n👋 Thanks for using UnoBot!")


# -----------------------------
# Signal handling
# -----------------------------
def handle_exit(sig, frame):
    """Handle Ctrl+C / SIGTERM safely."""
    global should_exit, listener

    if should_exit:
        return

    should_exit = True
    print("\n🛑 Exit signal received (Ctrl+C)")

    # Force unblock socket wait
    if listener:
        try:
            listener.disconnect()
        except:
            pass


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)
atexit.register(cleanup_and_exit)


# -----------------------------
# Main bot runner
# -----------------------------
def start_bot():
    global listener, stats_tracker, room_manager, should_exit

    try:
        display_startup_banner()

        stats_tracker = StatsTracker()
        room_manager = RoomManager()

        print(f"🧠 Loading strategy: {ACTIVE_STRATEGY}")
        strategy = load_strategy(ACTIVE_STRATEGY)
        current_strategy_name = ACTIVE_STRATEGY
        print(f"✅ Strategy loaded: {strategy.__class__.__name__}\n")

        room_config = prompt_room_mode()

        target_players = room_config.get("target_players")
        mode = room_config.get("mode")
        only_players = room_config.get("only_players", False)

        auto_wait = (mode == "wait")
        game_count = 0

        while not should_exit:
            game_count += 1

            print(f"\n{'=' * 60}")
            print(f"🎮 GAME SESSION #{game_count}")
            print(f"{'=' * 60}\n")

            # ---------------- Join Room ----------------
            if game_count == 1:
                if mode == "target" and target_players:
                    room_id, player_id = room_manager.find_room_with_players(
                        target_players,
                        only_players=only_players
                    )

                    if not room_id and not room_config.get("require_targets"):
                        if auto_wait:
                            room_id, player_id = room_manager.wait_for_open_room()
                        else:
                            room_id, player_id = room_manager.join_or_create_room()

                elif mode == "wait":
                    room_id, player_id = room_manager.wait_for_open_room(
                        only_players=only_players
                    )
                else:
                    room_id, player_id = room_manager.join_or_create_room(
                        only_players=only_players
                    )
            else:
                if AUTO_REJOIN:
                    room_id, player_id = room_manager.rejoin_room(
                        delay=REJOIN_DELAY
                    )
                else:
                    action = prompt_post_game_action()

                    if action == "leave":
                        print("\n🚪 Leaving room...")
                        room_manager.leave_current_room()
                        break

                    elif action == "view_stats":
                        display_game_summary(stats_tracker)
                        if not prompt_continue_after_game():
                            room_manager.leave_current_room()
                            break
                        continue

                    elif action == "change_strategy":
                        new_strategy = prompt_strategy_change()
                        if new_strategy:
                            strategy = load_strategy(new_strategy)
                            current_strategy_name = new_strategy
                            set_setting("active_strategy", new_strategy)

                    room_id, player_id = room_manager.rejoin_room(delay=2)

            if not room_id or not player_id:
                print("\n❌ Failed to join room.")
                break

            save_state(room_id, player_id)

            print(f"\n✅ Connected to room!")
            print(f"   Room ID: {room_id}")
            print(f"   Player ID: {player_id}")
            print(f"   Strategy: {current_strategy_name}")

            listener = SocketListener(
                room_id,
                player_id,
                strategy,
                stats_tracker
            )
            listener.connect()

            print("\n🤖 Bot active — waiting for game events")
            print("   Press Ctrl+C to exit\n")

            try:
                listener.wait()
            except Exception as e:
                if not should_exit:
                    print(f"\n⚠️ Listener error: {e}")

            if listener:
                try:
                    listener.disconnect()
                except:
                    pass
                listener = None

            if not should_exit:
                display_game_summary(stats_tracker)

                if AUTO_REJOIN:
                    print("\n⏳ Rejoining shortly...\n")

        print("\n🏁 SESSION COMPLETE\n")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        if DEBUG_MODE:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    start_bot()