"""
Room Manager - Handles room finding, joining, and auto-rejoin logic.
"""

import time
from typing import Optional, Tuple
from api.actions import (
    get_room_id,
    join_room,
    find_and_join_room,
    get_room_state,
    is_player_in_room,
    leave_room
)
from config.settings import (
    AUTO_JOIN_OPEN_ROOM,
    ROOM_CHECK_INTERVAL,
    MAX_WAIT_TIME,
    TARGET_PLAYERS,
    REQUIRE_TARGET_PLAYERS,
    DEBUG_MODE
)


class RoomManager:
    def __init__(self):
        self.current_room_id = None
        self.current_player_id = None
        self.only_players = False

    # -------------------------------------------------
    # INTERNAL STATE HELPER (CRITICAL)
    # -------------------------------------------------
    def _set_current_room(self, room_id, player_id):
        self.current_room_id = room_id
        self.current_player_id = player_id

    # -------------------------------------------------
    # FIND ROOM WITH PLAYERS
    # -------------------------------------------------
    def find_room_with_players(self, target_players: list, only_players: bool = True):
        print(f"🔍 Searching for room with players: {', '.join(target_players)}")
        self.only_players = only_players

        try:
            result = find_and_join_room(target_players, only_players=only_players)

            if result and result.get("roomId") and result.get("playerId"):
                room_id = result["roomId"]
                player_id = result["playerId"]

                self._set_current_room(room_id, player_id)

                print("✅ Found and joined target room")
                return room_id, player_id

        except Exception as e:
            print(f"❌ Error finding room: {e}")

        return None, None

    # -------------------------------------------------
    # WAIT FOR OPEN ROOM
    # -------------------------------------------------
    def wait_for_open_room(self, max_wait_time=MAX_WAIT_TIME, only_players=False):
        print(f"⏳ Waiting for open room (max {max_wait_time}s)")
        self.only_players = only_players

        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                room_id = get_room_id()
                player_id = join_room(room_id, only_players=only_players)

                if room_id and player_id:
                    self._set_current_room(room_id, player_id)
                    print("✅ Joined open room")
                    return room_id, player_id

            except Exception as e:
                if DEBUG_MODE:
                    print(f"⏳ Waiting: {e}")

            time.sleep(ROOM_CHECK_INTERVAL)

        print("⏰ Timeout waiting for room")
        return None, None

    # -------------------------------------------------
    # JOIN OR CREATE
    # -------------------------------------------------
    def join_or_create_room(self, target_players=None, only_players=False):
        self.only_players = only_players

        if target_players:
            room_id, player_id = self.find_room_with_players(
                target_players,
                only_players=only_players
            )
            if room_id:
                return room_id, player_id

            if REQUIRE_TARGET_PLAYERS:
                return None, None

        if AUTO_JOIN_OPEN_ROOM:
            return self.wait_for_open_room(only_players=only_players)

        try:
            room_id = get_room_id()
            player_id = join_room(room_id, only_players=only_players)
            self._set_current_room(room_id, player_id)
            return room_id, player_id
        except Exception as e:
            print(f"❌ Failed to join room: {e}")
            return None, None

    # -------------------------------------------------
    # CREATE NEW ROOM (auto grind mode — always fresh)
    # -------------------------------------------------
    def create_and_join_room(self, only_players=False):
        """Always create a brand-new room. Never joins an existing one."""
        from api.client import post as api_post
        from config.settings import IS_SANDBOX_MODE
        try:
            resp = api_post("/rooms", {"isSandbox": IS_SANDBOX_MODE})
            room_id = resp.json().get("roomId")
            if not room_id:
                raise ValueError("Server did not return a roomId")
            player_id = join_room(room_id, only_players=only_players)
            if not player_id:
                raise ValueError("Could not join the created room")
            self._set_current_room(room_id, player_id)
            print(f"🏠 Created new room: {room_id}", flush=True)
            return room_id, player_id
        except Exception as e:
            print(f"❌ Failed to create room: {e}", flush=True)
            return None, None

    # -------------------------------------------------
    # REJOIN
    # -------------------------------------------------
    def rejoin_room(self, delay=3, force_create=False):
        print(f"⏳ Rejoining in {delay}s...", flush=True)
        time.sleep(delay)

        # Clear old room state — the previous game is over
        self.current_room_id = None
        self.current_player_id = None

        if force_create:
            print("🏠 Auto Grind — creating a new room", flush=True)
            return self.create_and_join_room(only_players=self.only_players)

        print("🔄 Finding a new WAITING room", flush=True)
        return self.join_or_create_room(
            target_players=TARGET_PLAYERS,
            only_players=self.only_players
        )

    # -------------------------------------------------
    # LEAVE (THIS NOW ALWAYS FIRES)
    # -------------------------------------------------
    def leave_current_room(self):
        if not self.current_room_id or not self.current_player_id:
            print("⚠️ leave_current_room: no active room")
            return False

        room_id = self.current_room_id
        player_id = self.current_player_id

        print(f"🚪 Leaving room {room_id}")

        try:
            leave_room(room_id, player_id)
            print("✅ Leave request sent")
        except Exception as e:
            print(f"❌ Leave failed: {e}")
            return False
        finally:
            self.current_room_id = None
            self.current_player_id = None

        return True

    # -------------------------------------------------
    # STATE CHECKS
    # -------------------------------------------------
    def check_room_state(self):
        if not self.current_room_id or not self.current_player_id:
            return None

        try:
            response = get_room_state(self.current_room_id, self.current_player_id)
            return response.get("result") if response else None
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Room state error: {e}")
            return None

    def is_room_active(self):
        if not self.current_room_id or not self.current_player_id:
            return False
        return is_player_in_room(self.current_room_id, self.current_player_id)