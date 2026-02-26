"""
BaseStrategy — the foundation all UnoBot strategies must inherit from.

Every strategy folder must contain:
    __init__.py   – imports the strategy class
    strategy.py   – defines the strategy class (inherits BaseStrategy)
    stats.json    – auto-created; stores persistent stats for this strategy

To create a new strategy:
    1. mkdir strategies/my_strategy
    2. Create __init__.py and strategy.py inside it
    3. Run: python generate_config.py

Stats are tracked automatically — just call record_card_played(),
record_card_drawn(), etc. during choose_card(). Call record_uno_call()
and record_penalty() from the socket listener.
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

    Stats are tracked per-strategy automatically.  During choose_card() call:
        self._record_play(card)     when you decide to play a card
        self._record_draw()         when you decide to draw
    """

    def __init__(self):
        self._session_cards_played: int = 0
        self._session_cards_drawn:  int = 0
        self._session_uno_calls:    int = 0
        self._session_penalties:    int = 0
        self._session_card_types:   Dict[str, int] = {}
        self._session_wild_colors:  Dict[str, int] = {
            "RED": 0, "BLUE": 0, "GREEN": 0, "YELLOW": 0
        }

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    def _record_play(self, card: Dict, wild_color: Optional[str] = None):
        self._session_cards_played += 1
        card_type = card.get("type", "UNKNOWN")
        self._session_card_types[card_type] = (
            self._session_card_types.get(card_type, 0) + 1
        )
        if wild_color and wild_color in self._session_wild_colors:
            self._session_wild_colors[wild_color] += 1

    def _record_draw(self):
        self._session_cards_drawn += 1

    def _record_uno(self):
        self._session_uno_calls += 1

    def _record_penalty(self):
        self._session_penalties += 1

    def _reset_session(self):
        self._session_cards_played = 0
        self._session_cards_drawn  = 0
        self._session_uno_calls    = 0
        self._session_penalties    = 0
        self._session_card_types   = {}
        self._session_wild_colors  = {
            "RED": 0, "BLUE": 0, "GREEN": 0, "YELLOW": 0
        }

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_game_start(self):
        """Called once when a new game begins."""
        self._reset_session()

    def on_game_end(self, won: bool, placement: int, points: int):
        """
        Called when the game ends.
        Subclasses must call super().on_game_end(...) to persist stats.
        """
        self._persist_stats(won, placement, points)

    def on_turn_start(self, hand: List[Dict], top_card: Dict, current_color: str):
        """Called at the start of every turn before choose_card."""
        pass

    # ------------------------------------------------------------------
    # Stats persistence
    # ------------------------------------------------------------------

    def _persist_stats(self, won: bool, placement: int, points: int):
        """Fallback stats save — only runs when no external stats_tracker is active.
        When running via the UI/bot, SocketListener calls stats_tracker.end_game()
        directly, which already persists everything. We guard against double-counting
        by checking for the live_state.json sentinel written by start_game().
        """
        try:
            import os
            strategy_name = self._get_strategy_folder_name()
            strategies_dir = os.path.dirname(os.path.abspath(__file__))
            live_path = os.path.join(strategies_dir, strategy_name, "live_state.json")
            # live_state.json exists while stats_tracker is managing this game session
            if os.path.exists(live_path):
                return  # stats_tracker.end_game() will handle it — don't double-count
            from strategies.stats import StrategyStats
            tracker = StrategyStats(strategy_name)
            tracker.record_game(
                won=won, placement=placement, points=points,
                cards_played=self._session_cards_played,
                cards_drawn=self._session_cards_drawn,
                uno_calls=self._session_uno_calls,
                penalties=self._session_penalties,
                card_type_counts=dict(self._session_card_types),
                wild_color_choices=dict(self._session_wild_colors),
            )
        except Exception as e:
            print(f"⚠️  Could not save stats: {e}", flush=True)

    def _get_strategy_folder_name(self) -> str:
        module = self.__class__.__module__
        parts = module.split(".")
        if len(parts) >= 2 and parts[0] == "strategies":
            return parts[1]
        return self.__class__.__name__.lower()

    # ------------------------------------------------------------------
    # Core method — MUST be implemented by subclasses
    # ------------------------------------------------------------------

    def choose_card(
        self,
        hand: List[Dict[str, Any]],
        top_card: Dict[str, Any],
        current_color: str,
    ) -> Tuple[Optional[int], Optional[str]]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement choose_card()"
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_playable(card: Dict, top_card: Dict, current_color: str) -> bool:
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
        return [
            (i, card)
            for i, card in enumerate(hand)
            if BaseStrategy.is_playable(card, top_card, current_color)
        ]

    @staticmethod
    def pick_wild_color(hand: List[Dict]) -> str:
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
        return [(i, c) for i, c in enumerate(hand) if c["type"] == card_type]

    @staticmethod
    def count_color(hand: List[Dict], color: str) -> int:
        return sum(1 for c in hand if c.get("color") == color)
