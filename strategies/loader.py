"""
Strategy loader — auto-discovers folder-based strategy packages.

Each strategy lives in its own sub-folder:
    strategies/
        adaptive_bot/
            __init__.py     ← must export the strategy class
            strategy.py     ← defines the class (inherits BaseStrategy)
            stats.json      ← auto-created by StrategyStats
            learning.json   ← optional; used by learning strategies

Discovery rules:
  - Every sub-folder that contains an __init__.py is scanned.
  - Any class that inherits from BaseStrategy is registered.
  - The registry key is the folder name (already snake_case).

Adding a new strategy:
    1. Create strategies/my_strategy/__init__.py and strategy.py
    2. Run: python generate_config.py
    3. No other files need editing.
"""

import importlib
import inspect
import os
from typing import Dict, Type

from strategies.base_strategy import BaseStrategy

_EXCLUDED_CLASSES = {"BaseStrategy"}


def _discover_strategies() -> Dict[str, Type[BaseStrategy]]:
    """Scan strategy sub-folders and return a {folder_name: class} registry."""
    registry: Dict[str, Type[BaseStrategy]] = {}
    strategies_dir = os.path.dirname(os.path.abspath(__file__))

    for entry in sorted(os.listdir(strategies_dir)):
        folder = os.path.join(strategies_dir, entry)
        init   = os.path.join(folder, "__init__.py")

        if not os.path.isdir(folder) or not os.path.exists(init):
            continue  # skip plain files and folders without __init__.py

        module_name = f"strategies.{entry}"
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            print(f"⚠️  Could not load strategy package '{module_name}': {e}")
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                obj.__name__ not in _EXCLUDED_CLASSES
                and issubclass(obj, BaseStrategy)
                and obj is not BaseStrategy
            ):
                registry[entry] = obj  # key = folder name
                break  # one class per folder

    return registry


def load_strategy(name: str = "adaptive_bot") -> BaseStrategy:
    """
    Instantiate a strategy by its folder name.

    Args:
        name: Folder name of the strategy (e.g. "adaptive_bot").

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
    print(f"🧠 Loaded strategy: {cls.__name__}  (folder: '{name}')")
    return cls()


def list_strategies() -> Dict[str, str]:
    """Return a {folder_name: class_name} dict of all discoverable strategies."""
    return {k: v.__name__ for k, v in sorted(_discover_strategies().items())}
