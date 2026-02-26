"""
Game Engine — orchestrates turn-taking and card actions.
"""

from api.actions import play_card, draw_card, call_uno, pass_turn
from config.settings import DEBUG_MODE


class Engine:
    """Core game engine that drives turn-taking for a single game session."""

    def __init__(self, room_id, player_id, strategy, stats_tracker=None):
        self.room_id        = room_id
        self.player_id      = player_id
        self.strategy       = strategy
        self.stats_tracker  = stats_tracker
        self.has_drawn      = False
        self._last_top_card = None
        self._last_color    = ""

    def take_turn(self, hand: list, top_card: dict, current_color: str):
        self.has_drawn      = False
        self._last_top_card = top_card
        self._last_color    = current_color

        if not hand:
            print("⚠️  Hand is empty — nothing to play or draw", flush=True)
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
            print("🗣️  Called UNO!", flush=True)
            if self.stats_tracker:
                self.stats_tracker.record_uno_call()
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️  UNO call failed: {e}", flush=True)

    def _play_card(self, hand: list, card_index: int, wild_color: str):
        try:
            played_card = hand[card_index]
            result = play_card(self.room_id, self.player_id, card_index, wild_color)

            res = result.get("result", {})
            if res.get("penalty"):
                title = res.get("penaltyTitle", "Penalty")
                desc  = res.get("penaltyDescription", "")
                print(f"⚠️  PENALTY: {title} — {desc}", flush=True)
                if self.stats_tracker:
                    self.stats_tracker.record_penalty()
            else:
                card_desc = f"{played_card.get('color')} {played_card.get('type')}"
                if played_card.get("type") == "NUMBER":
                    card_desc += f" {played_card.get('value')}"
                print(f"🤖 Played: {card_desc}", flush=True)
                if wild_color:
                    print(f"   Chose colour: {wild_color}", flush=True)
                if self.stats_tracker:
                    self.stats_tracker.record_card_played(played_card, wild_color)

        except Exception as e:
            print(f"❌ Failed to play card: {e}", flush=True)
            self._draw_card()

    def _draw_card(self):
        try:
            result = draw_card(self.room_id, self.player_id)

            res = result.get("result", {})
            if res.get("penalty"):
                title = res.get("penaltyTitle", "Penalty")
                desc  = res.get("penaltyDescription", "")
                print(f"⚠️  PENALTY: {title} — {desc}", flush=True)
                if self.stats_tracker:
                    self.stats_tracker.record_penalty()
            else:
                drawn_card = res.get("card")
                if drawn_card:
                    card_desc = f"{drawn_card.get('color')} {drawn_card.get('type')}"
                    if drawn_card.get("type") == "NUMBER":
                        card_desc += f" {drawn_card.get('value')}"
                    print(f"🃏 Drew: {card_desc}", flush=True)
                    # If drawn card is not playable, pass the turn per API rules
                    if self.strategy and self._last_top_card:
                        playable = self.strategy.is_playable(
                            drawn_card, self._last_top_card, self._last_color
                        )
                        if not playable:
                            self._pass_turn()
                else:
                    print("🃏 Drew a card", flush=True)

                if self.stats_tracker:
                    self.stats_tracker.record_card_drawn()

            self.has_drawn = True

        except Exception as e:
            print(f"❌ Failed to draw card: {e}", flush=True)

    def _pass_turn(self):
        try:
            pass_turn(self.room_id, self.player_id)
            print("⏭ Passed turn (drawn card not playable)", flush=True)
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️  Pass turn failed: {e}", flush=True)
