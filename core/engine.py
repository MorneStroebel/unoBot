from api.actions import play_card, draw_card, call_uno
from config.settings import DEBUG_MODE


class Engine:
    """Core game engine that orchestrates turn-taking and game actions."""
    
    def __init__(self, room_id, player_id, strategy, stats_tracker=None):
        self.room_id = room_id
        self.player_id = player_id
        self.strategy = strategy
        self.stats_tracker = stats_tracker
        self.has_drawn = False  # Track if we've drawn this turn

    def take_turn(self, hand, top_card, current_color):
        """
        Decide what to play or whether to draw.
        
        Args:
            hand: List of cards in player's hand
            top_card: The current top card on discard pile
            current_color: The current active color
        """
        # Reset draw flag at start of turn
        self.has_drawn = False
        
        # Call UNO if we have exactly 2 cards (before playing one)
        if len(hand) == 2:
            try:
                call_uno(self.room_id, self.player_id)
                print("🗣️ Called UNO!")
                if self.stats_tracker:
                    self.stats_tracker.record_uno_call()
            except Exception as e:
                if DEBUG_MODE:
                    print(f"⚠️ UNO call failed: {e}")
        
        # Ask strategy for a card to play
        card_index, wild_color = self.strategy.choose_card(hand, top_card, current_color)

        if card_index is not None:
            # Strategy chose a card to play
            try:
                played_card = hand[card_index]
                result = play_card(self.room_id, self.player_id, card_index, wild_color)
                
                # Check for penalties
                if result.get('result', {}).get('penalty'):
                    penalty = result['result']
                    print(f"⚠️ PENALTY: {penalty.get('penaltyTitle')} - {penalty.get('penaltyDescription')}")
                    if self.stats_tracker:
                        self.stats_tracker.record_penalty()
                else:
                    card_desc = f"{played_card.get('color')} {played_card.get('type')}"
                    if played_card.get('type') == 'NUMBER':
                        card_desc += f" {played_card.get('value')}"
                    print(f"🤖 Played: {card_desc}")
                    if wild_color:
                        print(f"   Chose color: {wild_color}")
                    
                    # Record in stats
                    if self.stats_tracker:
                        self.stats_tracker.record_card_played(played_card, wild_color)
                        
            except Exception as e:
                print(f"❌ Failed to play card: {e}")
                # If play failed, try to draw instead
                self._draw_card()
        else:
            # No playable card, draw one
            self._draw_card()
    
    def _draw_card(self):
        """Draw a card from the deck."""
        try:
            result = draw_card(self.room_id, self.player_id)
            
            # Check for penalties
            if result.get('result', {}).get('penalty'):
                penalty = result['result']
                print(f"⚠️ PENALTY: {penalty.get('penaltyTitle')} - {penalty.get('penaltyDescription')}")
                if self.stats_tracker:
                    self.stats_tracker.record_penalty()
            else:
                drawn_card = result.get('result', {}).get('card')
                if drawn_card and DEBUG_MODE:
                    card_desc = f"{drawn_card.get('color')} {drawn_card.get('type')}"
                    if drawn_card.get('type') == 'NUMBER':
                        card_desc += f" {drawn_card.get('value')}"
                    print(f"🃏 Drew: {card_desc}")
                else:
                    print("🃏 Drew a card")
                
                # Record in stats
                if self.stats_tracker:
                    self.stats_tracker.record_card_drawn()
                    
            self.has_drawn = True
        except Exception as e:
            print(f"❌ Failed to draw card: {e}")