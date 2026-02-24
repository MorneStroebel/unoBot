# UnoBot — Strategy Guide

Everything you need to know to create, test, and ship a new UnoBot strategy.

---

## How strategies work

The bot's sole decision point is a single method:

```python
choose_card(hand, top_card, current_color) -> (card_index, wild_color)
```

Every strategy is a class that inherits from `BaseStrategy` and implements
this method. The engine calls it on your turn and acts on what you return.

---

## Creating a new strategy — one file, zero config

### Step 1 — Create your file

Save a new `.py` file inside the `strategies/` folder:

```
UnoBot/
└── strategies/
    ├── base_strategy.py   ← do not edit
    ├── loader.py          ← do not edit
    └── my_strategy.py     ← your new file goes here ✅
```

Name the file anything you like (e.g. `aggressive.py`, `gemini_bot.py`, `my_strategy.py`).

### Step 2 — Write your class

Inside that file, write a class that inherits from `BaseStrategy` and implements `choose_card`:

```python
# strategies/my_strategy.py

from strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):

    def choose_card(self, hand, top_card, current_color):
        playable = self.get_playable_cards(hand, top_card, current_color)

        if not playable:
            return None, None          # No playable card → draw

        idx, card = playable[0]        # Pick the first legal card

        wild_color = None
        if card["type"].startswith("WILD"):
            wild_color = self.pick_wild_color(hand)

        return idx, wild_color
```

### Step 3 — Activate it

Open (or create) `config/config.json` and set `active_strategy` to your strategy's key.

The key is derived automatically from the class name — CamelCase → snake_case,
with a trailing `_strategy` suffix stripped:

| Class name              | Key in config.json  |
|-------------------------|---------------------|
| `MyStrategy`            | `my`                |
| `MyAwesomeStrategy`     | `my_awesome`        |
| `GeminiBot`             | `gemini_bot`        |
| `AggressiveBotStrategy` | `aggressive_bot`    |
| `BaseBotStrategy`      | `base_bot`         (built-in default)         |

```json
{
  "active_strategy": "my"
}
```

That's it. No imports to add, no registries to update. The loader auto-discovers
every `.py` file in `strategies/` on startup.

---

## Naming your bot per strategy

Each strategy can have its own bot name that is used when joining a room.
Add a `"strategies"` block to `config/config.json`:

```json
{
  "active_strategy": "my_awesome",
  "strategies": {
    "my_awesome": {
      "bot_first_name": "Blitz",
      "bot_last_name": "Alpha"
    },
    "gemini_bot": {
      "bot_first_name": "Gemini",
      "bot_last_name": "Pro"
    }
  }
}
```

If no override is set for a strategy, the global `bot_first_name` / `bot_last_name`
values are used as a fallback. The name is resolved at join time, so switching
strategies mid-session picks up the right name automatically.

---

## `choose_card` — input / output reference

### Arguments

#### `hand` — `List[Dict]`

List of card dicts currently in the bot's hand. Each card has:

| Key     | Type  | Values / notes                                                                    |
|---------|-------|-----------------------------------------------------------------------------------|
| `type`  | `str` | `"NUMBER"` · `"SKIP"` · `"REVERSE"` · `"DRAW_TWO"` · `"WILD"` · `"WILD_DRAW_FOUR"` |
| `color` | `str` | `"RED"` · `"BLUE"` · `"GREEN"` · `"YELLOW"` · `"BLACK"` (wilds only)            |
| `value` | `int` | Only present when `type == "NUMBER"` (0–9)                                       |

#### `top_card` — `Dict`

The card on top of the discard pile. Same structure as a hand card.

#### `current_color` — `str`

The active colour. Matches `top_card["color"]` except after a wild is played,
where it reflects the colour the wild player chose.

### Return value

Return a tuple `(card_index, wild_color)`:

| Value        | Meaning                                                          |
|--------------|------------------------------------------------------------------|
| `card_index` | `int` index into `hand` — the card to play                      |
| `card_index` | `None` — draw a card instead of playing                         |
| `wild_color` | `"RED"` / `"BLUE"` / `"GREEN"` / `"YELLOW"` when playing a wild |
| `wild_color` | `None` for all non-wild cards                                    |

---

## Helper methods (from `BaseStrategy`)

Available as `self.<method>` inside any strategy:

```python
# True if card is legal to play right now
self.is_playable(card, top_card, current_color) -> bool

# All playable cards as [(index, card), ...]
self.get_playable_cards(hand, top_card, current_color) -> List[Tuple[int, Dict]]

# Best wild colour based on what you hold the most of
self.pick_wild_color(hand) -> str   # "RED" | "BLUE" | "GREEN" | "YELLOW"

# All cards of a specific type as [(index, card), ...]
self.cards_by_type(hand, "SKIP") -> List[Tuple[int, Dict]]

# Count cards of a colour in hand
self.count_color(hand, "RED") -> int
```

