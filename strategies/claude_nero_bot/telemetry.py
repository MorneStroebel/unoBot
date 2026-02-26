"""
ClaudeNeroBot — Real-Time Sentence Telemetry
=============================================
Writes human-readable sentences to telemetry.json after every event.
Designed to be read directly in a web app.

JSON structure:
{
  "live":    "Latest status sentence — updates every turn",
  "feed":    ["Most recent line", ...],   // last 200 lines, newest at end
  "session": {"games": N, "wins": N, "win_rate": "X%"},
  "lifetime":{"games": N, "wins": N, "win_rate": "X%"}
}
"""

import json
import os
import time
from typing import List

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _find_bot_dir() -> str:
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        pass
    import sys
    for base in sys.path:
        c = os.path.join(base, "claude_nero_bot")
        if os.path.isdir(c): return c
    return os.getcwd()

TELEMETRY_FILE = os.path.join(_find_bot_dir(), "telemetry.json")
MAX_FEED       = 200


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

class Telemetry:
    def __init__(self):
        self._feed:          List[str] = []
        self._session_games  = 0
        self._session_wins   = 0
        self._lifetime_games = 0
        self._lifetime_wins  = 0
        self._live           = "Bot initialising..."
        self._init_cur_game(0)
        self._load_lifetime()
        self._emit(
            f"ClaudeNeroBot started. "
            f"Lifetime record: {self._lifetime_wins} wins from {self._lifetime_games} games."
        )

    def _init_cur_game(self, game_num: int):
        """Reset per-game accumulators. Safe to call any time."""
        self._cur_game_num   = game_num
        self._cur_turn       = 0
        self._cur_draws      = 0
        self._cur_actions    = 0
        self._cur_w4         = 0
        self._cur_targeted   = 0
        self._cur_faults:    List[str] = []
        self._cur_nn_scores: List[float] = []

    def _ensure_game(self):
        """Auto-bootstrap game context if game_start() was never called."""
        if not hasattr(self, '_cur_faults'):
            self._init_cur_game(1)

    def _load_lifetime(self):
        try:
            with open(TELEMETRY_FILE) as f:
                d = json.load(f)
            lt = d.get("lifetime", {})
            self._lifetime_games = lt.get("games", 0)
            self._lifetime_wins  = lt.get("wins",  0)
            self._feed = d.get("feed", [])[-MAX_FEED:]
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def game_start(self, game_num: int, epsilon: float, replay_size: int):
        self._init_cur_game(game_num)
        explore_pct = round(epsilon * 100)
        self._emit(
            f"Game {game_num} started. "
            f"Exploration rate is {explore_pct}% with {replay_size} past experiences loaded."
        )

    def turn(self, turn_num: int, hand_size: int, playable: int,
             mode: str, threat: str, dominant_color: str,
             min_opp: int, nn_score: float, nn_weight: float):
        self._ensure_game()
        self._cur_turn = turn_num
        if nn_score > 0:
            self._cur_nn_scores.append(nn_score)

        conf = (
            "very confident" if nn_score > 0.70 else
            "confident"      if nn_score > 0.55 else
            "uncertain"      if nn_score > 0.40 else
            "guessing"
        )
        nn_pct = round(nn_weight * 100)
        threat_phrase = {
            "CRITICAL": f"CRITICAL — opponent has only {min_opp} card(s) left",
            "HIGH":     f"high — closest opponent has {min_opp} cards",
            "MEDIUM":   f"medium — closest opponent has {min_opp} cards",
            "LOW":      f"low — opponents still have plenty of cards",
        }.get(threat, threat)

        self._emit(
            f"Turn {turn_num}: holding {hand_size} cards with {playable} playable. "
            f"Mode is {mode}. Threat level is {threat_phrase}. "
            f"Dominant colour is {dominant_color}. "
            f"Network is {conf} (score {round(nn_score, 2)}, {nn_pct}% NN vs heuristic)."
        )

    def played(self, card_type: str, card_color: str,
               wild_color: str = None, epsilon_used: bool = False):
        self._ensure_game()
        if card_type == "NUMBER":
            desc = f"a {card_color} number card"
        elif card_type in ("WILD", "WILD_DRAW_FOUR"):
            desc = f"{card_type.replace('_', ' ').title()} choosing {wild_color}"
            if card_type == "WILD_DRAW_FOUR":
                self._cur_w4 += 1
        else:
            desc = f"a {card_color} {card_type.replace('_', ' ').title()}"
            self._cur_actions += 1

        how = "randomly (exploring)" if epsilon_used else "strategically"
        self._emit(f"Played {desc} {how}.")

    def drew(self, current_color: str, stuck: bool = False):
        self._ensure_game()
        self._cur_draws += 1
        msg = f"No playable card — drew from the deck. Current colour is {current_color}."
        if stuck:
            msg += f" WARNING: stuck on {current_color} again."
        self._emit(msg)

    def targeted(self, by_card: str):
        self._ensure_game()
        self._cur_targeted += 1
        self._emit(f"Opponent played {by_card.replace('_', ' ')} against us.")

    def fault(self, code: str, detail: str = ""):
        self._ensure_game()
        self._cur_faults.append(code)
        messages = {
            "THREAT_UNMET": f"Fault THREAT_UNMET — played a safe card while an opponent is nearly out. {detail}",
            "LOW_ACTIONS":  f"Fault LOW_ACTIONS — in defensive mode but running low on attack cards. {detail}",
            "WILD_WASTED":  f"Fault WILD_WASTED — used a wild card when matching colour cards were available. {detail}",
            "STUCK_COLOR":  f"Fault STUCK_COLOR — forced to draw on {detail} multiple turns in a row.",
            "NN_COLD":      f"Fault NN_COLD — network confidence is low ({detail}), still learning from early games.",
            "EPSILON_HIGH": f"Fault EPSILON_HIGH — still exploring too randomly after many games. {detail}",
        }
        self._emit(messages.get(code, f"Fault {code}: {detail}"))

    def game_end(self, game_num: int, won: bool, placement: int,
                 points: int, total_turns: int, td_errors: List[float]):
        self._ensure_game()
        self._session_games  += 1
        self._lifetime_games += 1
        if won:
            self._session_wins  += 1
            self._lifetime_wins += 1

        result = "won" if won else f"finished {_ordinal(placement)}"
        avg_nn = round(sum(self._cur_nn_scores) / len(self._cur_nn_scores), 2) \
                 if self._cur_nn_scores else 0.0
        avg_td = round(sum(abs(e) for e in td_errors) / len(td_errors), 3) \
                 if td_errors else 0.0
        fault_summary = (
            f"Faults this game: {', '.join(sorted(set(self._cur_faults)))}."
            if self._cur_faults else "No faults this game."
        )
        sess_wr     = round(self._session_wins / self._session_games * 100)
        lifetime_wr = round(self._lifetime_wins / self._lifetime_games * 100)

        self._emit(
            f"Game {game_num} over — {result} in {total_turns} turns. "
            f"Scored {points} points. "
            f"Draws: {self._cur_draws}. Actions played: {self._cur_actions}. "
            f"Wild Draw Fours: {self._cur_w4}. Targeted: {self._cur_targeted} times. "
            f"Average network confidence: {avg_nn}. Average training error: {avg_td}. "
            f"{fault_summary} "
            f"Session win rate: {sess_wr}% ({self._session_wins}/{self._session_games}). "
            f"Lifetime win rate: {lifetime_wr}% ({self._lifetime_wins}/{self._lifetime_games})."
        )
        self._flush()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(self, sentence: str):
        ts   = time.strftime("%H:%M:%S")
        line = f"[{ts}] {sentence}"
        self._live = line
        self._feed.append(line)
        if len(self._feed) > MAX_FEED:
            self._feed = self._feed[-MAX_FEED:]
        self._flush()
        print(f"[TELEMETRY] {line}")

    def _flush(self):
        try:
            sess_wr = (
                f"{round(self._session_wins / self._session_games * 100)}%"
                if self._session_games else "0%"
            )
            life_wr = (
                f"{round(self._lifetime_wins / self._lifetime_games * 100)}%"
                if self._lifetime_games else "0%"
            )
            payload = {
                "live":    self._live,
                "feed":    self._feed,
                "session": {
                    "games":    self._session_games,
                    "wins":     self._session_wins,
                    "win_rate": sess_wr,
                },
                "lifetime": {
                    "games":    self._lifetime_games,
                    "wins":     self._lifetime_wins,
                    "win_rate": life_wr,
                },
            }
            tmp = TELEMETRY_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp, TELEMETRY_FILE)
        except Exception as e:
            print(f"[TELEMETRY] Write failed: {e}")


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")
