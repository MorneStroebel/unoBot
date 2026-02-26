"""
ui/server.py — UnoBot Web UI Server
Run:  python3 ui/server.py [--port 8080]
"""

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory

PROJECT_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRATEGIES_DIR  = os.path.join(PROJECT_ROOT, "strategies")
sys.path.insert(0, PROJECT_ROOT)

from strategies.loader import list_strategies
from strategies.stats  import StrategyStats

app = Flask(__name__, static_folder="static")

# ── Bot process ───────────────────────────────────────────────────────────────
_bot_process    = None
_bot_lock       = threading.Lock()
_bot_log        = []
_bot_start_time = None
_MAX_LOG        = 800

_PAUSE_FILE = os.path.join(PROJECT_ROOT, ".bot_paused")
_HINT_FILE  = os.path.join(PROJECT_ROOT, ".ui_launch_hint.json")


def _is_paused():
    return os.path.exists(_PAUSE_FILE)

def _set_paused(state):
    if state:
        open(_PAUSE_FILE, "w").close()
    elif os.path.exists(_PAUSE_FILE):
        os.remove(_PAUSE_FILE)

def _append_log(line):
    ts = datetime.now().strftime("%H:%M:%S")
    _bot_log.append(f"[{ts}] {line.rstrip()}")
    if len(_bot_log) > _MAX_LOG:
        del _bot_log[: len(_bot_log) - _MAX_LOG]

def _stream_proc(proc):
    try:
        for line in iter(proc.stdout.readline, ""):
            if line:
                _append_log(line)
    except Exception:
        pass
    finally:
        proc.wait()

# ── Config ────────────────────────────────────────────────────────────────────

def _cfg_path():
    return os.path.join(PROJECT_ROOT, "config", "config.json")

def _load_cfg():
    p = _cfg_path()
    return json.load(open(p)) if os.path.exists(p) else {}

def _save_cfg(cfg):
    p = _cfg_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(cfg, f, indent=2)

def _bot_status():
    global _bot_process
    if _bot_process is None:
        return "stopped"
    if _bot_process.poll() is None:
        return "running"
    _bot_process = None
    return "stopped"

# ── Room state (shared between bot process and UI via state.json) ─────────────

def _room_state():
    """Read the current room/player from state.json (written by core/state.py).
    state.py stores keys as 'roomId' and 'playerId'."""
    p = os.path.join(PROJECT_ROOT, "state.json")
    if os.path.exists(p):
        try:
            with open(p) as f:
                data = json.load(f)
            # Normalise to snake_case for internal use
            return {
                "room_id":   data.get("roomId")   or data.get("room_id"),
                "player_id": data.get("playerId") or data.get("player_id"),
            }
        except Exception:
            pass
    return {}

def _clear_room_state():
    p = os.path.join(PROJECT_ROOT, "state.json")
    if os.path.exists(p):
        with open(p, "w") as f:
            json.dump({}, f)

# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    st   = _bot_status()
    cfg  = _load_cfg()
    room = _room_state()
    uptime = int(time.time() - _bot_start_time) if st == "running" and _bot_start_time else None
    return jsonify({
        "status":          st,
        "paused":          _is_paused(),
        "uptime_seconds":  uptime,
        "active_strategy": cfg.get("active_strategy", "—"),
        "is_sandbox_mode": cfg.get("is_sandbox_mode", True),
        "pid":             _bot_process.pid if _bot_process else None,
        "room_id":         room.get("room_id"),
        "player_id":       room.get("player_id"),
    })

# ── Bot control ───────────────────────────────────────────────────────────────

