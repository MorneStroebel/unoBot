"""
StatsTracker — persistent statistics for UnoBot game sessions.

Tracks per-strategy and overall:
  - Games played, wins, losses, placements
  - Points (total, average, best)
  - Action counts (cards played/drawn, UNO calls, penalties, catchouts)
  - Card-type breakdown and wild-color choices
"""

import json
import os
import threading
from datetime import datetime
from typing import Optional, Dict, Any


_COLORS = ("RED", "BLUE", "GREEN", "YELLOW")


def _default_color_dict() -> Dict[str, int]:
    return {c: 0 for c in _COLORS}


def _default_actions() -> Dict[str, int]:
    return {
        "cards_played": 0,
        "cards_drawn": 0,
        "uno_calls": 0,
        "penalties": 0,
        "catchouts_attempted": 0,
        "catchouts_successful": 0,
    }


def _default_strategy_stats() -> Dict:
    return {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "total_points": 0,
        "win_rate": 0.0,
        "avg_points_per_game": 0.0,
        "placements": {"1": 0, "2": 0, "3": 0, "4+": 0},
        "best_game_points": 0,
        "total_cards_played": 0,
        "total_cards_drawn": 0,
        "total_uno_calls": 0,
        "total_penalties": 0,
    }


def _default_stats() -> Dict:
    return {
        "strategies": {},
        "overall": {
            "total_games": 0,
            "total_wins": 0,
            "total_points": 0,
            "win_rate": 0.0,
        },
        "actions": {
            "total_cards_played": 0,
            "total_cards_drawn": 0,
            "total_uno_calls": 0,
            "total_penalties": 0,
            "total_catchouts_attempted": 0,
            "total_catchouts_successful": 0,
            "card_types": {},
            "colors_chosen": _default_color_dict(),
        },
        "last_updated": None,
    }


