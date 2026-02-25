import json
import os
import logging
import random
from strategies.base_strategy import BaseStrategy

# Configure console logger for stack monitoring
logger = logging.getLogger("GrandmasterAI")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(ch)
logger.setLevel(logging.INFO)


class GrandMasterStrategy(BaseStrategy):
    """
    GrandmasterAI: A Reinforcement Learning strategy inspired by Chess engines.

    Strategies:
    1. Phase Evaluation: Adjusts weights for Opening vs Endgame.
    2. Prophylaxis: Prevents opponent 'checkmate' (Uno) by saving action cards.
    3. Q-Learning: Learns which card types win games over time via brain.json.
    """

    def __init__(self):
        super().__init__()
        self.brain_path = "brain.json"
        self.q_table = self._load_brain()
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self._session_records = []
        self._last_state_action = None

    def _load_brain(self):
        if os.path.exists(self.brain_path):
            with open(self.brain_path, 'r') as f:
                return json.load(f)
        # Default weights for card types if no training data exists
        return {
            "NUMBER": 1.0, "SKIP": 2.0, "REVERSE": 2.0,
            "DRAW_TWO": 3.0, "WILD": 4.0, "WILD_DRAW_FOUR": 5.0
        }

    def _save_brain(self):
        with open(self.brain_path, 'w') as f:
            json.dump(self.q_table, f)

    def on_game_start(self):
        self._session_records = []
        logger.info("\n" + "=" * 50)
        logger.info("♟️ GRANDMASTER AI: NEW GAME STARTED")
        logger.info("=" * 50)

    def on_game_end(self, won, placement, points):
        # Reinforcement Learning: Update weights based on success
        reward = 10 if won else -5
        if self._last_state_action:
            card_type = self._last_state_action
            # Q-learning update: NewValue = OldValue + LR * (Reward - OldValue)
            self.q_table[card_type] += self.learning_rate * (reward - self.q_table[card_type])
            self._save_brain()
            logger.info(f"🧠 LEARNING: Updated {card_type} weight to {self.q_table[card_type]:.2f}")

    def _get_card_id(self, card):
        c_type = card.get('type', 'UNK')
        c_color = card.get('color', 'BLK')
        c_val = card.get('value', 'X')
        return f"({c_color[0]}-{c_type[:3]}-{c_val})"

    def choose_card(self, hand, top_card, current_color):
        stack_id = self._get_card_id({'type': top_card['type'], 'color': current_color, 'value': top_card.get('value')})
        self._session_records.append(stack_id)

        # LOGGING: Total count and Top 3 cards
        top_3 = " -> ".join(self._session_records[-3:])
        logger.info(f"[Played: {len(self._session_records):03}] Stack: {top_3}")

        playable = self.get_playable_cards(hand, top_card, current_color)
        if not playable:
            return None, None

        best_move_idx = None
        max_score = -float('inf')

        # CHESS STRATEGY: Determine Phase
        # Opening: Many cards, Endgame: Someone likely has few cards
        is_endgame = len(hand) <= 3

        for idx, card in playable:
            # 1. Base Score from ML Q-Table
            score = self.q_table.get(card['type'], 1.0)

            # 2. Material Value (Chess Logic: High numbers are 'heavier' pieces)
            if card['type'] == "NUMBER":
                score += (card.get('value', 0) / 10.0)

            # 3. Prophylaxis (Saving Wilds/Draws for Endgame)
            if not is_endgame and card['type'] in ["WILD", "WILD_DRAW_FOUR", "DRAW_TWO"]:
                score -= 2.0  # Penalty for 'wasting' power pieces early
            elif is_endgame and card['type'] in ["SKIP", "DRAW_TWO"]:
                score += 5.0  # High priority to stop opponent 'checkmate'

            # 4. Mobility (Prefer colors we have more of)
            score += self.count_color(hand, card['color']) * 0.5

            if score > max_score:
                max_score = score
                best_move_idx = idx

        # Record action for RL learning
        chosen_card = hand[best_move_idx]
        self._last_state_action = chosen_card['type']

        return best_move_idx, self.pick_wild_color(hand)