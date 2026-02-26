"""
strategies/stats.py — Per-strategy statistics tracker.

Architecture
------------
Stats are split into two layers:

  1. **Persisted stats** (stats.json) — lifetime totals written only when a
     game *ends*, so the file is never in a partial/corrupt state mid-game.

  2. **Live / in-memory accumulator** (_live_store) — collects every action
     during the current game.  The UI polls live_snapshot() for real-time
     data without touching the file at all.

When end_game() is called the accumulator is merged into persisted totals
and the file is written exactly once.
"""

import json
import os
import threading
from datetime import datetime
from typing import Optional, Dict

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


def _default_live() -> Dict:
    return {
        "active": False,
        "room_id": None,
        "player_id": None,
        "strategy_name": None,
        "started_at": None,
        "cards_played": 0,
        "cards_drawn": 0,
        "uno_calls": 0,
        "penalties": 0,
        "turns": 0,
        "current_hand_size": 0,
        "card_type_counts": {},
        "wild_color_choices": {"RED": 0, "BLUE": 0, "GREEN": 0, "YELLOW": 0},
    }


# Module-level live store — shared across all StrategyStats instances for the
# same strategy name (so the server can read live data from a fresh instance).
_live_store: Dict[str, Dict] = {}
_live_lock = threading.Lock()


