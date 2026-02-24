#!/usr/bin/env python3
"""
UnoBot Stats Viewer

View detailed statistics about your bot's performance.
"""

import json
import os
import sys
from datetime import datetime
from collections import Counter

def load_stats():
    """Load statistics from file."""
    stats_file = "stats/statistics.json"
    if not os.path.exists(stats_file):
        print("❌ No statistics found. Play some games first!")
        return None
    
    with open(stats_file, 'r') as f:
        return json.load(f)

def load_game_history():
    """Load game history from file."""
    games_file = "stats/game_history.json"
    if not os.path.exists(games_file):
        return []
    
    with open(games_file, 'r') as f:
        return json.load(f)

def print_header(title):
    """Print a section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_overall_stats(stats):
    """Print overall performance statistics."""
    print_header("📊 OVERALL PERFORMANCE")
    
    overall = stats['overall']
    print(f"\n  Total Games Played: {overall['total_games']}")
    print(f"  Total Wins: {overall['total_wins']}")
    print(f"  Total Losses: {overall['total_games'] - overall['total_wins']}")
    print(f"  Win Rate: {overall['win_rate']:.2f}%")
    print(f"  Total Points Earned: {overall['total_points']}")
    
    if overall['total_games'] > 0:
        avg_points = overall['total_points'] / overall['total_games']
        print(f"  Average Points per Game: {avg_points:.2f}")

def print_strategy_comparison(stats):
    """Print comparison of all strategies."""
    print_header("🧠 STRATEGY COMPARISON")
    
    if not stats['strategies']:
        print("\n  No strategy data available yet.")
        return
    
    # Header
    print(f"\n  {'Strategy':<20} {'Games':<8} {'Wins':<8} {'Win%':<8} {'Pts':<10} {'Avg':<8} {'Best':<8}")
    print("  " + "-"*68)
    
    # Sort by win rate
    strategies = sorted(
        stats['strategies'].items(),
        key=lambda x: x[1]['win_rate'],
        reverse=True
    )
    
    for name, data in strategies:
        print(f"  {name:<20} {data['games_played']:<8} {data['wins']:<8} "
              f"{data['win_rate']:<7.1f}% {data['total_points']:<10} "
              f"{data['avg_points_per_game']:<7.1f} {data['best_game_points']:<8}")

def print_strategy_details(stats, strategy_name):
    """Print detailed stats for a specific strategy."""
    if strategy_name not in stats['strategies']:
        print(f"\n❌ Strategy '{strategy_name}' not found.")
        return
    
    data = stats['strategies'][strategy_name]
    
    print_header(f"🎯 STRATEGY: {strategy_name}")
    
    print(f"\n  📈 Performance:")
    print(f"     Games Played: {data['games_played']}")
    print(f"     Wins: {data['wins']}")
    print(f"     Losses: {data['losses']}")
    print(f"     Win Rate: {data['win_rate']:.2f}%")
    
    print(f"\n  🏆 Scoring:")
    print(f"     Total Points: {data['total_points']}")
    print(f"     Average per Game: {data['avg_points_per_game']:.2f}")
    print(f"     Best Game: {data['best_game_points']} points")
    
    print(f"\n  🥇 Placements:")
    print(f"     1st Place: {data['placements']['1']}")
    print(f"     2nd Place: {data['placements']['2']}")
    print(f"     3rd Place: {data['placements']['3']}")
    print(f"     4th+ Place: {data['placements']['4+']}")
    
    print(f"\n  🎴 Actions:")
    print(f"     Cards Played: {data['total_cards_played']}")
    print(f"     Cards Drawn: {data['total_cards_drawn']}")
    print(f"     UNO Calls: {data['total_uno_calls']}")
    print(f"     Penalties: {data['total_penalties']}")
    
    if data['games_played'] > 0:
        print(f"\n  📊 Averages per Game:")
        print(f"     Cards Played: {data['total_cards_played'] / data['games_played']:.1f}")
        print(f"     Cards Drawn: {data['total_cards_drawn'] / data['games_played']:.1f}")
        print(f"     Penalties: {data['total_penalties'] / data['games_played']:.1f}")

def print_action_stats(stats):
    """Print action statistics."""
    print_header("🎴 ACTION STATISTICS")
    
    actions = stats['actions']
    
    print(f"\n  Total Actions:")
    print(f"     Cards Played: {actions['total_cards_played']}")
    print(f"     Cards Drawn: {actions['total_cards_drawn']}")
    print(f"     UNO Calls: {actions['total_uno_calls']}")
    print(f"     Penalties Received: {actions['total_penalties']}")
    
    if actions['total_catchouts_attempted'] > 0:
        success_rate = (actions['total_catchouts_successful'] / actions['total_catchouts_attempted']) * 100
        print(f"     Catchouts: {actions['total_catchouts_successful']}/{actions['total_catchouts_attempted']} ({success_rate:.1f}%)")
    
    if actions['card_types']:
        print(f"\n  Card Types Played:")
        sorted_types = sorted(actions['card_types'].items(), key=lambda x: x[1], reverse=True)
        for card_type, count in sorted_types:
            print(f"     {card_type}: {count}")
    
    print(f"\n  Wild Color Choices:")
    colors = actions['colors_chosen']
    total_wilds = sum(colors.values())
    if total_wilds > 0:
        for color in ['RED', 'BLUE', 'GREEN', 'YELLOW']:
            count = colors[color]
            percentage = (count / total_wilds) * 100
            print(f"     {color}: {count} ({percentage:.1f}%)")

def print_recent_games(games, limit=10):
    """Print recent game history."""
    print_header(f"📜 RECENT GAMES (Last {limit})")
    
    if not games:
        print("\n  No games recorded yet.")
        return
    
    recent = games[-limit:]
    
    print(f"\n  {'Date':<20} {'Strategy':<15} {'Result':<8} {'Place':<7} {'Points':<8} {'Actions':<12}")
    print("  " + "-"*68)
    
    for game in reversed(recent):
        date_str = datetime.fromisoformat(game['start_time']).strftime('%Y-%m-%d %H:%M')
        strategy = game['strategy'][:14]
        result = "WIN" if game['result'] == 'win' else "LOSS"
        place = f"{game['placement']}"
        points = game['points_earned']
        actions = f"{game['actions']['cards_played']}P/{game['actions']['cards_drawn']}D"
        
        print(f"  {date_str:<20} {strategy:<15} {result:<8} {place:<7} {points:<8} {actions:<12}")

def print_trends(games):
    """Print performance trends."""
    print_header("📈 PERFORMANCE TRENDS")
    
    if len(games) < 5:
        print("\n  Not enough games for trend analysis (need at least 5).")
        return
    
    # Last 5 games
    last_5 = games[-5:]
    wins_last_5 = sum(1 for g in last_5 if g['result'] == 'win')
    
    # Last 10 games
    last_10 = games[-10:] if len(games) >= 10 else games
    wins_last_10 = sum(1 for g in last_10 if g['result'] == 'win')
    
    print(f"\n  Recent Performance:")
    print(f"     Last 5 games: {wins_last_5}/5 wins ({wins_last_5/5*100:.0f}%)")
    if len(games) >= 10:
        print(f"     Last 10 games: {wins_last_10}/10 wins ({wins_last_10/10*100:.0f}%)")
    
    # Strategy usage
    strategies_used = Counter(g['strategy'] for g in games[-20:])
    print(f"\n  Strategy Usage (Last 20 games):")
    for strategy, count in strategies_used.most_common():
        print(f"     {strategy}: {count} games")
    
    # Average points trend
    if len(games) >= 10:
        first_half = games[:len(games)//2]
        second_half = games[len(games)//2:]
        
        avg_first = sum(g['points_earned'] for g in first_half) / len(first_half)
        avg_second = sum(g['points_earned'] for g in second_half) / len(second_half)
        
        print(f"\n  Points Trend:")
        print(f"     First half average: {avg_first:.1f}")
        print(f"     Second half average: {avg_second:.1f}")
        
        if avg_second > avg_first:
            print(f"     📈 Improving! (+{avg_second - avg_first:.1f} points)")
        elif avg_second < avg_first:
            print(f"     📉 Declining (-{avg_first - avg_second:.1f} points)")
        else:
            print(f"     ➡️  Stable performance")

def main():
    """Main function."""
    stats = load_stats()
    if not stats:
        return
    
    games = load_game_history()
    
    # Print all stats
    print("\n" + "🎮 UNOBOT STATISTICS DASHBOARD 🎮".center(70))
    
    if stats['last_updated']:
        update_time = datetime.fromisoformat(stats['last_updated']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Last Updated: {update_time}".center(70))
    
    print_overall_stats(stats)
    print_strategy_comparison(stats)
    
    # Print details for each strategy
    for strategy_name in stats['strategies'].keys():
        print_strategy_details(stats, strategy_name)
    
    print_action_stats(stats)
    
    if games:
        print_recent_games(games, min(10, len(games)))
        print_trends(games)
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
