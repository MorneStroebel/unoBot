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
    """Manages room joining, finding, and auto-rejoin functionality."""

    def __init__(self):
        self.current_room_id = None
        self.current_player_id = None
        self.waiting_for_room = False
        self.only_players = False  # Track if only_players mode is active

    def find_room_with_players(self, target_players: list, only_players: bool = True) -> Tuple[Optional[str], Optional[str]]:
        """
        Find and join a room with specific players.

        Args:
            target_players: List of player names to search for
            only_players: If True, no system bots will be added

        Returns:
            Tuple of (room_id, player_id) or (None, None) if not found
        """
        print(f"🔍 Searching for room with players: {', '.join(target_players)}")
        print(f"   Only players mode: {only_players}")

        # Update the only_players state
        self.only_players = only_players

        try:
            result = find_and_join_room(target_players, only_players=only_players)

            # Result comes directly with roomId and playerId
            if result and result.get('roomId') and result.get('playerId'):
                room_id = result['roomId']
                player_id = result['playerId']
                print(f"✅ Found and joined room with target players!")
                print(f"   Room ID: {room_id}")
                print(f"   Player ID: {player_id}")
                return room_id, player_id
            else:
                print(f"❌ No room found with players: {', '.join(target_players)}")
        except Exception as e:
            print(f"❌ Error finding room with players: {e}")

        return None, None

    def wait_for_open_room(self, max_wait_time: int = MAX_WAIT_TIME, only_players: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """
        Wait for an open room and join when available.

        Args:
            max_wait_time: Maximum seconds to wait
            only_players: If True, no system bots will be added

        Returns:
            Tuple of (room_id, player_id) or (None, None) if timeout
        """
        print(f"⏳ Waiting for open room (max {max_wait_time}s, checking every {ROOM_CHECK_INTERVAL}s)...")
        if only_players:
            print(f"   Only players mode: {only_players}")

        # Update the only_players state
        self.only_players = only_players

        start_time = time.time()
        attempt = 0

        while time.time() - start_time < max_wait_time:
            attempt += 1
            elapsed = int(time.time() - start_time)

            try:
                # Try to get a room and join
                room_id = get_room_id()
                player_id = join_room(room_id, only_players=only_players)

                if room_id and player_id:
                    print(f"\n✅ Joined open room after {elapsed}s (attempt {attempt})")
                    return room_id, player_id

            except Exception as e:
                if DEBUG_MODE:
                    print(f"⏳ Attempt {attempt}: {e}")
                else:
                    print(f"⏳ Waiting... ({elapsed}/{max_wait_time}s)", end='\r')

            # Wait before next attempt
            time.sleep(ROOM_CHECK_INTERVAL)

        print(f"\n⏰ Timeout: No open room found after {max_wait_time}s")
        return None, None

    def join_or_create_room(self, target_players: Optional[list] = None, only_players: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """
        Join a room based on configuration and target players.

        Args:
            target_players: Optional list of player names to search for
            only_players: If True, no system bots will be added

        Returns:
            Tuple of (room_id, player_id)
        """
        # Update the only_players state
        self.only_players = only_players

        # If target players specified, try to find them first
        if target_players:
            room_id, player_id = self.find_room_with_players(target_players, only_players=only_players)

            if room_id and player_id:
                self.current_room_id = room_id
                self.current_player_id = player_id
                return room_id, player_id

            if REQUIRE_TARGET_PLAYERS:
                print(f"⚠️ REQUIRE_TARGET_PLAYERS is True, not joining other rooms")
                return None, None
            else:
                print("⚠️ Target players not found, trying regular room join...")

        # If AUTO_JOIN_OPEN_ROOM is enabled, wait for open room
        if AUTO_JOIN_OPEN_ROOM:
            room_id, player_id = self.wait_for_open_room(only_players=only_players)
        else:
            # Standard join - try once
            try:
                room_id = get_room_id()
                player_id = join_room(room_id, only_players=only_players)
                print(f"✅ Joined room")
            except Exception as e:
                print(f"❌ Failed to join room: {e}")
                return None, None

        if room_id and player_id:
            self.current_room_id = room_id
            self.current_player_id = player_id

        return room_id, player_id

    def rejoin_room(self, delay: int = 3) -> Tuple[Optional[str], Optional[str]]:
        """
        Rejoin the same room or find a new one.

        Args:
            delay: Seconds to wait before rejoining

        Returns:
            Tuple of (room_id, player_id)
        """
        print(f"\n⏳ Waiting {delay}s before rejoining...")
        time.sleep(delay)

        # Check if we're still in the room
        if self.current_room_id and self.current_player_id:
            if is_player_in_room(self.current_room_id, self.current_player_id):
                print("✅ Still in room, reconnecting...")
                return self.current_room_id, self.current_player_id

        # Not in room anymore, join a new one with same only_players setting
        print("🔄 Room ended, finding new room...")
        print(f"   Using only_players: {self.only_players}")

        # Join with preserved only_players setting
        return self.join_or_create_room(
            target_players=TARGET_PLAYERS if TARGET_PLAYERS else None,
            only_players=self.only_players
        )

    def leave_current_room(self) -> bool:
        """
        Leave the current room.

        Returns:
            True if successfully left, False otherwise
        """
        if not self.current_room_id or not self.current_player_id:
            print("⚠️ Not currently in a room")
            return False

        print(f"🚪 Leaving room {self.current_room_id}...")

        try:
            result = leave_room(self.current_room_id, self.current_player_id)

            if result:
                # Clear current room info
                self.current_room_id = None
                self.current_player_id = None
                print("✅ Successfully left room")
                return True
            else:
                print("❌ Failed to leave room")
                return False
        except Exception as e:
            print(f"❌ Error leaving room: {e}")
            return False

    def check_room_state(self) -> Optional[dict]:
        """
        Check the current room state.

        Returns:
            Room state dict or None
        """
        if not self.current_room_id or not self.current_player_id:
            return None

        try:
            response = get_room_state(self.current_room_id, self.current_player_id)
            if response and response.get('result'):
                return response['result']
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Error checking room state: {e}")

        return None

    def is_room_active(self) -> bool:
        """
        Check if the current room is still active.

        Returns:
            True if room is active, False otherwise
        """
        if not self.current_room_id or not self.current_player_id:
            return False

        return is_player_in_room(self.current_room_id, self.current_player_id)