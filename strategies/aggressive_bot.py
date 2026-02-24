import random
from .base import BaseStrategy

class AggressiveBotStrategy(BaseStrategy):
    """
    Aggressive strategy that prioritizes playing action cards and wild cards.
    
    Priority order:
    1. Wild Draw Four (if legal)
    2. Draw Two cards
    3. Skip cards
    4. Reverse cards
    5. Wild cards
    6. Number cards (highest first)
    """
    
    def choose_card(self, hand, top_card, current_color):
        playable_cards = []
        
        # Find all playable cards
        for i, card in enumerate(hand):
            if self.is_playable(card, top_card, current_color):
                playable_cards.append((i, card))
        
        if not playable_cards:
            return None, None
        
        # Prioritize cards
        wild_draw_fours = []
        draw_twos = []
        skips = []
        reverses = []
        wilds = []
        numbers = []
        
        for i, card in playable_cards:
            card_type = card['type']
            
            if card_type == 'WILD_DRAW_FOUR':
                # Check if legal to play (no matching color in hand)
                if self._can_play_wild_draw_four(hand, current_color):
                    wild_draw_fours.append((i, card))
            elif card_type == 'DRAW_TWO':
                draw_twos.append((i, card))
            elif card_type == 'SKIP':
                skips.append((i, card))
            elif card_type == 'REVERSE':
                reverses.append((i, card))
            elif card_type == 'WILD':
                wilds.append((i, card))
            elif card_type == 'NUMBER':
                numbers.append((i, card))
        
        # Choose in priority order
        if wild_draw_fours:
            card_index, card = wild_draw_fours[0]
        elif draw_twos:
            card_index, card = draw_twos[0]
        elif skips:
            card_index, card = skips[0]
        elif reverses:
            card_index, card = reverses[0]
        elif wilds:
            card_index, card = wilds[0]
        elif numbers:
            # Sort numbers by value (highest first)
            numbers.sort(key=lambda x: x[1].get('value', 0), reverse=True)
            card_index, card = numbers[0]
        else:
            # Fallback to first playable card
            card_index, card = playable_cards[0]
        
        # Determine wild color if needed
        wild_color = None
        if card['type'].startswith('WILD'):
            wild_color = self._choose_wild_color(hand)
        
        return card_index, wild_color
    
    def _can_play_wild_draw_four(self, hand, current_color):
        """Check if Wild Draw Four is legal (no cards matching current color)."""
        for card in hand:
            if card['color'] == current_color and card['type'] != 'WILD_DRAW_FOUR':
                return False
        return True
    
    def _choose_wild_color(self, hand):
        """Choose the most common color in hand, excluding wild cards."""
        color_counts = {'RED': 0, 'BLUE': 0, 'GREEN': 0, 'YELLOW': 0}
        
        for card in hand:
            color = card.get('color')
            if color in color_counts:
                color_counts[color] += 1
        
        # Return most common color, or random if all equal
        max_count = max(color_counts.values())
        if max_count == 0:
            return random.choice(['RED', 'BLUE', 'GREEN', 'YELLOW'])
        
        best_colors = [color for color, count in color_counts.items() if count == max_count]
        return random.choice(best_colors)
    
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
