import json
import os
import signal
import sys
import threading
import atexit

from api.socket_listener import SocketListener
from core.room_manager import RoomManager
from core.state import save_state
from strategies.loader import load_strategy
from strategies.stats import StrategyStats
from config.settings import (
    ACTIVE_STRATEGY,
    AUTO_REJOIN,
    REJOIN_DELAY,
    DEBUG_MODE,
    set_setting,
)

# ── UI mode: skip all interactive prompts when launched from the web UI ────────
_UI_MODE = os.environ.get("UNO_UI_MODE") == "1"
_LAUNCH_HINT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".ui_launch_hint.json")
_PAUSE_FILE       = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".bot_paused")


def _check_paused():
    """In UI mode, block here until the pause file is removed."""
    if not _UI_MODE:
        return
    if os.path.exists(_PAUSE_FILE):
        print("⏸ Bot paused by UI — waiting to resume...", flush=True)

        while os.path.exists(_PAUSE_FILE) and not should_exit:
            import time; time.sleep(1)
        if not should_exit:
            print("▶ Bot resumed — rejoining game loop.", flush=True)



def _read_launch_hint() -> dict:
    """Read launch config written by the UI server before starting the bot."""
    if os.path.exists(_LAUNCH_HINT_FILE):
        try:
            with open(_LAUNCH_HINT_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _prompt_room_mode() -> dict:
    """Interactive room-joining mode selection (only used in CLI mode)."""
    from app.prompts import prompt_room_mode
    return prompt_room_mode()


# ── Global state ───────────────────────────────────────────────────────────────
listener     = None
room_manager = None

should_exit    = False
exit_lock      = threading.Lock()
already_exiting = False


# ── Cleanup ────────────────────────────────────────────────────────────────────
def cleanup_and_exit():
    global already_exiting, room_manager, listener

    with exit_lock:
        if already_exiting:
            return
        already_exiting = True

    print("\n\n🛑 Shutting down bot gracefully...", flush=True)


    if room_manager:
        try:
            if room_manager.current_room_id and room_manager.current_player_id:
                print("🚪 Leaving room...", flush=True)

                room_manager.leave_current_room()
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Error leaving room: {e}", flush=True)


    if listener:
        try:
            listener.disconnect()
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Error disconnecting: {e}", flush=True)


    print("\n👋 UnoBot shut down.", flush=True)



# ── Signal handling ────────────────────────────────────────────────────────────
def handle_exit(sig, frame):
    global should_exit, listener
    if should_exit:
        return
    should_exit = True
    print("\n🛑 Exit signal received", flush=True)

    if listener:
        try:
            listener.disconnect()
        except:
            pass


signal.signal(signal.SIGINT,  handle_exit)
signal.signal(signal.SIGTERM, handle_exit)
atexit.register(cleanup_and_exit)


# ── Main bot runner ────────────────────────────────────────────────────────────
def start_bot():
    global listener, room_manager, should_exit

    try:
        if not _UI_MODE:
            from app.prompts import display_startup_banner
            display_startup_banner()

        room_manager = RoomManager()

        # ── Resolve launch config ──────────────────────────────────────────
        if _UI_MODE:
            hint = _read_launch_hint()
            strategy_name = hint.get("strategy") or ACTIVE_STRATEGY
            mode          = hint.get("mode", "auto")
            only_players  = hint.get("only_players", False)
            target_players = hint.get("target_players") or []
            auto_rejoin   = hint.get("auto_rejoin", AUTO_REJOIN)
            rejoin_delay  = hint.get("rejoin_delay", REJOIN_DELAY)
            print(f"🖥  UI mode — strategy={strategy_name}  room_mode={mode}", flush=True)

        else:
            strategy_name  = ACTIVE_STRATEGY
            room_cfg       = _prompt_room_mode()
            mode           = room_cfg.get("mode", "quick")
            only_players   = room_cfg.get("only_players", False)
            target_players = room_cfg.get("target_players") or []
            auto_rejoin    = AUTO_REJOIN
            rejoin_delay   = REJOIN_DELAY

        print(f"🧠 Loading strategy: {strategy_name}", flush=True)

        strategy = load_strategy(strategy_name)
        current_strategy_name = strategy_name
        stats_tracker = StrategyStats(current_strategy_name)
        print(f"✅ Strategy loaded: {strategy.__class__.__name__}\n", flush=True)

        game_count = 0

        while not should_exit:
            game_count += 1
            print(f"\n{'=' * 60}", flush=True)

            print(f"🎮 GAME SESSION #{game_count}", flush=True)

            print(f"{'=' * 60}\n", flush=True)


            # ── Join room ──────────────────────────────────────────────────
            if game_count == 1:
                if mode == "target" and target_players:
                    room_id, player_id = room_manager.find_room_with_players(
                        target_players, only_players=only_players
                    )
                    if not room_id:
                        room_id, player_id = room_manager.join_or_create_room(
                            only_players=only_players
                        )

                elif mode == "wait":
                    room_id, player_id = room_manager.wait_for_open_room(
                        only_players=only_players
                    )

                else:  # auto — always create a fresh room
                    room_id, player_id = room_manager.create_and_join_room(
                        only_players=only_players
                    )

            else:
                # Subsequent games
                _check_paused()  # blocks if paused via UI
                if should_exit:
                    break
                if auto_rejoin:
                    # auto mode always creates a new room; wait mode polls forever
                    room_id, player_id = room_manager.rejoin_room(
                        delay=rejoin_delay,
                        force_create=(mode == "auto"),
                        mode=mode,
                    )
                elif _UI_MODE:
                    # In UI mode without auto-rejoin, stop after one game
                    print("🏁 Auto-rejoin disabled — stopping after game.", flush=True)

                    break
                else:
                    from app.prompts import (
                        prompt_post_game_action, prompt_continue_after_game,
                        prompt_strategy_change,
                    )
                    action = prompt_post_game_action()

                    if action == "leave":
                        print("\n🚪 Leaving room...", flush=True)

                        room_manager.leave_current_room()
                        break

                    elif action == "view_stats":
                        if not prompt_continue_after_game():
                            room_manager.leave_current_room()
                            break
                        continue

                    elif action == "change_strategy":
                        new_strategy = prompt_strategy_change()
                        if new_strategy:
                            strategy = load_strategy(new_strategy)
                            current_strategy_name = new_strategy
                            stats_tracker = StrategyStats(current_strategy_name)
                            set_setting("active_strategy", new_strategy)

                    room_id, player_id = room_manager.rejoin_room(delay=2)

            if not room_id or not player_id:
                print("\n❌ Failed to join room.", flush=True)

                break

            save_state(room_id, player_id)
            print(f"\n✅ Connected to room: {room_id}", flush=True)

            print(f"   Strategy: {current_strategy_name}", flush=True)


            listener = SocketListener(room_id, player_id, strategy, stats_tracker=stats_tracker)
            listener.connect()

            print("\n🤖 Bot active — waiting for game events", flush=True)

            if not _UI_MODE:
                print("   Press Ctrl+C to exit\n", flush=True)


            try:
                listener.wait()
            except Exception as e:
                if not should_exit:
                    print(f"\n⚠️ Listener error: {e}", flush=True)


            if listener:
                try:
                    listener.disconnect()
                except:
                    pass
                listener = None

            if not should_exit and auto_rejoin:
                print("\n⏳ Rejoining shortly...\n", flush=True)


        print("\n🏁 SESSION COMPLETE\n", flush=True)


    except Exception as e:
        print(f"\n❌ Fatal error: {e}", flush=True)

        if DEBUG_MODE:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    start_bot()