class StatsTracker:
    """Thread-safe statistics tracker for UnoBot."""

    def __init__(self, stats_dir: str = "stats"):
        self.stats_dir = stats_dir
        self.stats_file = os.path.join(stats_dir, "statistics.json")
        self.games_file = os.path.join(stats_dir, "game_history.json")
        self._lock = threading.Lock()

        os.makedirs(stats_dir, exist_ok=True)

        self.current_game: Optional[Dict] = None
        self._reset_session()

        self.stats = self._load_stats()
        self.game_history = self._load_game_history()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset_session(self):
        self._session_actions = _default_actions()
        self._session_actions.update({
            "wild_cards_played": 0,
            "action_cards_played": 0,
            "number_cards_played": 0,
        })
        self._session_card_types: Dict[str, int] = {}
        self._session_colors = _default_color_dict()

    def _load_stats(self) -> Dict:
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r") as f:
                    loaded = json.load(f)
                # Back-fill any missing keys so old files still work
                base = _default_stats()
                base.update(loaded)
                # Ensure colors_chosen exists in actions
                base["actions"].setdefault("colors_chosen", _default_color_dict())
                for color in _COLORS:
                    base["actions"]["colors_chosen"].setdefault(color, 0)
                return base
            except Exception as e:
                print(f"⚠️  Error loading stats: {e}")
        return _default_stats()

    def _load_game_history(self) -> list:
        if os.path.exists(self.games_file):
            try:
                with open(self.games_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading game history: {e}")
        return []

    def _save_stats(self):
        self.stats["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.stats_file, "w") as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving stats: {e}")

    def _save_game_history(self):
        try:
            with open(self.games_file, "w") as f:
                json.dump(self.game_history, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving game history: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_game(self, room_id: str, player_id: str, strategy_name: str):
        """Begin tracking a new game session."""
        with self._lock:
            self.current_game = {
                "room_id": room_id,
                "player_id": player_id,
                "strategy": strategy_name,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "result": None,
                "placement": None,
                "points_earned": 0,
                "actions": _default_actions(),
                "card_types_played": {},
                "colors_chosen": _default_color_dict(),
            }
            self._reset_session()
        print(f"📊 Started tracking game — strategy: {strategy_name}")

    def record_card_played(self, card: Dict[str, Any], wild_color: Optional[str] = None):
        """Record a card being played."""
        if not self.current_game:
            return
        with self._lock:
            self._session_actions["cards_played"] += 1
            self.current_game["actions"]["cards_played"] += 1

            card_type = card.get("type", "UNKNOWN")
            self._session_card_types[card_type] = self._session_card_types.get(card_type, 0) + 1
            self.current_game["card_types_played"][card_type] = (
                self.current_game["card_types_played"].get(card_type, 0) + 1
            )

            if card_type.startswith("WILD"):
                self._session_actions["wild_cards_played"] += 1
            elif card_type in ("SKIP", "REVERSE", "DRAW_TWO"):
                self._session_actions["action_cards_played"] += 1
            elif card_type == "NUMBER":
                self._session_actions["number_cards_played"] += 1

            if wild_color and wild_color in self._session_colors:
                self._session_colors[wild_color] += 1
                self.current_game["colors_chosen"][wild_color] += 1

    def record_card_drawn(self):
        """Record a card being drawn."""
        if not self.current_game:
            return
        with self._lock:
            self._session_actions["cards_drawn"] += 1
            self.current_game["actions"]["cards_drawn"] += 1

    def record_uno_call(self):
        """Record an UNO call."""
        if not self.current_game:
            return
        with self._lock:
            self._session_actions["uno_calls"] += 1
            self.current_game["actions"]["uno_calls"] += 1

    def record_penalty(self):
        """Record a penalty received."""
        if not self.current_game:
            return
        with self._lock:
            self._session_actions["penalties"] += 1
            self.current_game["actions"]["penalties"] += 1

    def record_catchout(self, success: bool):
        """Record a catchout attempt."""
        if not self.current_game:
            return
        with self._lock:
            self._session_actions["catchouts_attempted"] += 1
            self.current_game["actions"]["catchouts_attempted"] += 1
            if success:
                self._session_actions["catchouts_successful"] += 1
                self.current_game["actions"]["catchouts_successful"] += 1

    def end_game(self, won: bool, placement: int, points: int):
        """
        Finalise the current game and persist results.

        Args:
            won:       Whether the bot won.
            placement: Finishing position (1 = first).
            points:    Points earned this game.
        """
        if not self.current_game:
            print("⚠️  No active game to end — stats not recorded for this session.")
            return

        with self._lock:
            self.current_game["end_time"] = datetime.now().isoformat()
            self.current_game["result"] = "win" if won else "loss"
            self.current_game["placement"] = placement
            self.current_game["points_earned"] = points

            strategy = self.current_game["strategy"]

            # Initialise strategy stats if first time seeing this strategy
            if strategy not in self.stats["strategies"]:
                self.stats["strategies"][strategy] = _default_strategy_stats()

            s = self.stats["strategies"][strategy]
            s["games_played"] += 1
            if won:
                s["wins"] += 1
            else:
                s["losses"] += 1
            s["total_points"] += points

            # Placement bucket
            placement_key = str(placement) if placement <= 3 else "4+"
            s["placements"][placement_key] = s["placements"].get(placement_key, 0) + 1

            if points > s["best_game_points"]:
                s["best_game_points"] = points

            # Recompute derived fields
            s["win_rate"] = (s["wins"] / s["games_played"]) * 100
            s["avg_points_per_game"] = s["total_points"] / s["games_played"]

            # Accumulate action totals into strategy
            game_actions = self.current_game["actions"]
            s["total_cards_played"] += game_actions["cards_played"]
            s["total_cards_drawn"]  += game_actions["cards_drawn"]
            s["total_uno_calls"]    += game_actions["uno_calls"]
            s["total_penalties"]    += game_actions["penalties"]

            # Overall totals
            overall = self.stats["overall"]
            overall["total_games"] += 1
            if won:
                overall["total_wins"] += 1
            overall["total_points"] += points
            overall["win_rate"] = (overall["total_wins"] / overall["total_games"]) * 100

            # Overall action totals
            actions = self.stats["actions"]
            actions["total_cards_played"]          += game_actions["cards_played"]
            actions["total_cards_drawn"]           += game_actions["cards_drawn"]
            actions["total_uno_calls"]             += game_actions["uno_calls"]
            actions["total_penalties"]             += game_actions["penalties"]
            actions["total_catchouts_attempted"]   += game_actions["catchouts_attempted"]
            actions["total_catchouts_successful"]  += game_actions["catchouts_successful"]

            for card_type, count in self.current_game["card_types_played"].items():
                actions["card_types"][card_type] = actions["card_types"].get(card_type, 0) + count

            for color, count in self.current_game["colors_chosen"].items():
                actions["colors_chosen"].setdefault(color, 0)
                actions["colors_chosen"][color] += count

            self.game_history.append(self.current_game)

            self._save_stats()
            self._save_game_history()

            # Print summary
            emoji = "🏆" if won else "📊"
            print(f"\n{emoji} Game Ended!")
            print(f"   Strategy:    {strategy}")
            print(f"   Result:      {'WIN' if won else 'LOSS'} (Placement: {placement})")
            print(f"   Points:      {points}")
            print(f"   Cards Played:{game_actions['cards_played']}")
            print(f"   Cards Drawn: {game_actions['cards_drawn']}")
            print(f"   Penalties:   {game_actions['penalties']}")
            print(f"\n📈 Strategy Win Rate: {s['win_rate']:.1f}%")
            print(f"📈 Overall Win Rate:  {overall['win_rate']:.1f}%\n")

            self.current_game = None

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_strategy_stats(self, strategy_name: str) -> Optional[Dict]:
        """Return stats for a specific strategy, or None if not found."""
        return self.stats["strategies"].get(strategy_name)

    def get_all_stats(self) -> Dict:
        return self.stats

    def get_recent_games(self, limit: int = 10) -> list:
        return self.game_history[-limit:]

    def print_summary(self):
        """Print a formatted summary of all tracked statistics."""
        print("\n" + "=" * 60)
        print("📊 UNOBOT STATISTICS SUMMARY")
        print("=" * 60)

        overall = self.stats["overall"]
        print("\n🎮 OVERALL PERFORMANCE")
        print(f"   Total Games:  {overall['total_games']}")
        print(f"   Total Wins:   {overall['total_wins']}")
        print(f"   Win Rate:     {overall['win_rate']:.1f}%")
        print(f"   Total Points: {overall['total_points']}")

        if self.stats["strategies"]:
            print("\n🎯 STRATEGY BREAKDOWN")
            for strategy, data in self.stats["strategies"].items():
                p = data["placements"]
                print(f"\n  [{strategy}]")
                print(f"    Games: {data['games_played']}  Wins: {data['wins']}  Losses: {data['losses']}")
                print(f"    Win Rate: {data['win_rate']:.1f}%")
                print(f"    Points — Total: {data['total_points']}  Avg: {data['avg_points_per_game']:.1f}  Best: {data['best_game_points']}")
                print(f"    Placements — 1st: {p['1']}  2nd: {p['2']}  3rd: {p['3']}  4th+: {p['4+']}")

        actions = self.stats["actions"]
        print("\n🎴 ACTION STATISTICS")
        print(f"   Cards Played: {actions['total_cards_played']}")
        print(f"   Cards Drawn:  {actions['total_cards_drawn']}")
        print(f"   UNO Calls:    {actions['total_uno_calls']}")
        print(f"   Penalties:    {actions['total_penalties']}")
        catchouts = f"{actions['total_catchouts_successful']}/{actions['total_catchouts_attempted']}"
        print(f"   Catchouts:    {catchouts}")

        if actions["card_types"]:
            print("\n🃏 CARD TYPES PLAYED")
            for card_type, count in sorted(actions["card_types"].items(), key=lambda x: x[1], reverse=True):
                print(f"   {card_type}: {count}")

        print("\n🎨 WILD COLOR CHOICES")
        for color, count in actions["colors_chosen"].items():
            print(f"   {color}: {count}")

        print("\n" + "=" * 60 + "\n")
