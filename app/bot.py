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


def cleanup_and_exit():
    """Cleanup function called on exit."""
    global already_exiting, room_manager, stats_tracker, listener

    # Prevent multiple calls
    with exit_lock:
        if already_exiting:
            return
        already_exiting = True

    print("\n\n🛑 Shutting down bot gracefully...")

    # Leave room if we're in one
    if room_manager:
        try:
            if room_manager.current_room_id and room_manager.current_player_id:
                print("🚪 Leaving room...")
                room_manager.leave_current_room()
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Error leaving room on exit: {e}")

    # Display final stats
    if stats_tracker:
        try:
            print("\n📊 Final Statistics:")
            stats_tracker.print_summary()
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Error displaying stats: {e}")

    # Disconnect socket
    if listener:
        try:
            listener.disconnect()
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Error disconnecting listener: {e}")

    print("\n👋 Thanks for using UnoBot!")


def handle_exit(sig, frame):
    """Handle graceful shutdown on signals."""
    global should_exit
    should_exit = True

    # Call cleanup
    cleanup_and_exit()

    # Exit
    sys.exit(0)


# Register exit handlers
signal.signal(signal.SIGINT, handle_exit)  # Ctrl+C
signal.signal(signal.SIGTERM, handle_exit)  # Kill command
atexit.register(cleanup_and_exit)  # Normal exit or crash


# -----------------------------
# Main bot runner
# -----------------------------
def start_bot():
    global listener, stats_tracker, room_manager, should_exit

    try:
        # Display startup banner
        display_startup_banner()

        # Initialize systems
        stats_tracker = StatsTracker()
        room_manager = RoomManager()

        print(f"🧠 Loading strategy: {ACTIVE_STRATEGY}")
        strategy = load_strategy(ACTIVE_STRATEGY)
        current_strategy_name = ACTIVE_STRATEGY

        print(f"✅ Strategy loaded: {strategy.__class__.__name__}\n")

        # Get user preferences for room joining
        room_config = prompt_room_mode()

        target_players = room_config.get('target_players')
        mode = room_config.get('mode')
        only_players = room_config.get('only_players', False)

        print(f"\n📋 Configuration:")
        print(f"   Mode: {mode}")
        print(f"   Only Players: {only_players}")
        if target_players:
            print(f"   Target Players: {', '.join(target_players)}")

        # Update AUTO_JOIN_OPEN_ROOM based on mode
        auto_wait = (mode == 'wait')

        # Main game loop
        game_count = 0

        while not should_exit:
            game_count += 1

            print(f"\n{'=' * 60}")
            print(f"🎮 GAME SESSION #{game_count}")
            print(f"{'=' * 60}\n")

            # Join or rejoin room
            if game_count == 1:
                # First game - use user's configuration
                print(f"🔍 Joining room with mode: {mode}")

                if mode == 'target' and target_players:
                    room_id, player_id = room_manager.find_room_with_players(target_players, only_players=only_players)

                    # If not found and not requiring targets, fall back to regular join
                    if not room_id and not room_config.get('require_targets'):
                        print("\n⚠️ Target players not found, joining any available room...")
                        if auto_wait:
                            room_id, player_id = room_manager.wait_for_open_room(only_players=False)
                        else:
                            room_id, player_id = room_manager.join_or_create_room(only_players=False)

                elif mode == 'wait':
                    room_id, player_id = room_manager.wait_for_open_room(only_players=only_players)

                else:  # quick mode
                    room_id, player_id = room_manager.join_or_create_room(only_players=only_players)

            else:
                # Subsequent games
                if AUTO_REJOIN:
                    print(f"🔄 Auto-rejoin enabled...")
                    # Use the saved only_players setting from room_manager
                    room_id, player_id = room_manager.rejoin_room(delay=REJOIN_DELAY)
                else:
                    # Ask user what they want to do
                    action = prompt_post_game_action()

                    if action == 'leave':
                        # Leave room and exit
                        print("\n🚪 Leaving room...")
                        room_manager.leave_current_room()
                        print("\n👋 Ending session...")
                        break

                    elif action == 'view_stats':
                        # Show stats then ask again
                        print("\n📊 Current Statistics:")
                        display_game_summary(stats_tracker)

                        # Ask again
                        continue_playing = prompt_continue_after_game()
                        if not continue_playing:
                            print("\n🚪 Leaving room...")
                            room_manager.leave_current_room()
                            print("\n👋 Ending session...")
                            break

                    elif action == 'change_strategy':
                        # Change strategy
                        new_strategy = prompt_strategy_change()
                        if new_strategy:
                            strategy = load_strategy(new_strategy)
                            current_strategy_name = new_strategy
                            set_setting("active_strategy", new_strategy)
                            bot_first = get_strategy_setting(new_strategy, "bot_first_name")
                            bot_last  = get_strategy_setting(new_strategy, "bot_last_name")
                            print(f"✅ Strategy changed to: {strategy.__class__.__name__} ({bot_first} {bot_last})")

                    # Continue/change_strategy both lead to rejoin
                    if action in ['continue', 'change_strategy']:
                        print(f"\n🔄 Rejoining...")
                        room_id, player_id = room_manager.rejoin_room(delay=2)

            # Check if we successfully joined a room
            if not room_id or not player_id:
                print("\n❌ Failed to join room.")

                if game_count == 1:
                    print("Exiting...")
                    break
                else:
                    # Ask if user wants to try again
                    retry = prompt_continue_after_game()
                    if retry:
                        continue
                    else:
                        break

            # Save state
            save_state(room_id, player_id)

            print(f"\n✅ Connected to room!")
            print(f"   Room ID: {room_id}")
            print(f"   Player ID: {player_id}")
            print(f"   Strategy: {current_strategy_name}")
            print(f"   Only Players: {room_manager.only_players}")

            # Create socket listener for this game
            listener = SocketListener(room_id, player_id, strategy, stats_tracker)
            listener.connect()

            print(f"\n🤖 Bot active and waiting for game events...")
            print(f"   Press Ctrl+C to exit and leave room\n")
            print(f"{'=' * 60}\n")

            # Wait for game to end
            try:
                listener.wait()
            except KeyboardInterrupt:
                # This will trigger handle_exit which calls cleanup_and_exit
                raise
            except Exception as e:
                print(f"\n⚠️ Connection error: {e}")

            # Disconnect after game
            if listener:
                try:
                    listener.disconnect()
                except:
                    pass
                listener = None

            # Display quick summary
            if not should_exit:
                display_game_summary(stats_tracker)

                # Small pause between games
                if AUTO_REJOIN:
                    print(f"\n⏳ Next game starting soon...")
                else:
                    print("\n")

        # Normal exit - leave room
        if room_manager and room_manager.current_room_id:
            print("\n🚪 Leaving room before exit...")
            room_manager.leave_current_room()

        # Final cleanup and summary
        print(f"\n{'=' * 60}")
        print("🏁 SESSION COMPLETE")
        print(f"{'=' * 60}\n")

        if stats_tracker:
            stats_tracker.print_summary()

        print("\n👋 Thanks for using UnoBot!\n")

    except KeyboardInterrupt:
        # Ctrl+C pressed - handle_exit already called via signal handler
        pass
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        if DEBUG_MODE:
            import traceback
            traceback.print_exc()
        # cleanup_and_exit will be called via atexit
        sys.exit(1)


if __name__ == "__main__":
    start_bot()