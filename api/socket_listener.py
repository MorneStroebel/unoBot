"""
Socket listener — handles all Socket.io events for an active game session.
"""

import socketio
from config.settings import SOCKET_URL, DEBUG_MODE
from core.engine import Engine


class SocketListener:
    """Handles Socket.io connection and in-game events."""

    def __init__(self, room_id, player_id, strategy, stats_tracker=None, room_manager=None):
        self.room_id        = room_id
        self.player_id      = player_id
        self.strategy       = strategy
        self.stats_tracker  = stats_tracker
        self.room_manager   = room_manager
        self.strategy_name  = self._class_to_strategy_name(strategy.__class__.__name__)
        self.engine         = Engine(room_id, player_id, strategy, stats_tracker)
        self.sio            = socketio.Client(reconnection=True, reconnection_attempts=5)
        self.game_started   = False   # True once stats tracking begun for this game
        self.game_ended     = False
        self._is_reconnect  = False   # True after the first connect fires
        self._players       = {}      # id → name
        self._setup_handlers()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _class_to_strategy_name(class_name: str) -> str:
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        if name.endswith("_strategy"):
            name = name[:-9]
        return name

    def _ensure_game_started(self):
        """Start stats tracking exactly once per game — ignore reconnect signals."""
        if self.game_started:
            return
        if self._is_reconnect:
            # We reconnected mid-game; don't start a new stats session
            print("🔄 Reconnected mid-game — stats session continuing", flush=True)
            self.game_started = True   # suppress future calls but don't reset stats
            return
        if self.stats_tracker:
            self.stats_tracker.start_game(self.room_id, self.player_id, self.strategy_name)
        self.game_started = True

    @staticmethod
    def _card_str(card):
        if not card:
            return "?"
        color = card.get("color", "")
        value = card.get("value", card.get("type", "?"))
        return f"{color} {value}" if color else str(value)

    # ── Event setup ───────────────────────────────────────────────────────────

    def _setup_handlers(self):

        @self.sio.on("connect")
        def on_connect():
            print(f"🔌 Connected to game server", flush=True)
            self.sio.emit("joinRoom", {
                "roomId":   self.room_id,
                "playerId": self.player_id,
            })
            print(f"🚪 Joined room {self.room_id}", flush=True)
            # Mark subsequent connects as reconnects so we don't double-count games
            self._is_reconnect = True

        @self.sio.on("disconnect")
        def on_disconnect():
            print("🔌 Disconnected from game server", flush=True)

        @self.sio.on("turn")
        def on_turn(data):
            if DEBUG_MODE:
                print(f"[DEBUG] turn: {data}", flush=True)

            for p in data.get("players", []):
                pid   = p.get("id")
                pname = p.get("name") or p.get("playerName")
                if pid and pname:
                    self._players[pid] = pname

            current_player_id = data.get("playerId")

            if current_player_id == self.player_id:
                hand          = data.get("hand", [])
                top_card      = data.get("topCard")
                current_color = data.get("currentColor", "")
                top_str       = self._card_str(top_card)
                color_str     = f" [{current_color}]" if current_color else ""
                print(f"🎮 MY TURN  │  Hand: {len(hand)} cards  │  Top: {top_str}{color_str}", flush=True)
                if self.stats_tracker:
                    self.stats_tracker.record_hand_size(len(hand))
                self.engine.take_turn(hand, top_card, current_color)
            else:
                pname      = data.get("playerName") or self._players.get(current_player_id, "?")
                card_count = next(
                    (p["cardCount"] for p in data.get("players", [])
                     if p["id"] == current_player_id),
                    "?",
                )
                print(f"⏳ {pname}'s turn  │  {card_count} cards in hand", flush=True)

        @self.sio.on("action")
        def on_action(data):
            if DEBUG_MODE:
                print(f"[DEBUG] action: {data}", flush=True)

            action_type = data.get("type", "?")
            actor_id    = data.get("playerId")
            actor_name  = self._players.get(actor_id, "Opponent")
            result      = data.get("result", {})
            card        = data.get("card") or result.get("card")
            card_str    = self._card_str(card) if card else ""

            if actor_id == self.player_id:
                if result.get("penalty"):
                    title = result.get("penaltyTitle", "Penalty")
                    desc  = result.get("penaltyDescription", "")
                    print(f"⚠️  PENALTY  │  {title}: {desc}", flush=True)
                elif action_type == "play":
                    chosen_color = result.get("chosenColor", "")
                    extra = f" → chose {chosen_color}" if chosen_color else ""
                    print(f"✅ Played {card_str}{extra}", flush=True)
                elif action_type == "draw":
                    count = result.get("count", 1)
                    print(f"🃏 Drew {count} card{'s' if count != 1 else ''}", flush=True)
                elif action_type == "uno":
                    print(f"📣 Called UNO!", flush=True)
                else:
                    print(f"✅ {action_type}", flush=True)
            else:
                if action_type == "play":
                    uno_flag = "  📣 UNO!" if result.get("uno") else ""
                    print(f"🎴 {actor_name} played {card_str}{uno_flag}", flush=True)
                elif action_type == "draw":
                    count = result.get("count", 1)
                    print(f"🃏 {actor_name} drew {count} card{'s' if count != 1 else ''}", flush=True)
                elif action_type == "uno":
                    print(f"📣 {actor_name} called UNO!", flush=True)
                elif action_type == "penalty":
                    print(f"⚠️  {actor_name} got a penalty", flush=True)

        @self.sio.on("gameStart")
        def on_game_start(data):
            if DEBUG_MODE:
                print(f"[DEBUG] gameStart: {data}", flush=True)
            players = data.get("players", [])
            names   = [p.get("name", p.get("playerName", "?")) for p in players]
            for p in players:
                pid   = p.get("id")
                pname = p.get("name") or p.get("playerName")
                if pid and pname:
                    self._players[pid] = pname
            print(f"🃏 GAME STARTED  │  Players: {', '.join(names)}", flush=True)
            self._ensure_game_started()
            try:
                self.strategy.on_game_start()
            except Exception:
                pass

        @self.sio.on("countdownStart")
        def on_countdown_start(data):
            seconds = data.get("seconds", 0)
            message = data.get("message", "Starting in")
            print(f"⏰ {message} {seconds}s…", flush=True)
            # Do NOT call _ensure_game_started here — countdown fires before the
            # game actually begins and can be cancelled; gameStart is authoritative.

        @self.sio.on("countdownCancel")
        def on_countdown_cancel(data):
            reason = data.get("reason", "Unknown")
            print(f"❌ Countdown cancelled: {reason}", flush=True)

        @self.sio.on("gameEnd")
        def on_game_end(data):
            winner  = data.get("winner", {})
            score   = data.get("score", 0)
            reason  = data.get("reason", "")
            players = data.get("players", [])

            if isinstance(winner, dict):
                winner_id   = winner.get("id")
                winner_name = winner.get("name", "Unknown")
            else:
                winner_id   = winner
                winner_name = self._players.get(winner, str(winner))

            won = (winner_id == self.player_id)

            placement = 1
            if players:
                for i, p in enumerate(players, 1):
                    if p.get("id") == self.player_id:
                        placement = i
                        break
            elif not won:
                placement = 2

            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            medal  = medals.get(placement, f"#{placement}")

            if won:
                print(f"🏆 WE WON!  │  Score: {score} pts  │  Reason: {reason}", flush=True)
            else:
                suffix = {1:"st",2:"nd",3:"rd"}.get(placement,"th")
                print(f"😔 Game over  │  {medal} {placement}{suffix} place  │  Winner: {winner_name}", flush=True)

            # Notify strategy lifecycle hook FIRST (before end_game clears live_state.json)
            # This lets base_strategy._persist_stats see live_state.json still exists
            # and skip the legacy record_game() call → prevents double counting.
            try:
                self.strategy.on_game_end(won, placement, score if won else 0)
            except Exception:
                pass

            # Now commit stats and delete live_state.json (single write per game)
            if self.game_started and self.stats_tracker:
                self.stats_tracker.end_game(won, placement, score if won else 0)

            self.game_started = False
            self.game_ended   = True

    # ── Public interface ──────────────────────────────────────────────────────

    def connect(self):
        # Reset reconnect flag so the very first connect is treated as fresh
        self._is_reconnect = False
        print(f"🔌 Connecting to game server…", flush=True)
        self.sio.connect(SOCKET_URL)

    def disconnect(self):
        try:
            self.sio.disconnect()
        except Exception:
            pass

    def wait(self):
        self.sio.wait()

    def is_game_ended(self) -> bool:
        return self.game_ended

    def reset_game_state(self):
        self.game_ended   = False
        self.game_started = False
