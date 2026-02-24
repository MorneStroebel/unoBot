"""
Strategy loader — auto-discovers all strategy classes in this package.

Adding a new strategy requires ONLY dropping a .py file into strategies/.
No changes to this file or any other file are needed.

Discovery rules:
  - Every .py file in strategies/ is scanned (including base_strategy.py).
  - Any class that inherits from BaseStrategy and is NOT BaseStrategy itself
    is registered automatically.
  - The registry key is the snake_case form of the class name with a trailing
    _strategy suffix stripped:
      BaseBotStrategy      →  base_bot
      MyAwesomeStrategy    →  my_awesome
      GeminiBot            →  gemini_bot
"""

import importlib
import inspect
import os
import re
from typing import Dict, Type

from strategies.base_strategy import BaseStrategy

# Only the abstract base is excluded — everything else is fair game
_EXCLUDED_CLASSES = {"BaseStrategy"}


def _to_snake_case(name: str) -> str:
    """Convert CamelCase class name to snake_case registry key."""
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    if s.endswith("_strategy"):
        s = s[: -len("_strategy")]
    return s


def _discover_strategies() -> Dict[str, Type[BaseStrategy]]:
    """Scan the strategies package and return a {key: class} registry."""
    registry: Dict[str, Type[BaseStrategy]] = {}

    strategies_dir = os.path.dirname(os.path.abspath(__file__))
    skip_files = {"__init__.py", "loader.py"}

    for filename in sorted(os.listdir(strategies_dir)):
        if not filename.endswith(".py") or filename in skip_files:
            continue

        module_name = f"strategies.{filename[:-3]}"
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            print(f"⚠️  Could not load strategy module '{module_name}': {e}")
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                obj.__name__ not in _EXCLUDED_CLASSES
                and issubclass(obj, BaseStrategy)
                and obj is not BaseStrategy
            ):
                key = _to_snake_case(obj.__name__)
                registry[key] = obj

    return registry


def load_strategy(name: str = "base_bot") -> BaseStrategy:
    """
    Instantiate a strategy by its registry key.

    Args:
        name: Snake_case strategy name (e.g. "base_bot", "gemini_bot").
              Defaults to "base_bot" (BaseBotStrategy from base_strategy.py).

    Returns:
        An instance of the requested strategy.

    Raises:
        ValueError: If no strategy with that name is found.
    """
    registry = _discover_strategies()

    if name not in registry:
        available = ", ".join(sorted(registry.keys()))
        raise ValueError(
            f"Unknown strategy '{name}'. Available strategies: {available}"
        )

    cls = registry[name]
    print(f"🧠 Loaded strategy: {cls.__name__}  (key: '{name}')")
    return cls()


def list_strategies() -> Dict[str, str]:
    """
    Return a {key: class_name} dict of all discoverable strategies.
    Useful for UI / CLI menus.
    """
    return {k: v.__name__ for k, v in sorted(_discover_strategies().items())}
