"""
ClaudeNeroBot — Real-Time Sentence Telemetry
=============================================
Writes human-readable sentences to telemetry.json after every event.
Designed to be read directly in a web app.

JSON structure:
{
  "live":     "Latest status sentence — updates every turn",
  "feed":     ["Line 1", "Line 2", ...],   // current game only, clears each game
  "game":     { "turns": N, "draws": N, "actions": N, "w4": N, "targeted": N,
                "faults": ["FAULT_CODE", ...], "result": "won/2nd/3rd/4th" },
  "lifetime": { "games": N, "wins": N, "win_rate": "X%", "losses": N }
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
MAX_FEED       = 500


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

class Telemetry:
    def __init__(self):
        self._live           = "Bot initialising..."
        self._feed:          List[str] = []
        self._lifetime_games = 0
        self._lifetime_wins  = 0

        # Current game stats — reset each game_start
        self._cur_turns    = 0
        self._cur_draws    = 0
        self._cur_actions  = 0
        self._cur_w4       = 0
        self._cur_targeted = 0
        self._cur_faults:    List[str]  = []
        self._cur_nn_scores: List[float] = []
        self._cur_result   = "in progress"

        self._load_lifetime()
        self._emit(
            f"ClaudeNeroBot loaded. "
            f"Lifetime: {self._lifetime_wins} wins from {self._lifetime_games} games."
        )

    def _reset_game_stats(self):
        self._cur_turns     = 0
        self._cur_draws     = 0
        self._cur_actions   = 0
        self._cur_w4        = 0
        self._cur_targeted  = 0
        self._cur_faults    = []
        self._cur_nn_scores = []
        self._cur_result    = "in progress"

    def _load_lifetime(self):
        try:
            with open(TELEMETRY_FILE) as f:
                d = json.load(f)
            lt = d.get("lifetime", {})
            self._lifetime_games = lt.get("games", 0)
            self._lifetime_wins  = lt.get("wins",  0)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def game_start(self, game_num: int, epsilon: float, replay_size: int):
        self._reset_game_stats()
        self._feed = []          # fresh feed for this game only
        self._cur_game_num = game_num
        explore_pct = round(epsilon * 100)
        self._emit(
            f"Game {game_num} started. "
            f"Exploration rate is {explore_pct}%, "
            f"{replay_size} past experiences in memory."
        )

    def turn(self, turn_num: int, hand_size: int, playable: int,
             mode: str, threat: str, dominant_color: str,
             min_opp: int, nn_score: float, nn_weight: float):
        self._cur_turns = turn_num
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
            "LOW":      f"low — opponents have plenty of cards",
        }.get(threat, threat)

        self._emit(
            f"Turn {turn_num}: holding {hand_size} cards, {playable} playable. "
            f"Mode is {mode}. Threat is {threat_phrase}. "
            f"Dominant colour is {dominant_color}. "
            f"Network is {conf} (score {round(nn_score, 2)}, {nn_pct}% NN weight)."
        )

    def played(self, card_type: str, card_color: str,
               wild_color: str = None, epsilon_used: bool = False):
        if card_type == "NUMBER":
            desc = f"a {card_color} number card"
        elif card_type in ("WILD", "WILD_DRAW_FOUR"):
            label = "Wild Draw Four" if card_type == "WILD_DRAW_FOUR" else "Wild"
            desc  = f"a {label}, choosing {wild_color}"
            if card_type == "WILD_DRAW_FOUR":
                self._cur_w4 += 1
        else:
            desc = f"a {card_color} {card_type.replace('_', ' ').title()}"
            self._cur_actions += 1

        how = "randomly (exploring)" if epsilon_used else "strategically"
        self._emit(f"Played {desc} {how}.")

    def drew(self, current_color: str, stuck: bool = False):
        self._cur_draws += 1
        msg = f"No playable card — drew from the deck. Active colour is {current_color}."
        if stuck:
            msg += f" Warning: stuck on {current_color} again."
        self._emit(msg)

    def targeted(self, by_card: str):
        self._cur_targeted += 1
        self._emit(f"Opponent played {by_card.replace('_', ' ')} against us.")

    def fault(self, code: str, detail: str = ""):
        # Deduplicate — don't repeat the same fault code every turn
        if code in self._cur_faults:
            return
        self._cur_faults.append(code)
        messages = {
            "THREAT_UNMET": f"Warning: opponent is nearly out but we played a safe card. {detail}",
            "LOW_ACTIONS":  f"Warning: in defensive mode but low on attack cards. {detail}",
            "WILD_WASTED":  f"Warning: used a wild when a matching colour card was available. {detail}",
            "STUCK_COLOR":  f"Warning: stuck drawing on {detail} repeatedly.",
            "NN_COLD":      f"Note: network confidence is still low ({detail}) — still learning.",
            "EPSILON_HIGH": f"Note: still exploring heavily after many games. {detail}",
        }
        self._emit(messages.get(code, f"Fault {code}: {detail}"))

    def game_end(self, game_num: int, won: bool, placement: int,
                 points: int, td_errors: List[float]):
        self._lifetime_games += 1
        if won:
            self._lifetime_wins += 1

        self._cur_result = "won" if won else f"finished {_ordinal(placement)}"
        lifetime_wr = round(self._lifetime_wins / self._lifetime_games * 100)

        avg_nn = (round(sum(self._cur_nn_scores) / len(self._cur_nn_scores), 2)
                  if self._cur_nn_scores else 0.0)
        avg_td = (round(sum(abs(e) for e in td_errors) / len(td_errors), 3)
                  if td_errors else 0.0)

        unique_faults = sorted(set(self._cur_faults))
        fault_str = (f"Faults: {', '.join(unique_faults)}."
                     if unique_faults else "No faults.")

        self._emit(
            f"Game over — {self._cur_result} in {self._cur_turns} turns. "
            f"Points scored: {points}. "
            f"Draws: {self._cur_draws}. "
            f"Action cards: {self._cur_actions}. "
            f"Wild Draw Fours: {self._cur_w4}. "
            f"Times targeted: {self._cur_targeted}. "
            f"Network confidence: {avg_nn}. Training error: {avg_td}. "
            f"{fault_str} "
            f"Lifetime: {self._lifetime_wins} wins from {self._lifetime_games} games "
            f"({lifetime_wr}% win rate)."
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
            life_wr = (
                f"{round(self._lifetime_wins / self._lifetime_games * 100)}%"
                if self._lifetime_games else "0%"
            )
            unique_faults = sorted(set(self._cur_faults))
            payload = {
                "live":  self._live,
                "feed":  self._feed,
                "game": {
                    "turns":    self._cur_turns,
                    "draws":    self._cur_draws,
                    "actions":  self._cur_actions,
                    "w4":       self._cur_w4,
                    "targeted": self._cur_targeted,
                    "faults":   unique_faults,
                    "result":   self._cur_result,
                    "avg_nn":   round(sum(self._cur_nn_scores) / len(self._cur_nn_scores), 2)
                                if self._cur_nn_scores else 0.0,
                },
                "lifetime": {
                    "games":    self._lifetime_games,
                    "wins":     self._lifetime_wins,
                    "losses":   self._lifetime_games - self._lifetime_wins,
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
