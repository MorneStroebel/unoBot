"""
ClaudeNeroBot — F1-Style Telemetry System
==========================================
Records every measurable event during a game and session, writes to
telemetry.json for post-session analysis and sharing with the dev.

Inspired by F1 data channels:
  - Sector times     → turn timing / performance per phase
  - Tyre degradation → hand degradation (card count over time)
  - DRS / ERS usage  → wild card / action card deployment events
  - Lap delta        → win delta vs. opponents
  - Fault codes      → anomalies detected mid-game

Data saved to: claude_nero_bot/telemetry.json (human-readable, shareable)
"""

import json
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional


TELEMETRY_FILE = os.path.join(os.path.dirname(__file__), "telemetry.json")
MAX_SESSIONS_STORED = 20   # keep last 20 sessions in file


# ---------------------------------------------------------------------------
# Turn Record — one per turn, like an F1 sector
# ---------------------------------------------------------------------------

class TurnRecord:
    def __init__(self, turn: int):
        self.turn              = turn
        self.timestamp         = time.time()

        # Hand state
        self.hand_size         = 0
        self.playable_count    = 0
        self.dominant_color    = ""
        self.hand_colors       = {}       # {color: count}
        self.hand_action_count = 0
        self.hand_wild_count   = 0

        # Decision
        self.mode              = "NORMAL"    # NORMAL/OFFENSIVE/DEFENSIVE/ENDGAME
        self.epsilon_used      = False       # random exploration turn?
        self.card_played       = None        # card dict or None (drew)
        self.wild_color_chosen = None
        self.drew_card         = False
        self.nn_score          = 0.0         # network's confidence in the chosen state
        self.heuristic_score   = 0.0
        self.nn_weight         = 0.0         # how much NN vs heuristic this turn

        # Opponent snapshot
        self.opponent_counts   = {}          # {pid: card_count}
        self.min_opp_cards     = 7
        self.threat_level      = "LOW"       # LOW / MEDIUM / HIGH / CRITICAL
        self.pain_color        = None

        # Anomalies / fault codes
        self.faults            = []          # list of fault strings

    def to_dict(self) -> Dict:
        return {
            "turn":              self.turn,
            "ts":                round(self.timestamp, 3),
            "hand_size":         self.hand_size,
            "playable_count":    self.playable_count,
            "dominant_color":    self.dominant_color,
            "hand_colors":       self.hand_colors,
            "hand_actions":      self.hand_action_count,
            "hand_wilds":        self.hand_wild_count,
            "mode":              self.mode,
            "epsilon_used":      self.epsilon_used,
            "card_played":       self.card_played,
            "wild_color":        self.wild_color_chosen,
            "drew":              self.drew_card,
            "nn_score":          round(self.nn_score, 4),
            "heuristic_score":   round(self.heuristic_score, 4),
            "nn_weight":         round(self.nn_weight, 3),
            "opp_counts":        self.opponent_counts,
            "min_opp_cards":     self.min_opp_cards,
            "threat":            self.threat_level,
            "pain_color":        self.pain_color,
            "faults":            self.faults,
        }


# ---------------------------------------------------------------------------
# Game Record — one per game, like an F1 race report
# ---------------------------------------------------------------------------

