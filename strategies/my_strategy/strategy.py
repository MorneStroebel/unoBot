from strategies.base_strategy import BaseStrategy
from typing import Optional, Tuple, List, Dict, Any


class MyStrategy(BaseStrategy):
    """
    Aggressive UNO strategy with adaptive play:

    Priority tiers (highest → lowest):
      1. WILD_DRAW_FOUR  — when opponent is dangerous or hand is small
      2. DRAW_TWO        — always aggressive
      3. SKIP / REVERSE  — disruption
      4. NUMBER cards    — prefer the color we hold most of
      5. WILD            — last resort, or when hand ≤ 3 cards

    Color steering: always pick our most-held color for wilds.
    Endgame awareness: if any opponent has ≤ 2 cards, escalate to draw attacks.
    """

    # Card type play-priority weights (lower = higher priority)
    _TYPE_PRIORITY = {
        "WILD_DRAW_FOUR": 0,
        "DRAW_TWO":       1,
        "SKIP":           2,
        "REVERSE":        3,
        "NUMBER":         4,
        "WILD":           5,
    }

    def on_game_start(self):
        super().on_game_start()
        self._opponent_card_counts: Dict[str, int] = {}

    def on_game_end(self, won: bool, placement: int, points: int):
        super().on_game_end(won, placement, points)

    # ------------------------------------------------------------------
    # Core decision
    # ------------------------------------------------------------------

    def choose_card(
        self,
        hand: List[Dict],
        top_card: Dict,
        current_color: str,
        # Extra context injected by some runners — safe to ignore if absent
        **kwargs,
    ) -> Tuple[Optional[int], Optional[str]]:

        playable = self.get_playable_cards(hand, top_card, current_color)

        if not playable:
            self._record_draw()
            return None, None

        hand_size = len(hand)
        opponent_counts: List[int] = list(kwargs.get("opponent_card_counts", {}).values())
        danger = any(c <= 2 for c in opponent_counts)  # someone is close to winning

        chosen_idx, chosen_card = self._pick_best(
            playable, hand, hand_size, danger
        )

        wild_color = None
        if chosen_card["type"] in ("WILD", "WILD_DRAW_FOUR"):
            wild_color = self.pick_wild_color(hand)

        self._record_play(chosen_card, wild_color=wild_color)
        return chosen_idx, wild_color

    # ------------------------------------------------------------------
    # Selection logic
    # ------------------------------------------------------------------

    def _pick_best(
        self,
        playable: List[Tuple[int, Dict]],
        hand: List[Dict],
        hand_size: int,
        danger: bool,
    ) -> Tuple[int, Dict]:
        """
        Score each playable card and return the best one.
        Lower score = better play.
        """
        best_score = float("inf")
        best_pair = playable[0]
        dominant_color = self.pick_wild_color(hand)

        for idx, card in playable:
            score = self._score_card(card, hand_size, danger, dominant_color)
            if score < best_score:
                best_score = score
                best_pair = (idx, card)

        return best_pair

    def _score_card(
        self,
        card: Dict,
        hand_size: int,
        danger: bool,
        dominant_color: str,
    ) -> float:
        ctype = card["type"]

        # Base priority tier
        score = float(self._TYPE_PRIORITY.get(ctype, 4))

        # --- WILD / WILD_DRAW_FOUR adjustments ---
        if ctype == "WILD_DRAW_FOUR":
            # Always great; even better when danger or low hand
            if danger or hand_size <= 3:
                score -= 1.5
            # Slight penalty when we have plenty of other options and lots of cards
            elif hand_size > 6:
                score += 0.5

        elif ctype == "WILD":
            # Hold back wilds unless hand is small or no better option
            if hand_size <= 3:
                score -= 0.5
            else:
                score += 1.5  # discourage early wild use

        # --- Color alignment bonus ---
        # Prefer cards that match our dominant color (keeps momentum)
        if card.get("color") == dominant_color:
            score -= 0.3

        # --- Number card tie-breaking: prefer higher value (dump big points) ---
        if ctype == "NUMBER":
            face = card.get("value", 0)
            score -= face * 0.01  # tiny nudge toward higher numbers

        # --- Danger escalation: punish non-attack cards when opponent near win ---
        if danger and ctype in ("NUMBER", "WILD"):
            score += 1.0

        return score

    # ------------------------------------------------------------------
    # Utility override (optional clarity)
    # ------------------------------------------------------------------

    def pick_wild_color(self, hand: List[Dict]) -> str:
        """Return the color we hold most of; fall back to RED."""
        color_counts = {"RED": 0, "BLUE": 0, "GREEN": 0, "YELLOW": 0}
        for card in hand:
            c = card.get("color")
            if c in color_counts:
                color_counts[c] += 1
        best = max(color_counts, key=lambda k: color_counts[k])
        # If tied at 0, RED is fine
        return best if color_counts[best] > 0 else "RED"
