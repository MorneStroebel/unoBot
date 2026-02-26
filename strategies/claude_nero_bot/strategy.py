"""
ClaudeNeroBot — Neurologic Self-Learning UNO Strategy with F1 Telemetry
=======================================================================
Neural network bot (TD learning + experience replay) with full telemetry.

Files in this folder:
  strategy.py   — this file, the bot logic
  telemetry.py  — F1-style telemetry system (imported below)
  nn_weights.json — persisted neural network weights (auto-created)
  telemetry.json  — per-game telemetry data (auto-created, shareable)
"""

import json
import math
import os
import random
import time
from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional, Tuple

from strategies.base_strategy import BaseStrategy

# ---------------------------------------------------------------------------
# Safe telemetry import — 3-tier fallback for all runner environments
# ---------------------------------------------------------------------------
try:
    from .telemetry import Telemetry              # package-style (preferred)
except ImportError:
    try:
        from telemetry import Telemetry           # flat-file fallback
    except ImportError:
        import importlib.util as _ilu
        _tpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telemetry.py")
        _spec  = _ilu.spec_from_file_location("telemetry", _tpath)
        _tmod  = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_tmod)
        Telemetry = _tmod.Telemetry


# ---------------------------------------------------------------------------
# Resolve the bot's own folder — robust against all runner environments
# ---------------------------------------------------------------------------

def _bot_dir() -> str:
    """Return the absolute directory this file lives in, with fallbacks."""
    try:
        p = os.path.abspath(__file__)
        d = os.path.dirname(p)
        if d and os.path.isdir(d):
            return d
    except Exception:
        pass
    # Fallback 1: look for a folder named claude_nero_bot on sys.path
    import sys
    for base in sys.path:
        candidate = os.path.join(base, "claude_nero_bot")
        if os.path.isdir(candidate):
            return candidate
    # Fallback 2: current working directory
    return os.getcwd()


_BOT_DIR       = _bot_dir()
_WEIGHTS_FILE  = os.path.join(_BOT_DIR, "nn_weights.json")
_TELEMETRY_FILE = os.path.join(_BOT_DIR, "telemetry.json")


# ---------------------------------------------------------------------------
# Activations
# ---------------------------------------------------------------------------

def _relu(x):    return x if x > 0.0 else 0.0
def _relu_d(x):  return 1.0 if x > 0.0 else 0.0
def _sigmoid(x):
    x = max(-30.0, min(30.0, x))
    return 1.0 / (1.0 + math.exp(-x))


# ---------------------------------------------------------------------------
# Neural Network
# ---------------------------------------------------------------------------

class TinyNet:
    def __init__(self, n_in=24, n_hidden=48, lr=0.005):
        self.n_in = n_in; self.n_hidden = n_hidden; self.lr = lr
        s1 = math.sqrt(2.0 / n_in);  s2 = math.sqrt(2.0 / n_hidden)
        self.W1 = [[random.gauss(0, s1) for _ in range(n_in)]  for _ in range(n_hidden)]
        self.b1 = [0.0] * n_hidden
        self.W2 = [random.gauss(0, s2) for _ in range(n_hidden)]
        self.b2 = 0.0

    def forward(self, x):
        h_pre = [sum(self.W1[j][i]*x[i] for i in range(self.n_in)) + self.b1[j]
                 for j in range(self.n_hidden)]
        h   = [_relu(v) for v in h_pre]
        out = _sigmoid(sum(self.W2[j]*h[j] for j in range(self.n_hidden)) + self.b2)
        return out, h_pre, h

    def predict(self, x):
        out, _, _ = self.forward(x); return out

    def update(self, x, td_error):
        out, h_pre, h = self.forward(x)
        d_out = td_error * out * (1.0 - out)
        for j in range(self.n_hidden):
            self.W2[j] += self.lr * d_out * h[j]
        self.b2 += self.lr * d_out
        for j in range(self.n_hidden):
            d_h = d_out * self.W2[j] * _relu_d(h_pre[j])
            for i in range(self.n_in):
                self.W1[j][i] += self.lr * d_h * x[i]
            self.b1[j] += self.lr * d_h

    def to_dict(self):
        return {"W1": self.W1, "b1": self.b1, "W2": self.W2, "b2": self.b2,
                "n_in": self.n_in, "n_hidden": self.n_hidden, "lr": self.lr}

    @classmethod
    def from_dict(cls, d):
        net = cls(d["n_in"], d["n_hidden"], d.get("lr", 0.005))
        net.W1=d["W1"]; net.b1=d["b1"]; net.W2=d["W2"]; net.b2=d["b2"]
        return net