class StrategyStats:
    """Per-strategy stats tracker with in-memory live accumulation."""

    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self._lock = threading.Lock()
        self._stats_path = os.path.join(_STRATEGIES_DIR, strategy_name, "stats.json")
        self._data = self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> Dict:
        if os.path.exists(self._stats_path):
            try:
                with open(self._stats_path) as f:
                    loaded = json.load(f)
                base = _default_stats()
                base.update(loaded)
                for color in ("RED", "BLUE", "GREEN", "YELLOW"):
                    base["wild_color_choices"].setdefault(color, 0)
                for p in ("1", "2", "3", "4+"):
                    base["placements"].setdefault(p, 0)
                return base
            except Exception as e:
                print(f"⚠️  Could not load stats for '{self.strategy_name}': {e}")
        return _default_stats()

    def _save(self):
        """Write persisted stats to disk. Called only at game end."""
        self._data["last_updated"] = datetime.now().isoformat()
        try:
            os.makedirs(os.path.dirname(self._stats_path), exist_ok=True)
            with open(self._stats_path, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"❌ Could not save stats for '{self.strategy_name}': {e}")

    # ── Live accumulator ──────────────────────────────────────────────────────

    def _live(self) -> Dict:
        with _live_lock:
            if self.strategy_name not in _live_store:
                _live_store[self.strategy_name] = _default_live()
            return _live_store[self.strategy_name]

    def _reset_live(self):
        with _live_lock:
            _live_store[self.strategy_name] = _default_live()

    # ── Game lifecycle ────────────────────────────────────────────────────────

    def start_game(self, room_id: str, player_id: str, strategy_name: str):
        """Reset live accumulator and mark game as started."""
        self._reset_live()
        with _live_lock:
            _live_store[self.strategy_name].update({
                "active": True,
                "room_id": room_id,
                "player_id": player_id,
                "strategy_name": strategy_name,
                "started_at": datetime.now().isoformat(),
            })
        print(f"📊 Stats tracking started", flush=True)

    def end_game(self, won: bool, placement: int, points: int):
        """Merge live accumulator into persisted totals and write to disk once."""
        live = self._live()
        with self._lock:
            d = self._data
            d["games_played"] += 1
            d["wins"] += 1 if won else 0
            d["losses"] += 0 if won else 1
            d["total_points"] += points
            if points > d["best_game_points"]:
                d["best_game_points"] = points
            pk = str(placement) if placement <= 3 else "4+"
            d["placements"][pk] = d["placements"].get(pk, 0) + 1
            d["win_rate"] = (d["wins"] / d["games_played"]) * 100
            d["avg_points_per_game"] = d["total_points"] / d["games_played"]
            d["total_cards_played"] += live.get("cards_played", 0)
            d["total_cards_drawn"]  += live.get("cards_drawn",  0)
            d["total_uno_calls"]    += live.get("uno_calls",    0)
            d["total_penalties"]    += live.get("penalties",    0)
            for ct, cnt in live.get("card_type_counts", {}).items():
                d["card_type_counts"][ct] = d["card_type_counts"].get(ct, 0) + cnt
            for color, cnt in live.get("wild_color_choices", {}).items():
                if color in d["wild_color_choices"]:
                    d["wild_color_choices"][color] += cnt
            self._save()   # ← single write per game
        self._reset_live()
        self._data = self._load()
        print(f"📊 Stats saved — {'WIN' if won else 'LOSS'} #{placement} {points}pts", flush=True)

    # ── In-game recording (memory only, no disk I/O) ──────────────────────────

    def record_card_played(self, card: dict, wild_color: Optional[str] = None):
        with _live_lock:
            live = self._live()
            live["cards_played"] += 1
            live["turns"] += 1
            ct = card.get("type", "UNKNOWN")
            live["card_type_counts"][ct] = live["card_type_counts"].get(ct, 0) + 1
            if wild_color and wild_color in live["wild_color_choices"]:
                live["wild_color_choices"][wild_color] += 1

    def record_card_drawn(self):
        with _live_lock:
            live = self._live()
            live["cards_drawn"] += 1
            live["turns"] += 1

    def record_uno_call(self):
        with _live_lock:
            self._live()["uno_calls"] += 1

    def record_penalty(self):
        with _live_lock:
            self._live()["penalties"] += 1

    def record_hand_size(self, size: int):
        with _live_lock:
            self._live()["current_hand_size"] = size

    # ── Read API ──────────────────────────────────────────────────────────────

    def live_snapshot(self) -> Dict:
        """
        Return persisted totals merged with current live game data.
        Safe to call at any time — even mid-game.
        Returned dict includes a 'live_game' key with raw accumulator.
        """
        snap = dict(self._data)
        # Deep-copy sub-dicts so we don't mutate
        snap["card_type_counts"]   = dict(snap["card_type_counts"])
        snap["wild_color_choices"] = dict(snap["wild_color_choices"])
        snap["placements"]         = dict(snap["placements"])

        with _live_lock:
            live = dict(_live_store.get(self.strategy_name, _default_live()))
            live_ctc = dict(live.get("card_type_counts", {}))
            live_wcc = dict(live.get("wild_color_choices", {}))

        snap["live_game"] = live

        if live.get("active"):
            snap["total_cards_played"] += live.get("cards_played", 0)
            snap["total_cards_drawn"]  += live.get("cards_drawn",  0)
            snap["total_uno_calls"]    += live.get("uno_calls",    0)
            snap["total_penalties"]    += live.get("penalties",    0)
            for ct, cnt in live_ctc.items():
                snap["card_type_counts"][ct] = snap["card_type_counts"].get(ct, 0) + cnt
            for color, cnt in live_wcc.items():
                if color in snap["wild_color_choices"]:
                    snap["wild_color_choices"][color] += cnt

        return snap

    def reset(self):
        with self._lock:
            self._data = _default_stats()
            self._save()
        self._reset_live()

    # Legacy shim
    def record_game(self, won, placement, points,
                    cards_played=0, cards_drawn=0, uno_calls=0, penalties=0,
                    card_type_counts=None, wild_color_choices=None):
        with self._lock:
            d = self._data
            d["games_played"] += 1
            d["wins"] += 1 if won else 0
            d["losses"] += 0 if won else 1
            d["total_points"] += points
            if points > d["best_game_points"]:
                d["best_game_points"] = points
            pk = str(placement) if placement <= 3 else "4+"
            d["placements"][pk] = d["placements"].get(pk, 0) + 1
            d["win_rate"] = (d["wins"] / d["games_played"]) * 100
            d["avg_points_per_game"] = d["total_points"] / d["games_played"]
            d["total_cards_played"] += cards_played
            d["total_cards_drawn"]  += cards_drawn
            d["total_uno_calls"]    += uno_calls
            d["total_penalties"]    += penalties
            for ct, cnt in (card_type_counts or {}).items():
                d["card_type_counts"][ct] = d["card_type_counts"].get(ct, 0) + cnt
            for color, cnt in (wild_color_choices or {}).items():
                if color in d["wild_color_choices"]:
                    d["wild_color_choices"][color] += cnt
            self._save()

    # Properties
    @property
    def games_played(self): return self._data["games_played"]
    @property
    def wins(self): return self._data["wins"]
    @property
    def losses(self): return self._data["losses"]
    @property
    def win_rate(self): return round(self._data["win_rate"], 2)
    @property
    def avg_points_per_game(self): return round(self._data["avg_points_per_game"], 2)
    @property
    def total_points(self): return self._data["total_points"]
    @property
    def best_game_points(self): return self._data["best_game_points"]
    @property
    def placements(self): return dict(self._data["placements"])

    def as_dict(self) -> Dict:
        return dict(self._data)

    def summary(self) -> str:
        d = self._data
        p = d["placements"]
        return "\n".join([
            f"Strategy: {self.strategy_name}",
            f"  Games: {d['games_played']} (W:{d['wins']} L:{d['losses']})",
            f"  Win Rate: {d['win_rate']:.1f}%",
            f"  Cards: played={d['total_cards_played']} drawn={d['total_cards_drawn']}",
            f"  UNO={d['total_uno_calls']} Penalties={d['total_penalties']}",
        ])

    def __repr__(self):
        return f"<StrategyStats '{self.strategy_name}' games={self.games_played} wr={self.win_rate}%>"
