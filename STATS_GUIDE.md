# 📊 Statistics System Documentation

## Overview

The UnoBot statistics system provides comprehensive tracking of your bot's performance across all games, strategies, and actions.

---

## 📁 Files Created

### 1. `stats/tracker.py`
Core statistics tracking module that records all game data in real-time.

### 2. `stats/statistics.json`
Aggregated statistics file containing:
- Overall performance metrics
- Per-strategy statistics
- Action summaries
- Card type distributions
- Wild color preferences

### 3. `stats/game_history.json`
Complete game-by-game history with:
- Timestamps (start and end)
- Strategy used
- Win/loss result
- Placement (1st, 2nd, 3rd, 4th+)
- Points earned
- Detailed action counts
- Card types played
- Wild colors chosen

### 4. `view_stats.py`
Command-line tool for viewing and analyzing statistics.

---

## 🎯 What Gets Tracked

### Strategy Performance
For each strategy (base_bot, aggressive_bot, smart_bot, custom):

- **Games Played** - Total number of games
- **Wins** - Number of victories
- **Losses** - Number of defeats
- **Win Rate** - Percentage of games won
- **Total Points** - All points earned
- **Average Points per Game** - Mean points per game
- **Best Game Points** - Highest single-game score
- **Placements**:
  - 1st Place finishes
  - 2nd Place finishes
  - 3rd Place finishes
  - 4th+ Place finishes

### Action Statistics
Every action is tracked:

- **Cards Played** - Total cards played (broken down by type)
- **Cards Drawn** - Total cards drawn from deck
- **UNO Calls** - Number of times UNO was called
- **Penalties** - Penalty cards received
- **Catchouts Attempted** - Challenges issued
- **Catchouts Successful** - Successful challenges

### Card Type Distribution
Detailed breakdown of cards played:

- NUMBER cards (0-9)
- SKIP cards
- REVERSE cards
- DRAW_TWO cards
- WILD cards
- WILD_DRAW_FOUR cards

### Wild Color Choices
Tracks which colors you choose for wild cards:

- RED
- BLUE
- GREEN
- YELLOW

Helps analyze strategy color preferences.

### Game Details
Each game records:

- **Room ID** - Unique game identifier
- **Player ID** - Your player identifier
- **Strategy** - Which strategy was used
- **Start Time** - Game start timestamp
- **End Time** - Game end timestamp
- **Result** - Win or loss
- **Placement** - Final ranking (1-4+)
- **Points Earned** - Points scored
- **All Actions** - Complete action log for that game

---

## 🚀 Using the Stats System

### Automatic Tracking

Stats are tracked automatically when you run the bot. No configuration needed!

```bash
python -m app.main
```

The bot will:
1. ✅ Load existing statistics
2. ✅ Track all actions during gameplay
3. ✅ Record game results
4. ✅ Save updated statistics
5. ✅ Display summary on exit (Ctrl+C)

### Viewing Statistics

Use the stats viewer tool:

```bash
python view_stats.py
```

This displays:
- 📊 Overall performance summary
- 🧠 Strategy comparison table
- 🎯 Detailed per-strategy breakdowns
- 🎴 Action statistics
- 📜 Recent game history
- 📈 Performance trends

---

## 📊 Statistics Dashboard

### Overall Performance
```
Total Games Played: 45
Total Wins: 23
Total Losses: 22
Win Rate: 51.11%
Total Points Earned: 1,250
Average Points per Game: 27.78
```

### Strategy Comparison
```
Strategy              Games    Wins     Win%     Pts        Avg      Best
--------------------------------------------------------------------------------
smart_bot            20       13       65.0%    780        39.0     95
aggressive_bot       15       7        46.7%    310        20.7     65
base_bot            10       3        30.0%    160        16.0     45
```

### Strategy Details (Example: smart_bot)
```
📈 Performance:
   Games Played: 20
   Wins: 13
   Losses: 7
   Win Rate: 65.00%

🏆 Scoring:
   Total Points: 780
   Average per Game: 39.00
   Best Game: 95 points

🥇 Placements:
   1st Place: 13
   2nd Place: 5
   3rd Place: 2
   4th+ Place: 0

🎴 Actions:
   Cards Played: 234
   Cards Drawn: 89
   UNO Calls: 15
   Penalties: 3

📊 Averages per Game:
   Cards Played: 11.7
   Cards Drawn: 4.5
   Penalties: 0.2
```

### Action Statistics
```
Total Actions:
   Cards Played: 523
   Cards Drawn: 198
   UNO Calls: 38
   Penalties Received: 12
   Catchouts: 3/5 (60.0%)

Card Types Played:
   NUMBER: 287
   SKIP: 82
   DRAW_TWO: 75
   REVERSE: 45
   WILD: 28
   WILD_DRAW_FOUR: 6

Wild Color Choices:
   RED: 12 (35.3%)
   BLUE: 9 (26.5%)
   GREEN: 8 (23.5%)
   YELLOW: 5 (14.7%)
```

### Recent Games
```
Date                 Strategy        Result   Place   Points   Actions
------------------------------------------------------------------------
2024-02-24 14:32    smart_bot       WIN      1       65       12P/3D
2024-02-24 14:15    smart_bot       LOSS     2       0        15P/8D
2024-02-24 13:58    aggressive_bot  WIN      1       45       10P/4D
...
```

### Performance Trends
```
Recent Performance:
   Last 5 games: 3/5 wins (60%)
   Last 10 games: 6/10 wins (60%)

Strategy Usage (Last 20 games):
   smart_bot: 12 games
   aggressive_bot: 5 games
   base_bot: 3 games

Points Trend:
   First half average: 24.5
   Second half average: 31.2
   📈 Improving! (+6.7 points)
```

