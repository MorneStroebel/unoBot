"""
AdaptiveUNO Strategy
====================
An opponent-modeling bot that builds live profiles of every player at the table
and shifts its own play style to exploit what it observes.

Core research principles implemented
--------------------------------------
1. Opponent Profiling
   - Tracks each player's color preferences (colors they play voluntarily)
   - Detects draw-frequency per color (colors they get stuck on = "weak colors")
   - Classifies opponents: AGGRESSIVE / PASSIVE / HOARDER / DESPERATE
   - Monitors card-count to identify the "leader" to attack

2. Adaptive Color Control (highest-impact single decision in UNO)
   - Steers wild-color INTO colors opponents struggle with (pain colors)
   - Avoids colors that opponents are clearly flush in
   - Combines hand-concentration + opponent-draw-history + discard-depletion
   - Keeps play in your dominant color when possible

3. Smart Attack Targeting
   - Focuses draw-cards on the current leader (lowest card count)
   - Uses SKIP/REVERSE to freeze players who are about to go out
   - Research finding: at 4+ players, burning action cards EARLY hurts win
     rate — they are saved and released only when an opponent threatens

4. Hand Composition / Card Counting
   - Tracks discard-pile color distribution (if a color is depleted from
     the pile opponents likely don't hold it — force that color)
   - Dumps high-point cards (9s, action cards) as soon as any opponent ≤ 3
   - Prefer shedding cards in the color we hold most of

5. Mode Switching (posture-based play)
   - NORMAL    — save action cards, steer colors, balanced
   - OFFENSIVE — we have ≤ 4 cards: shed fast, dump high-value first
   - DEFENSIVE — a leader has ≤ 3 cards: attack with everything we have
   - ENDGAME   — we have ≤ 2 cards: play safe, go out cleanly
"""

from strategies.base_strategy import BaseStrategy
from typing import Optional, Tuple, List, Dict, DefaultDict
from collections import defaultdict


# ---------------------------------------------------------------------------
# Opponent Profile
# ---------------------------------------------------------------------------

class OpponentProfile:
    """Live statistical model of one opponent built from observed actions."""

    def __init__(self, player_id: str):
        self.player_id = player_id
        self.color_plays:  DefaultDict[str, int] = defaultdict(int)
        self.color_draws:  DefaultDict[str, int] = defaultdict(int)
        self.action_plays: DefaultDict[str, int] = defaultdict(int)
        self.play_count: int = 0
        self.draw_count: int = 0
        self.card_count: int = 7

    def record_play(self, card: Dict):
        self.play_count += 1
        color = card.get("color", "WILD")
        ctype = card.get("type", "NUMBER")
        if color != "WILD":
            self.color_plays[color] += 1
        if ctype != "NUMBER":
            self.action_plays[ctype] += 1

    def record_draw(self, current_color: str):
        self.draw_count += 1
        self.color_draws[current_color] += 1

    def set_card_count(self, count: int):
        self.card_count = count

    @property
    def preferred_color(self) -> Optional[str]:
        if not self.color_plays:
            return None
        return max(self.color_plays, key=lambda c: self.color_plays[c])

    @property
    def weak_colors(self) -> List[str]:
        return [c for c, n in self.color_draws.items() if n >= 2]

    @property
    def aggression_score(self) -> float:
        if self.play_count == 0:
            return 0.5
        return sum(self.action_plays.values()) / self.play_count

    @property
    def style(self) -> str:
        if self.aggression_score > 0.45:
            return "AGGRESSIVE"
        total = self.play_count + self.draw_count
        if total > 3 and self.draw_count / total > 0.5:
            return "DESPERATE"
        if self.play_count > 5 and self.draw_count == 0:
            return "HOARDER"
        return "PASSIVE"

    @property
    def is_dangerous(self) -> bool:
        return self.card_count <= 2

    @property
    def is_leader(self) -> bool:
        return self.card_count <= 3


# ---------------------------------------------------------------------------
# Main Strategy
# ---------------------------------------------------------------------------

