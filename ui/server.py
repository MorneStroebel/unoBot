"""
ui/server.py — UnoBot Web UI Server
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from strategies.loader import list_strategies
from strategies.stats import StrategyStats

app = Flask(__name__, static_folder="static")

# ── Bot process state ─────────────────────────────────────────────────────────
_bot_process    = None
_bot_lock       = threading.Lock()
_bot_log        = []
_bot_start_time = None
_MAX_LOG        = 500

# ── Pause flag — written to disk so the bot process can read it ───────────────
_PAUSE_FILE = os.path.join(PROJECT_ROOT, ".bot_paused")


def _is_paused():
    return os.path.exists(_PAUSE_FILE)


def _set_paused(paused: bool):
    if paused:
        open(_PAUSE_FILE, "w").close()
    elif os.path.exists(_PAUSE_FILE):
        os.remove(_PAUSE_FILE)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _append_log(line):
    ts = datetime.now().strftime("%H:%M:%S")
    _bot_log.append(f"[{ts}] {line.rstrip()}")
    if len(_bot_log) > _MAX_LOG:
        del _bot_log[: len(_bot_log) - _MAX_LOG]


def _stream_output(proc):
    for line in proc.stdout:
        _append_log(line)
    proc.wait()


def _config_path():
    return os.path.join(PROJECT_ROOT, "config", "config.json")


def _load_config():
    path = _config_path()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_config(cfg):
    path = _config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)


def _bot_status():
    global _bot_process
    if _bot_process is None:
        return "stopped"
    if _bot_process.poll() is None:
        return "running"
    _bot_process = None
    return "stopped"


# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    status = _bot_status()
    uptime = None
    if status == "running" and _bot_start_time:
        uptime = int(time.time() - _bot_start_time)
    cfg = _load_config()
    return jsonify({
        "status":          status,
        "paused":          _is_paused(),
        "uptime_seconds":  uptime,
        "active_strategy": cfg.get("active_strategy", "—"),
        "pid":             _bot_process.pid if _bot_process else None,
    })


# ── Bot control ───────────────────────────────────────────────────────────────

@app.route("/api/bot/start", methods=["POST"])
def api_bot_start():
    global _bot_process, _bot_start_time
    with _bot_lock:
        if _bot_status() == "running":
            return jsonify({"ok": False, "error": "Bot is already running"}), 400

        data     = request.get_json(silent=True) or {}
        mode     = data.get("mode", "auto")
        strategy = data.get("strategy")

        if strategy:
            cfg = _load_config()
            cfg["active_strategy"] = strategy
            _save_config(cfg)

        # Write launch hint for bot.py to read
        hint = {"mode": mode, "strategy": strategy or "", "auto_rejoin": True}
        hint_path = os.path.join(PROJECT_ROOT, ".ui_launch_hint.json")
        with open(hint_path, "w") as f:
            json.dump(hint, f)

        # Clear pause on start
        _set_paused(False)

        env = os.environ.copy()
        env["UNO_UI_MODE"]    = "1"
        env["UNO_LAUNCH_MODE"] = mode

        _bot_process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        _bot_start_time = time.time()
        _append_log(f"▶ Bot started — PID {_bot_process.pid}  mode={mode}  strategy={strategy or 'from config'}")
        threading.Thread(target=_stream_output, args=(_bot_process,), daemon=True).start()

    return jsonify({"ok": True, "pid": _bot_process.pid})


@app.route("/api/bot/stop", methods=["POST"])
def api_bot_stop():
    global _bot_process
    with _bot_lock:
        if _bot_status() != "running":
            return jsonify({"ok": False, "error": "Bot is not running"}), 400
        _bot_process.terminate()
        try:
            _bot_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _bot_process.kill()
        _set_paused(False)
        _append_log("⏹ Bot stopped by UI")
        _bot_process = None
    return jsonify({"ok": True})


@app.route("/api/bot/pause", methods=["POST"])
def api_bot_pause():
    """Pause between games — bot finishes current game but won't start another."""
    if _bot_status() != "running":
        return jsonify({"ok": False, "error": "Bot is not running"}), 400
    _set_paused(True)
    _append_log("⏸ Bot paused — will stop after current game")
    return jsonify({"ok": True, "paused": True})