# ---------------------------------------------------------------------------
# Replay Buffer
# ---------------------------------------------------------------------------

class ReplayBuffer:
    def __init__(self, capacity=4000):
        self.capacity = capacity; self.buf = []; self.pos = 0

    def push(self, s, s_next, reward):
        e = (s, s_next, reward)
        if len(self.buf) < self.capacity: self.buf.append(e)
        else: self.buf[self.pos] = e
        self.pos = (self.pos + 1) % self.capacity

    def sample(self, n): return random.sample(self.buf, min(n, len(self.buf)))
    def __len__(self):   return len(self.buf)
    def to_list(self):   return self.buf

    @classmethod
    def from_list(cls, data, capacity=4000):
        rb = cls(capacity); rb.buf = list(data)[-capacity:]
        rb.pos = len(rb.buf) % capacity; return rb


# ---------------------------------------------------------------------------
# Opponent Profile
# ---------------------------------------------------------------------------

class OpponentProfile:
    def __init__(self):
        self.color_plays:  DefaultDict[str, int] = defaultdict(int)
        self.color_draws:  DefaultDict[str, int] = defaultdict(int)
        self.action_plays: DefaultDict[str, int] = defaultdict(int)
        self.play_count = 0; self.draw_count = 0; self.card_count = 7

    def record_play(self, card):
        self.play_count += 1
        c = card.get("color", "WILD"); t = card.get("type", "NUMBER")
        if c != "WILD":   self.color_plays[c]  += 1
        if t != "NUMBER": self.action_plays[t] += 1

    def record_draw(self, color):
        self.draw_count += 1; self.color_draws[color] += 1

    @property
    def preferred_color(self):
        return max(self.color_plays, key=lambda c: self.color_plays[c]) \
               if self.color_plays else None

    @property
    def is_leader(self): return self.card_count <= 3

    @property
    def style(self):
        if self.play_count == 0: return "PASSIVE"
        if sum(self.action_plays.values()) / self.play_count > 0.45: return "AGGRESSIVE"
        total = self.play_count + self.draw_count
        if total > 3 and self.draw_count / total > 0.5: return "DESPERATE"
        return "PASSIVE"





# ---------------------------------------------------------------------------
# Null Telemetry — silent fallback if telemetry.py fails to import
# ---------------------------------------------------------------------------

class _NullTelemetry:
    """Drop-in replacement that silently ignores all telemetry calls."""
    def game_start(self, *a, **kw): pass
    def turn(self, *a, **kw):       pass
    def played(self, *a, **kw):     pass
    def drew(self, *a, **kw):       pass
    def targeted(self, *a, **kw):   pass
    def fault(self, *a, **kw):      pass
    def game_end(self, *a, **kw):   pass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLORS        = ("RED", "BLUE", "GREEN", "YELLOW")
N_FEATURES    = 24
GAMMA         = 0.92
BATCH_SIZE    = 128
EPSILON_START = 0.25
EPSILON_MIN   = 0.03
EPSILON_DECAY = 0.993
_H_PRI        = {"WILD_DRAW_FOUR":0,"DRAW_TWO":1,"SKIP":2,"REVERSE":3,"NUMBER":4,"WILD":5}


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

