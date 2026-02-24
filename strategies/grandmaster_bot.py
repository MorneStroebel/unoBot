from strategies.base_strategy import BaseStrategy


class GrandmasterBotStrategy(BaseStrategy):
    """
    GrandmasterBot Strategy

    Inspired by Chessprogramming.org concepts:
    1. Evaluation Phases: Adjusts weights for Opening, Middlegame, and Endgame.
    2. Mobility: Prioritizes moves that keep our 'hand mobility' (color variety) high.
    3. Prophylaxis: Holds 'defensive pieces' (Wilds) to prevent being stuck.
    4. Zugzwang: Forces opponents into undesirable draws in the endgame.
    """

    def on_game_start(self):
        self.turn_count = 0
        self.opponent_aggression = 0  # Tracks how many action cards are played against us

    def choose_card(self, hand, top_card, current_color):
        playable_cards = self.get_playable_cards(hand, top_card, current_color)

        if not playable_cards:
            return None, None

        # 1. IDENTIFY GAME PHASE (Chess Analogy)
        # Opening: > 7 cards, Middlegame: 4-7 cards, Endgame: <= 3 cards
        hand_size = len(hand)
        is_endgame = any(True for _ in range(1))  # Placeholder for opponent hand tracking if available
        # Since we can't see opponent hands, we use our hand size and turn count as a proxy

        # 2. EVALUATION FUNCTION (Heuristics)
        best_move_idx = -1
        highest_score = -float('inf')

        for index, card in playable_cards:
            score = 0

            # Strategy A: Material Value (High numbers are 'heavier' pieces to develop early)
            if card['type'] == "NUMBER":
                score += card['value'] * (1.5 if hand_size > 6 else 1.0)

            # Strategy B: Mobility/Tempo (Action cards)
            # In Opening, we develop pieces. In Endgame, we use them for 'Check' (Draw 2 / Skip)
            if card['type'] in ["SKIP", "REVERSE", "DRAW_TWO"]:
                if hand_size <= 4:
                    score += 20  # Endgame 'Forcing Move'
                else:
                    score += 5  # Mid-game 'Positional Adjustment'

            # Strategy C: King Safety (Wilds are our 'Escapes')
            # A Grandmaster saves Wilds for when they are 'in check' (no other legal moves)
            if card['type'] in ["WILD", "WILD_DRAW_FOUR"]:
                if hand_size > 2:
                    score -= 15  # Don't waste Wilds early (Prophylaxis)
                else:
                    score += 50  # Use to finish the game (Mating Net)

            # Strategy D: Color Consolidation (Pawn Structure)
            # Keep a diverse hand to avoid getting 'frozen' (Mobility)
            color_count = self.count_color(hand, card['color'])
            if color_count > 1:
                score += 10  # Strengthen our 'center' by playing colors we have duplicates of

            if score > highest_score:
                highest_score = score
                best_move_idx = index

        # 3. SELECT WILD COLOR (Positioning)
        # Choose the color that gives us the most 'future mobility'
        wild_color = self.pick_wild_color(hand)

        return best_move_idx, wild_color