@app.route("/api/bot/resume", methods=["POST"])
def api_bot_resume():
    """Resume after pause."""
    _set_paused(False)
    _append_log("▶ Bot resumed")
    return jsonify({"ok": True, "paused": False})


@app.route("/api/bot/log")
def api_bot_log():
    since = int(request.args.get("since", 0))
    return jsonify({"lines": _bot_log[since:], "total": len(_bot_log)})


# ── Strategies ────────────────────────────────────────────────────────────────

@app.route("/api/strategies")
def api_strategies():
    discovered = list_strategies()
    cfg        = _load_config()
    active     = cfg.get("active_strategy", "")
    strat_cfgs = cfg.get("strategies", {})
    result = []
    for folder, class_name in sorted(discovered.items()):
        s      = StrategyStats(folder)
        s_cfg  = strat_cfgs.get(folder, {})
        result.append({
            "id":             folder,
            "name":           class_name,
            "active":         folder == active,
            "config":         s_cfg,
            "stats":          s.as_dict(),
        })
    return jsonify(result)


@app.route("/api/strategies/<n>/activate", methods=["POST"])
def api_activate_strategy(n):
    if n not in list_strategies():
        return jsonify({"ok": False, "error": f"Unknown strategy '{n}'"}), 404
    cfg = _load_config()
    cfg["active_strategy"] = n
    _save_config(cfg)
    _append_log(f"🔀 Strategy switched to: {n}")
    return jsonify({"ok": True, "active_strategy": n})


@app.route("/api/strategies/<n>/config", methods=["GET"])
def api_strategy_config_get(n):
    cfg       = _load_config()
    s_cfg     = cfg.get("strategies", {}).get(n, {})
    return jsonify(s_cfg)


@app.route("/api/strategies/<n>/config", methods=["PATCH"])
def api_strategy_config_patch(n):
    data = request.get_json(silent=True) or {}
    cfg  = _load_config()
    cfg.setdefault("strategies", {}).setdefault(n, {})
    ALLOWED = {"bot_first_name", "bot_last_name", "player_name", "mac_address"}
    for k, v in data.items():
        if k in ALLOWED:
            cfg["strategies"][n][k] = v
    _save_config(cfg)
    _append_log(f"💾 Config updated for strategy: {n}")
    return jsonify({"ok": True, "config": cfg["strategies"][n]})


@app.route("/api/strategies/<n>/stats")
def api_strategy_stats(n):
    return jsonify(StrategyStats(n).as_dict())


@app.route("/api/strategies/<n>/stats/reset", methods=["POST"])
def api_strategy_stats_reset(n):
    StrategyStats(n).reset()
    _append_log(f"🗑 Stats reset for: {n}")
    return jsonify({"ok": True})


# ── Global config ─────────────────────────────────────────────────────────────

@app.route("/api/config")
def api_config():
    return jsonify(_load_config())


@app.route("/api/config", methods=["PATCH"])
def api_config_patch():
    data = request.get_json(silent=True) or {}
    cfg  = _load_config()
    ALLOWED = {
        "active_strategy", "bot_first_name", "bot_last_name",
        "player_name", "mac_address", "is_sandbox_mode", "debug_mode",
        "auto_rejoin", "rejoin_delay", "auto_join_open_room",
        "room_check_interval", "max_wait_time", "only_players_mode",
    }
    for k, v in data.items():
        if k in ALLOWED:
            cfg[k] = v
    _save_config(cfg)
    return jsonify({"ok": True, "config": cfg})


# ── Static UI ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(os.path.join(os.path.dirname(__file__), "static"), "index.html")


@app.route("/<path:p>")
def static_files(p):
    return send_from_directory(os.path.join(os.path.dirname(__file__), "static"), p)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UnoBot Web UI")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    print(f"\n🎮 UnoBot Web UI")
    print(f"   Open http://localhost:{args.port} in your browser\n")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
