"""
Game Engine — orchestrates turn-taking and card actions.
"""

from api.actions import play_card, draw_card, call_uno
from config.settings import DEBUG_MODE


class Engine:
    """Core game engine that drives turn-taking for a single game session."""

    def __init__(self, room_id, player_id, strategy, stats_tracker=None):
        self.room_id = room_id
        self.player_id = player_id
        self.strategy = strategy
        self.stats_tracker = stats_tracker
        self.has_drawn = False

    def take_turn(self, hand: list, top_card: dict, current_color: str):
        """
        Execute one turn: optionally call UNO, choose a card to play, or draw.

        Args:
            hand:          List of card dicts in the player's hand.
            top_card:      The current top card on the discard pile.
            current_color: The active colour (may differ from top_card colour after a wild).
        """
        self.has_drawn = False

        if not hand:
            print("⚠️  Hand is empty — nothing to play or draw")
            return

        # Call UNO when holding exactly 2 cards (about to play one of them)
        if len(hand) == 2:
            self._call_uno()

        card_index, wild_color = self.strategy.choose_card(hand, top_card, current_color)

        if card_index is not None:
            self._play_card(hand, card_index, wild_color)
        else:
            self._draw_card()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_uno(self):
        try:
            call_uno(self.room_id, self.player_id)
            print("🗣️  Called UNO!")
            if self.stats_tracker:
                self.stats_tracker.record_uno_call()
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️  UNO call failed: {e}")

    def _play_card(self, hand: list, card_index: int, wild_color: str):
        try:
            played_card = hand[card_index]
            result = play_card(self.room_id, self.player_id, card_index, wild_color)

            if result.get("result", {}).get("penalty"):
                penalty = result["result"]
                print(f"⚠️  PENALTY: {penalty.get('penaltyTitle')} — {penalty.get('penaltyDescription')}")
                if self.stats_tracker:
                    self.stats_tracker.record_penalty()
            else:
                card_desc = f"{played_card.get('color')} {played_card.get('type')}"
                if played_card.get("type") == "NUMBER":
                    card_desc += f" {played_card.get('value')}"
                print(f"🤖 Played: {card_desc}")
                if wild_color:
                    print(f"   Chose colour: {wild_color}")
                if self.stats_tracker:
                    self.stats_tracker.record_card_played(played_card, wild_color)

        except Exception as e:
            print(f"❌ Failed to play card: {e}")
            self._draw_card()

    def _draw_card(self):
        try:
            result = draw_card(self.room_id, self.player_id)

            if result.get("result", {}).get("penalty"):
                penalty = result["result"]
                print(f"⚠️  PENALTY: {penalty.get('penaltyTitle')} — {penalty.get('penaltyDescription')}")
                if self.stats_tracker:
                    self.stats_tracker.record_penalty()
            else:
                drawn_card = result.get("result", {}).get("card")
                if drawn_card and DEBUG_MODE:
                    card_desc = f"{drawn_card.get('color')} {drawn_card.get('type')}"
                    if drawn_card.get("type") == "NUMBER":
                        card_desc += f" {drawn_card.get('value')}"
                    print(f"🃏 Drew: {card_desc}")
                else:
                    print("🃏 Drew a card")

                if self.stats_tracker:
                    self.stats_tracker.record_card_drawn()

            self.has_drawn = True

        except Exception as e:
            print(f"❌ Failed to draw card: {e}")
