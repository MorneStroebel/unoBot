from strategies.base_strategy import BaseStrategy
from typing import Optional, Tuple


class GptBaseBot(BaseStrategy):
    """
    GPT Base Bot Strategy
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

        wild_draw_fours = [(i, c) for i, c in playable if c["type"] == "WILD_DRAW_FOUR"]
        wilds = [(i, c) for i, c in playable if c["type"] == "WILD"]
        draw_twos = [(i, c) for i, c in playable if c["type"] == "DRAW_TWO"]
        skips = [(i, c) for i, c in playable if c["type"] == "SKIP"]
        reverses = [(i, c) for i, c in playable if c["type"] == "REVERSE"]
        numbers = [(i, c) for i, c in playable if c["type"] == "NUMBER"]

        if hand_size <= 3:
            if wild_draw_fours:
                idx, card = wild_draw_fours[0]
                color = self.pick_wild_color(hand)
                self._record_play(card, color)
                return idx, color
            if wilds:
                idx, card = wilds[0]
                color = self.pick_wild_color(hand)
                self._record_play(card, color)
                return idx, color

        if draw_twos:
            idx, card = draw_twos[0]
            self._record_play(card)
            return idx, None

        if skips:
            idx, card = skips[0]
            self._record_play(card)
            return idx, None

        if reverses:
            idx, card = reverses[0]
            self._record_play(card)
            return idx, None

        if numbers:
            numbers.sort(key=lambda x: x[1]["value"])
            idx, card = numbers[0]
            self._record_play(card)
            return idx, None

        if wilds:
            idx, card = wilds[0]
            color = self.pick_wild_color(hand)
            self._record_play(card, color)
            return idx, color

        if wild_draw_fours:
            idx, card = wild_draw_fours[0]
            color = self.pick_wild_color(hand)
            self._record_play(card, color)
            return idx, color

        self._record_draw()
        return None, None