---

## Optional lifecycle hooks

Override any of these in your strategy for extra control:

```python
def on_game_start(self):
    """Called once when a new game begins. Good for resetting per-game state."""
    pass

def on_game_end(self, won: bool, placement: int, points: int):
    """Called when the game ends. Useful for logging or adaptive learning."""
    pass

def on_turn_start(self, hand, top_card, current_color):
    """Called at the start of every turn, before choose_card."""
    pass
```

---

## Setting your strategy as active

**Option A — `config/config.json` (recommended):**
```json
{
  "active_strategy": "my_awesome"
}
```

**Option B — runtime menu:** after a game ends, choose option 2 "Change strategy"
from the in-game menu. The selection is saved to `config.json` automatically.

---

## Activating a Gemini / AI API strategy

If your strategy calls an external AI API, store your key as an environment variable:

```bash
export GEMINI_API_KEY="your-key-here"
```

Then read it inside your strategy:

```python
import os
api_key = os.environ.get("GEMINI_API_KEY")
```

---

## AI generation prompt

Copy the prompt below into any capable LLM (Claude, GPT-4, Gemini, etc.) to
generate a ready-to-use strategy file. Fill in the `[STRATEGY GOAL]` section
at the bottom — everything else is fixed context the model needs.

**Save the output as:** `strategies/<your_name>.py`  
**Then set in `config/config.json`:** `"active_strategy": "<your_key>"`

---

```
You are writing a Python strategy class for UnoBot, an AI Uno player.

== SAVE LOCATION ==
Save the output file to: strategies/<snake_case_name>.py
Example: strategies/aggressive_bot.py

== ACTIVATION ==
After saving, open config/config.json and set:
  "active_strategy": "<snake_case_class_name>"
The key is the class name converted to snake_case with "_strategy" suffix removed.
Example: AggressiveBotStrategy → "aggressive_bot"

== PROJECT CONTEXT ==
- File goes in: strategies/<snake_case_name>.py
- Must inherit from BaseStrategy: from strategies.base_strategy import BaseStrategy
- Must implement: choose_card(self, hand, top_card, current_color) -> (card_index, wild_color)
- Return (None, None) to draw instead of playing
- No print statements (the engine handles all logging)

== BOT NAMING (optional) ==
To give this strategy a custom bot name, add to config/config.json:
  "strategies": {
    "<strategy_key>": {
      "bot_first_name": "YourName",
      "bot_last_name": "YourLastName"
    }
  }

== BASE STRATEGY HELPERS (available via self.*) ==
  is_playable(card, top_card, current_color) -> bool
  get_playable_cards(hand, top_card, current_color) -> [(index, card), ...]
  pick_wild_color(hand) -> "RED"|"BLUE"|"GREEN"|"YELLOW"
  cards_by_type(hand, type_str) -> [(index, card), ...]
  count_color(hand, color_str) -> int

== CARD DICT STRUCTURE ==
  {
    "type":  "NUMBER"|"SKIP"|"REVERSE"|"DRAW_TWO"|"WILD"|"WILD_DRAW_FOUR",
    "color": "RED"|"BLUE"|"GREEN"|"YELLOW"|"BLACK",
    "value": int   # only present when type == "NUMBER"
  }

== OPTIONAL LIFECYCLE HOOKS (override if needed) ==
  on_game_start(self)
  on_game_end(self, won: bool, placement: int, points: int)
  on_turn_start(self, hand, top_card, current_color)

== OUTPUT REQUIREMENTS ==
- Single .py file, no external dependencies beyond the standard library
- CamelCase class name ending with Strategy or Bot
- Docstring explaining the overall approach
- Inline comments on non-obvious logic

== STRATEGY GOAL ==
[Describe the play style you want here. Examples:
  "Aggressive — prioritise SKIP, REVERSE, DRAW_TWO and wilds. Hold wilds
   until hand size ≤ 4. Always pick the colour held most."

  "Defensive — avoid drawing penalties. Prefer number cards. Only play
   action cards when hand size > 6."

  "Gemini AI — call the Gemini API with the hand and board state, parse
   the response to pick a card. Fall back to first playable card on error."
]
```

---

## Quick-start checklist

- [ ] Create `strategies/my_strategy.py`
- [ ] Class inherits `BaseStrategy` (imported from `strategies.base_strategy`)
- [ ] `choose_card` implemented and returns `(card_index, wild_color)`
- [ ] `config/config.json` updated: `"active_strategy": "my_strategy_key"`
- [ ] *(Optional)* Bot name set in `config/config.json` under `"strategies"`
- [ ] Run `python app/main.py` — your strategy appears in the menu automatically
