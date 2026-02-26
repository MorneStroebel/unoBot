from strategies.base_strategy import BaseStrategy


class GeminiBaseBot(BaseStrategy):
    def __init__(self):
        super().__init__()

    def choose_card(self, hand, top_card, current_color):
        playable = self.get_playable_cards(hand, top_card, current_color)

        # 1. If we have no playable cards, we must draw
        if not playable:
            self._record_draw()
            return None, None

        hand_size = len(hand)

        # Categorize playable cards for strategic decision making
        draw_twos = []
        action_cards = []  # SKIP, REVERSE
        number_cards = []
        wild_cards = []  # WILD, WILD_DRAW_FOUR

        for idx, card in playable:
            ctype = card["type"]
            if ctype == "DRAW_TWO":
                draw_twos.append((idx, card))
            elif ctype in ["WILD", "WILD_DRAW_FOUR"]:
                wild_cards.append((idx, card))
            elif ctype in ["SKIP", "REVERSE"]:
                action_cards.append((idx, card))
            elif ctype == "NUMBER":
                number_cards.append((idx, card))

        chosen_idx = None
        chosen_card = None

        # STRATEGY 1: Aggressive play - Play DRAW_TWO if available
        if draw_twos:
            chosen_idx, chosen_card = draw_twos[0]

        # STRATEGY 2: Late-game aggression - Unleash Wild Draw Fours and Wilds
        # Only prioritize if hand <= 3, otherwise save them!
        elif wild_cards and hand_size <= 3:
            # Prefer WILD_DRAW_FOUR over standard WILD if we are going for the win
            wd4 = [c for c in wild_cards if c[1]["type"] == "WILD_DRAW_FOUR"]
            if wd4:
                chosen_idx, chosen_card = wd4[0]
            else:
                chosen_idx, chosen_card = wild_cards[0]

        # STRATEGY 3: General play - High point value first to minimize penalty if we lose
        elif action_cards:
            # SKIP and REVERSE are worth 20 points
            chosen_idx, chosen_card = action_cards[0]

        elif number_cards:
            # Play the highest number face-value first
            number_cards.sort(key=lambda x: x[1]["value"], reverse=True)
            chosen_idx, chosen_card = number_cards[0]

        # STRATEGY 4: Forced play - We only have Wilds left but our hand size is > 3
        if chosen_idx is None and wild_cards:
            chosen_idx, chosen_card = wild_cards[0]

        # Fallback (Should mathematically never trigger given the above logic, but safe to keep)
        if chosen_idx is None:
            chosen_idx, chosen_card = playable[0]

        # Determine wild color if a Wild card is played
        wild_color = None
        if chosen_card["type"].startswith("WILD"):
            wild_color = self.pick_wild_color(hand)

        # Record the play for stats tracking
        self._record_play(chosen_card, wild_color)

        return chosen_idx, wild_color

    def on_game_start(self):
        super().on_game_start()

    def on_game_end(self, won, placement, points):
        # Automatically saves stats to strategies/gemini_base_bot/stats.json
        super().on_game_end(won, placement, points)