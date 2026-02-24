"""
Settings management for UnoBot.

Values are loaded from config.json (if present), falling back to defaults.
Call save_settings() to persist any runtime changes.

Per-strategy overrides live under settings['strategies'][strategy_name],
e.g. {"bot_first_name": "Blitz", "bot_last_name": "Alpha"}.
"""

import json
import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_CONFIG_DIR, "config.json")

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------
_DEFAULTS = {
    # API
    "api_base_url": "https://uno-839271117832.europe-west1.run.app/api",
    "socket_url":   "https://uno-839271117832.europe-west1.run.app",

    # Bot identity (can be overridden per-strategy)
    "bot_first_name": "WorldClass",
    "bot_last_name":  "UnoBot",
    "player_name":    "HoerBoer",
    "mac_address":    "00:11:22:33:44:55",

    # Runtime flags
    "is_sandbox_mode":   True,
    "debug_mode":        True,
    "only_players_mode": False,

    # Strategy
    # Options: "base_bot", "aggressive_bot", "smart_bot", "gemini_bot"
    "active_strategy": "base_bot",

    # Auto-rejoin
    "auto_rejoin":  True,
    "rejoin_delay": 3,

    # Room joining
    "auto_join_open_room":  True,
    "room_check_interval":  5,
    "max_wait_time":        300,

    # Player targeting
    "target_players":         [],
    "require_target_players": False,

    # Per-strategy overrides
    # Each key is a strategy name; values override any global identity field.
    # Example:
    #   "strategies": {
    #       "aggressive_bot": {"bot_first_name": "Blitz", "bot_last_name": "Alpha"},
    #       "smart_bot":      {"bot_first_name": "Sage",  "bot_last_name": "Pro"}
    #   }
    "strategies": {},
}


# ---------------------------------------------------------------------------
# Load / save helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load config.json, merging with defaults so new keys are always present."""
    config = dict(_DEFAULTS)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            # Deep-merge strategy overrides
            strategies = dict(_DEFAULTS["strategies"])
            strategies.update(saved.get("strategies", {}))
            config.update(saved)
            config["strategies"] = strategies
        except Exception as e:
            print(f"⚠️  Could not load config.json: {e}  (using defaults)")
    return config


def save_settings(cfg: dict = None):
    """
    Persist settings to config.json.

    Args:
        cfg: dict to save. Defaults to the live _config so callers can do
             save_settings() with no arguments.
    """
    target = cfg if cfg is not None else _config
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(target, f, indent=2)
        print(f"💾 Settings saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"❌ Could not save settings: {e}")


def get_strategy_setting(strategy_name: str, key: str, fallback=None):
    """
    Return a per-strategy override for *key*, falling back to the global
    value or *fallback*.
    """
    override = _config.get("strategies", {}).get(strategy_name, {})
    if key in override:
        return override[key]
    return _config.get(key, fallback)


def set_strategy_setting(strategy_name: str, key: str, value):
    """Set a per-strategy override and save immediately."""
    _config.setdefault("strategies", {}).setdefault(strategy_name, {})[key] = value
    save_settings()


def set_setting(key: str, value):
    """Update a global setting and save immediately."""
    _config[key] = value
    # Keep module-level constants in sync for the current process
    _sync_module_constants()
    save_settings()


def _sync_module_constants():
    """Refresh module-level constants from _config (called after set_setting)."""
    import sys
    mod = sys.modules[__name__]
    for attr, key in _CONSTANT_MAP.items():
        setattr(mod, attr, _config[key])


# ---------------------------------------------------------------------------
# Load on import
# ---------------------------------------------------------------------------
_config = _load_config()

# ---------------------------------------------------------------------------
# Public constants (consumed by the rest of the codebase)
# ---------------------------------------------------------------------------
API_BASE_URL:            str  = _config["api_base_url"]
SOCKET_URL:              str  = _config["socket_url"]

BOT_FIRST_NAME:          str  = _config["bot_first_name"]
BOT_LAST_NAME:           str  = _config["bot_last_name"]
PLAYER_NAME:             str  = _config["player_name"]
MAC_ADDRESS:             str  = _config["mac_address"]

IS_SANDBOX_MODE:         bool = _config["is_sandbox_mode"]
DEBUG_MODE:              bool = _config["debug_mode"]
ONLY_PLAYERS_MODE:       bool = _config["only_players_mode"]

ACTIVE_STRATEGY:         str  = _config["active_strategy"]

AUTO_REJOIN:             bool = _config["auto_rejoin"]
REJOIN_DELAY:            int  = _config["rejoin_delay"]

AUTO_JOIN_OPEN_ROOM:     bool = _config["auto_join_open_room"]
ROOM_CHECK_INTERVAL:     int  = _config["room_check_interval"]
MAX_WAIT_TIME:           int  = _config["max_wait_time"]

TARGET_PLAYERS:          list = _config["target_players"]
REQUIRE_TARGET_PLAYERS:  bool = _config["require_target_players"]

# Map of module constant name -> config key (used by _sync_module_constants)
_CONSTANT_MAP = {
    "API_BASE_URL":           "api_base_url",
    "SOCKET_URL":             "socket_url",
    "BOT_FIRST_NAME":         "bot_first_name",
    "BOT_LAST_NAME":          "bot_last_name",
    "PLAYER_NAME":            "player_name",
    "MAC_ADDRESS":            "mac_address",
    "IS_SANDBOX_MODE":        "is_sandbox_mode",
    "DEBUG_MODE":             "debug_mode",
    "ONLY_PLAYERS_MODE":      "only_players_mode",
    "ACTIVE_STRATEGY":        "active_strategy",
    "AUTO_REJOIN":            "auto_rejoin",
    "REJOIN_DELAY":           "rejoin_delay",
    "AUTO_JOIN_OPEN_ROOM":    "auto_join_open_room",
    "ROOM_CHECK_INTERVAL":    "room_check_interval",
    "MAX_WAIT_TIME":          "max_wait_time",
    "TARGET_PLAYERS":         "target_players",
    "REQUIRE_TARGET_PLAYERS": "require_target_players",
}
