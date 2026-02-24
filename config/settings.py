API_BASE_URL = "https://uno-839271117832.europe-west1.run.app/api"
SOCKET_URL = "https://uno-839271117832.europe-west1.run.app"
BOT_FIRST_NAME = "WorldClass"
BOT_LAST_NAME = "UnoBot"
PLAYER_NAME = "HoerBoer"
MAC_ADDRESS = "00:11:22:33:44:55"

IS_SANDBOX_MODE = True
DEBUG_MODE = False
ONLY_PLAYERS_MODE = False

# Strategy to use (change this to swap strategies)
# Options: "base_bot", "aggressive_bot", "smart_bot", or any custom strategy
ACTIVE_STRATEGY = "gemini_bot"

# Auto-Rejoin Configuration
AUTO_REJOIN = True  # Automatically rejoin after game ends
REJOIN_DELAY = 3  # Seconds to wait before rejoining

# Room Joining Configuration
AUTO_JOIN_OPEN_ROOM = True  # Wait for and join open rooms automatically
ROOM_CHECK_INTERVAL = 5  # Seconds between checking for open rooms
MAX_WAIT_TIME = 300  # Maximum seconds to wait for open room (5 minutes)

# Player Targeting Configuration
TARGET_PLAYERS = []  # List of player names to search for (e.g., ["Alice", "Bob"])
REQUIRE_TARGET_PLAYERS = False  # If True, only join rooms with target players