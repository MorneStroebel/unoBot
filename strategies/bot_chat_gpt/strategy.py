from strategies.base_strategy import BaseStrategy
from typing import Optional, Tuple
import random


class bot_chtgpt(BaseStrategy):
    """
    High-performance UNO bot focused on win rate.
    """

    def __init__(self):
        super().__init__()

    def on_game_start(self):
        super().on_game_start()

    def on_game_end(self, won, placement, points):
        super().on_game_end(won, placement, points)

    def choose_card(self, hand, top_card, current_color) -> Tuple[Optional[int], Optional[str]]:
        playable = self.get_playable_cards(hand, top_card, current_color)

        if not playable:
            self._record_draw()
            return None, None

        hand_size = len(hand)
        if hand_size <= 3:
            phase = "LATE"
        elif hand_size <= 6:
            phase = "MID"
        else:
            phase = "EARLY"

        wild_draw4, wilds, draw_twos, skips, reverses, numbers = [], [], [], [], [], []

        for idx, card in playable:
            t = card["type"]
            if t == "WILD_DRAW_FOUR":
                wild_draw4.append((idx, card))
            elif t == "WILD":
                wilds.append((idx, card))
            elif t == "DRAW_TWO":
                draw_twos.append((idx, card))
            elif t == "SKIP":
                skips.append((idx, card))
            elif t == "REVERSE":
                reverses.append((idx, card))
            else:
                numbers.append((idx, card))

        if phase == "LATE":
            for bucket in (wild_draw4, draw_twos, skips, reverses, wilds, numbers):
                if bucket:
                    idx, card = bucket[0]
                    color = self.pick_wild_color(hand) if card["type"].startswith("WILD") else None
                    self._record_play(card, color)
                    return idx, color

        if phase == "MID":
            if draw_twos:
                idx, card = draw_twos[0]
                self._record_play(card)
                return idx, None
            if skips:
                idx, card = skips[0]
                self._record_play(card)
                return idx, None
            if numbers:
                idx, card = self._best_number(numbers, hand)
                self._record_play(card)
                return idx, None
            if wilds:
                idx, card = wilds[0]
                color = self.pick_wild_color(hand)
                self._record_play(card, color)
                return idx, color

        if numbers:
            idx, card = self._best_number(numbers, hand)
            self._record_play(card)
            return idx, None

        idx, card = playable[0]
        color = self.pick_wild_color(hand) if card["type"].startswith("WILD") else None
        self._record_play(card, color)
        return idx, color

    def _best_number(self, number_cards, hand):
        color_strength = {
            "RED": self.count_color(hand, "RED"),
            "BLUE": self.count_color(hand, "BLUE"),
            "GREEN": self.count_color(hand, "GREEN"),
            "YELLOW": self.count_color(hand, "YELLOW"),
        }
        return sorted(
            number_cards,
            key=lambda x: (x[1]["value"], color_strength.get(x[1]["color"], 0)),
            reverse=True
        )[0]