class MyStrategy(BaseStrategy):
    """
    Adaptive UNO bot with live opponent modeling and mode-switching posture.
    No external dependencies beyond stdlib + base_strategy.
    """

    COLORS = ("RED", "BLUE", "GREEN", "YELLOW")

    # Base priority tiers — lower = play sooner (before mode adjustments)
    _BASE_PRIORITY = {
        "WILD_DRAW_FOUR": 0,
        "DRAW_TWO":       1,
        "SKIP":           2,
        "REVERSE":        3,
        "NUMBER":         4,
        "WILD":           5,
    }

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def on_game_start(self):
        super().on_game_start()
        self._profiles: Dict[str, OpponentProfile] = {}
        self._discard_color_counts: DefaultDict[str, int] = defaultdict(int)
        self._turn_number: int = 0
        self._current_color_streak: Dict[str, int] = defaultdict(int)

    def on_game_end(self, won: bool, placement: int, points: int):
        super().on_game_end(won, placement, points)

    # -----------------------------------------------------------------------
    # Core decision
    # -----------------------------------------------------------------------

    def choose_card(
        self,
        hand: List[Dict],
        top_card: Dict,
        current_color: str,
        **kwargs,
    ) -> Tuple[Optional[int], Optional[str]]:

        self._turn_number += 1

        # Absorb optional context from the runner
        opponent_card_counts: Dict[str, int] = kwargs.get("opponent_card_counts", {})
        last_player_id: Optional[str] = kwargs.get("last_player_id")
        last_card_played: Optional[Dict] = kwargs.get("last_card_played")
        last_player_drew: bool = kwargs.get("last_player_drew", False)

        # Update opponent models
        self._update_profiles(
            opponent_card_counts,
            last_player_id,
            last_card_played,
            last_player_drew,
            current_color,
        )

        # Track what colors have been played to the discard pile
        if top_card:
            tc_color = top_card.get("color")
            if tc_color and tc_color != "WILD":
                self._discard_color_counts[tc_color] += 1
            # Track color streaks (if same color is up multiple turns in a row)
            self._current_color_streak[current_color] += 1

        playable = self.get_playable_cards(hand, top_card, current_color)

        if not playable:
            self._record_draw()
            return None, None

        hand_size = len(hand)
        mode = self._determine_mode(hand_size, opponent_card_counts)

        chosen_idx, chosen_card = self._pick_best(
            playable, hand, hand_size, mode, current_color, opponent_card_counts
        )

        wild_color = None
        if chosen_card["type"] in ("WILD", "WILD_DRAW_FOUR"):
            wild_color = self._pick_best_wild_color(hand, opponent_card_counts, mode)

        self._record_play(chosen_card, wild_color=wild_color)
        return chosen_idx, wild_color

    # -----------------------------------------------------------------------
    # Mode determination
    # -----------------------------------------------------------------------

    def _determine_mode(
        self, hand_size: int, opponent_counts: Dict[str, int]
    ) -> str:
        if hand_size <= 2:
            return "ENDGAME"
        counts = list(opponent_counts.values()) if opponent_counts else [
            p.card_count for p in self._profiles.values()
        ]
        if any(c <= 3 for c in counts):
            return "DEFENSIVE"
        if hand_size <= 4:
            return "OFFENSIVE"
        return "NORMAL"

    # -----------------------------------------------------------------------
    # Card scoring & selection
    # -----------------------------------------------------------------------

    def _pick_best(
        self,
        playable: List[Tuple[int, Dict]],
        hand: List[Dict],
        hand_size: int,
        mode: str,
        current_color: str,
        opponent_counts: Dict[str, int],
    ) -> Tuple[int, Dict]:

        dominant_color = self._dominant_color(hand)
        pain_color     = self._best_pain_color(opponent_counts)
        scarce_color   = self._scarcest_discard_color()

        best_score = float("inf")
        best_pair  = playable[0]

        for idx, card in playable:
            score = self._score_card(
                card, hand_size, mode,
                dominant_color, pain_color, scarce_color, current_color
            )
            if score < best_score:
                best_score = score
                best_pair  = (idx, card)

        return best_pair

    def _score_card(
        self,
        card: Dict,
        hand_size: int,
        mode: str,
        dominant_color: str,
        pain_color: Optional[str],
        scarce_color: Optional[str],
        current_color: str,
    ) -> float:

        ctype  = card["type"]
        ccolor = card.get("color", "WILD")
        score  = float(self._BASE_PRIORITY.get(ctype, 4))

        # ----------------------------------------------------------------
        # Mode-specific adjustments
        # ----------------------------------------------------------------

        if mode == "ENDGAME":
            # We're nearly out — play it safe and go out cleanly
            # Prefer color cards in our dominant color to guarantee exit
            if ctype == "NUMBER" and ccolor == dominant_color:
                score -= 1.5
            # Don't waste W+4 if we can naturally go out
            if ctype == "WILD_DRAW_FOUR":
                score += 0.5

        elif mode == "DEFENSIVE":
            # A leader is close to winning — unleash everything to stop them
            # Research: this is exactly when action cards pay off
            if ctype == "WILD_DRAW_FOUR":
                score -= 4.0
            elif ctype == "DRAW_TWO":
                score -= 2.5
            elif ctype in ("SKIP", "REVERSE"):
                score -= 1.5
            elif ctype == "NUMBER":
                score += 2.0  # avoid wasting turn on safe plays

        elif mode == "OFFENSIVE":
            # We're close to going out — shed as fast as possible
            if ctype == "NUMBER":
                face_val = card.get("value", 0)
                score -= face_val * 0.06  # dump 9s before 1s
            # Hold wilds in case we need them to match on last card
            if ctype == "WILD" and hand_size > 2:
                score += 1.2
            if ctype == "WILD_DRAW_FOUR" and hand_size > 2:
                score += 0.6

        else:  # NORMAL
            # Key research finding: at 4 players, saving action cards beats
            # playing them early — add a delay penalty
            if ctype in ("SKIP", "REVERSE", "DRAW_TWO"):
                score += 1.0
            if ctype == "WILD":
                score += 1.8
            if ctype == "WILD_DRAW_FOUR":
                score += 0.7

        # ----------------------------------------------------------------
        # Color control bonuses (apply in all modes)
        # ----------------------------------------------------------------

        # Playing our dominant color maintains color control
        if ccolor == dominant_color:
            score -= 0.5

        # Naturally landing on pain color is great even without a wild
        if pain_color and ccolor == pain_color:
            score -= 0.4

        # Scarce discard color = opponents probably don't have it
        if scarce_color and ccolor == scarce_color:
            score -= 0.2

        # Opponent is benefiting from current color? Any card changing it is good
        beneficiaries = sum(
            1 for p in self._profiles.values()
            if p.preferred_color == current_color and p.card_count <= 5
        )
        if beneficiaries >= 1 and ccolor != current_color and ccolor != "WILD":
            score -= 0.35

        # Don't stay on a color an aggressive opponent loves (they'll ride it out)
        if any(
            p.style == "AGGRESSIVE" and p.preferred_color == ccolor
            for p in self._profiles.values()
        ):
            score += 0.3

        return score

    # -----------------------------------------------------------------------
    # Wild color selection — composite scoring
    # -----------------------------------------------------------------------

    def _pick_best_wild_color(
        self,
        hand: List[Dict],
        opponent_counts: Dict[str, int],
        mode: str,
    ) -> str:
        """
        Multi-factor wild color picker:
          + How many cards we hold in this color (hand concentration)
          + How much opponents have drawn on this color (pain penalty for them)
          - How much opponents prefer/play this color (avoid feeding them)
          + Boost for pain_color in DEFENSIVE mode
          - Penalty for scarce discard colors (keep some colors in circulation)
        """
        pain_color   = self._best_pain_color(opponent_counts)
        scarce_color = self._scarcest_discard_color()
        hand_counts  = {c: self.count_color(hand, c) for c in self.COLORS}
        max_count    = max(hand_counts.values()) or 1

        color_scores: Dict[str, float] = {}
        for color in self.COLORS:
            # Base: card density in our hand
            s = (hand_counts[color] / max_count) * 3.0

            # Opponent pain: they draw a lot on this color
            total_draws = sum(
                p.color_draws.get(color, 0) for p in self._profiles.values()
            )
            s += total_draws * 0.6

            # Opponent preference: they play this color easily — avoid
            total_plays = sum(
                p.color_plays.get(color, 0) for p in self._profiles.values()
            )
            s -= total_plays * 0.4

            # Defensive escalation: really push pain color
            if mode == "DEFENSIVE" and pain_color == color:
                s += 2.5

            # Slight bonus for scarce colors in normal play
            if mode == "NORMAL" and scarce_color == color:
                s += 0.4

            color_scores[color] = s

        best = max(color_scores, key=lambda c: color_scores[c])
        return best if best else "RED"

    # -----------------------------------------------------------------------
    # Profile updates
    # -----------------------------------------------------------------------

    def _update_profiles(
        self,
        opponent_card_counts: Dict[str, int],
        last_player_id: Optional[str],
        last_card_played: Optional[Dict],
        last_player_drew: bool,
        current_color: str,
    ):
        # Sync current card counts into all profiles
        for pid, count in opponent_card_counts.items():
            if pid not in self._profiles:
                self._profiles[pid] = OpponentProfile(pid)
            self._profiles[pid].set_card_count(count)

        # Record the last player's action
        if last_player_id:
            if last_player_id not in self._profiles:
                self._profiles[last_player_id] = OpponentProfile(last_player_id)
            p = self._profiles[last_player_id]
            if last_card_played:
                p.record_play(last_card_played)
            elif last_player_drew:
                p.record_draw(current_color)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _dominant_color(self, hand: List[Dict]) -> str:
        counts = {c: self.count_color(hand, c) for c in self.COLORS}
        best = max(counts, key=lambda c: counts[c])
        return best if counts[best] > 0 else "RED"

    def _best_pain_color(self, opponent_counts: Dict[str, int]) -> Optional[str]:
        """Color opponents draw on most, weighted by how close they are to winning."""
        if not self._profiles:
            return None
        pain: DefaultDict[str, float] = defaultdict(float)
        for pid, profile in self._profiles.items():
            weight = 2.5 if profile.is_leader else 1.0
            for color, draws in profile.color_draws.items():
                pain[color] += draws * weight
        if not pain:
            return None
        return max(pain, key=lambda c: pain[c])

    def _scarcest_discard_color(self) -> Optional[str]:
        """Color least seen in discard pile — opponents probably don't hold it."""
        if not self._discard_color_counts:
            return None
        return min(self.COLORS, key=lambda c: self._discard_color_counts.get(c, 0))

    def pick_wild_color(self, hand: List[Dict]) -> str:
        """Fallback override: use dominant color if no context available."""
        return self._dominant_color(hand)