class GameRecord:
    def __init__(self, game_id: int, games_trained: int, epsilon: float):
        self.game_id        = game_id
        self.games_trained  = games_trained
        self.epsilon        = round(epsilon, 4)
        self.start_time     = time.time()
        self.end_time       = None

        # Outcome
        self.won            = False
        self.placement      = 0
        self.points_scored  = 0
        self.total_turns    = 0

        # Aggregated performance channels (like F1 lap summary)
        self.draws_taken        = 0
        self.cards_played       = 0
        self.action_cards_used  = 0
        self.wilds_used         = 0
        self.w4_used            = 0
        self.times_targeted     = 0     # times an opponent played DRAW_TWO/W4 on us
        self.color_changes      = 0     # how many times we changed the colour
        self.exploration_turns  = 0     # epsilon random turns

        # Mode distribution
        self.mode_counts: Dict[str, int] = defaultdict(int)

        # Neural net stats
        self.avg_nn_score    = 0.0
        self.nn_scores       = []
        self.td_errors       = []       # training errors at end of game
        self.terminal_reward = 0.0

        # Fault log
        self.faults: List[str] = []

        # Turn-by-turn data
        self.turns: List[TurnRecord] = []

    def add_turn(self, t: TurnRecord):
        self.turns.append(t)
        self.total_turns = len(self.turns)
        self.mode_counts[t.mode] += 1
        if t.drew_card:      self.draws_taken += 1
        if t.card_played:    self.cards_played += 1
        if t.epsilon_used:   self.exploration_turns += 1
        if t.nn_score > 0:   self.nn_scores.append(t.nn_score)
        if t.faults:         self.faults.extend(t.faults)

        if t.card_played:
            ct = t.card_played.get("type","")
            if ct in ("SKIP","REVERSE","DRAW_TWO"): self.action_cards_used += 1
            if ct == "WILD":            self.wilds_used += 1
            if ct == "WILD_DRAW_FOUR":  self.w4_used += 1

    def close(self, won: bool, placement: int, points: int,
              terminal_reward: float, td_errors: List[float]):
        self.end_time        = time.time()
        self.won             = won
        self.placement       = placement
        self.points_scored   = points
        self.terminal_reward = round(terminal_reward, 4)
        self.td_errors       = [round(e, 4) for e in td_errors[-20:]]  # last 20
        self.avg_nn_score    = round(
            sum(self.nn_scores) / len(self.nn_scores), 4) if self.nn_scores else 0.0

    def duration_s(self) -> float:
        if self.end_time:
            return round(self.end_time - self.start_time, 2)
        return round(time.time() - self.start_time, 2)

    def to_dict(self) -> Dict:
        return {
            "game_id":          self.game_id,
            "games_trained":    self.games_trained,
            "epsilon":          self.epsilon,
            "duration_s":       self.duration_s(),

            # Outcome
            "won":              self.won,
            "placement":        self.placement,
            "points_scored":    self.points_scored,
            "terminal_reward":  self.terminal_reward,
            "total_turns":      self.total_turns,

            # Performance channels
            "draws_taken":      self.draws_taken,
            "cards_played":     self.cards_played,
            "action_cards":     self.action_cards_used,
            "wilds":            self.wilds_used,
            "wild_draw_fours":  self.w4_used,
            "color_changes":    self.color_changes,
            "exploration_pct":  round(self.exploration_turns / max(self.total_turns,1) * 100, 1),

            # Mode distribution
            "mode_dist":        dict(self.mode_counts),

            # Neural net diagnostics
            "avg_nn_score":     self.avg_nn_score,
            "td_errors":        self.td_errors,

            # Fault codes
            "faults":           list(set(self.faults)),

            # Turn-by-turn
            "turn_log":         [t.to_dict() for t in self.turns],
        }


# ---------------------------------------------------------------------------
# Session Record — wraps all games in one run
# ---------------------------------------------------------------------------

class SessionRecord:
    def __init__(self):
        self.session_id  = int(time.time())
        self.start_time  = time.time()
        self.games: List[GameRecord] = []

    def add_game(self, g: GameRecord):
        self.games.append(g)

    @property
    def win_rate(self) -> float:
        if not self.games: return 0.0
        return round(sum(1 for g in self.games if g.won) / len(self.games) * 100, 1)

    @property
    def avg_placement(self) -> float:
        if not self.games: return 0.0
        return round(sum(g.placement for g in self.games) / len(self.games), 2)

    @property
    def avg_turns(self) -> float:
        if not self.games: return 0.0
        return round(sum(g.total_turns for g in self.games) / len(self.games), 1)

    def to_dict(self) -> Dict:
        return {
            "session_id":   self.session_id,
            "start_time":   self.start_time,
            "total_games":  len(self.games),
            "win_rate_pct": self.win_rate,
            "avg_placement":self.avg_placement,
            "avg_turns":    self.avg_turns,
            "games":        [g.to_dict() for g in self.games],
        }