class ClaudeNeroBot(BaseStrategy):

    def __init__(self):
        super().__init__()
        self._net, self._replay, self._games_trained, self._epsilon = self._load_weights()
        self._game_active = False   # tracks whether a game has been started
        try:
            self._telem = Telemetry()
        except Exception as e:
            print(f"[ClaudeNeroBot] Telemetry init failed: {e}")
            self._telem = _NullTelemetry()
        self._reset_game_state()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_weights(self):
        try:
            with open(_WEIGHTS_FILE) as f: d = json.load(f)
            net    = TinyNet.from_dict(d["net"])
            replay = ReplayBuffer.from_list(d.get("replay", []))
            games  = d.get("games", 0)
            eps    = max(EPSILON_MIN, EPSILON_START * (EPSILON_DECAY ** games))
            print(f"[ClaudeNeroBot] Loaded — {games} games trained, ε={eps:.3f}, replay={len(replay)}")
            return net, replay, games, eps
        except Exception:
            print(f"[ClaudeNeroBot] Fresh start — weights will save to: {_WEIGHTS_FILE}")
            return TinyNet(N_FEATURES, 48, 0.005), ReplayBuffer(), 0, EPSILON_START

    def _save_weights(self):
        try:
            with open(_WEIGHTS_FILE, "w") as f:
                json.dump({"net": self._net.to_dict(),
                           "replay": self._replay.to_list(),
                           "games": self._games_trained}, f)
        except Exception as e:
            print(f"[ClaudeNeroBot] Weight save failed: {e}")

    # ------------------------------------------------------------------
    # Game state
    # ------------------------------------------------------------------

    def _reset_game_state(self):
        self._profiles:      Dict[str, OpponentProfile] = {}
        self._discard_cc:    DefaultDict[str, int]      = defaultdict(int)
        self._turn_number    = 0
        self._last_color:    Optional[str] = None
        self._episode:       List[Tuple[List[float], float]] = []
        self._last_td_errors: List[float] = []
        self._game_active    = True

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_game_start(self):
        super().on_game_start()
        self._reset_game_state()
        self._telem.game_start(self._games_trained + 1, self._epsilon, len(self._replay))

    def _ensure_game_started(self):
        """Called at the top of choose_card — auto-starts a game if the runner
        skipped on_game_start, so the bot always plays from turn 1."""
        needs_reset  = not hasattr(self, "_profiles") or not hasattr(self, "_episode")
        needs_telem  = not hasattr(self, "_telem")
        game_inactive = not getattr(self, "_game_active", False)

        if needs_telem:
            try:
                self._telem = Telemetry()
            except Exception:
                self._telem = _NullTelemetry()

        if needs_reset:
            self._reset_game_state()
        elif game_inactive:
            self._reset_game_state()
            # Auto-fire game_start so telemetry knows a game is running
            self._telem.game_start(self._games_trained + 1, self._epsilon, len(self._replay))

    def on_game_end(self, won: bool, placement: int, points: int):
        super().on_game_end(won, placement, points)
        self._games_trained += 1
        self._epsilon = max(EPSILON_MIN, self._epsilon * EPSILON_DECAY)

        terminal = {1:1.0, 2:-0.25, 3:-0.6, 4:-1.0}.get(placement, -1.0)
        if won: terminal = 1.0

        # Monte Carlo return propagation
        discounted = terminal; returns = []
        for i in reversed(range(len(self._episode))):
            state, shaped = self._episode[i]
            returns.append((state, discounted + shaped))
            discounted *= GAMMA
        returns.reverse()

        for i, (state, g) in enumerate(returns):
            next_state = returns[i+1][0] if i+1 < len(returns) else [0.0]*N_FEATURES
            self._replay.push(state, next_state, g)

        self._train_batch()
        self._save_weights()

        if self._games_trained > 100 and self._epsilon > 0.15:
            self._telem.fault("EPSILON_HIGH", f"ε={self._epsilon:.3f} after {self._games_trained} games")

        self._telem.game_end(self._games_trained, won, placement, points,
                           len(self._episode), self._last_td_errors)

    # ------------------------------------------------------------------
    # Core decision
    # ------------------------------------------------------------------

    def choose_card(
        self,
        hand: List[Dict],
        top_card: Dict,
        current_color: str,
        **kwargs,
    ) -> Tuple[Optional[int], Optional[str]]:

        self._ensure_game_started()
        self._turn_number += 1
        opp_counts = kwargs.get("opponent_card_counts") or {}
        last_pid   = kwargs.get("last_player_id")
        last_card  = kwargs.get("last_card_played")
        last_drew  = kwargs.get("last_player_drew", False)

        if last_card and last_card.get("type") in ("DRAW_TWO","WILD_DRAW_FOUR"):
            self._telem.targeted(last_card["type"])


        self._update_profiles(opp_counts, last_pid, last_card, last_drew, current_color)

        if top_card:
            tc = top_card.get("color")
            if tc and tc != "WILD":
                self._discard_cc[tc] += 1

        playable = self.get_playable_cards(hand, top_card, current_color)

        # ---- Telemetry: start turn ----
        cc = {c: self.count_color(hand, c) for c in COLORS}
        dominant = max(cc, key=lambda c: cc[c]) if hand else "RED"
        pain = self._pain_color()

        if not playable:
            self._record_draw()
            stuck = self._last_color == current_color
            self._telem.drew(current_color, stuck=stuck)
            if stuck:
                self._telem.fault("STUCK_COLOR", current_color)
            return None, None

        # (colour change noted inline in turn sentence)

        mode = self._determine_mode(len(hand), opp_counts)

        action_count = sum(1 for c in hand
                           if c["type"] in ("SKIP","REVERSE","DRAW_TWO","WILD_DRAW_FOUR"))
        if mode == "DEFENSIVE" and action_count <= 1:
            self._telem.fault("LOW_ACTIONS", f"{action_count} attack cards in DEFENSIVE")

        state  = self._encode_state(hand, top_card, current_color, opp_counts)
        shaped = self._shaped_reward(hand, opp_counts)
        self._episode.append((state, shaped))

        nn_weight    = min(1.0, self._games_trained / 80.0)
        epsilon_used = random.random() < self._epsilon
        best_nn = 0.0; best_h = 0.0

        if epsilon_used:
            chosen_idx, chosen_card = random.choice(playable)
        else:
            chosen_idx, chosen_card, best_nn, best_h = self._nn_pick(
                playable, hand, top_card, current_color, opp_counts, nn_weight
            )

        # Fault checks
        opp_list = list(opp_counts.values()) if opp_counts else \
                   [p.card_count for p in self._profiles.values()]
        if opp_list and any(c <= 1 for c in opp_list):
            if chosen_card.get("type") not in ("DRAW_TWO","WILD_DRAW_FOUR","SKIP","REVERSE"):
                self._telem.fault("THREAT_UNMET",
                    f"played {chosen_card.get('type')} while opp has {min(opp_list)} cards")

        wild_color = None
        if chosen_card["type"] in ("WILD","WILD_DRAW_FOUR"):
            wild_color = self._best_wild_color(hand, opp_counts)
            if self.count_color(hand, current_color) > 1:
                self._telem.fault("WILD_WASTED",
                    f"{chosen_card['type']} with {self.count_color(hand,current_color)} {current_color} in hand")

        if best_nn > 0 and best_nn < 0.35 and self._games_trained > 50:
            self._telem.fault("NN_COLD", f"conf={best_nn:.3f}")

        # ---- Telemetry: emit turn + play sentences ----
        opp_min = min(opp_list) if opp_list else 7
        threat = ("CRITICAL" if opp_min <= 1 else "HIGH" if opp_min <= 2
                  else "MEDIUM" if opp_min <= 4 else "LOW")
        self._telem.turn(
            self._turn_number, len(hand), len(playable),
            mode, threat, dominant, opp_min, best_nn, nn_weight
        )
        self._telem.played(
            chosen_card["type"],
            chosen_card.get("color", "WILD"),
            wild_color=wild_color,
            epsilon_used=epsilon_used,
        )

        self._last_color = wild_color or chosen_card.get("color", current_color)
        self._record_play(chosen_card, wild_color=wild_color)
        return chosen_idx, wild_color

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    def _determine_mode(self, hand_size, opp_counts):
        if hand_size <= 2: return "ENDGAME"
        counts = list(opp_counts.values()) if opp_counts else \
                 [p.card_count for p in self._profiles.values()]
        if any(c <= 3 for c in counts): return "DEFENSIVE"
        if hand_size <= 4:              return "OFFENSIVE"
        return "NORMAL"

    # ------------------------------------------------------------------
    # Card selection
    # ------------------------------------------------------------------

    def _nn_pick(self, playable, hand, top_card, current_color, opp_counts, nn_weight):
        h_weight = 1.0 - nn_weight
        best_score = -999.0; best_pair = playable[0]; best_nn = 0.0; best_h = 0.0

        for idx, card in playable:
            next_hand  = [c for i, c in enumerate(hand) if i != idx]
            wild_col   = self._best_wild_color(hand, opp_counts) \
                         if card["type"] in ("WILD","WILD_DRAW_FOUR") else None
            next_color = wild_col or card.get("color", current_color)
            next_state = self._encode_state(next_hand, card, next_color, opp_counts)
            nn_s = self._net.predict(next_state)
            h_s  = self._heuristic_score(card, hand, next_hand, opp_counts, current_color)
            combined = nn_weight * nn_s + h_weight * h_s
            if combined > best_score:
                best_score = combined; best_pair = (idx, card)
                best_nn = nn_s; best_h = h_s

        return best_pair[0], best_pair[1], best_nn, best_h

    def _heuristic_score(self, card, hand, next_hand, opp_counts, current_color):
        ctype = card["type"]; ccolor = card.get("color","WILD")
        counts = list(opp_counts.values()) if opp_counts else \
                 [p.card_count for p in self._profiles.values()]
        danger  = any(c <= 3 for c in counts) if counts else False
        endgame = len(hand) <= 2
        base    = 1.0 - (_H_PRI.get(ctype, 4) / 5.0)
        boost   = 0.0
        if danger:
            if ctype == "WILD_DRAW_FOUR":           boost += 0.4
            elif ctype == "DRAW_TWO":               boost += 0.3
            elif ctype in ("SKIP","REVERSE"):       boost += 0.2
        elif endgame:
            if ctype=="NUMBER" and ccolor==self._dominant_color(hand): boost += 0.3
        else:
            if ctype in ("WILD","WILD_DRAW_FOUR"):        boost -= 0.15
            if ctype in ("SKIP","REVERSE","DRAW_TWO"):    boost -= 0.1
        if next_hand and ccolor == self._dominant_color(next_hand): boost += 0.1
        pain = self._pain_color()
        if pain and ccolor == pain: boost += 0.08
        beneficiaries = sum(1 for p in self._profiles.values()
                            if p.preferred_color==current_color and p.card_count<=5)
        if beneficiaries>=1 and ccolor not in (current_color,"WILD"): boost += 0.07
        return min(1.0, max(0.0, base + boost))

    # ------------------------------------------------------------------
    # Shaped reward
    # ------------------------------------------------------------------

    def _shaped_reward(self, hand, opp_counts):
        r = -0.02 * len(hand)
        counts = list(opp_counts.values()) if opp_counts else \
                 [p.card_count for p in self._profiles.values()]
        if counts and len(hand) < min(counts): r += 0.05
        return r

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def _train_batch(self):
        if len(self._replay) < 16: return
        errors = []
        for s, s_next, g in self._replay.sample(BATCH_SIZE):
            v_next    = self._net.predict(s_next)
            td_target = 0.7*g + 0.3*(g + GAMMA*v_next)
            v_s       = self._net.predict(s)
            td_error  = max(-1.0, min(1.0, td_target - v_s))
            errors.append(td_error)
            self._net.update(s, td_error)
        self._last_td_errors = errors

    # ------------------------------------------------------------------
    # State encoding — 24 features
    # ------------------------------------------------------------------

    def _encode_state(self, hand, top_card, current_color, opp_counts):
        cc  = {c: self.count_color(hand, c) for c in COLORS}
        def tc(t): return sum(1 for c in hand if c["type"]==t)
        ocl = list(opp_counts.values()) if opp_counts else \
              [p.card_count for p in self._profiles.values()]
        min_o = min(ocl) if ocl else 7; max_o = max(ocl) if ocl else 7
        mean_o = sum(ocl)/len(ocl) if ocl else 7
        dom   = max(cc, key=lambda c: cc[c]) if hand else "RED"
        tt    = top_card.get("type","NUMBER") if top_card else "NUMBER"
        pain  = self._pain_color()
        return [
            min(len(hand)/10.0, 1.0),
            min(tc("SKIP")/5.0, 1.0),
            min(tc("REVERSE")/5.0, 1.0),
            min(tc("DRAW_TWO")/5.0, 1.0),
            min(tc("WILD")/4.0, 1.0),
            min(tc("WILD_DRAW_FOUR")/4.0, 1.0),
            min(cc["RED"]/10.0, 1.0),
            min(cc["BLUE"]/10.0, 1.0),
            min(cc["GREEN"]/10.0, 1.0),
            min(cc["YELLOW"]/10.0, 1.0),
            1.0 if dom == current_color else 0.0,
            1.0 if tt in ("SKIP","REVERSE","DRAW_TWO") else 0.0,
            1.0 if tt in ("WILD","WILD_DRAW_FOUR") else 0.0,
            min(min_o/10.0, 1.0),
            min(max_o/10.0, 1.0),
            min(mean_o/10.0, 1.0),
            min(sum(1 for c in ocl if c<=2)/3.0, 1.0),
            min(sum(1 for c in ocl if c<=4)/3.0, 1.0),
            min(self._turn_number/50.0, 1.0),
            1.0 if pain=="RED"    else 0.0,
            1.0 if pain=="BLUE"   else 0.0,
            1.0 if pain=="GREEN"  else 0.0,
            1.0 if pain=="YELLOW" else 0.0,
            min(self._games_trained/200.0, 1.0),
        ]

    # ------------------------------------------------------------------
    # Wild color
    # ------------------------------------------------------------------

    def _best_wild_color(self, hand, opp_counts):
        pain = self._pain_color()
        hc   = {c: self.count_color(hand, c) for c in COLORS}
        mx   = max(hc.values()) or 1
        scores = {}
        for color in COLORS:
            s  = (hc[color]/mx)*3.0
            s += sum(p.color_draws.get(color,0) for p in self._profiles.values())*0.6
            s -= sum(p.color_plays.get(color,0) for p in self._profiles.values())*0.4
            if pain == color: s += 1.5
            scores[color] = s
        return max(scores, key=lambda c: scores[c])

    # ------------------------------------------------------------------
    # Opponent profiles
    # ------------------------------------------------------------------

    def _update_profiles(self, opp_counts, last_pid, last_card, last_drew, cur_color):
        for pid, count in opp_counts.items():
            if pid not in self._profiles:
                self._profiles[pid] = OpponentProfile()
            self._profiles[pid].card_count = count
        if last_pid:
            if last_pid not in self._profiles:
                self._profiles[last_pid] = OpponentProfile()
            p = self._profiles[last_pid]
            if last_card:   p.record_play(last_card)
            elif last_drew: p.record_draw(cur_color)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _dominant_color(self, hand):
        cc = {c: self.count_color(hand, c) for c in COLORS}
        best = max(cc, key=lambda c: cc[c])
        return best if cc[best] > 0 else "RED"

    def _pain_color(self):
        if not self._profiles: return None
        pain: DefaultDict[str,float] = defaultdict(float)
        for p in self._profiles.values():
            w = 2.5 if p.is_leader else 1.0
            for color, draws in p.color_draws.items():
                pain[color] += draws * w
        return max(pain, key=lambda c: pain[c]) if pain else None

    def pick_wild_color(self, hand):
        return self._dominant_color(hand)
