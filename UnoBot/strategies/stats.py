"""
strategies/stats.py — Per-strategy statistics tracker.

Each strategy stores its own stats in a `stats.json` file inside its folder.
This module provides a clean API for reading and writing those stats, plus a
convenience class for loading any strategy's stats by name.

Usage:
    from strategies.stats import StrategyStats

    # Read stats for a strategy
    s = StrategyStats("adaptive_bot")
    print(s.win_rate)
    print(s.summary())

    # The tracker is used internally by strategies:
    tracker = StrategyStats("adaptive_bot")
    tracker.record_game(won=True, placement=1, points=0, cards_played=12, cards_drawn=2)
"""

import json
import os
import threading
from datetime import datetime
from typing import Optional, Dict, Any


_STRATEGIES_DIR = os.path.dirname(os.path.abspath(__file__))


def _default_stats() -> Dict:
    return {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "total_points": 0,
        "best_game_points": 0,
        "win_rate": 0.0,
        "avg_points_per_game": 0.0,
        "placements": {"1": 0, "2": 0, "3": 0, "4+": 0},
        "total_cards_played": 0,
        "total_cards_drawn": 0,
        "total_uno_calls": 0,
        "total_penalties": 0,
        "card_type_counts": {},
        "wild_color_choices": {"RED": 0, "BLUE": 0, "GREEN": 0, "YELLOW": 0},
        "last_updated": None,
    }