---

## 🔍 Analyzing Your Stats

### Comparing Strategies

Look at the Strategy Comparison table to see which strategy performs best:

- **Win Rate** - Most important metric for competitive play
- **Average Points** - Shows scoring efficiency
- **Best Game** - Indicates peak performance potential
- **Placements** - Distribution of finishes

### Identifying Weaknesses

Check the detailed strategy stats:

- **High Penalties** - Strategy may be playing illegal moves
- **Low Cards Played** - Strategy might be too conservative
- **High Cards Drawn** - Not finding playable cards efficiently
- **Poor Placements** - Consistently finishing lower

### Optimization Tips

Based on stats, you can:

1. **Switch strategies** if one significantly outperforms others
2. **Tune strategy behavior** based on action patterns
3. **Identify favorable wild colors** from distribution
4. **Track improvement** over time with trends

---

## 📈 Understanding Metrics

### Win Rate
```
Win Rate = (Wins / Total Games) × 100
```
- **50%+** = Good performance
- **60%+** = Excellent performance
- **70%+** = Elite performance

### Average Points per Game
- Points are earned from opponents' remaining cards
- Higher average = more dominant wins
- Typical range: 15-40 points per game

### Cards Played vs. Drawn Ratio
```
Efficiency = Cards Played / (Cards Played + Cards Drawn)
```
- **>70%** = Efficient, finding playable cards
- **50-70%** = Average efficiency
- **<50%** = Drawing too many cards, strategy issue

### Penalty Rate
```
Penalty Rate = Penalties / Games Played
```
- **<0.5** = Excellent, clean play
- **0.5-1.0** = Acceptable
- **>1.0** = Concerning, check strategy legality

---

## 🛠️ Stats Files Format

### statistics.json Structure
```json
{
  "strategies": {
    "smart_bot": {
      "games_played": 20,
      "wins": 13,
      "losses": 7,
      "total_points": 780,
      "win_rate": 65.0,
      "avg_points_per_game": 39.0,
      "placements": {
        "1": 13,
        "2": 5,
        "3": 2,
        "4+": 0
      },
      "best_game_points": 95,
      "total_cards_played": 234,
      "total_cards_drawn": 89,
      "total_uno_calls": 15,
      "total_penalties": 3
    }
  },
  "overall": {
    "total_games": 45,
    "total_wins": 23,
    "total_points": 1250,
    "win_rate": 51.11
  },
  "actions": {
    "total_cards_played": 523,
    "total_cards_drawn": 198,
    "card_types": {
      "NUMBER": 287,
      "SKIP": 82
    },
    "colors_chosen": {
      "RED": 12,
      "BLUE": 9,
      "GREEN": 8,
      "YELLOW": 5
    }
  },
  "last_updated": "2024-02-24T14:32:15.123456"
}
```

### game_history.json Structure
```json
[
  {
    "room_id": "uuid",
    "player_id": "uuid",
    "strategy": "smart_bot",
    "start_time": "2024-02-24T14:30:00.000000",
    "end_time": "2024-02-24T14:32:15.000000",
    "result": "win",
    "placement": 1,
    "points_earned": 65,
    "actions": {
      "cards_played": 12,
      "cards_drawn": 3,
      "uno_calls": 1,
      "penalties": 0
    },
    "card_types_played": {
      "NUMBER": 7,
      "SKIP": 2,
      "WILD": 2,
      "DRAW_TWO": 1
    },
    "colors_chosen": {
      "RED": 1,
      "BLUE": 1,
      "GREEN": 0,
      "YELLOW": 0
    }
  }
]
```

---

## 🔄 Resetting Statistics

To start fresh:

```bash
rm stats/statistics.json
rm stats/game_history.json
```

Or to backup before reset:

```bash
cp stats/statistics.json stats/statistics_backup_$(date +%Y%m%d).json
cp stats/game_history.json stats/game_history_backup_$(date +%Y%m%d).json
rm stats/statistics.json stats/game_history.json
```

---

## 📊 Export & Analysis

### Export to CSV

You can write a simple script to export data:

```python
import json
import csv

# Load game history
with open('stats/game_history.json', 'r') as f:
    games = json.load(f)

# Export to CSV
with open('games_export.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Date', 'Strategy', 'Result', 'Placement', 'Points'])
    
    for game in games:
        writer.writerow([
            game['start_time'],
            game['strategy'],
            game['result'],
            game['placement'],
            game['points_earned']
        ])
```

### Import into Spreadsheet

1. Export data as shown above
2. Open in Excel/Google Sheets
3. Create charts and pivot tables
4. Perform advanced analysis

---

## 🎯 Best Practices

1. **Play Multiple Games** - Need at least 10 games for meaningful stats
2. **Test Each Strategy** - Compare all strategies fairly
3. **Review Regularly** - Check stats after every 5-10 games
4. **Backup Stats** - Save backups before major changes
5. **Track Trends** - Monitor improvement over time

---

## 🐛 Troubleshooting

**Stats not updating?**
- Check that files exist in `stats/` directory
- Verify bot has write permissions
- Enable DEBUG_MODE to see tracking messages

**Missing game data?**
- Game must complete for stats to be saved
- Ctrl+C during game may not record it
- Check game_history.json for partial entries

**Incorrect stats?**
- Stats are cumulative, check if you reset recently
- Verify strategy names match exactly
- Look for penalties that indicate issues

---

## 🔮 Future Enhancements

Potential additions:
- Head-to-head strategy comparisons
- Time-of-day performance analysis
- Opponent strategy detection
- Win streak tracking
- Elo rating system
- Web dashboard
- Real-time graphs

---

**Enjoy tracking your bot's journey to Uno mastery! 📊🏆**
