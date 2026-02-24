import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

class StatsTracker:
    """
    Comprehensive statistics tracker for UnoBot.
    
    Tracks:
    - Strategy performance (games played, wins, placements, points)
    - Action statistics (cards played, drawn, UNO calls, etc.)
    - Game history with timestamps
    - Detailed per-game statistics
    """
    
    def __init__(self, stats_dir="stats"):
        self.stats_dir = stats_dir
        self.stats_file = os.path.join(stats_dir, "statistics.json")
        self.games_file = os.path.join(stats_dir, "game_history.json")
        
        # Ensure stats directory exists
        os.makedirs(stats_dir, exist_ok=True)
        
        # Current game session data
        self.current_game = None
        self.current_session = {
            'actions': {
                'cards_played': 0,
                'cards_drawn': 0,
                'uno_calls': 0,
                'penalties': 0,
                'catchouts_attempted': 0,
                'catchouts_successful': 0,
                'wild_cards_played': 0,
                'action_cards_played': 0,
                'number_cards_played': 0
            },
            'card_types_played': {},
            'colors_chosen': {'RED': 0, 'BLUE': 0, 'GREEN': 0, 'YELLOW': 0}
        }
        
        # Load existing stats
        self.stats = self._load_stats()
        self.game_history = self._load_game_history()
    
    def _load_stats(self) -> Dict:
        """Load statistics from file or create new structure."""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading stats: {e}")
        
        # Default structure
        return {
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
    
    def _load_game_history(self) -> list:
        """Load game history from file."""
        if os.path.exists(self.games_file):
            try:
                with open(self.games_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading game history: {e}")
        return []
    
    def _save_stats(self):
        """Save statistics to file."""
        self.stats['last_updated'] = datetime.now().isoformat()
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving stats: {e}")
    
    def _save_game_history(self):
        """Save game history to file."""
        try:
            with open(self.games_file, 'w') as f:
                json.dump(self.game_history, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving game history: {e}")
    
    def start_game(self, room_id: str, player_id: str, strategy_name: str):
        """Start tracking a new game."""
        self.current_game = {
            'room_id': room_id,
            'player_id': player_id,
            'strategy': strategy_name,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'result': None,
            'placement': None,
            'points_earned': 0,
            'actions': {
                'cards_played': 0,
                'cards_drawn': 0,
                'uno_calls': 0,
                'penalties': 0,
                'catchouts_attempted': 0,
                'catchouts_successful': 0
            },
            'card_types_played': {},
            'colors_chosen': {'RED': 0, 'BLUE': 0, 'GREEN': 0, 'YELLOW': 0}
        }
        
        # Reset session data
        self.current_session = {
            'actions': {
                'cards_played': 0,
                'cards_drawn': 0,
                'uno_calls': 0,
                'penalties': 0,
                'catchouts_attempted': 0,
                'catchouts_successful': 0,
                'wild_cards_played': 0,
                'action_cards_played': 0,
                'number_cards_played': 0
            },
            'card_types_played': {},
            'colors_chosen': {'RED': 0, 'BLUE': 0, 'GREEN': 0, 'YELLOW': 0}
        }
        
        print(f"📊 Started tracking game with strategy: {strategy_name}")
    
    def record_card_played(self, card: Dict[str, Any], wild_color: Optional[str] = None):
        """Record a card being played."""
        if not self.current_game:
            return
        
        self.current_session['actions']['cards_played'] += 1
        self.current_game['actions']['cards_played'] += 1
        
        # Track card type
        card_type = card.get('type', 'UNKNOWN')
        self.current_session['card_types_played'][card_type] = \
            self.current_session['card_types_played'].get(card_type, 0) + 1
        self.current_game['card_types_played'][card_type] = \
            self.current_game['card_types_played'].get(card_type, 0) + 1
        
        # Categorize card
        if card_type.startswith('WILD'):
            self.current_session['actions']['wild_cards_played'] += 1
        elif card_type in ['SKIP', 'REVERSE', 'DRAW_TWO']:
            self.current_session['actions']['action_cards_played'] += 1
        elif card_type == 'NUMBER':
            self.current_session['actions']['number_cards_played'] += 1
        
        # Track wild color choice
        if wild_color:
            self.current_session['colors_chosen'][wild_color] += 1
            self.current_game['colors_chosen'][wild_color] += 1
    
    def record_card_drawn(self):
        """Record a card being drawn."""
        if not self.current_game:
            return
        
        self.current_session['actions']['cards_drawn'] += 1
        self.current_game['actions']['cards_drawn'] += 1
    
    def record_uno_call(self):
        """Record an UNO call."""
        if not self.current_game:
            return
        
        self.current_session['actions']['uno_calls'] += 1
        self.current_game['actions']['uno_calls'] += 1
    
    def record_penalty(self):
        """Record a penalty received."""
        if not self.current_game:
            return
        
        self.current_session['actions']['penalties'] += 1
        self.current_game['actions']['penalties'] += 1
    
    def record_catchout(self, success: bool):
        """Record a catchout attempt."""
        if not self.current_game:
            return
        
        self.current_session['actions']['catchouts_attempted'] += 1
        self.current_game['actions']['catchouts_attempted'] += 1
        
        if success:
            self.current_session['actions']['catchouts_successful'] += 1
            self.current_game['actions']['catchouts_successful'] += 1
    
    def end_game(self, won: bool, placement: int, points: int):
        """
        End the current game and record results.
        
        Args:
            won: Whether the bot won
            placement: Final placement (1 = winner, 2 = second, etc.)
            points: Points earned this game
        """
        if not self.current_game:
            print("⚠️ No active game to end")
            return
        
        # Update current game data
        self.current_game['end_time'] = datetime.now().isoformat()
        self.current_game['result'] = 'win' if won else 'loss'
        self.current_game['placement'] = placement
        self.current_game['points_earned'] = points
        
        strategy = self.current_game['strategy']
        
        # Initialize strategy stats if needed
        if strategy not in self.stats['strategies']:
            self.stats['strategies'][strategy] = {
                'games_played': 0,
                'wins': 0,
                'losses': 0,
                'total_points': 0,
                'win_rate': 0.0,
                'avg_points_per_game': 0.0,
                'placements': {
                    '1': 0,  # First place
                    '2': 0,  # Second place
                    '3': 0,  # Third place
                    '4+': 0  # Fourth or worse
                },
                'best_game_points': 0,
                'total_cards_played': 0,
                'total_cards_drawn': 0,
                'total_uno_calls': 0,
                'total_penalties': 0
            }
        
        strategy_stats = self.stats['strategies'][strategy]
        
        # Update strategy stats
        strategy_stats['games_played'] += 1
        if won:
            strategy_stats['wins'] += 1
        else:
            strategy_stats['losses'] += 1
        
        strategy_stats['total_points'] += points
        
        # Update placement stats
        if placement == 1:
            strategy_stats['placements']['1'] += 1
        elif placement == 2:
            strategy_stats['placements']['2'] += 1
        elif placement == 3:
            strategy_stats['placements']['3'] += 1
        else:
            strategy_stats['placements']['4+'] += 1
        
        # Update best game
        if points > strategy_stats['best_game_points']:
            strategy_stats['best_game_points'] = points
        
        # Calculate averages
        strategy_stats['win_rate'] = (strategy_stats['wins'] / strategy_stats['games_played']) * 100
        strategy_stats['avg_points_per_game'] = strategy_stats['total_points'] / strategy_stats['games_played']
        
        # Update action stats for strategy
        strategy_stats['total_cards_played'] += self.current_game['actions']['cards_played']
        strategy_stats['total_cards_drawn'] += self.current_game['actions']['cards_drawn']
        strategy_stats['total_uno_calls'] += self.current_game['actions']['uno_calls']
        strategy_stats['total_penalties'] += self.current_game['actions']['penalties']
        
        # Update overall stats
        self.stats['overall']['total_games'] += 1
        if won:
            self.stats['overall']['total_wins'] += 1
        self.stats['overall']['total_points'] += points
        self.stats['overall']['win_rate'] = (
            self.stats['overall']['total_wins'] / self.stats['overall']['total_games']
        ) * 100
        
        # Update overall action stats
        actions = self.stats['actions']
        actions['total_cards_played'] += self.current_game['actions']['cards_played']
        actions['total_cards_drawn'] += self.current_game['actions']['cards_drawn']
        actions['total_uno_calls'] += self.current_game['actions']['uno_calls']
        actions['total_penalties'] += self.current_game['actions']['penalties']
        actions['total_catchouts_attempted'] += self.current_game['actions']['catchouts_attempted']
        actions['total_catchouts_successful'] += self.current_game['actions']['catchouts_successful']
        
        # Update card type stats
        for card_type, count in self.current_game['card_types_played'].items():
            actions['card_types'][card_type] = actions['card_types'].get(card_type, 0) + count
        
        # Update color choices
        for color, count in self.current_game['colors_chosen'].items():
            actions['colors_chosen'][color] += count
        
        # Add to game history
        self.game_history.append(self.current_game)
        
        # Save everything
        self._save_stats()
        self._save_game_history()
        
        # Print summary
        result_emoji = "🏆" if won else "📊"
        print(f"\n{result_emoji} Game Ended!")
        print(f"Strategy: {strategy}")
        print(f"Result: {'WIN' if won else 'LOSS'} (Placement: {placement})")
        print(f"Points Earned: {points}")
        print(f"Cards Played: {self.current_game['actions']['cards_played']}")
        print(f"Cards Drawn: {self.current_game['actions']['cards_drawn']}")
        print(f"Penalties: {self.current_game['actions']['penalties']}")
        print(f"\n📈 Strategy Win Rate: {strategy_stats['win_rate']:.1f}%")
        print(f"📈 Overall Win Rate: {self.stats['overall']['win_rate']:.1f}%\n")
        
        # Clear current game
        self.current_game = None
    
    def get_strategy_stats(self, strategy_name: str) -> Optional[Dict]:
        """Get statistics for a specific strategy."""
        return self.stats['strategies'].get(strategy_name)
    
    def get_all_stats(self) -> Dict:
        """Get all statistics."""
        return self.stats
    
    def get_recent_games(self, limit: int = 10) -> list:
        """Get recent game history."""
        return self.game_history[-limit:]
    
    def print_summary(self):
        """Print a summary of all statistics."""
        print("\n" + "="*60)
        print("📊 UNOBOT STATISTICS SUMMARY")
        print("="*60)
        
        overall = self.stats['overall']
        print(f"\n🎮 OVERALL PERFORMANCE")
        print(f"Total Games: {overall['total_games']}")
        print(f"Total Wins: {overall['total_wins']}")
        print(f"Win Rate: {overall['win_rate']:.1f}%")
        print(f"Total Points: {overall['total_points']}")
        
        print(f"\n🎯 STRATEGY BREAKDOWN")
        for strategy, data in self.stats['strategies'].items():
            print(f"\n  Strategy: {strategy}")
            print(f"    Games: {data['games_played']} | Wins: {data['wins']} | Losses: {data['losses']}")
            print(f"    Win Rate: {data['win_rate']:.1f}%")
            print(f"    Total Points: {data['total_points']} | Avg: {data['avg_points_per_game']:.1f}")
            print(f"    Best Game: {data['best_game_points']} points")
            print(f"    Placements: 1st: {data['placements']['1']} | 2nd: {data['placements']['2']} | 3rd: {data['placements']['3']} | 4th+: {data['placements']['4+']}")
        
        actions = self.stats['actions']
        print(f"\n🎴 ACTION STATISTICS")
        print(f"Cards Played: {actions['total_cards_played']}")
        print(f"Cards Drawn: {actions['total_cards_drawn']}")
        print(f"UNO Calls: {actions['total_uno_calls']}")
        print(f"Penalties: {actions['total_penalties']}")
        print(f"Catchouts: {actions['total_catchouts_successful']}/{actions['total_catchouts_attempted']}")
        
        if actions['card_types']:
            print(f"\n🃏 CARD TYPES PLAYED")
            for card_type, count in sorted(actions['card_types'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {card_type}: {count}")
        
        print(f"\n🎨 WILD COLOR CHOICES")
        for color, count in actions['colors_chosen'].items():
            print(f"  {color}: {count}")
        
        print("\n" + "="*60 + "\n")
