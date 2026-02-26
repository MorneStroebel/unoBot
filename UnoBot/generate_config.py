"""
generate_config.py — Config generator for UnoBot.

Scans the strategies/ folder for sub-folders (each is a strategy package),
then writes (or updates) config/config.json with a block for every discovered
strategy.

Usage:
    python generate_config.py
    python generate_config.py --dry-run
    python generate_config.py --overwrite

What it does:
  1. Discovers every strategy folder in strategies/ (must contain __init__.py).
  2. Loads the existing config.json if present.
  3. Adds any missing strategy blocks under "strategies".
  4. Preserves any values you've already customised.
  5. Writes the result back to config/config.json.
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from strategies.loader import list_strategies  # noqa: E402

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "config.json")

DEFAULT_FIRST_NAME = "WorldClass"
DEFAULT_LAST_NAME  = "UnoBot"


def _load_existing() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Could not read existing config ({e}). Starting fresh.")
    return {}


def _build_config(existing: dict, overwrite: bool):
    discovered = list_strategies()  # {folder_name: ClassName}

    if not discovered:
        print("⚠️  No strategy folders found in strategies/. Nothing to generate.")
        sys.exit(0)

    config = {} if overwrite else dict(existing)

    if "active_strategy" not in config:
        config["active_strategy"] = sorted(discovered.keys())[0]

    if overwrite or "strategies" not in config:
        config["strategies"] = {}

    strategies_block: dict = config.setdefault("strategies", {})

    added   = []
    skipped = []

    for key, class_name in sorted(discovered.items()):
        if key in strategies_block and not overwrite:
            skipped.append(key)
            continue

        strategies_block[key] = {
            "bot_first_name": DEFAULT_FIRST_NAME,
            "bot_last_name":  DEFAULT_LAST_NAME,
        }
        added.append((key, class_name))

    config["strategies"] = dict(sorted(strategies_block.items()))
    return config, added, skipped


def _print_summary(config: dict, added: list, skipped: list, dry_run: bool):
    print()
    print("=" * 55)
    print("  UnoBot Config Generator")
    print("=" * 55)

    if added:
        print(f"\n✅ Added {len(added)} strategy block(s):")
        for key, class_name in added:
            print(f"   • {key}  ({class_name})")
    else:
        print("\n✅ No new strategies to add.")

    if skipped:
        print(f"\n⏭  Skipped {len(skipped)} existing block(s) (values preserved):")
        for key in skipped:
            print(f"   • {key}")

    active = config.get("active_strategy", "—")
    print(f"\n🎮 Active strategy: {active}")

    if dry_run:
        print("\n📋 Generated config (dry run — not saved):")
        print("-" * 55)
        print(json.dumps(config, indent=2))
    else:
        print(f"\n💾 Saved to: {CONFIG_PATH}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Generate config/config.json from discovered strategy folders."
    )
    parser.add_argument("--dry-run",   action="store_true",
                        help="Print the result without writing to disk.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Rebuild the strategies block from scratch.")
    args = parser.parse_args()

    existing = _load_existing()
    config, added, skipped = _build_config(existing, overwrite=args.overwrite)

    _print_summary(config, added, skipped, dry_run=args.dry_run)

    if not args.dry_run:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            f.write("\n")

        print("✅ Done. Edit config/config.json to customise bot names,")
        print("   then run the bot with: python app/main.py\n")


if __name__ == "__main__":
    main()
