# 🎮 UnoBot - Intelligent Uno Game Bot

A clean, modular, strategy-driven bot for playing Uno through the official Uno Game Engine API.

## 🌟 Features

- **🎯 Interactive Startup Menu** - Choose specific players or open rooms
- **🔄 Auto-Rejoin System** - Automatically rejoin and play continuously
- **⏳ Smart Room Waiting** - Wait for specific players or available rooms
- **🔌 Real-time Socket.io Integration** - Instant game state updates
- **🧠 Multiple AI Strategies** - Easy strategy swapping via config
- **📊 Comprehensive Statistics** - Track performance, actions, and trends
- **🔄 Auto-Reconnection** - Handles connection drops gracefully
- **📈 Smart Decision Making** - From basic to advanced AI strategies
- **🛡️ Rule Compliance** - Follows all official Uno rules and penalties
- **🎯 State Persistence** - Recovers from crashes automatically

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [New Features](#-new-features)
- [Strategy Swapping](#-strategy-swapping)
- [Statistics Tracking](#-statistics-tracking)
- [Architecture](#-architecture)
- [Available Strategies](#-available-strategies)
- [Game Rules](#-game-rules)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Development](#-development)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip or poetry

### Installation

1. **Clone or extract the repository**
   ```bash
   cd UnoBot
   ```

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install requests python-socketio --break-system-packages
   ```

4. **Run the bot**
   ```bash
   python -m app.main
   ```

### Interactive Startup

When you run the bot, you'll see an interactive menu:

```
============================================================
🎮 UNOBOT STARTUP - ROOM SELECTION
============================================================

How would you like to join games?

1. 🎯 Play against specific player(s)
2. 🌐 Join any available open room
3. 🔄 Auto-rejoin after games end (recommended)

Enter your choice (1-3):
```

**Choose your mode:**
- **Option 1:** Find and play against a specific player by name
- **Option 2:** Join any available open room immediately  
- **Option 3:** Continuous play - auto-rejoin after each game ends

**Features:**
- ⏳ Bot waits for players/rooms to become available
- 🔄 Auto-rejoins for continuous play sessions
- 📊 Stats tracked across all games
- 🛑 Press Ctrl+C anytime for graceful exit

See **[NEW_FEATURES.md](NEW_FEATURES.md)** for complete guide.

---

## 🆕 New Features

### 🎯 Interactive Startup Menu

Choose how you want to play when starting the bot:

1. **Play against specific player** - Enter a player name, bot finds and plays with them
2. **Join any open room** - Bot joins first available room
3. **Auto-rejoin mode** - Continuous play, automatically rejoins after each game

### 🔄 Auto-Rejoin System

Bot can automatically rejoin rooms after games end:

```
🎉 WE WON! Score: 65 points

⏳ Game ended. Preparing to rejoin in 3 seconds...

============================================================
🔄 REJOINING - Preparing for next game...
============================================================

✅ Successfully joined room with JohnDoe!
```

Perfect for:
- Overnight training sessions
- Testing strategies over many games
- Playing continuously with friends
- Building comprehensive statistics

### ⏳ Smart Room Waiting

Bot intelligently waits for players or rooms:

- **Waiting for specific player:** Checks every 5 seconds until player is available
- **Waiting for open room:** Finds first WAITING room, creates new if none exist
- **Progress updates:** Shows waiting status every 30 seconds
- **Never times out:** Waits as long as needed

Example:
```
🔍 Searching for player: Alice...
⚠️  Player 'Alice' not found or room not available
⏳ Waiting for player to be available...
⏳ Still waiting... (attempt 6)
✅ Successfully joined room with Alice!
```

### 📊 Enhanced Statistics

All new features are fully integrated with stats tracking:
- Stats saved after every game
- Works with auto-rejoin for multi-game sessions
- Tracks wins, losses, placements, points across all modes
- Graceful shutdown (Ctrl+C) saves everything

For complete guide, see **[NEW_FEATURES.md](NEW_FEATURES.md)**

---

## 🔄 Strategy Swapping

**SUPER EASY!** Just change one line in `config/settings.py`:

```python
# Options: "base_bot", "aggressive_bot", "smart_bot"
ACTIVE_STRATEGY = "smart_bot"  # Change this!
```

That's it! No code changes needed. Restart the bot and it will use the new strategy.

---

## 📊 Statistics Tracking

UnoBot automatically tracks comprehensive statistics for all your games!

### What Gets Tracked

**Strategy Performance:**
- Games played, wins, losses, win rate
- Points earned (total, average, best game)
- Placements (1st, 2nd, 3rd, 4th+)

**Action Statistics:**
- Cards played/drawn, UNO calls, penalties
- Card type distribution (NUMBER, SKIP, WILD, etc.)
- Wild color preferences

**Game History:**
- Complete game-by-game records with timestamps
- Strategy used per game
- Detailed action logs

### Viewing Your Stats

```bash
python view_stats.py
```

This shows:
- 📊 Overall performance summary
- 🧠 Strategy comparison table
- 🎯 Detailed per-strategy breakdowns
- 🎴 Action statistics
- 📜 Recent game history
- 📈 Performance trends

### Example Output

```
🎮 UNOBOT STATISTICS DASHBOARD 🎮

📊 OVERALL PERFORMANCE
  Total Games Played: 45
  Total Wins: 23
  Win Rate: 51.11%
  Total Points Earned: 1,250

🧠 STRATEGY COMPARISON
  Strategy              Games    Wins     Win%     Pts        Avg      Best
  ------------------------------------------------------------------------
  smart_bot            20       13       65.0%    780        39.0     95
  aggressive_bot       15       7        46.7%    310        20.7     65
  base_bot            10       3        30.0%    160        16.0     45
```

### Stats Files

All statistics are saved in the `stats/` directory:
- `statistics.json` - Aggregated stats
- `game_history.json` - Complete game history

For detailed documentation, see [STATS_GUIDE.md](STATS_GUIDE.md)

---

## 🏗️ Architecture

```
UnoBot/
├── api/                          # API communication layer
│   ├── actions.py               # REST API endpoints (join, play, draw, etc.)
│   ├── client.py                # HTTP client with MAC address auth
│   └── socket_listener.py       # Socket.io real-time events
│
├── app/                          # Application entry point
│   ├── bot.py                   # Main bot runner
│   └── main.py                  # Entry point
│
├── config/                       # Configuration
│   └── settings.py              # API URL, bot name, active strategy
│
├── core/                         # Core game engine
│   ├── engine.py                # Turn-taking logic
│   └── state.py                 # State persistence
│
├── strategies/                   # AI strategies (plug & play)
│   ├── base.py                  # Abstract strategy interface
│   ├── base_bot.py              # Simple strategy
│   ├── aggressive_bot.py        # Action card prioritization
│   ├── smart_bot.py             # Advanced strategic play
│   └── loader.py                # Strategy factory
│
├── stats/                        # Statistics tracking
│   ├── tracker.py               # Stats tracker module
│   ├── statistics.json          # Aggregated statistics
│   └── game_history.json        # Complete game history
│
├── view_stats.py                 # Stats viewer tool
└── state.json                    # Persisted game state
```

### Key Design Principles

1. **Separation of Concerns** - API, game logic, and strategies are independent
2. **Strategy Pattern** - Swap AI without touching core code
3. **Event-Driven** - Socket.io for real-time game updates
4. **Resilient** - Auto-reconnection and state persistence

---

## 🤖 Available Strategies

### 1. Base Bot (`base_bot`)
**Best for:** Learning, testing, simple gameplay

**Strategy:**
- Plays the first legal card in hand
- Random color selection for wild cards
- No advanced decision-making

**Pros:** Simple, fast, predictable  
**Cons:** Not competitive, doesn't optimize play

---

### 2. Aggressive Bot (`aggressive_bot`)
**Best for:** Disrupting opponents, competitive play

**Strategy Priority:**
1. Wild Draw Four (if legal)
2. Draw Two cards
3. Skip cards
4. Reverse cards
5. Wild cards
6. Number cards (highest first)

**Features:**
- Validates Wild Draw Four legality
- Chooses wild color based on hand distribution
- Maximizes opponent disruption

**Pros:** Competitive, aggressive, fun  
**Cons:** May hold onto number cards too long

---

### 3. Smart Bot (`smart_bot`)
**Best for:** Winning, competitive tournaments

**Strategy:**
- **Card Tracking** - Remembers played cards
- **Situational Awareness** - Different tactics for early/mid/end game
- **Value Optimization** - Prioritizes getting rid of high-point cards
- **Smart Wild Colors** - Weighted by card count and value

**Game Phase Tactics:**
- **Early Game (5+ cards):** Save wilds and action cards, play low-value cards
- **Mid Game (3-5 cards):** Balanced approach, use action cards strategically
- **End Game (≤3 cards):** Play high-value cards first to minimize risk

**Pros:** Most competitive, strategic depth  
**Cons:** Slightly more complex, requires more computation

---

## 📜 Game Rules

### Objective
Be the first to get rid of all your cards. First to 1000 points wins the game.

### Card Types

**Number Cards (0-9)**
- 76 cards total (19 per color)
- One '0' per color, two of each '1-9' per color

**Action Cards**
- **Draw Two** (20 pts) - Next player draws 2, skips turn
- **Reverse** (20 pts) - Reverses play direction
- **Skip** (20 pts) - Next player loses turn

**Wild Cards**
- **Wild** (50 pts) - Play anytime, declare color
- **Wild Draw Four** (50 pts) - Next player draws 4, skips turn
  - **RESTRICTION:** Can only play if you have NO cards matching current color
  - Can be challenged!

### Playing Cards

A card is **playable** if it matches the top card by:
- **Color** (RED, BLUE, GREEN, YELLOW)
- **Number** (0-9)
- **Type** (SKIP, REVERSE, DRAW_TWO)
- Or it's a **WILD** card (always playable)

### Calling UNO

⚠️ **CRITICAL RULE**
- You MUST call "UNO!" before playing your second-to-last card
- If caught not calling it, you draw 2 penalty cards
- Other players can challenge you with a "catchout"

### Catchout Challenges

- Any player can challenge someone with 1 card who didn't call UNO
- **Successful:** Target draws 2 cards
- **Failed:** Challenger draws 2 cards

### Wild Draw Four Challenges

- Next player can challenge if they suspect you had a matching color
- **Guilty:** You draw 4 cards (not the challenger)
- **Innocent:** Challenger draws 6 cards (4 + 2 penalty)

### Scoring

**Card Values:**
- Number cards: Face value (0-9 points)
- Action cards: 20 points each
- Wild cards: 50 points each

Winner scores points from cards remaining in all opponents' hands.

### Penalties

❌ **Actions that result in drawing 2 cards:**
- Playing out of turn
- Playing an illegal card
- Not calling UNO before playing 2nd-to-last card
- Failed catchout challenge
- Various other rule violations

---

## 🔌 API Reference

### Socket.io Events

**Connection:**
```python
socket.emit('joinRoom', {
    'roomId': 'room-uuid',
    'playerId': 'player-uuid'
})
```

**Events Received:**

| Event | Description | When |
|-------|-------------|------|
| `turn` | Game state update | Every action |
| `turn` (private) | Includes your hand | Your turn |
| `action` | Specific action result | After play/draw |
| `gameEnd` | Game over | Someone wins |
| `countdownStart` | Game starting | Before game |

### REST API Endpoints

**Base URL:** `https://uno-839271117832.europe-west1.run.app/api`

**Key Endpoints:**
- `GET /rooms/list` - List active rooms
- `GET /rooms/:id` - Get room state
- `POST /rooms` - Create room
- `POST /rooms/:id/join` - Join room
- `POST /rooms/:id/play` - Play card
- `POST /rooms/:id/draw` - Draw card
- `POST /rooms/:id/uno` - Call UNO
- `POST /rooms/:id/catchout` - Challenge opponent
- `POST /rooms/:id/pass` - Pass turn (after drawing)

**Authentication:**
All requests include `X-MAC-Address` header for rate limiting.

---

## ⚙️ Configuration

Edit `config/settings.py`:

```python
# API Configuration
API_BASE_URL = "https://uno-839271117832.europe-west1.run.app/api"
SOCKET_URL = "https://uno-839271117832.europe-west1.run.app"

# Bot Identity
BOT_FIRST_NAME = "WorldClass"
BOT_LAST_NAME = "UnoBot"
MAC_ADDRESS = "00:11:22:33:44:55"  # Change for multiple bots

# Game Mode
IS_SANDBOX_MODE = True  # True for testing, False for competitive

# Strategy Selection (CHANGE THIS TO SWAP STRATEGIES!)
ACTIVE_STRATEGY = "smart_bot"  # Options: base_bot, aggressive_bot, smart_bot

# Debug Mode
DEBUG_MODE = False  # Set to True for verbose logging
```

---

## 🛠️ Development

### Creating a Custom Strategy

1. **Create a new file** in `strategies/` (e.g., `my_strategy.py`)

2. **Inherit from BaseStrategy:**
```python
from .base import BaseStrategy

class MyStrategy(BaseStrategy):
    def choose_card(self, hand, top_card, current_color):
        """
        Your decision logic here.
        
        Args:
            hand: List of card objects
            top_card: Current top card on discard pile
            current_color: Active color
            
        Returns:
            (card_index, wild_color) or (None, None)
            
        Card format:
        {
            'color': 'RED'|'BLUE'|'GREEN'|'YELLOW'|'BLACK',
            'type': 'NUMBER'|'SKIP'|'REVERSE'|'DRAW_TWO'|'WILD'|'WILD_DRAW_FOUR',
            'value': 0-9 (for NUMBER cards only)
        }
        """
        # Your logic here
        return card_index, wild_color
```

3. **Register in `strategies/loader.py`:**
```python
from .my_strategy import MyStrategy

strategies = {
    "base_bot": BaseBotStrategy,
    "aggressive_bot": AggressiveBotStrategy,
    "smart_bot": SmartBotStrategy,
    "my_strategy": MyStrategy,  # Add this
}
```

4. **Activate in `config/settings.py`:**
```python
ACTIVE_STRATEGY = "my_strategy"
```

### Card Playability Helper

All strategies include this helper method:
```python
@staticmethod
def is_playable(card, top_card, current_color):
    """Check if a card can be legally played."""
    # Wild cards always playable
    if card['type'].startswith('WILD'):
        return True
    
    # Color match
    if card['color'] == current_color:
        return True
    
    # Type match (actions)
    if card['type'] == top_card['type'] and card['type'] != 'NUMBER':
        return True
    
    # Number match
    if card['type'] == 'NUMBER' and top_card['type'] == 'NUMBER':
        if card['value'] == top_card['value']:
            return True
    
    return False
```

---

## 📊 Rate Limits

Per IP/MAC address:
- **Global API:** 100 requests per 15 minutes
- **Room Creation:** 5 rooms per hour
- **Gameplay Actions:** 60 actions per minute

Exceeding limits returns HTTP 429.

---

## 🐛 Troubleshooting

**Bot not connecting?**
- Check API_BASE_URL in settings
- Verify internet connection
- Check for rate limiting (429 errors)

**Penalties appearing?**
- Check DEBUG_MODE = True to see what's happening
- Verify strategy is playing legal cards
- Ensure UNO is being called correctly

**Bot not playing?**
- Verify it's your turn (check socket events)
- Ensure hand data is being received
- Check for exceptions in console

**Connection drops?**
- Socket.io auto-reconnects and rejoins room
- State is persisted in state.json
- Bot should recover automatically

---

## 🏆 Competitive Tips

1. **Use smart_bot for tournaments** - Most competitive strategy
2. **Test in sandbox mode first** - IS_SANDBOX_MODE = True
3. **Monitor penalties** - Enable DEBUG_MODE to see what's happening
4. **Unique MAC addresses** - Change MAC_ADDRESS for multiple bots
5. **Watch the leaderboard** - Track your wins and losses

---

## 📝 License

This project is provided as-is for educational and competitive purposes.

---

## 🤝 Contributing

Want to add a new strategy or improve existing ones? Follow the Development guide above!

---

**Good luck and have fun! 🎉**

For API documentation: https://uno-839271117832.europe-west1.run.app/docs  
For game rules: https://uno-839271117832.europe-west1.run.app/
