# 📜 Official Uno Game Rules

## 🎯 Objective

Be the first player to get rid of all your cards in each round. The first player to reach **1000 points** wins the game.

---

## 🃏 Deck Contents (108 cards)

### Numbered Cards (0-9)
- **76 cards total**
- 19 Blue cards (0 to 9)
- 19 Green cards (0 to 9)
- 19 Red cards (0 to 9)
- 19 Yellow cards (0 to 9)
- **Note:** There is one '0' and two of each number '1-9' per color.

### Action Cards (24 cards)
- **8 Draw Two cards** (2 of each color)
- **8 Reverse cards** (2 of each color)
- **8 Skip cards** (2 of each color)

### Wild Cards (8 cards)
- **4 Wild cards**
- **4 Wild Draw Four cards**

---

## 🎲 Setup

1. Each player draws a card; the highest point value deals.
2. Dealer shuffles and deals **7 cards** to each player.
3. Remaining cards form the **Draw Pile** (face down).
4. Top card of Draw Pile is flipped to start the **Discard Pile** (face up).
   - If the first card is a **Wild** or **Wild Draw Four**, return it to the deck and flip another.
   - If it's an Action card (Skip, Reverse, Draw Two), the effect applies to the first player (to the dealer's left).

---

## 🎮 Gameplay

### Turn Order
- Play proceeds **clockwise** (initially)
- Can be reversed by **Reverse** cards

### On Your Turn

You have two options:

**Option 1: Play a Card**
- Match the top card of the Discard Pile by:
  - **Color** (RED, BLUE, GREEN, YELLOW)
  - **Number** (0-9)
  - **Symbol** (SKIP, REVERSE, DRAW_TWO)
- OR play a **Wild** or **Wild Draw Four** card

**Option 2: Draw a Card**
- If you cannot play (or choose not to), draw one card from the Draw Pile
- If the drawn card is playable, you **may** play it immediately
- Otherwise, your turn ends

### Draw Pile Depletion
- If the Draw Pile is depleted, shuffle the Discard Pile (excluding the top card) to form a new Draw Pile.

---

## 🎴 Action Card Rules

### Draw Two (20 points)
- **Effect:** Next player draws 2 cards and **misses their turn**
- **Cannot be stacked** (next player must draw, no playing another Draw Two)

### Reverse (20 points)
- **Effect:** Reverses direction of play
- **Special:** In 2-player games, acts as a **Skip** card

### Skip (20 points)
- **Effect:** Next player misses their turn
- Play continues with the player after the skipped player

### Wild (50 points)
- **Effect:** Player declares the next color to be matched
- **Can be played at any time**, even if you have other playable cards

### Wild Draw Four (50 points)
- **Effect:** Player declares the next color; next player draws 4 cards and misses their turn
- **RESTRICTION:** Can only be played if you have **NO** card in your hand that matches the **COLOR** of the discard pile
  - Matching the number or action is okay
  - Only the color matters for this restriction
- **Can be challenged!** (See Wild Draw Four Challenge below)

---

## 🗣️ Calling "Uno"

### The Rule
- When playing your **second-to-last card**, you must yell **"Uno!"**
- This alerts other players that you're one card away from winning

### Penalty for Not Calling
- If caught not saying "Uno" before the next player begins their turn, you must draw **2 penalty cards**
- Any player can catch you out (see Catchout Challenges below)

### When to Call
- Call "Uno" **BEFORE** playing your second-to-last card
- The bot automatically calls UNO when it has 2 cards and is about to play one

---

## 🎯 Catchout Challenges

### What is a Catchout?
- Any player can challenge another player who has **1 card** but hasn't called "Uno"
- This is a way to catch opponents who forgot to call Uno

### Challenge Results

**Successful Challenge:**
- Target player **did not** call Uno (or has exactly 1 card without calling)
- Target player draws **2 penalty cards**

**Failed Challenge:**
- Target player **did** call Uno, or has more than 1 card
- The **challenger** must draw **2 penalty cards**

### Timing
- Challenge must happen after the player plays their second-to-last card
- Before the next player takes their turn

---

## 🃏 Wild Draw Four Challenge

### The Challenge
- When someone plays a Wild Draw Four, the next player can **challenge** the play
- The challenger suspects the player had a card matching the current color

### Challenge Resolution

**Player is Guilty (had a matching color card):**
- The player who played Wild Draw Four draws **4 cards** instead
- The challenger does not draw any cards
- Turn continues normally

**Player is Innocent (had no matching color cards):**
- The challenger draws **6 cards** (4 from the Wild Draw Four + 2 penalty)
- The challenger also **loses their turn**
- Turn passes to the next player

### Strategy
- Only challenge if you're confident they had a matching color
- Failed challenges are very costly (6 cards + lost turn)

---

## 🏆 Winning a Round & Scoring

### Round End
- Round ends when a player empties their hand
- Winner scores points for cards left in **all opponents' hands**

