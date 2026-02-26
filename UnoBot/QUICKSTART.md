# 🚀 Quick Start Guide

Get your UnoBot up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install requests python-socketio
```

## Step 2: Configure Your Bot

Edit `config/settings.py`:

```python
# Choose your strategy (this is the only line you need to change!)
ACTIVE_STRATEGY = "smart_bot"  # Options: base_bot, aggressive_bot, smart_bot

# Optional: Customize bot identity
BOT_FIRST_NAME = "YourBot"
BOT_LAST_NAME = "Name"
MAC_ADDRESS = "00:11:22:33:44:56"  # Change if running multiple bots
```

## Step 3: Run the Bot

```bash
python -m app.main
```

## What Happens Next?

1. ✅ Bot connects to Uno Game Engine
2. ✅ Joins an available room (or creates one)
3. ✅ Starts playing automatically
4. 🎮 Watch it play in real-time!

## Changing Strategies

Want to try a different AI? Just change one line:

```python
ACTIVE_STRATEGY = "aggressive_bot"
```

Then restart the bot. That's it!

## Troubleshooting

**"Module not found" error?**
```bash
pip install requests python-socketio --break-system-packages
```

**Bot not playing?**
- Check that you're connected to internet
- Verify the API is accessible
- Enable DEBUG_MODE in settings.py

**Getting penalties?**
- Enable DEBUG_MODE to see what's happening
- Check the bot is following game rules
- Review the GAME_RULES.md file

## Next Steps

- 📖 Read the full [README.md](README.md) for detailed documentation
- 📜 Review [GAME_RULES.md](GAME_RULES.md) to understand Uno rules
- 🧠 Create your own strategy (see Development section in README)
- 🏆 Enable competitive mode (set IS_SANDBOX_MODE = False)

**Happy playing! 🎉**
