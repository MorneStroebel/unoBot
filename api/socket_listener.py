"""
Socket listener — handles all Socket.io events for an active game session.
"""

import socketio
from config.settings import SOCKET_URL, DEBUG_MODE
from core.engine import Engine


class SocketListener:
    """Handles Socket.io connection and in-game events."""

    def __init__(self, room_id, player_id, strategy, stats_tracker=None, room_manager=None):
        self.room_id = room_id
        self.player_id = player_id
        self.strategy = strategy
        self.stats_tracker = stats_tracker
        self.room_manager = room_manager

        # Derive a consistent strategy name from the class name so it matches
        # what the loader uses (e.g. GeminiBot → gemini_bot).
        self.strategy_name = self._class_to_strategy_name(strategy.__class__.__name__)

        self.engine = Engine(room_id, player_id, strategy, stats_tracker)
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=5)
        self.game_started = False
        self.game_ended = False
        self._setup_handlers()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _class_to_strategy_name(class_name: str) -> str:
        """
        Convert a CamelCase class name to snake_case strategy name so that
        stats are stored under the same key used in settings.

        Examples:
            GeminiBot        → gemini_bot
            AggressiveBotStrategy → aggressive_bot_strategy
            SmartBotStrategy → smart_bot_strategy
            BaseBotStrategy  → base_bot_strategy
        """
        import re
        # Insert underscore before each uppercase letter (except the first)
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        # Strip common suffixes that don't appear in loader keys
        for suffix in ("_strategy",):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
        return name

    def _ensure_game_started(self):
        """Start tracking if we haven't already (guards against missed countdownStart)."""
        if not self.game_started and self.stats_tracker:
            self.stats_tracker.start_game(self.room_id, self.player_id, self.strategy_name)
            self.game_started = True

    # ------------------------------------------------------------------
    # Event setup
    # ------------------------------------------------------------------

    def _setup_handlers(self):
        """Register all Socket.io event handlers."""

        @self.sio.on("connect")
        def on_connect():
            print("🔌 Connected to Socket.io server")
            self.sio.emit("joinRoom", {
                "roomId": self.room_id,
                "playerId": self.player_id,
            })
            print(f"🔄 Joined room {self.room_id}")

        @self.sio.on("disconnect")
        def on_disconnect():
            print("🔌 Disconnected from Socket.io server")

        @self.sio.on("turn")
        def on_turn(data):
            if DEBUG_MODE:
                print(f"📨 Turn event: {data}")

            if data.get("playerId") == self.player_id:
                hand = data.get("hand")
                if hand:
                    top_card = data.get("topCard")
                    current_color = data.get("currentColor")
                    print(
                        f"🎮 My turn! Hand size: {len(hand)}, "
                        f"Top card: {top_card}, Current color: {current_color}"
                    )
                    self.engine.take_turn(hand, top_card, current_color)
                else:
                    print("⚠️ My turn but no hand data received")
            else:
                player_name = data.get("playerName", "Unknown")
                card_count = next(
                    (p["cardCount"] for p in data.get("players", [])
                     if p["id"] == data.get("playerId")),
                    "?",
                )
                print(f"⏳ {player_name}'s turn ({card_count} cards)")

        @self.sio.on("action")
        def on_action(data):
            if DEBUG_MODE:
                print(f"📨 Action event: {data}")

            action_type = data.get("type")
            actor_id = data.get("playerId")
            result = data.get("result", {})

            if actor_id == self.player_id:
                if result.get("penalty"):
                    title = result.get("penaltyTitle", "Unknown penalty")
                    desc = result.get("penaltyDescription", "")
                    print(f"⚠️ PENALTY: {title} - {desc}")
                else:
                    print(f"✅ Action '{action_type}' successful")
            else:
                if action_type == "play":
                    print("🎴 Player played a card")
                elif action_type == "draw":
                    print("🃏 Player drew a card")

        @self.sio.on("gameStart")
        def on_game_start(data):
            """Some servers emit a gameStart event — use it as a reliable tracking trigger."""
            if DEBUG_MODE:
                print(f"📨 gameStart event: {data}")
            self._ensure_game_started()

        @self.sio.on("countdownStart")
        def on_countdown_start(data):
            seconds = data.get("seconds", 0)
            message = data.get("message", "Countdown")
            print(f"⏰ {message} {seconds} seconds...")
            self._ensure_game_started()

        @self.sio.on("countdownCancel")
        def on_countdown_cancel(data):
            reason = data.get("reason", "Unknown reason")
            print(f"❌ Countdown cancelled: {reason}")
            # Only reset if the game hasn't actually started yet
            if not self.game_started:
                pass  # nothing to reset
            # If it was started we leave it running; the server may resume

        @self.sio.on("gameEnd")
        def on_game_end(data):
            winner = data.get("winner", {})
            score = data.get("score", 0)
            reason = data.get("reason", "unknown")
            players = data.get("players", [])

            # "winner" may arrive as a plain string ID or as a dict
            if isinstance(winner, dict):
                winner_id   = winner.get("id")
                winner_name = winner.get("name", "Unknown")
            else:
                winner_id   = winner          # it's already the ID string
                winner_name = str(winner)
            won = winner_id == self.player_id

            # Determine placement
            placement = 1
            if players:
                for i, player in enumerate(players, 1):
                    if player.get("id") == self.player_id:
                        placement = i
                        break
            elif not won:
                placement = 2

            if won:
                print(f"🎉 WE WON! Score: {score} points (Reason: {reason})")
            else:
                print(f"😔 Game ended. Winner: {winner_name}, Score: {score} points")
                print(f"📊 Final placement: {placement}")

            # Guarantee game is tracked even if countdownStart was missed
            self._ensure_game_started()

            if self.stats_tracker:
                self.stats_tracker.end_game(won, placement, score if won else 0)

            self.game_started = False
            self.game_ended = True

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def connect(self):
        """Connect to the Socket.io server."""
        print(f"🔌 Connecting to {SOCKET_URL}...")
        self.sio.connect(SOCKET_URL)

    def disconnect(self):
        """Disconnect from the Socket.io server."""
        try:
            self.sio.disconnect()
        except Exception:
            pass

    def wait(self):
        """Block until the connection drops or the game ends."""
        self.sio.wait()

    def is_game_ended(self) -> bool:
        return self.game_ended

    def reset_game_state(self):
        """Reset state ready for a new game."""
        self.game_ended = False
        self.game_started = False
