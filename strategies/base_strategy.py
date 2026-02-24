"""
BaseStrategy — the foundation all UnoBot strategies must inherit from.

This file serves two purposes:
  1. It defines the abstract BaseStrategy class every strategy must extend.
  2. It provides a fully-working reference implementation (plays the first legal
     card it finds, draws when stuck) that you can copy and customise.

To create a new strategy, copy this file, rename the class, and override
`choose_card`. See STRATEGY_GUIDE.md for full instructions.
"""

import random
from typing import Optional, Tuple, List, Dict, Any


class BaseStrategy:
    """
    Abstract base class for all UnoBot strategies.

    Subclasses MUST implement:
        choose_card(hand, top_card, current_color) -> (card_index, wild_color)

    Subclasses MAY override:
        on_game_start()
        on_game_end(won, placement, points)
        on_turn_start(hand, top_card, current_color)
    """

    # ------------------------------------------------------------------
    # Lifecycle hooks  (optional overrides)
    # ------------------------------------------------------------------

    def on_game_start(self):
        """Called once when a new game begins."""
        pass

    def on_game_end(self, won: bool, placement: int, points: int):
        """Called when the game ends with the final result."""
        pass

    def on_turn_start(self, hand: List[Dict], top_card: Dict, current_color: str):
        """Called at the start of every turn before choose_card."""
        pass

    # ------------------------------------------------------------------
    # Core method — MUST be implemented by every strategy
    # ------------------------------------------------------------------

    def choose_card(
        self,
        hand: List[Dict[str, Any]],
        top_card: Dict[str, Any],
        current_color: str,
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Decide which card to play (or whether to draw).

        Args:
            hand:          List of card dicts in the player's hand.
                           Each card has at minimum:
                             - "type":  "NUMBER" | "SKIP" | "REVERSE" | "DRAW_TWO"
                                        | "WILD" | "WILD_DRAW_FOUR"
                             - "color": "RED" | "BLUE" | "GREEN" | "YELLOW" | "BLACK"
                             - "value": int (only present when type == "NUMBER")
            top_card:      The card currently on top of the discard pile.
                           Same structure as a hand card.
            current_color: The active colour. Usually matches top_card["color"]
                           but differs after a wild is played.

        Returns:
            (card_index, wild_color)
              card_index  – int index into `hand` of the card to play,
                            or None to draw instead.
              wild_color  – "RED" | "BLUE" | "GREEN" | "YELLOW" when playing
                            a WILD / WILD_DRAW_FOUR, otherwise None.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement choose_card()"
        )

    # ------------------------------------------------------------------
    # Shared helpers  (available to every strategy)
    # ------------------------------------------------------------------

    @staticmethod
    def is_playable(card: Dict, top_card: Dict, current_color: str) -> bool:
        """
        Return True when *card* is legally playable given the discard state.

        Rules implemented:
          - Wild cards are always playable.
          - A card matching the current colour is playable.
          - A non-number action card matching the top card's type is playable.
          - A number card matching both type and value is playable.
        """
        if card["type"].startswith("WILD"):
            return True
        if card["color"] == current_color:
            return True
        if card["type"] != "NUMBER" and card["type"] == top_card["type"]:
            return True
        if (
            card["type"] == "NUMBER"
            and top_card["type"] == "NUMBER"
            and card.get("value") == top_card.get("value")
        ):
            return True
        return False

    @staticmethod
    def get_playable_cards(
        hand: List[Dict], top_card: Dict, current_color: str
    ) -> List[Tuple[int, Dict]]:
        """
        Return a list of (index, card) pairs for every playable card in hand.
        Order matches the original hand order.
        """
        return [
            (i, card)
            for i, card in enumerate(hand)
            if BaseStrategy.is_playable(card, top_card, current_color)
        ]

    @staticmethod
    def pick_wild_color(hand: List[Dict]) -> str:
        """
        Choose the best colour to call after playing a wild card.
        Picks the colour you hold the most of; falls back to a random choice.
        """
        counts: Dict[str, int] = {}
        for card in hand:
            color = card.get("color", "")
            if color and color != "BLACK":
                counts[color] = counts.get(color, 0) + 1

        if counts:
            return max(counts, key=counts.__getitem__)
        return random.choice(["RED", "BLUE", "GREEN", "YELLOW"])

    @staticmethod
    def cards_by_type(hand: List[Dict], card_type: str) -> List[Tuple[int, Dict]]:
        """Return all (index, card) pairs whose type matches *card_type*."""
        return [(i, c) for i, c in enumerate(hand) if c["type"] == card_type]

    @staticmethod
    def count_color(hand: List[Dict], color: str) -> int:
        """Count how many cards of *color* are in hand."""
        return sum(1 for c in hand if c.get("color") == color)


# ---------------------------------------------------------------------------
# Reference implementation
# ---------------------------------------------------------------------------

class BaseBotStrategy(BaseStrategy):
    """
    The default UnoBot strategy — simple and fully working.

    Behaviour:
      1. Plays the first playable non-wild card found.
      2. Falls back to the first playable wild, choosing the most-held colour.
      3. Draws if nothing is playable.

    This is intentionally simple — copy base_strategy.py as a starting point for your own
    strategy and customise choose_card to your liking.
    """

    def choose_card(
        self,
        hand: List[Dict],
        top_card: Dict,
        current_color: str,
    ) -> Tuple[Optional[int], Optional[str]]:

        playable = self.get_playable_cards(hand, top_card, current_color)

        if not playable:
            return None, None  # Signal to draw a card

        # Prefer non-wild cards first
        non_wilds = [(i, c) for i, c in playable if not c["type"].startswith("WILD")]
        if non_wilds:
            idx, _ = non_wilds[0]
            return idx, None

        # Fall back to wild — pick best colour
        idx, _ = playable[0]
        wild_color = self.pick_wild_color(hand)
        return idx, wild_color