# ---------------------------------------------------------------------------
# Telemetry Manager — singleton-style, used by the strategy
# ---------------------------------------------------------------------------

class Telemetry:
    """
    Main telemetry interface. Strategy calls these methods;
    Telemetry handles all logging and disk I/O.
    """

    def __init__(self):
        self._session    = SessionRecord()
        self._cur_game:  Optional[GameRecord] = None
        self._cur_turn:  Optional[TurnRecord] = None
        self._game_counter = self._load_game_counter()

    def _load_game_counter(self) -> int:
        try:
            with open(TELEMETRY_FILE) as f:
                data = json.load(f)
            sessions = data.get("sessions", [])
            if sessions:
                last = sessions[-1]
                last_games = last.get("games", [])
                if last_games:
                    return last_games[-1].get("game_id", 0) + 1
        except Exception:
            pass
        return 1

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------

    def start_game(self, games_trained: int, epsilon: float):
        self._cur_game = GameRecord(self._game_counter, games_trained, epsilon)
        self._game_counter += 1

    def end_game(self, won: bool, placement: int, points: int,
                 terminal_reward: float, td_errors: List[float]):
        if not self._cur_game: return
        self._cur_game.close(won, placement, points, terminal_reward, td_errors)
        self._session.add_game(self._cur_game)
        self._flush()
        self._cur_game = None

    # ------------------------------------------------------------------
    # Turn lifecycle
    # ------------------------------------------------------------------

    def start_turn(self, turn: int):
        self._cur_turn = TurnRecord(turn)

    def end_turn(self):
        if self._cur_game and self._cur_turn:
            self._cur_game.add_turn(self._cur_turn)
        self._cur_turn = None

    # ------------------------------------------------------------------
    # Data channels — called by strategy during choose_card
    # ------------------------------------------------------------------

    def record_hand(self, hand: List[Dict], playable_count: int,
                    dominant_color: str, color_counts: Dict[str, int]):
        if not self._cur_turn: return
        t = self._cur_turn
        t.hand_size       = len(hand)
        t.playable_count  = playable_count
        t.dominant_color  = dominant_color
        t.hand_colors     = {k: v for k, v in color_counts.items() if v > 0}
        t.hand_action_count = sum(1 for c in hand
                                  if c["type"] in ("SKIP","REVERSE","DRAW_TWO"))
        t.hand_wild_count   = sum(1 for c in hand
                                  if c["type"] in ("WILD","WILD_DRAW_FOUR"))

    def record_opponents(self, opp_counts: Dict[str, int], pain_color: Optional[str]):
        if not self._cur_turn: return
        t = self._cur_turn
        t.opponent_counts = dict(opp_counts)
        t.min_opp_cards   = min(opp_counts.values()) if opp_counts else 7
        t.pain_color      = pain_color

        # Threat level — like F1 gap-to-leader warning
        m = t.min_opp_cards
        if m <= 1:   t.threat_level = "CRITICAL"
        elif m <= 2: t.threat_level = "HIGH"
        elif m <= 4: t.threat_level = "MEDIUM"
        else:        t.threat_level = "LOW"

    def record_decision(self, mode: str, epsilon_used: bool,
                        nn_score: float, heuristic_score: float, nn_weight: float):
        if not self._cur_turn: return
        t = self._cur_turn
        t.mode            = mode
        t.epsilon_used    = epsilon_used
        t.nn_score        = nn_score
        t.heuristic_score = heuristic_score
        t.nn_weight       = nn_weight

    def record_play(self, card: Dict, wild_color: Optional[str]):
        if not self._cur_turn: return
        self._cur_turn.card_played = {
            "type":  card.get("type"),
            "color": card.get("color"),
            "value": card.get("value"),
        }
        self._cur_turn.wild_color_chosen = wild_color

    def record_draw(self):
        if not self._cur_turn: return
        self._cur_turn.drew_card = True

    def record_color_change(self, old_color: str, new_color: str):
        if self._cur_game and old_color != new_color:
            self._cur_game.color_changes += 1

    def record_targeted(self, card_type: str):
        """Called when an opponent plays a draw card against us."""
        if self._cur_game:
            self._cur_game.times_targeted += 1

    # ------------------------------------------------------------------
    # Fault codes — like F1 MGU-K failure codes
    # ------------------------------------------------------------------

    def fault(self, code: str, detail: str = ""):
        """
        Fault codes:
          NO_PLAY      — no playable cards (forced draw)
          STUCK_COLOR  — drew 3+ times on same color in a game
          LOW_ACTIONS  — ≤1 action card when in DEFENSIVE mode
          WILD_WASTED  — played wild when same color was available
          THREAT_UNMET — CRITICAL threat but no attack card played
          NN_COLD      — network confidence very low (<0.35) — still learning
          EPSILON_HIGH — still exploring >15% turns after 100+ games
        """
        msg = f"{code}" + (f":{detail}" if detail else "")
        if self._cur_turn:
            self._cur_turn.faults.append(msg)
        elif self._cur_game:
            self._cur_game.faults.append(msg)

    # ------------------------------------------------------------------
    # Summary printer — logged to stdout after each game
    # ------------------------------------------------------------------

    def print_game_summary(self):
        if not self._session.games: return
        g = self._session.games[-1]
        result = "WIN 🏆" if g.won else f"P{g.placement}"
        faults = ", ".join(set(g.faults)) if g.faults else "none"
        avg_threat = "—"
        if g.turns:
            th_map = {"LOW":0,"MEDIUM":1,"HIGH":2,"CRITICAL":3}
            avg_t = sum(th_map.get(t.threat_level,0) for t in g.turns) / len(g.turns)
            avg_threat = ["LOW","MEDIUM","HIGH","CRITICAL"][min(3, int(avg_t + 0.5))]

        print(
            f"\n[TELEMETRY] Game #{g.game_id} | {result} | "
            f"Turns:{g.total_turns} | Draws:{g.draws_taken} | "
            f"Actions:{g.action_cards_used} | W4:{g.w4_used} | "
            f"Explore:{round(g.exploration_turns/max(g.total_turns,1)*100,1)}% | AvgNN:{g.avg_nn_score:.3f} | "
            f"Threat:{avg_threat} | Faults:[{faults}]"
        )
        # Session rolling stats
        print(
            f"[TELEMETRY] Session: {len(self._session.games)} games | "
            f"WR:{self._session.win_rate}% | "
            f"AvgPlace:{self._session.avg_placement} | "
            f"ε:{g.epsilon:.3f}"
        )

    # ------------------------------------------------------------------
    # Disk I/O
    # ------------------------------------------------------------------

    def _flush(self):
        """Append current session to telemetry.json."""
        try:
            # Load existing data
            try:
                with open(TELEMETRY_FILE) as f:
                    data = json.load(f)
            except Exception:
                data = {"sessions": [], "meta": {"version": "1.0", "bot": "ClaudeNeroBot"}}

            # Update or append current session
            sessions = data.get("sessions", [])
            cur_dict = self._session.to_dict()

            # Replace if same session_id already exists, else append
            replaced = False
            for i, s in enumerate(sessions):
                if s.get("session_id") == self._session.session_id:
                    sessions[i] = cur_dict
                    replaced = True
                    break
            if not replaced:
                sessions.append(cur_dict)

            # Keep only last MAX_SESSIONS_STORED sessions
            data["sessions"] = sessions[-MAX_SESSIONS_STORED:]

            # Compute lifetime summary
            all_games = [g for s in data["sessions"] for g in s.get("games", [])]
            total     = len(all_games)
            wins      = sum(1 for g in all_games if g.get("won"))
            data["lifetime"] = {
                "total_games":  total,
                "total_wins":   wins,
                "win_rate_pct": round(wins / total * 100, 1) if total else 0,
                "avg_placement":round(sum(g.get("placement",0) for g in all_games)
                                      / total, 2) if total else 0,
            }

            with open(TELEMETRY_FILE, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"[TELEMETRY] Warning: flush failed: {e}")