### Card Point Values
- **Number cards (0-9):** Face value (0-9 points)
- **Draw Two, Reverse, Skip:** 20 points each
- **Wild, Wild Draw Four:** 50 points each

### Special Rule
- If the last card played is a **Draw Two** or **Wild Draw Four**, the next player must still draw the cards
- These cards count toward the winner's score

### Strategic Insight
💡 Since points come from opponents' remaining cards, discard your high-value cards (Wilds and Actions) early if you think another player is close to winning!

---

## 🎖️ Winning the Game

The first player to reach **1000 points** over multiple rounds wins the game.

---

## ⚠️ Penalties & Enforcement

### Out of Turn Penalty
- **Violation:** Attempting to play or draw when it's NOT your turn
- **Penalty:** Draw **2 cards**
- **Action:** Rejected

### Illegal Action Penalty
- **Violation:** Playing a card that doesn't match (illegal play)
- **Examples:**
  - Playing a RED 5 when current color is BLUE and top card is not 5
  - Playing a card that doesn't match color, number, or type
- **Penalty:** Draw **2 cards**
- **Action:** Rejected

### UNO Bypass Penalty
- **Violation:** Playing second-to-last card without calling "Uno"
- **Penalty:** Draw **2 penalty cards**
- **Note:** The play remains valid, but you end up with more cards

### One Room Policy
- **Rule:** A player instance may only join one room at a time
- **Violation:** Attempting to join a second room
- **Action:** Rejected

### Leaving Rooms
- **Allowed:** Players may leave when game status is **WAITING** (not started) or **ENDED**
- **Forbidden:** Players cannot leave while game is **PLAYING**
- **Penalty:** Varies by implementation

---

## ⏱️ Turn Timeout

### Time Limit
- Players have **15 seconds** to take an action (Play or Draw) from the start of their turn
- Timer starts when it becomes your turn

### Timeout Consequences
- **If no action taken:**
  - Player automatically draws **1 card**
  - Turn immediately passes to the next player
- **No additional penalty** beyond the forced draw

### In Sandbox Mode
- Turn timer is **disabled**
- Players have **unlimited time** to take their turn
- Useful for testing and bot development

---

## 🏖️ Sandbox Mode

**Purpose:** Testing, bot development, and casual play

### Features
- **Disabled Timer:** No 15-second turn limit
- **Separate Leaderboard:** Results tracked separately from competitive play
- **Flexible Leaving:** Players can leave at any time without restriction
- **Bot Testing:** Perfect for testing strategies without pressure

### Enabling Sandbox
When joining via API, include `"isSandbox": true` in the request body:
```json
{
  "firstName": "TestBot",
  "lastName": "AI",
  "MAC": "00:11:22:33:44:55",
  "isSandbox": true
}
```

---

## 🚫 Rate Limiting

To ensure server stability and fair play:

### Limits (per IP/MAC address)
- **Global API:** 100 requests per 15 minutes
- **Room Creation:** 5 rooms per hour
- **Gameplay Actions:** 60 actions per minute (Play, Draw, Uno, etc.)

### Exceeding Limits
- Returns HTTP **429 "Too Many Requests"** error
- Bot should implement backoff and retry logic

---

## 💡 Strategic Tips

### Early Game
- Get rid of high-point cards (Wilds, Draw Twos)
- Save action cards for strategic moments
- Build color diversity in your hand

### Mid Game
- Use action cards to disrupt opponents
- Pay attention to opponents' card counts
- Consider which colors are being played most

### End Game
- Play high-point cards first (if you might lose)
- Save low-point cards for the final plays
- Remember to call UNO!

### Color Selection (Wild Cards)
- Choose the color you have most of
- Choose the color that was just played (continuity)
- Choose a color your opponent seems weak in

---

## 📊 Scoring Reference Table

| Card Type | Point Value |
|-----------|-------------|
| 0 | 0 points |
| 1-9 | Face value (1-9 points) |
| Draw Two | 20 points |
| Reverse | 20 points |
| Skip | 20 points |
| Wild | 50 points |
| Wild Draw Four | 50 points |

---

## 🎓 Example Scenarios

### Scenario 1: Legal Wild Draw Four
**Current Color:** RED  
**Your Hand:** [BLUE 5, GREEN Skip, YELLOW 2, Wild Draw Four]  
**Can you play Wild Draw Four?** ✅ **YES** - No RED cards in hand

### Scenario 2: Illegal Wild Draw Four
**Current Color:** RED  
**Your Hand:** [RED 5, BLUE 7, Wild Draw Four]  
**Can you play Wild Draw Four?** ❌ **NO** - You have RED 5

### Scenario 3: Calling UNO
**Your Hand:** [RED 5, BLUE 7]  
**Action:** Play RED 5  
**Required:** Call "UNO!" before or while playing RED 5

### Scenario 4: Catchout Success
**Opponent:** Plays second-to-last card, doesn't call UNO  
**You:** Call "Catchout!" immediately  
**Result:** Opponent draws 2 cards

---

**Good luck and have fun playing UNO! 🎉**
