from strategies.base_strategy import BaseStrategy
from typing import Optional, Tuple, List, Dict, Any


class ClaudeBaseBot(BaseStrategy):
    """
    Claude Base Bot — A balanced UNO strategy with the following priorities:

    Card play priority (highest to lowest):
      1. WILD_DRAW_FOUR  — when opponent has <= 3 cards (aggressive), else save
      2. DRAW_TWO        — always play to punish opponents
      3. SKIP / REVERSE  — disruptive cards next
      4. Color match     — prefer the color we have the most of
      5. Number match    — fallback number match
      6. WILD            — save wilds; play only if no other option
      7. WILD_DRAW_FOUR  — last resort if still no play

    Wild color: always pick the color we hold the most of.
    Draw: only when truly no playable card exists.
    """

    def __init__(self):
        super().__init__()
        # Track rough opponent card counts (decremented on draw events if available)
        self._opponent_card_counts: Dict[str, int] = {}

    # ------------------------------------------------------------------ #
    #  Core decision method
    # ------------------------------------------------------------------ #

    def choose_card(self, hand, top_card, current_color):
        playable = self.get_playable_cards(hand, top_card, current_color)

        if not playable:
            self._record_draw()
            return None, None

        chosen_idx, chosen_card = self._pick_best(playable, hand)
        wild_color = None
        if chosen_card["type"] in ("WILD", "WILD_DRAW_FOUR"):
            wild_color = self.pick_wild_color(hand)

        self._record_play(chosen_card, wild_color=wild_color)
        return chosen_idx, wild_color

    # ------------------------------------------------------------------ #
    #  Strategy logic
    # ------------------------------------------------------------------ #

    def _pick_best(self, playable, hand):
        """Return (index, card) using priority tiers."""

        # Determine if any opponent appears close to winning
        opponent_danger = self._opponent_in_danger()

        # --- Tier 1: DRAW_TWO — always punish ---
        draw_twos = [(i, c) for i, c in playable if c["type"] == "DRAW_TWO"]
        if draw_twos:
            return draw_twos[0]

        # --- Tier 2: WILD_DRAW_FOUR — aggressive when opponent near win ---
        wd4s = [(i, c) for i, c in playable if c["type"] == "WILD_DRAW_FOUR"]
        if wd4s and opponent_danger:
            return wd4s[0]

        # --- Tier 3: SKIP / REVERSE ---
        disruptive = [(i, c) for i, c in playable
                      if c["type"] in ("SKIP", "REVERSE")]
        if disruptive:
            return disruptive[0]

        # --- Tier 4: Best color match (most cards in hand of that color) ---
        best_color_card = self._best_color_match(playable, hand)
        if best_color_card:
            return best_color_card

        # --- Tier 5: Any number match ---
        numbers = [(i, c) for i, c in playable if c["type"] == "NUMBER"]
        if numbers:
            return numbers[0]

        # --- Tier 6: WILD (plain) ---
        wilds = [(i, c) for i, c in playable if c["type"] == "WILD"]
        if wilds:
            return wilds[0]

        # --- Tier 7: WILD_DRAW_FOUR as last resort ---
        if wd4s:
            return wd4s[0]

        # Fallback — should never reach here if playable is non-empty
        return playable[0]

    def _best_color_match(self, playable, hand):
        """Among playable non-wild cards, pick the one whose color we hold the most."""
        color_cards = [(i, c) for i, c in playable
                       if c["color"] not in ("WILD",)
                       and c["type"] not in ("WILD", "WILD_DRAW_FOUR")]
        if not color_cards:
            return None

        # Score each by how many cards of that color remain in hand
        best = max(color_cards,
                   key=lambda ic: self.count_color(hand, ic[1]["color"]))
        return best

    def _opponent_in_danger(self):
        """Return True if any tracked opponent has <= 3 cards."""
        if not self._opponent_card_counts:
            return False
        return any(v <= 3 for v in self._opponent_card_counts.values())

    # ------------------------------------------------------------------ #
    #  Lifecycle hooks
    # ------------------------------------------------------------------ #

    def on_game_start(self):
        super().on_game_start()
        self._opponent_card_counts = {}

    def on_game_end(self, won, placement, points):
        super().on_game_end(won, placement, points)
