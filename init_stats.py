#!/usr/bin/env python3
"""
Initialize stats files if they don't exist.
This is useful to avoid the "No statistics found" error when running view_stats.py
before playing any games.
"""

import os
import json

# Create stats directory if it doesn't exist
os.makedirs('stats', exist_ok=True)

# Default statistics structure
default_stats = {
    'strategies': {},
    'overall': {
        'total_games': 0,
        'total_wins': 0,
        'total_points': 0,
        'win_rate': 0.0
    },
    'actions': {
        'total_cards_played': 0,
        'total_cards_drawn': 0,
        'total_uno_calls': 0,
        'total_penalties': 0,
        'total_catchouts_attempted': 0,
        'total_catchouts_successful': 0,
        'card_types': {},
        'colors_chosen': {'RED': 0, 'BLUE': 0, 'GREEN': 0, 'YELLOW': 0}
    },
    'last_updated': None
}

# Create statistics.json if it doesn't exist
stats_file = 'stats/statistics.json'
if not os.path.exists(stats_file):
    with open(stats_file, 'w') as f:
        json.dump(default_stats, f, indent=2)
    print(f"✅ Created {stats_file}")
else:
    print(f"ℹ️  {stats_file} already exists")

# Create game_history.json if it doesn't exist
history_file = 'stats/game_history.json'
if not os.path.exists(history_file):
    with open(history_file, 'w') as f:
        json.dump([], f, indent=2)
    print(f"✅ Created {history_file}")
else:
    print(f"ℹ️  {history_file} already exists")

print("\n✅ Stats files initialized! You can now run view_stats.py")
