"""
Interactive Prompts - Handle user input for room selection and configuration.
"""

from typing import Optional, List


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """
    Prompt user for yes/no answer.
    
    Args:
        question: Question to ask
        default: Default value if user just presses Enter
        
    Returns:
        True for yes, False for no
    """
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{question} [{default_str}]: ").strip().lower()
        
        if response == '':
            return default
        elif response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please answer 'y' or 'n'")


def prompt_target_players() -> Optional[List[str]]:
    """
    Prompt user to enter target player names.
    
    Returns:
        List of player names or None if user skips
    """
    print("\n🎯 Enter player names to search for (comma-separated)")
    print("   Example: Alice, Bob, Charlie")
    print("   Press Enter to skip")
    
    response = input("Player names: ").strip()
    
    if not response:
        return None
    
    # Split by comma and clean up names
    players = [name.strip() for name in response.split(',')]
    players = [name for name in players if name]  # Remove empty strings
    
    if not players:
        return None
    
    print(f"✅ Target players: {', '.join(players)}")
    return players


def prompt_room_mode() -> dict:
    """
    Interactive prompt for room joining mode.
    
    Returns:
        Dictionary with configuration:
        - mode: 'target', 'wait', 'quick'
        - target_players: List of player names (if mode is 'target')
        - require_targets: Boolean (if mode is 'target')
        - only_players: Boolean (True if mode is 'target', False otherwise)
    """
    print("\n" + "="*60)
    print("🎮 UNOBOT ROOM SELECTION")
    print("="*60)
    print("\nHow do you want to join a room?")
    print()
    print("1. 🎯 Play with specific players ONLY")
    print("   - Search for rooms with target players")
    print("   - No AI bots will be added")
    print("   - Option to wait for them or join any room")
    print()
    print("2. ⏳ Wait for an open room")
    print("   - Automatically retry until a room is available")
    print("   - AI bots will fill empty spots")
    print("   - Good for busy servers")
    print()
    print("3. 🚀 Quick join")
    print("   - Join any available room immediately")
    print("   - AI bots will fill empty spots")
    print("   - No waiting, single attempt")
    print()
    
    # Get user choice
    while True:
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == '1':
            # Target players mode - only_players = True
            players = prompt_target_players()
            
            if players:
                print("⚠️ No players entered, switching to quick join mode")
                return {
                    'mode': 'quick',
                    'target_players': None,
                    'require_targets': False,
                    'only_players': True
                }
            
            # Ask if they want to require these players
            require = prompt_yes_no(
                "Only join rooms with these players (fallback to any room if not found)?",
                default=False
            )
            
            return {
                'mode': 'target',
                'target_players': players,
                'require_targets': require,
                'only_players': True  # Always True for target mode
            }
        
        elif choice == '2':
            # Wait mode - only_players = False
            return {
                'mode': 'wait',
                'target_players': None,
                'require_targets': False,
                'only_players': False
            }
        
        elif choice == '3':
            # Quick join mode - only_players = False
            return {
                'mode': 'quick',
                'target_players': None,
                'require_targets': False,
                'only_players': False
            }
        
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")


def prompt_continue_after_game() -> bool:
    """
    Ask user if they want to continue after a game ends.
    
    Returns:
        True to continue, False to exit
    """
    print("\n" + "="*60)
    return prompt_yes_no("Continue playing?", default=True)


def prompt_strategy_change() -> Optional[str]:
    """
    Prompt user if they want to change strategy.
    
    Returns:
        Strategy name or None to keep current
    """
    if not prompt_yes_no("Change strategy?", default=False):
        return None
    
    print("\nAvailable strategies:")
    print("1. base_bot - Simple, plays first legal card")
    print("2. aggressive_bot - Prioritizes action cards")
    print("3. smart_bot - Advanced strategic play")
    
    strategies = {
        '1': 'base_bot',
        '2': 'aggressive_bot',
        '3': 'smart_bot'
    }
    
    while True:
        choice = input("Enter your choice (1-3): ").strip()
        if choice in strategies:
            return strategies[choice]
        print("❌ Invalid choice. Please enter 1, 2, or 3.")


def prompt_leave_room() -> bool:
    """
    Ask user if they want to leave the current room.

    Returns:
        True to leave, False to stay
    """
    return prompt_yes_no("Leave current room?", default=False)


def prompt_post_game_action() -> str:
    """
    Prompt user for action after game ends.

    Returns:
        'continue' - Continue playing in same/new room
        'change_strategy' - Change strategy and continue
        'leave' - Leave room and exit
        'view_stats' - View statistics
    """
    print("\n" + "="*60)
    print("🎮 GAME ENDED - What would you like to do?")
    print("="*60)
    print()
    print("1. 🔄 Continue playing")
    print("2. 🧠 Change strategy and continue")
    print("3. 📊 View statistics")
    print("4. 🚪 Leave room and exit")
    print()

    while True:
        choice = input("Enter your choice (1-4): ").strip()

        if choice == '1':
            return 'continue'
        elif choice == '2':
            return 'change_strategy'
        elif choice == '3':
            return 'view_stats'
        elif choice == '4':
            return 'leave'
        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")


def display_startup_banner():
    """Display startup banner with bot information."""
    print("\n" + "="*60)
    print("🤖 UNOBOT - AI-Powered Uno Player")
    print("="*60)
    print("\nFeatures:")
    print("  ✅ Multiple AI strategies")
    print("  ✅ Auto-rejoin after games")
    print("  ✅ Target specific players")
    print("  ✅ Leave room anytime")
    print("  ✅ Comprehensive statistics tracking")
    print("  ✅ Real-time Socket.io events")
    print("="*60 + "\n")


def display_game_summary(stats_tracker):
    """
    Display a quick summary of current session.

    Args:
        stats_tracker: StatsTracker instance
    """
    if not stats_tracker:
        return

    stats = stats_tracker.get_all_stats()
    overall = stats['overall']

    print("\n" + "="*60)
    print("📊 SESSION SUMMARY")
    print("="*60)
    print(f"Total Games: {overall['total_games']}")
    print(f"Total Wins: {overall['total_wins']}")
    if overall['total_games'] > 0:
        print(f"Win Rate: {overall['win_rate']:.1f}%")
        print(f"Total Points: {overall['total_points']}")
    print("="*60)