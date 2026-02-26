"""
strategies/stats.py — Per-strategy statistics tracker.

Architecture
------------
Stats are split into two layers:

  1. Persisted stats  (strategies/<name>/stats.json)
     Written ONCE when a game ends.  Never touched mid-game.

  2. Live state       (strategies/<name>/live_state.json)
     Written on every action so the UI server (separate process) can read it.
     Deleted / reset when a new game starts or after game ends.
     Small file (~300 bytes), writes are fast.

The key insight: bot and UI server are separate OS processes.
Module-level dicts are NOT shared.  The only cross-process channel is
the filesystem.
"""

import json
import os
import threading
from datetime import datetime
from typing import Optional, Dict

_STRATEGIES_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Schema helpers ────────────────────────────────────────────────────────────

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
        "strategy_name": None,
        "room_id": None,
        "player_id": None,
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


# ── StrategyStats ─────────────────────────────────────────────────────────────

class StrategyStats:
    """
    Per-strategy stats tracker.

    Used in two modes:
      • Bot process  — calls start_game / record_* / end_game
      • Server process — calls live_snapshot() to read current state
    Both modes communicate via two small JSON files on disk.
    """

    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self._lock = threading.Lock()
        strat_dir = os.path.join(_STRATEGIES_DIR, strategy_name)
        os.makedirs(strat_dir, exist_ok=True)
        self._stats_path = os.path.join(strat_dir, "stats.json")
        self._live_path  = os.path.join(strat_dir, "live_state.json")
        self._data = self._load_stats()
        # In-process cache of live state (only meaningful in bot process)
        self._live_cache: Dict = _default_live()

    # ── Disk helpers ──────────────────────────────────────────────────────────

    def _load_stats(self) -> Dict:
        if os.path.exists(self._stats_path):
            try:
                with open(self._stats_path) as f:
                    loaded = json.load(f)
                base = _default_stats()
                base.update(loaded)
                for c in ("RED", "BLUE", "GREEN", "YELLOW"):
                    base["wild_color_choices"].setdefault(c, 0)
                for p in ("1", "2", "3", "4+"):
                    base["placements"].setdefault(p, 0)
                return base
            except Exception as e:
                print(f"⚠️  Could not load stats for '{self.strategy_name}': {e}", flush=True)
        return _default_stats()

    def _save_stats(self):
        """Write lifetime stats to disk.  Called only at end_game()."""
        self._data["last_updated"] = datetime.now().isoformat()
        try:
            with open(self._stats_path, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"❌ Could not save stats for '{self.strategy_name}': {e}", flush=True)

    def _write_live(self):
        """Write live cache to disk so the server process can read it."""
        try:
            with open(self._live_path, "w") as f:
                json.dump(self._live_cache, f)
        except Exception as e:
            print(f"⚠️  Could not write live_state: {e}", flush=True)

    def _read_live_from_disk(self) -> Dict:
        """Read live state written by the bot process (used by server process)."""
        if os.path.exists(self._live_path):
            try:
                with open(self._live_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return _default_live()

    def _clear_live(self):
        """Reset live cache and delete the live state file."""
        self._live_cache = _default_live()
        try:
            if os.path.exists(self._live_path):
                os.remove(self._live_path)
        except Exception:
            pass

    # ── Game lifecycle (called by bot process) ────────────────────────────────

    def start_game(self, room_id: str, player_id: str, strategy_name: str):
        """Start tracking a new game.  Resets live accumulator."""
        self._live_cache = _default_live()
        self._live_cache.update({
            "active": True,
            "room_id": room_id,
            "player_id": player_id,
            "strategy_name": strategy_name,
            "started_at": datetime.now().isoformat(),
        })
        self._write_live()
        print(f"📊 Stats tracking started (strategy={strategy_name})", flush=True)

    def end_game(self, won: bool, placement: int, points: int):
        """
        Merge live accumulator into lifetime stats and write stats.json once.
        Clears the live state file so the UI shows no active game.
        """
        live = self._live_cache
        with self._lock:
            d = self._data
            d["games_played"] += 1
            d["wins"]   += 1 if won else 0
            d["losses"] += 0 if won else 1
            d["total_points"] += points
            if points > d["best_game_points"]:
                d["best_game_points"] = points
            pk = str(placement) if placement <= 3 else "4+"
            d["placements"][pk] = d["placements"].get(pk, 0) + 1
            d["win_rate"]            = (d["wins"] / d["games_played"]) * 100
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
            self._save_stats()          # ← single disk write for lifetime stats

        self._clear_live()              # ← delete live_state.json, free memory
        self._data = self._load_stats() # ← reload so as_dict() is fresh
        result_str = f"{'WIN' if won else 'LOSS'} #{placement} {points}pts"
        print(f"📊 Stats saved — {result_str}", flush=True)

    # ── In-game action recording (bot process only) ───────────────────────────

    def record_card_played(self, card: dict, wild_color: Optional[str] = None):
        with self._lock:
            self._live_cache["cards_played"] += 1
            self._live_cache["turns"] += 1
            ct = card.get("type", "UNKNOWN")
            self._live_cache["card_type_counts"][ct] = \
                self._live_cache["card_type_counts"].get(ct, 0) + 1
            if wild_color and wild_color in self._live_cache["wild_color_choices"]:
                self._live_cache["wild_color_choices"][wild_color] += 1
        self._write_live()

    def record_card_drawn(self):
        with self._lock:
            self._live_cache["cards_drawn"] += 1
            self._live_cache["turns"] += 1
        self._write_live()

    def record_uno_call(self):
        with self._lock:
            self._live_cache["uno_calls"] += 1
        self._write_live()

    def record_penalty(self):
        with self._lock:
            self._live_cache["penalties"] += 1
        self._write_live()

    def record_hand_size(self, size: int):
        with self._lock:
            self._live_cache["current_hand_size"] = size
        self._write_live()

    # ── Read API (both processes) ─────────────────────────────────────────────

    def live_snapshot(self) -> Dict:
        """
        Return lifetime stats merged with current live game data.
        Reads live_state.json from disk — safe to call from server process.
        No memory leaks: live data is capped to a single small JSON file.
        """
        # Reload persisted stats fresh from disk every call (server process
        # does not keep a long-lived instance, so this is always up to date)
        persisted = self._load_stats()

        snap = dict(persisted)
        snap["card_type_counts"]   = dict(snap.get("card_type_counts", {}))
        snap["wild_color_choices"] = dict(snap.get("wild_color_choices", {}))
        snap["placements"]         = dict(snap.get("placements", {}))

        live = self._read_live_from_disk()
        snap["live_game"] = live

        if live.get("active"):
            snap["total_cards_played"] += live.get("cards_played", 0)
            snap["total_cards_drawn"]  += live.get("cards_drawn",  0)
            snap["total_uno_calls"]    += live.get("uno_calls",    0)
            snap["total_penalties"]    += live.get("penalties",    0)
            for ct, cnt in live.get("card_type_counts", {}).items():
                snap["card_type_counts"][ct] = \
                    snap["card_type_counts"].get(ct, 0) + cnt
            for color, cnt in live.get("wild_color_choices", {}).items():
                if color in snap["wild_color_choices"]:
                    snap["wild_color_choices"][color] += cnt

        return snap

    def reset(self):
        """Wipe all stats and live state for this strategy."""
        with self._lock:
            self._data = _default_stats()
            self._save_stats()
        self._clear_live()

    # ── Legacy shim (kept for compatibility) ──────────────────────────────────

    def record_game(self, won, placement, points,
                    cards_played=0, cards_drawn=0, uno_calls=0, penalties=0,
                    card_type_counts=None, wild_color_choices=None):
        with self._lock:
            d = self._data
            d["games_played"] += 1
            d["wins"]   += 1 if won else 0
            d["losses"] += 0 if won else 1
            d["total_points"] += points
            if points > d["best_game_points"]:
                d["best_game_points"] = points
            pk = str(placement) if placement <= 3 else "4+"
            d["placements"][pk] = d["placements"].get(pk, 0) + 1
            d["win_rate"]            = (d["wins"] / d["games_played"]) * 100
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
            self._save_stats()

    # ── Properties ────────────────────────────────────────────────────────────

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
        return (f"<StrategyStats '{self.strategy_name}' "
                f"games={self.games_played} wr={self.win_rate}%>")
