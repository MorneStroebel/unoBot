"""
AdaptiveBotStrategy — a strategy that learns from its own stats over time.

How it works
------------
The bot tracks three weights that control its playing style:

    aggression   (0.0–1.0)  — how eagerly it uses action cards (SKIP, DRAW_TWO…)
    wild_saving  (0.0–1.0)  — how long it holds on to wild cards
    draw_threshold (0–5)    — how many playable cards it needs before preferring
                               to draw (higher = more selective)

After every game, on_game_end() updates these weights using a simple gradient:
  - Win  → reinforce current weights (small nudge toward extremes)
  - Loss → nudge all weights toward the opposite direction

The weights are stored in learning.json alongside stats.json inside the
strategies/adaptive_bot/ folder so they persist across restarts.

Reading the strategy's stats from anywhere:
    from strategies.stats import StrategyStats
    s = StrategyStats("adaptive_bot")
    print(s.summary())
"""

import json
import os
import random
from typing import Optional, Tuple, List, Dict, Any

from strategies.base_strategy import BaseStrategy

_STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
_LEARNING_FILE = os.path.join(_STRATEGY_DIR, "learning.json")

# How far weights shift after each game (tune to taste)
_LEARNING_RATE = 0.05

# How many recent games to consider when deciding whether to reinforce or reverse
_WINDOW = 10


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _load_weights() -> Dict[str, float]:
    if os.path.exists(_LEARNING_FILE):
        try:
            with open(_LEARNING_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Balanced defaults
    return {
        "aggression":     0.5,
        "wild_saving":    0.5,
        "draw_threshold": 0.3,   # maps to 0–5 range; 0.3 ≈ threshold of 1
    }


def _save_weights(weights: Dict[str, float]):
    try:
        with open(_LEARNING_FILE, "w") as f:
            json.dump(weights, f, indent=2)
    except Exception as e:
        print(f"⚠️  Could not save adaptive weights: {e}")


class AdaptiveBotStrategy(BaseStrategy):
    """
    A self-improving UNO strategy.

    It starts with balanced play and gradually shifts its behaviour toward
    whatever style has been producing wins, based on its own stats history.
    """

    def __init__(self):
        super().__init__()
        self._weights = _load_weights()
        self._game_result_won: Optional[bool] = None

        # Per-game decision log used for end-of-game analysis
        self._turn_log: List[Dict] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_game_start(self):
        super().on_game_start()
        self._turn_log = []
        self._game_result_won = None
        self._refresh_weights_from_stats()
        print(
            f"🤖 AdaptiveBot — weights: "
            f"aggression={self._weights['aggression']:.2f}  "
            f"wild_saving={self._weights['wild_saving']:.2f}  "
            f"draw_threshold={self._weights['draw_threshold']:.2f}"
        )

    def on_game_end(self, won: bool, placement: int, points: int):
        self._game_result_won = won
        self._update_weights(won)
        super().on_game_end(won, placement, points)  # persists stats
        emoji = "✅" if won else "❌"
        print(
            f"{emoji} AdaptiveBot game ended — "
            f"{'WIN' if won else 'LOSS'} (P{placement}, {points}pts) | "
            f"new weights: aggression={self._weights['aggression']:.2f} "
            f"wild_saving={self._weights['wild_saving']:.2f}"
        )

    # ------------------------------------------------------------------
    # Core decision logic
    # ------------------------------------------------------------------

    def choose_card(
        self,
        hand: List[Dict[str, Any]],
        top_card: Dict[str, Any],
        current_color: str,
    ) -> Tuple[Optional[int], Optional[str]]:

        playable = self.get_playable_cards(hand, top_card, current_color)

        if not playable:
            self._record_draw()
            return None, None

        # Separate card categories
        numbers   = [(i, c) for i, c in playable if c["type"] == "NUMBER"]
        actions   = [(i, c) for i, c in playable if c["type"] in ("SKIP", "REVERSE", "DRAW_TWO")]
        wilds     = [(i, c) for i, c in playable if c["type"].startswith("WILD")]

        hand_size  = len(hand)
        is_endgame = hand_size <= 3

        # ----- choose a candidate -----

        chosen_idx: Optional[int] = None
        chosen_card: Optional[Dict] = None

        if is_endgame:
            # Endgame: dump highest-point card first
            best = max(playable, key=lambda x: self._card_points(x[1]))
            chosen_idx, chosen_card = best

        else:
            # Evaluate based on learned weights
            aggression    = self._weights["aggression"]
            wild_saving   = self._weights["wild_saving"]
            draw_threshold = int(self._weights["draw_threshold"] * 5)  # 0–5

            # Optionally draw instead of playing a marginal card
            if (
                len(playable) <= draw_threshold
                and len(playable) > 0
                and not actions
                and not wilds
                and random.random() > (aggression + 0.2)
            ):
                self._record_draw()
                return None, None

            # Prefer action cards when aggression is high
            if actions and random.random() < aggression:
                chosen_idx, chosen_card = random.choice(actions)

            # Try to hold wilds when wild_saving is high
            elif numbers and random.random() < wild_saving:
                # Play the number card that leaves the most options (highest value = fewer left)
                chosen_idx, chosen_card = max(numbers, key=lambda x: x[1].get("value", 0))

            elif actions:
                chosen_idx, chosen_card = actions[0]

            elif numbers:
                chosen_idx, chosen_card = max(numbers, key=lambda x: x[1].get("value", 0))

            elif wilds:
                chosen_idx, chosen_card = wilds[0]

            else:
                chosen_idx, chosen_card = playable[0]

        # ----- determine wild color -----
        wild_color: Optional[str] = None
        if chosen_card and chosen_card["type"].startswith("WILD"):
            wild_color = self.pick_wild_color(hand)

        self._record_play(chosen_card, wild_color)
        self._turn_log.append({
            "type": chosen_card["type"] if chosen_card else "DRAW",
            "hand_size": hand_size,
        })

        return chosen_idx, wild_color

    # ------------------------------------------------------------------
    # Weight update logic
    # ------------------------------------------------------------------

    def _refresh_weights_from_stats(self):
        """
        Before a game starts, recalculate the initial weights from cumulative
        stats so the bot adapts even across restarts.
        """
        try:
            from strategies.stats import StrategyStats
            s = StrategyStats("adaptive_bot")
            if s.games_played < 5:
                return  # Not enough data yet, keep current weights

            wr = s.win_rate / 100.0         # 0.0–1.0
            dr = _clamp(s.draw_rate, 0, 1)  # drawn/played ratio

            # High win rate → push aggression up; low → pull it back
            target_aggression = 0.3 + wr * 0.4          # range 0.3–0.7
            # High draw rate hurts; push wild_saving up if we're drawing too much
            target_wild_saving = 0.4 + (1 - dr) * 0.3   # range 0.4–0.7

            w = self._weights
            w["aggression"]  = w["aggression"]  * 0.7 + target_aggression  * 0.3
            w["wild_saving"] = w["wild_saving"]  * 0.7 + target_wild_saving * 0.3
            w["aggression"]  = _clamp(w["aggression"])
            w["wild_saving"] = _clamp(w["wild_saving"])
            _save_weights(w)
        except Exception:
            pass

    def _update_weights(self, won: bool):
        """Nudge weights in the direction that led to a win/loss."""
        w = self._weights
        lr = _LEARNING_RATE

        # Count how many action cards we played (rough signal for aggression)
        action_count = sum(1 for t in self._turn_log if t["type"] in ("SKIP", "REVERSE", "DRAW_TWO"))
        total_turns  = len(self._turn_log) or 1
        played_aggressively = (action_count / total_turns) > w["aggression"]

        if won:
            # Reinforce current behaviour
            if played_aggressively:
                w["aggression"] = _clamp(w["aggression"] + lr)
            else:
                w["aggression"] = _clamp(w["aggression"] - lr)

            # Winning with few wilds played → wild_saving was right
            wild_count = sum(1 for t in self._turn_log if "WILD" in t["type"])
            if wild_count == 0:
                w["wild_saving"] = _clamp(w["wild_saving"] + lr)
        else:
            # Reverse trend
            w["aggression"]     = _clamp(w["aggression"]  + (-lr if played_aggressively else lr))
            w["wild_saving"]    = _clamp(w["wild_saving"]  - lr)
            w["draw_threshold"] = _clamp(w["draw_threshold"] + lr * 0.5)

        _save_weights(w)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _card_points(card: Dict) -> int:
        t = card["type"]
        if t == "NUMBER":
            return card.get("value", 0)
        if t in ("SKIP", "REVERSE", "DRAW_TWO"):
            return 20
        if t in ("WILD", "WILD_DRAW_FOUR"):
            return 50
        return 0
