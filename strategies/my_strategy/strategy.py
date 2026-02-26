from strategies.base_strategy import BaseStrategy
from typing import Optional, Tuple, List, Dict, DefaultDict
from collections import defaultdict


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
    def is_leader(self) -> bool:
        return self.card_count <= 3


class MyStrategy(BaseStrategy):

    COLORS = ("RED", "BLUE", "GREEN", "YELLOW")

    _BASE_PRIORITY = {
        "WILD_DRAW_FOUR": 0,
        "DRAW_TWO":       1,
        "SKIP":           2,
        "REVERSE":        3,
        "NUMBER":         4,
        "WILD":           5,
    }

    def __init__(self):
        super().__init__()
        self._reset_state()

    def _reset_state(self):
        """Initialize (or re-initialize) all per-game state."""
        self._profiles: Dict[str, OpponentProfile] = {}
        self._discard_color_counts: DefaultDict[str, int] = defaultdict(int)
        self._turn_number: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_game_start(self):
        super().on_game_start()
        self._reset_state()

    def on_game_end(self, won: bool, placement: int, points: int):
        super().on_game_end(won, placement, points)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def choose_card(
        self,
        hand: List[Dict],
        top_card: Dict,
        current_color: str,
        **kwargs,
    ) -> Tuple[Optional[int], Optional[str]]:

        # Guard: ensure state exists even if on_game_start was never called
        if not hasattr(self, "_profiles"):
            self._reset_state()

        self._turn_number += 1

        # Optional context some runners provide
        opponent_card_counts: Dict[str, int] = kwargs.get("opponent_card_counts") or {}
        last_player_id: Optional[str]        = kwargs.get("last_player_id")
        last_card_played: Optional[Dict]     = kwargs.get("last_card_played")
        last_player_drew: bool               = kwargs.get("last_player_drew", False)

        self._update_profiles(
            opponent_card_counts, last_player_id,
            last_card_played, last_player_drew, current_color,
        )

        # Track discard pile colour distribution
        if top_card:
            tc = top_card.get("color")
            if tc and tc != "WILD":
                self._discard_color_counts[tc] += 1

        # ---- Core decision ----
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

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    def _determine_mode(self, hand_size: int, opponent_counts: Dict[str, int]) -> str:
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

    # ------------------------------------------------------------------
    # Card selection
    # ------------------------------------------------------------------

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
        pain_color     = self._best_pain_color()
        scarce_color   = self._scarcest_discard_color()

        best_score = float("inf")
        best_pair  = playable[0]

        for idx, card in playable:
            score = self._score_card(
                card, hand_size, mode,
                dominant_color, pain_color, scarce_color, current_color,
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

        # Mode adjustments
        if mode == "ENDGAME":
            if ctype == "NUMBER" and ccolor == dominant_color:
                score -= 1.5
            if ctype == "WILD_DRAW_FOUR":
                score += 0.5

        elif mode == "DEFENSIVE":
            if ctype == "WILD_DRAW_FOUR":
                score -= 4.0
            elif ctype == "DRAW_TWO":
                score -= 2.5
            elif ctype in ("SKIP", "REVERSE"):
                score -= 1.5
            elif ctype == "NUMBER":
                score += 2.0

        elif mode == "OFFENSIVE":
            if ctype == "NUMBER":
                score -= card.get("value", 0) * 0.06
            if ctype == "WILD" and hand_size > 2:
                score += 1.2
            if ctype == "WILD_DRAW_FOUR" and hand_size > 2:
                score += 0.6

        else:  # NORMAL — save action cards for when they matter
            if ctype in ("SKIP", "REVERSE", "DRAW_TWO"):
                score += 1.0
            if ctype == "WILD":
                score += 1.8
            if ctype == "WILD_DRAW_FOUR":
                score += 0.7

        # Colour control bonuses
        if ccolor == dominant_color:
            score -= 0.5
        if pain_color and ccolor == pain_color:
            score -= 0.4
        if scarce_color and ccolor == scarce_color:
            score -= 0.2

        # Penalise keeping the current colour if opponents are riding it
        beneficiaries = sum(
            1 for p in self._profiles.values()
            if p.preferred_color == current_color and p.card_count <= 5
        )
        if beneficiaries >= 1 and ccolor not in (current_color, "WILD"):
            score -= 0.35

        if any(
            p.style == "AGGRESSIVE" and p.preferred_color == ccolor
            for p in self._profiles.values()
        ):
            score += 0.3

        return score

    # ------------------------------------------------------------------
    # Wild colour selection
    # ------------------------------------------------------------------

    def _pick_best_wild_color(
        self,
        hand: List[Dict],
        opponent_counts: Dict[str, int],
        mode: str,
    ) -> str:
        pain_color   = self._best_pain_color()
        scarce_color = self._scarcest_discard_color()
        hand_counts  = {c: self.count_color(hand, c) for c in self.COLORS}
        max_count    = max(hand_counts.values()) or 1

        color_scores: Dict[str, float] = {}
        for color in self.COLORS:
            s = (hand_counts[color] / max_count) * 3.0
            s += sum(p.color_draws.get(color, 0) for p in self._profiles.values()) * 0.6
            s -= sum(p.color_plays.get(color, 0) for p in self._profiles.values()) * 0.4
            if mode == "DEFENSIVE" and pain_color == color:
                s += 2.5
            if mode == "NORMAL" and scarce_color == color:
                s += 0.4
            color_scores[color] = s

        return max(color_scores, key=lambda c: color_scores[c])

    # ------------------------------------------------------------------
    # Opponent profile updates
    # ------------------------------------------------------------------

    def _update_profiles(
        self,
        opponent_card_counts: Dict[str, int],
        last_player_id: Optional[str],
        last_card_played: Optional[Dict],
        last_player_drew: bool,
        current_color: str,
    ):
        for pid, count in opponent_card_counts.items():
            if pid not in self._profiles:
                self._profiles[pid] = OpponentProfile(pid)
            self._profiles[pid].set_card_count(count)

        if last_player_id:
            if last_player_id not in self._profiles:
                self._profiles[last_player_id] = OpponentProfile(last_player_id)
            p = self._profiles[last_player_id]
            if last_card_played:
                p.record_play(last_card_played)
            elif last_player_drew:
                p.record_draw(current_color)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _dominant_color(self, hand: List[Dict]) -> str:
        counts = {c: self.count_color(hand, c) for c in self.COLORS}
        best = max(counts, key=lambda c: counts[c])
        return best if counts[best] > 0 else "RED"

    def _best_pain_color(self) -> Optional[str]:
        if not self._profiles:
            return None
        pain: DefaultDict[str, float] = defaultdict(float)
        for profile in self._profiles.values():
            weight = 2.5 if profile.is_leader else 1.0
            for color, draws in profile.color_draws.items():
                pain[color] += draws * weight
        if not pain:
            return None
        return max(pain, key=lambda c: pain[c])

    def _scarcest_discard_color(self) -> Optional[str]:
        if not self._discard_color_counts:
            return None
        return min(self.COLORS, key=lambda c: self._discard_color_counts.get(c, 0))

    def pick_wild_color(self, hand: List[Dict]) -> str:
        return self._dominant_color(hand)