class StrategyStats:
    """
    Read/write statistics for a single strategy.

    The stats are stored in:
        strategies/<strategy_name>/stats.json

    This class is both the tracker used during a game AND the read API
    you can use externally to inspect stats:

        s = StrategyStats("adaptive_bot")
        print(s.win_rate)          # -> float (percentage)
        print(s.games_played)      # -> int
        print(s.summary())         # -> formatted string
        print(s.as_dict())         # -> raw stats dict
    """

    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self._lock = threading.Lock()
        self._stats_path = os.path.join(_STRATEGIES_DIR, strategy_name, "stats.json")
        self._data = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> Dict:
        if os.path.exists(self._stats_path):
            try:
                with open(self._stats_path, "r") as f:
                    loaded = json.load(f)
                base = _default_stats()
                base.update(loaded)
                # Back-fill any missing color keys
                for color in ("RED", "BLUE", "GREEN", "YELLOW"):
                    base["wild_color_choices"].setdefault(color, 0)
                    base["placements"].setdefault("1", 0)
                    base["placements"].setdefault("2", 0)
                    base["placements"].setdefault("3", 0)
                    base["placements"].setdefault("4+", 0)
                return base
            except Exception as e:
                print(f"⚠️  Could not load stats for '{self.strategy_name}': {e}")
        return _default_stats()

    def _save(self):
        self._data["last_updated"] = datetime.now().isoformat()
        try:
            os.makedirs(os.path.dirname(self._stats_path), exist_ok=True)
            with open(self._stats_path, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"❌ Could not save stats for '{self.strategy_name}': {e}")

    # ------------------------------------------------------------------
    # Write API (used by strategies)
    # ------------------------------------------------------------------

    def record_game(
        self,
        won: bool,
        placement: int,
        points: int,
        cards_played: int = 0,
        cards_drawn: int = 0,
        uno_calls: int = 0,
        penalties: int = 0,
        card_type_counts: Optional[Dict[str, int]] = None,
        wild_color_choices: Optional[Dict[str, int]] = None,
    ):
        """
        Record the outcome of a completed game.

        Args:
            won:               True if the strategy won.
            placement:         Finishing position (1 = first place).
            points:            Points earned this game.
            cards_played:      Number of cards played this game.
            cards_drawn:       Number of cards drawn this game.
            uno_calls:         Number of UNO calls this game.
            penalties:         Number of penalties received this game.
            card_type_counts:  Dict mapping card type -> count played this game.
            wild_color_choices: Dict mapping color -> count chosen this game.
        """
        with self._lock:
            d = self._data
            d["games_played"] += 1
            if won:
                d["wins"] += 1
            else:
                d["losses"] += 1
            d["total_points"] += points
            if points > d["best_game_points"]:
                d["best_game_points"] = points

            placement_key = str(placement) if placement <= 3 else "4+"
            d["placements"][placement_key] = d["placements"].get(placement_key, 0) + 1

            # Derived fields
            d["win_rate"] = (d["wins"] / d["games_played"]) * 100
            d["avg_points_per_game"] = d["total_points"] / d["games_played"]

            # Action totals
            d["total_cards_played"] += cards_played
            d["total_cards_drawn"]  += cards_drawn
            d["total_uno_calls"]    += uno_calls
            d["total_penalties"]    += penalties

            # Card type breakdown
            for card_type, count in (card_type_counts or {}).items():
                d["card_type_counts"][card_type] = (
                    d["card_type_counts"].get(card_type, 0) + count
                )

            # Wild color choices
            for color, count in (wild_color_choices or {}).items():
                if color in d["wild_color_choices"]:
                    d["wild_color_choices"][color] += count

            self._save()

    def reset(self):
        """Wipe all stats for this strategy."""
        with self._lock:
            self._data = _default_stats()
            self._save()

    # ------------------------------------------------------------------
    # Read API (use externally to inspect any strategy)
    # ------------------------------------------------------------------

    @property
    def games_played(self) -> int:
        return self._data["games_played"]

    @property
    def wins(self) -> int:
        return self._data["wins"]

    @property
    def losses(self) -> int:
        return self._data["losses"]

    @property
    def win_rate(self) -> float:
        """Win rate as a percentage (0–100)."""
        return round(self._data["win_rate"], 2)

    @property
    def avg_points_per_game(self) -> float:
        return round(self._data["avg_points_per_game"], 2)

    @property
    def total_points(self) -> int:
        return self._data["total_points"]

    @property
    def best_game_points(self) -> int:
        return self._data["best_game_points"]

    @property
    def placements(self) -> Dict[str, int]:
        return dict(self._data["placements"])

    @property
    def draw_rate(self) -> float:
        """Average cards drawn per card played (0 if no cards played)."""
        played = self._data["total_cards_played"]
        drawn  = self._data["total_cards_drawn"]
        if played == 0:
            return 0.0
        return round(drawn / played, 2)

    def as_dict(self) -> Dict:
        """Return the raw stats dict (a copy)."""
        return dict(self._data)

    def summary(self) -> str:
        """Return a human-readable summary string."""
        d = self._data
        p = d["placements"]
        lines = [
            f"Strategy: {self.strategy_name}",
            f"  Games:       {d['games_played']}  (W: {d['wins']}  L: {d['losses']})",
            f"  Win Rate:    {d['win_rate']:.1f}%",
            f"  Points:      total={d['total_points']}  avg={d['avg_points_per_game']:.1f}  best={d['best_game_points']}",
            f"  Placements:  1st={p['1']}  2nd={p['2']}  3rd={p['3']}  4th+={p['4+']}",
            f"  Cards:       played={d['total_cards_played']}  drawn={d['total_cards_drawn']}",
            f"  UNO Calls:   {d['total_uno_calls']}  Penalties: {d['total_penalties']}",
        ]
        if d["card_type_counts"]:
            breakdown = "  ".join(f"{k}={v}" for k, v in sorted(d["card_type_counts"].items()))
            lines.append(f"  Card Types:  {breakdown}")
        colors = d["wild_color_choices"]
        if any(colors.values()):
            color_str = "  ".join(f"{k}={v}" for k, v in colors.items())
            lines.append(f"  Wild Colors: {color_str}")
        if d["last_updated"]:
            lines.append(f"  Last Update: {d['last_updated'][:19]}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"<StrategyStats '{self.strategy_name}' "
            f"games={self.games_played} win_rate={self.win_rate}%>"
        )
