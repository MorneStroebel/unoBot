import random
from collections import Counter
from .base import BaseStrategy

class SmartBotStrategy(BaseStrategy):
    """
    Smart strategy with card tracking and strategic decision-making.
    
    Features:
    - Tracks played cards to estimate what's left in deck
    - Saves high-value cards (Wild, Wild Draw Four) for late game
    - Prioritizes getting rid of high-point cards when opponent is low on cards
    - Considers color distribution in hand when choosing wild colors
    """
    
    def __init__(self):
        self.played_cards = []
        self.round_number = 0
    
    def choose_card(self, hand, top_card, current_color):
        # Update our knowledge
        self._update_tracking(hand, top_card)
        
        playable_cards = []
        
        # Find all playable cards with metadata
        for i, card in enumerate(hand):
            if self.is_playable(card, top_card, current_color):
                card_value = self._get_card_value(card)
                is_action = card['type'] in ['SKIP', 'REVERSE', 'DRAW_TWO']
                is_wild = card['type'].startswith('WILD')
                
                playable_cards.append({
                    'index': i,
                    'card': card,
                    'value': card_value,
                    'is_action': is_action,
                    'is_wild': is_wild
                })
        
        if not playable_cards:
            return None, None
        
        # Strategic decision making
        hand_size = len(hand)
        
        if hand_size <= 3:
            # End game: Play high-value cards first to minimize points if we lose
            playable_cards.sort(key=lambda x: x['value'], reverse=True)
            chosen = playable_cards[0]
        elif hand_size > 5:
            # Early/mid game: Save wilds and high-value action cards for later
            # Prefer playing number cards and lower-value actions
            non_wild_cards = [c for c in playable_cards if not c['is_wild']]
            
            if non_wild_cards:
                # Play lowest value non-wild card
                non_wild_cards.sort(key=lambda x: x['value'])
                chosen = non_wild_cards[0]
            else:
                # Only wild cards available
                chosen = playable_cards[0]
        else:
            # Mid game: Balanced approach
            # Prefer action cards but avoid wilds unless necessary
            action_cards = [c for c in playable_cards if c['is_action']]
            non_wild_cards = [c for c in playable_cards if not c['is_wild']]
            
            if action_cards:
                chosen = action_cards[0]
            elif non_wild_cards:
                # Play higher value non-wild cards
                non_wild_cards.sort(key=lambda x: x['value'], reverse=True)
                chosen = non_wild_cards[0]
            else:
                chosen = playable_cards[0]
        
        card_index = chosen['index']
        card = chosen['card']
        
        # Determine wild color if needed
        wild_color = None
        if card['type'].startswith('WILD'):
            # For Wild Draw Four, verify it's legal
            if card['type'] == 'WILD_DRAW_FOUR':
                if not self._can_play_wild_draw_four(hand, current_color):
                    # Illegal, try to find another card
                    legal_cards = [c for c in playable_cards if c['card']['type'] != 'WILD_DRAW_FOUR']
                    if legal_cards:
                        chosen = legal_cards[0]
                        card_index = chosen['index']
                        card = chosen['card']
                        if card['type'] == 'WILD':
                            wild_color = self._choose_smart_wild_color(hand)
                    else:
                        # Only wild draw four available, play it anyway
                        wild_color = self._choose_smart_wild_color(hand)
                else:
                    wild_color = self._choose_smart_wild_color(hand)
            else:
                wild_color = self._choose_smart_wild_color(hand)
        
        return card_index, wild_color
    
    def _update_tracking(self, hand, top_card):
        """Update our card tracking."""
        # Track the top card if we haven't seen it
        if top_card and top_card not in self.played_cards:
            self.played_cards.append(top_card)
    
    def _can_play_wild_draw_four(self, hand, current_color):
        """Check if Wild Draw Four is legal (no cards matching current color)."""
        for card in hand:
            if card['color'] == current_color and card['type'] != 'WILD_DRAW_FOUR':
                return False
        return True
    
    def _choose_smart_wild_color(self, hand):
        """Choose wild color based on hand distribution and strategy."""
        color_counts = Counter()
        color_values = {'RED': 0, 'BLUE': 0, 'GREEN': 0, 'YELLOW': 0}
        
        for card in hand:
            color = card.get('color')
            if color in color_values:
                color_counts[color] += 1
                # Weight by card value
                color_values[color] += self._get_card_value(card)
        
        if not color_counts:
            return random.choice(['RED', 'BLUE', 'GREEN', 'YELLOW'])
        
        # Choose color with most cards, breaking ties by total value
        max_count = max(color_counts.values())
        best_colors = [color for color, count in color_counts.items() if count == max_count]
        
        if len(best_colors) == 1:
            return best_colors[0]
        
        # Tie: Choose by total value
        return max(best_colors, key=lambda c: color_values[c])
    
    @staticmethod
    def _get_card_value(card):
        """Get point value of a card."""
        card_type = card['type']
        if card_type == 'NUMBER':
            return card.get('value', 0)
        elif card_type in ['SKIP', 'REVERSE', 'DRAW_TWO']:
            return 20
        elif card_type in ['WILD', 'WILD_DRAW_FOUR']:
            return 50
        return 0
    
    @staticmethod
    def is_playable(card, top_card, current_color):
        """Check if a card can be played."""
        # Wild cards can always be played
        if card['type'].startswith('WILD'):
            return True
        
        # Color match
        if card['color'] == current_color:
            return True
        
        # Type match (for action cards)
        if card['type'] == top_card['type'] and card['type'] != 'NUMBER':
            return True
        
        # Number match
        if card['type'] == 'NUMBER' and top_card['type'] == 'NUMBER':
            if card['value'] == top_card['value']:
                return True
        
        return False
