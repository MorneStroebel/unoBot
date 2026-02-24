import random
from .base import BaseStrategy

class BaseBotStrategy(BaseStrategy):
    """
    Play only legal cards.
    """
    def choose_card(self, hand, top_card, current_color):
        for i, card in enumerate(hand):
            if self.is_playable(card, top_card, current_color):
                wild_color = None
                if card['type'].startswith('WILD'):
                    colors = [c['color'] for c in hand if c['color'] != 'BLACK']
                    wild_color = random.choice(colors) if colors else random.choice(['RED','BLUE','GREEN','YELLOW'])
                return i, wild_color
        return None, None

    @staticmethod
    def is_playable(card, top_card, current_color):
        if card['color'] == current_color:
            return True
        if card['type'] == top_card['type'] and card['type'] != 'NUMBER':
            return True
        if card['type'] == 'NUMBER' and top_card['type'] == 'NUMBER' and card['value'] == top_card['value']:
            return True
        if card['type'].startswith('WILD'):
            return True
        return False