@app.route("/api/bot/start", methods=["POST"])
def api_bot_start():
    global _bot_process, _bot_start_time, _bot_log
    with _bot_lock:
        if _bot_status() == "running":
            return jsonify({"ok": False, "error": "Bot is already running"}), 400

        data           = request.get_json(silent=True) or {}
        mode           = data.get("mode", "auto")
        strategy       = data.get("strategy") or None
        target_players = data.get("target_players") or []

        if strategy:
            cfg = _load_cfg()
            cfg["active_strategy"] = strategy
            _save_cfg(cfg)

        hint = {"mode": mode, "strategy": strategy or "",
                "target_players": target_players, "auto_rejoin": True}
        with open(_HINT_FILE, "w") as f:
            json.dump(hint, f)

        _set_paused(False)
        _bot_log.clear()

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["UNO_UI_MODE"]      = "1"
        env["UNO_LAUNCH_MODE"]  = mode

        _bot_process = subprocess.Popen(
            [sys.executable, "-u", "-m", "app.main"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, bufsize=1, env=env,
        )
        _bot_start_time = time.time()
        _append_log(f"▶ Bot started — PID {_bot_process.pid}  mode={mode}  strategy={strategy or 'from config'}")
        if target_players:
            _append_log(f"🎯 Targeting players: {', '.join(target_players)}")
        threading.Thread(target=_stream_proc, args=(_bot_process,), daemon=True).start()

    return jsonify({"ok": True, "pid": _bot_process.pid})


@app.route("/api/bot/stop", methods=["POST"])
def api_bot_stop():
    """Stop the bot. Bot's atexit handler calls leave_room before dying."""
    global _bot_process
    with _bot_lock:
        if _bot_status() != "running":
            return jsonify({"ok": False, "error": "Bot is not running"}), 400
        _bot_process.terminate()
        try:
            _bot_process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            _bot_process.kill()
        _set_paused(False)
        _append_log("⏹ Bot stopped — room will be left automatically")
        _bot_process = None
    return jsonify({"ok": True})


@app.route("/api/bot/pause", methods=["POST"])
def api_bot_pause():
    if _bot_status() != "running":
        return jsonify({"ok": False, "error": "Bot is not running"}), 400
    _set_paused(True)
    _append_log("⏸ Bot paused — will finish current game then wait")
    return jsonify({"ok": True, "paused": True})


@app.route("/api/bot/resume", methods=["POST"])
def api_bot_resume():
    _set_paused(False)
    _append_log("▶ Bot resumed")
    return jsonify({"ok": True, "paused": False})


@app.route("/api/bot/log")
def api_bot_log():
    since = int(request.args.get("since", 0))
    return jsonify({"lines": _bot_log[since:], "total": len(_bot_log)})


# ── Room control (direct API calls, bot not required) ─────────────────────────

@app.route("/api/room/leave", methods=["POST"])
def api_room_leave():
    """Leave the current room directly (without stopping the bot)."""
    room = _room_state()
    room_id   = room.get("room_id")
    player_id = room.get("player_id")
    if not room_id or not player_id:
        return jsonify({"ok": False, "error": "No active room"}), 400
    try:
        from api.actions import leave_room
        result = leave_room(room_id, player_id)
        _clear_room_state()
        _append_log(f"🚪 Left room {room_id}")
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/room/join", methods=["POST"])
def api_room_join():
    """Join a room (auto, wait, or by player name) outside of a full bot session."""
    data           = request.get_json(silent=True) or {}
    mode           = data.get("mode", "auto")   # auto | target
    target_players = data.get("target_players") or []
    try:
        from core.room_manager import RoomManager
        rm = RoomManager()
        if mode == "target" and target_players:
            room_id, player_id = rm.find_room_with_players(target_players)
        else:
            room_id, player_id = rm.join_or_create_room()
        if room_id and player_id:
            _append_log(f"🚪 Joined room {room_id}")
            return jsonify({"ok": True, "room_id": room_id, "player_id": player_id})
        return jsonify({"ok": False, "error": "Could not join a room"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Strategies ────────────────────────────────────────────────────────────────

@app.route("/api/room/create", methods=["POST"])
def api_room_create():
    """Create a new PvP room and join it as the host."""
    try:
        from api.client import post as api_post
        from api.actions import join_room
        from config.settings import IS_SANDBOX_MODE
        resp = api_post("/rooms", {"isSandbox": IS_SANDBOX_MODE})
        room_id = resp.json().get("roomId")
        if not room_id:
            return jsonify({"ok": False, "error": "Server did not return a room ID"}), 500
        player_id = join_room(room_id, only_players=True)
        if not player_id:
            return jsonify({"ok": False, "error": "Could not join the created room"}), 500
        _append_log(f"🏠 Created PvP room {room_id}")
        return jsonify({"ok": True, "room_id": room_id, "player_id": player_id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500



@app.route("/api/strategies")
def api_strategies():
    discovered = list_strategies()
    cfg        = _load_cfg()
    active     = cfg.get("active_strategy", "")
    strat_cfgs = cfg.get("strategies", {})
    result = []
    for folder, class_name in sorted(discovered.items()):
        s     = StrategyStats(folder)
        s_cfg = strat_cfgs.get(folder, {})
        result.append({"id": folder, "name": class_name,
                        "active": folder == active,
                        "config": s_cfg, "stats": s.as_dict()})
    return jsonify(result)


@app.route("/api/strategies/<n>/activate", methods=["POST"])
def api_activate_strategy(n):
    if n not in list_strategies():
        return jsonify({"ok": False, "error": f"Unknown strategy '{n}'"}), 404
    cfg = _load_cfg()
    cfg["active_strategy"] = n
    _save_cfg(cfg)
    _append_log(f"🔀 Active strategy → {n}")
    return jsonify({"ok": True, "active_strategy": n})


@app.route("/api/strategies/<n>/config", methods=["GET"])
def api_strategy_config_get(n):
    return jsonify(_load_cfg().get("strategies", {}).get(n, {}))


@app.route("/api/strategies/<n>/config", methods=["PATCH"])
def api_strategy_config_patch(n):
    data = request.get_json(silent=True) or {}
    cfg  = _load_cfg()
    cfg.setdefault("strategies", {}).setdefault(n, {})
    # Allow identity overrides + behavioural overrides
    ALLOWED = {
        "bot_first_name", "bot_last_name", "player_name", "mac_address",
        "only_players_mode", "auto_rejoin", "rejoin_delay",
        "require_target_players", "is_sandbox_mode", "debug_mode",
    }
    for k, v in data.items():
        if k in ALLOWED:
            # Empty strings → delete key (falls back to global)
            if v == "" or v is None:
                cfg["strategies"][n].pop(k, None)
            else:
                cfg["strategies"][n][k] = v
    if not cfg["strategies"].get(n):
        cfg["strategies"].pop(n, None)
    _save_cfg(cfg)
    _append_log(f"💾 Override config saved: {n}")
    return jsonify({"ok": True, "config": cfg.get("strategies", {}).get(n, {})})


@app.route("/api/strategies/<n>/stats")
def api_strategy_stats(n):
    return jsonify(StrategyStats(n).as_dict())


@app.route("/api/strategies/<n>/stats/reset", methods=["POST"])
def api_strategy_stats_reset(n):
    StrategyStats(n).reset()
    _append_log(f"🗑 Stats reset: {n}")
    return jsonify({"ok": True})


@app.route("/api/strategies/<n>/live")
def api_strategy_live(n):
    """Return live snapshot — persisted totals merged with current in-game accumulator.
    Safe to poll every second; no disk I/O on read."""
    return jsonify(StrategyStats(n).live_snapshot())


@app.route("/api/live")
def api_live_any():
    """Return live snapshot for the currently active strategy (from config)."""
    cfg = _load_cfg()
    active = cfg.get("active_strategy")
    if not active:
        return jsonify({"error": "No active strategy"}), 404
    snap = StrategyStats(active).live_snapshot()
    snap["strategy_id"] = active
    return jsonify(snap)


@app.route("/api/strategies/upload", methods=["POST"])
def api_strategy_upload():
    """
    Accept a .zip containing a strategy folder and install it into strategies/.
    The zip must contain a top-level folder with __init__.py inside.
    """
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400

    f = request.files["file"]
    if not f.filename.endswith(".zip"):
        return jsonify({"ok": False, "error": "Only .zip files accepted"}), 400

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "upload.zip")
        f.save(zip_path)

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()

        # Identify the top-level strategy folder name
        top_dirs = {n.split("/")[0] for n in names if "/" in n}
        if not top_dirs:
            return jsonify({"ok": False, "error": "Zip must contain a folder"}), 400

        strategy_name = sorted(top_dirs)[0]
        dest = os.path.join(STRATEGIES_DIR, strategy_name)

        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)

        src = os.path.join(tmp, strategy_name)
        if not os.path.exists(os.path.join(src, "__init__.py")):
            return jsonify({"ok": False, "error": "Folder must contain __init__.py"}), 400

        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(src, dest)

        # Re-discover to validate it loads
        try:
            discovered = list_strategies()
            if strategy_name not in discovered:
                shutil.rmtree(dest)
                return jsonify({"ok": False, "error": "Strategy loaded but no BaseStrategy subclass found"}), 400
        except Exception as e:
            shutil.rmtree(dest, ignore_errors=True)
            return jsonify({"ok": False, "error": f"Strategy failed to import: {e}"}), 400

        _append_log(f"📦 Strategy uploaded: {strategy_name}")
        return jsonify({"ok": True, "strategy": strategy_name, "class": discovered[strategy_name]})


# ── Global config ─────────────────────────────────────────────────────────────

@app.route("/api/config")
def api_config():
    return jsonify(_load_cfg())


@app.route("/api/config", methods=["PATCH"])
def api_config_patch():
    data = request.get_json(silent=True) or {}
    cfg  = _load_cfg()
    ALLOWED = {
        "active_strategy", "bot_first_name", "bot_last_name",
        "player_name", "mac_address", "is_sandbox_mode", "debug_mode",
        "auto_rejoin", "rejoin_delay", "auto_join_open_room",
        "room_check_interval", "max_wait_time", "only_players_mode",
    }
    for k, v in data.items():
        if k in ALLOWED:
            cfg[k] = v
    _save_cfg(cfg)
    return jsonify({"ok": True, "config": cfg})


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(os.path.join(os.path.dirname(__file__), "static"), "index.html")

@app.route("/<path:p>")
def static_files(p):
    return send_from_directory(os.path.join(os.path.dirname(__file__), "static"), p)

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    print(f"\n🎮 UnoBot Web UI  →  http://localhost:{args.port}\n")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
