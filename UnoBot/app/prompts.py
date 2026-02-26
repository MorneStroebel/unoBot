"""
Interactive prompts — user input for room selection, strategy changes, etc.
"""

from typing import Optional, List


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt for a yes/no answer. Returns True for yes, False for no."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{question} [{default_str}]: ").strip().lower()
        if response == "":
            return default
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'")


def prompt_target_players() -> Optional[List[str]]:
    """Prompt for target player names (comma-separated). Returns list or None."""
    print("\n🎯 Enter player names to search for (comma-separated)")
    print("   Example: Alice, Bob")
    print("   Press Enter to skip")

    response = input("Player names: ").strip()
    if not response:
        return None

    players = [n.strip() for n in response.split(",") if n.strip()]
    if players:
        print(f"✅ Target players: {', '.join(players)}")
    return players or None


def prompt_room_mode() -> dict:
    """
    Interactive room-joining mode selection.

    Returns a dict with keys:
      mode            – 'target' | 'wait' | 'quick'
      target_players  – list of names or None
      require_targets – bool
      only_players    – bool
    """
    print("\n" + "=" * 60)
    print("🎮 UNOBOT — ROOM SELECTION")
    print("=" * 60)
    print("\nHow do you want to join a room?\n")
    print("1. 🎯 Play with specific players only (no AI bots)")
    print("2. ⏳ Wait for an open room (AI bots fill empty spots)")
    print("3. 🚀 Quick join any available room")
    print()

    while True:
        choice = input("Enter your choice (1-3): ").strip()

        if choice == "1":
            players = prompt_target_players()
            if not players:
                print("⚠️  No players entered — switching to quick join.")
                return {"mode": "quick", "target_players": None, "require_targets": False, "only_players": True}
            require = prompt_yes_no(
                "Only join rooms with these players (fallback to any room if not found)?",
                default=False,
            )
            return {"mode": "target", "target_players": players, "require_targets": require, "only_players": True}

        elif choice == "2":
            return {"mode": "wait", "target_players": None, "require_targets": False, "only_players": False}

        elif choice == "3":
            return {"mode": "quick", "target_players": None, "require_targets": False, "only_players": False}

        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")


def prompt_continue_after_game() -> bool:
    """Ask whether to keep playing. Returns True to continue."""
    print("\n" + "=" * 60)
    return prompt_yes_no("Continue playing?", default=True)


def prompt_strategy_change() -> Optional[str]:
    """
    Let the user pick a new strategy from the auto-discovered list.
    Returns the strategy key string, or None to keep the current strategy.
    """
    if not prompt_yes_no("Change strategy?", default=False):
        return None

    # Import here to avoid circular imports at module load time
    from strategies.loader import list_strategies
    strategies = list_strategies()

    if not strategies:
        print("⚠️  No strategies found.")
        return None

    entries = sorted(strategies.items())
    print("\nAvailable strategies:")
    for i, (key, class_name) in enumerate(entries, 1):
        print(f"  {i}. {key}  ({class_name})")

    while True:
        choice = input(f"Enter number (1-{len(entries)}): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(entries):
                return entries[idx][0]
        print(f"❌ Please enter a number between 1 and {len(entries)}.")


def prompt_post_game_action() -> str:
    """
    Post-game action menu.

    Returns one of: 'continue' | 'change_strategy' | 'view_stats' | 'leave'
    """
    print("\n" + "=" * 60)
    print("🎮 GAME ENDED — What would you like to do?")
    print("=" * 60)
    print("\n1. 🔄 Continue playing")
    print("2. 🧠 Change strategy and continue")
    print("3. 📊 View statistics")
    print("4. 🚪 Leave room and exit\n")

    while True:
        choice = input("Enter your choice (1-4): ").strip()
        mapping = {"1": "continue", "2": "change_strategy", "3": "view_stats", "4": "leave"}
        if choice in mapping:
            return mapping[choice]
        print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")


def display_startup_banner():
    """Print the startup banner."""
    print("\n" + "=" * 60)
    print("🤖 UNOBOT — AI-Powered Uno Player")
    print("=" * 60)
    print("  ✅ Plug-and-play strategy system")
    print("  ✅ Auto-rejoin after games")
    print("  ✅ Target specific players")
    print("  ✅ Comprehensive statistics tracking")
    print("  ✅ Real-time Socket.io events")
    print("=" * 60 + "\n")


def display_game_summary(stats_tracker):
    """Print a quick session summary from a StatsTracker instance."""
    if not stats_tracker:
        return

    stats = stats_tracker.get_all_stats()
    overall = stats["overall"]

    print("\n" + "=" * 60)
    print("📊 SESSION SUMMARY")
    print("=" * 60)
    print(f"  Total Games:  {overall['total_games']}")
    print(f"  Total Wins:   {overall['total_wins']}")
    if overall["total_games"] > 0:
        print(f"  Win Rate:     {overall['win_rate']:.1f}%")
        print(f"  Total Points: {overall['total_points']}")
    print("=" * 60)
