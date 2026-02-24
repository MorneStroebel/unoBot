from .aggressive_bot import AggressiveBotStrategy
from .base_bot import BaseBotStrategy
from .gemini_bot import GeminiBot
from .smart_bot import SmartBotStrategy

def load_strategy(name="base_bot"):
    """
    Load a strategy by name.
    
    Available strategies:
    - base_bot: Simple strategy that plays first legal card
    - aggressive_bot: Prioritizes action cards and wilds
    - smart_bot: Strategic decision-making with card tracking
    
    Args:
        name: Strategy name to load
        
    Returns:
        Strategy instance
        
    Raises:
        ValueError: If strategy name is unknown
    """
    strategies = {
        "base_bot": BaseBotStrategy,
        "aggressive_bot": AggressiveBotStrategy,
        "smart_bot": SmartBotStrategy,
        "gemini_bot": GeminiBot
    }
    
    if name not in strategies:
        available = ", ".join(strategies.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available strategies: {available}")
    
    return strategies[name]()