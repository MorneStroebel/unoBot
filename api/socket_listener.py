import socketio
from config.settings import SOCKET_URL, DEBUG_MODE
from core.engine import Engine


class SocketListener:
    """Handles Socket.io connection and game events."""

    def __init__(self, room_id, player_id, strategy, stats_tracker=None, room_manager=None):
        self.room_id = room_id
        self.player_id = player_id
        self.strategy = strategy
        self.stats_tracker = stats_tracker
        self.room_manager = room_manager
        self.engine = Engine(room_id, player_id, strategy, stats_tracker)
        self.sio = socketio.Client()
        self.game_started = False
        self.game_ended = False
        self.setup_handlers()

    def setup_handlers(self):
        """Set up all Socket.io event handlers."""

        @self.sio.on('connect')
        def on_connect():
            print("🔌 Connected to Socket.io server")
            # Re-join room on reconnect (important for connection reliability)
            self.sio.emit('joinRoom', {
                'roomId': self.room_id,
                'playerId': self.player_id
            })
            print(f"🔄 Joined room {self.room_id}")

        @self.sio.on('disconnect')
        def on_disconnect():
            print("🔌 Disconnected from Socket.io server")

        @self.sio.on('turn')
        def on_turn(data):
            """Handle turn events (includes hand if it's your turn)."""
            if DEBUG_MODE:
                print(f"📨 Turn event: {data}")

            # Check if it's our turn
            if data.get('playerId') == self.player_id:
                hand = data.get('hand')
                if hand:
                    top_card = data.get('topCard')
                    current_color = data.get('currentColor')
                    print(f"🎮 My turn! Hand size: {len(hand)}, Top card: {top_card}, Current color: {current_color}")

                    # Take turn using the engine
                    self.engine.take_turn(hand, top_card, current_color)
                else:
                    print("⚠️ My turn but no hand data received")
            else:
                player_name = data.get('playerName', 'Unknown')
                card_count = next((p['cardCount'] for p in data.get('players', []) if p['id'] == data.get('playerId')),
                                  '?')
                print(f"⏳ {player_name}'s turn ({card_count} cards)")

        @self.sio.on('action')
        def on_action(data):
            """Handle action events (play, draw)."""
            if DEBUG_MODE:
                print(f"📨 Action event: {data}")

            action_type = data.get('type')
            player_id = data.get('playerId')
            result = data.get('result', {})

            if player_id == self.player_id:
                # Our action
                if result.get('penalty'):
                    penalty_title = result.get('penaltyTitle', 'Unknown penalty')
                    penalty_desc = result.get('penaltyDescription', '')
                    print(f"⚠️ PENALTY: {penalty_title} - {penalty_desc}")
                else:
                    print(f"✅ Action '{action_type}' successful")
            else:
                # Other player's action
                if action_type == 'play':
                    print(f"🎴 Player played a card")
                elif action_type == 'draw':
                    print(f"🃏 Player drew a card")

        @self.sio.on('gameEnd')
        def on_game_end(data):
            """Handle game end event."""
            winner = data.get('winner', {})
            score = data.get('score', 0)
            reason = data.get('reason', 'unknown')
            players = data.get('players', [])

            winner_name = winner.get('name', 'Unknown')
            winner_id = winner.get('id')
            
            # Determine if we won and our placement
            won = (winner_id == self.player_id)
            
            # Calculate placement from players list
            # Players are typically sorted by finish order
            placement = 1
            if players:
                for i, player in enumerate(players, 1):
                    if player.get('id') == self.player_id:
                        placement = i
                        break
            else:
                placement = 1 if won else 2

            if won:
                print(f"🎉 WE WON! Score: {score} points (Reason: {reason})")
            else:
                print(f"😔 Game ended. Winner: {winner_name}, Score: {score} points")
                print(f"📊 Final placement: {placement}")

            # Record game end in stats
            if self.stats_tracker and self.game_started:
                self.stats_tracker.end_game(won, placement, score if won else 0)
                self.game_started = False
            
            # Mark game as ended
            self.game_ended = True
            
            # Trigger rejoin if room manager is available
            if self.room_manager and self.room_manager.auto_rejoin:
                print("\n⏳ Game ended. Preparing to rejoin in 3 seconds...")
                import time
                time.sleep(3)
                
                # Disconnect from current room
                self.disconnect()
                
                # This will be handled by the main loop

        @self.sio.on('countdownStart')
        def on_countdown_start(data):
            """Handle countdown start."""
            seconds = data.get('seconds', 0)
            message = data.get('message', 'Countdown')
            print(f"⏰ {message} {seconds} seconds...")
            
            # Start tracking game when countdown begins
            if not self.game_started and self.stats_tracker:
                strategy_name = self.strategy.__class__.__name__
                self.stats_tracker.start_game(self.room_id, self.player_id, strategy_name)
                self.game_started = True

        @self.sio.on('countdownCancel')
        def on_countdown_cancel(data):
            """Handle countdown cancellation."""
            reason = data.get('reason', 'Unknown reason')
            print(f"❌ Countdown cancelled: {reason}")
            self.game_started = False

    def connect(self):
        """Connect to the Socket.io server."""
        print(f"🔌 Connecting to {SOCKET_URL}...")
        self.sio.connect(SOCKET_URL)

    def disconnect(self):
        """Disconnect from the Socket.io server."""
        self.sio.disconnect()

    def wait(self):
        """Block and wait for events."""
        self.sio.wait()
    
    def is_game_ended(self):
        """Check if the game has ended."""
        return self.game_ended
    
    def reset_game_state(self):
        """Reset game state for new game."""
        self.game_ended = False
        self.game_started = False
