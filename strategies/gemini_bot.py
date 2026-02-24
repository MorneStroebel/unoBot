from strategies.base import BaseStrategy
from typing import List, Dict, Optional, Tuple


class GeminiBot(BaseStrategy):
    """
    A competitive Uno strategy using weighted heuristics.
    Fixes the AttributeError by implementing local card validation.
    """

    def choose_card(self, hand: List[Dict], top_card: Dict, current_color: str) -> Tuple[Optional[int], Optional[str]]:
        # 1. Identify all playable cards manually
        legal_indices = [
            i for i, card in enumerate(hand)
            if self._is_playable(card, top_card, current_color)
        ]

        if not legal_indices:
            return None, None

        # 2. Separate Wild Draw Fours (Per requirements: only play if no other choice)
        other_legal_indices = [
            i for i in legal_indices if hand[i]['type'] != 'WILD_DRAW_FOUR'
        ]

        wild_four_indices = [
            i for i in legal_indices if hand[i]['type'] == 'WILD_DRAW_FOUR'
        ]

        # 3. Decision Logic
        if other_legal_indices:
            chosen_index = self._select_best_index(other_legal_indices, hand)
        elif wild_four_indices:
            # Only played if other_legal_indices is empty
            chosen_index = wild_four_indices[0]
        else:
            return None, None

        # 4. Handle Wild Color selection
        card_to_play = hand[chosen_index]
        wild_color = None
        if card_to_play['type'] in ['WILD', 'WILD_DRAW_FOUR']:
            wild_color = self._choose_wild_color(hand)

        return chosen_index, wild_color

    def _is_playable(self, card: Dict, top_card: Dict, current_color: str) -> bool:
        """Determines if a card can be played on the current top card."""
        # Wilds are always playable
        if card['type'] in ['WILD', 'WILD_DRAW_FOUR']:
            return True

        # Match by color
        if card['color'] == current_color:
            return True

        # Match by type (Skip on Skip, etc.) or number value
        if card['type'] == top_card['type']:
            if card['type'] == 'NUMBER':
                return card['value'] == top_card['value']
            return True

        return False

    def _select_best_index(self, legal_indices: List[int], hand: List[Dict]) -> int:
        """Weights cards: Actions (50) > High Numbers (10-19) > Wilds (5)."""
        best_index = legal_indices[0]
        max_weight = -1

        for idx in legal_indices:
            card = hand[idx]
            weight = 0
            if card['type'] in ['SKIP', 'REVERSE', 'DRAW_TWO']:
                weight = 50
            elif card['type'] == 'NUMBER':
                weight = 10 + card.get('value', 0)
            elif card['type'] == 'WILD':
                weight = 5

            if weight > max_weight:
                max_weight = weight
                best_index = idx
        return best_index

    def _choose_wild_color(self, hand: List[Dict]) -> str:
        counts = {'RED': 0, 'BLUE': 0, 'GREEN': 0, 'YELLOW': 0}
        for card in hand:
            color = card.get('color')
            if color in counts:
                counts[color] += 1
        return max(counts, key=counts.get)