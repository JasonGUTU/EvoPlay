"""EvoPlay – lightweight game server for humans and AI agents."""

from __future__ import annotations

import logging
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

# ── Player registry ──────────────────────────────────────────────────

PLAYERS_FILE = Path(__file__).resolve().parent / "players.json"


def _load_players() -> dict:
    """Load registered players from disk."""
    if PLAYERS_FILE.exists():
        with open(PLAYERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_players(players: dict) -> None:
    """Persist players to disk."""
    with open(PLAYERS_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

from games.game_2048 import Game2048
from games.game_mergefall import MergeFall
from games.game_nuts_bolts import NutsBolts
from games.game_sokoban import Sokoban
from games.game_fourinarow import FourInARow
from games.game_othello6 import Othello6
from games.game_tictactoe import TicTacToe
from games.game_sliding_puzzle import SlidingPuzzle

# ── Logging ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("evoplay")

# ── App setup ───────────────────────────────────────────────────────

import os

# In production, serve the built frontend static files
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path="/")
else:
    app = Flask(__name__)
CORS(app)

# Registry: add more games here.
GAMES: dict[str, type] = {
    "2048": Game2048,
    "mergefall": MergeFall,
    "nuts_bolts": NutsBolts,
    "sokoban": Sokoban,
    "fourinarow": FourInARow,
    "othello6": Othello6,
    "tictactoe": TicTacToe,
    "sliding_puzzle": SlidingPuzzle,
}

# Active game sessions keyed by (game_name, session_id) tuple.
# Each frontend gets its own independent game instance.
sessions: dict[tuple[str, str], object] = {}


def _get_session_id(required: bool = False) -> str | None:
    """
    Extract session ID from request.
    If required=True and not provided, returns None.
    If required=False and not provided, generates a new one.
    """
    session_id = request.args.get("session_id")
    if not session_id:
        if required:
            return None
        # Generate a new session ID if not provided and not required
        session_id = str(uuid.uuid4())
    return session_id


def _get_game(name: str, session_id: str | None = None, require_session: bool = False):
    """
    Return the game instance for *name* and *session_id*.
    
    Args:
        name: Game name
        session_id: Optional session ID. If None, gets from request.
        require_session: If True, session_id must be provided or returns error.
    
    Returns:
        (game_instance, session_id) or (None, None) if error
    """
    if session_id is None:
        session_id = _get_session_id(required=require_session)
        if require_session and session_id is None:
            return None, None
    
    key = (name, session_id)
    
    if key not in sessions:
        if name not in GAMES:
            return None, None
        game_instance = GAMES[name]()
        # Set session_id for logging
        game_instance.set_session_id(session_id)
        sessions[key] = game_instance
        log.info("Created new session for game '%s' session='%s'", name, session_id)

    # Always update player_name if provided (covers both new and existing sessions)
    player_name = request.args.get("player_name")
    if player_name and hasattr(sessions[key], "set_player_name"):
        sessions[key].set_player_name(player_name)

    return sessions[key], session_id


def _log_action(game_name: str, action: str | None, state: dict) -> None:
    log.info(
        "game=%s | action=%s | score=%s | game_over=%s | board=%s",
        game_name,
        action,
        state.get("score"),
        state.get("game_over"),
        json.dumps(state.get("board")),
    )


# ── Routes ──────────────────────────────────────────────────────────


@app.get("/api/games")
def list_games():
    """Return the list of available game names."""
    return jsonify({"games": list(GAMES.keys())})


@app.get("/api/game/<name>/state")
def game_state(name: str):
    """Return current state without modifying it. Requires session_id parameter."""
    game, session_id = _get_game(name, require_session=True)
    if session_id is None:
        return jsonify({"error": "Missing required 'session_id' query parameter."}), 400
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    state = game.get_state()
    state["session_id"] = session_id
    if hasattr(game, "_agent_error") and game._agent_error:
        state["agent_error"] = game._agent_error
    return jsonify(state)


@app.get("/api/game/<name>/action")
def game_action(name: str):
    """
    Apply an action via query parameter.

    Examples:
        GET /api/game/2048/action?move=up&session_id=abc123
        GET /api/game/2048/action?move=left
        (If session_id is omitted, a new one will be generated)
    """
    game, session_id = _get_game(name)
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404

    move = request.args.get("move")
    if not move:
        return jsonify({"error": "Missing 'move' query parameter."}), 400

    state = game.apply_action(move)

    # For agent callers: auto-chain bot move when bot_pending is set
    # Frontend callers use ?auto_bot=false (default) and call /bot_move separately
    auto_bot = request.args.get("auto_bot", "false").lower() in ("true", "1", "yes")
    if auto_bot and state.get("bot_pending") and hasattr(game, "apply_bot_move"):
        state = game.apply_bot_move()

    state["session_id"] = session_id  # Include session_id in response
    _log_action(f"{name}[{session_id[:8]}]", move, state)
    return jsonify(state)


@app.get("/api/game/<name>/reset")
def game_reset(name: str):
    """Reset the game and return the fresh state."""
    game, session_id = _get_game(name)
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    difficulty = request.args.get("difficulty")
    if difficulty and hasattr(game, "set_difficulty"):
        game.set_difficulty(difficulty)
    state = game.reset()
    state["session_id"] = session_id  # Include session_id in response
    _log_action(f"{name}[{session_id[:8]}]", "RESET", state)
    return jsonify(state)


@app.get("/api/game/<name>/bot_move")
def game_bot_move(name: str):
    """Trigger the bot's move (used for two-phase turn rendering)."""
    game, session_id = _get_game(name, require_session=True)
    if session_id is None:
        return jsonify({"error": "Missing required 'session_id' query parameter."}), 400
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    if not hasattr(game, "apply_bot_move"):
        return jsonify({"error": f"Game '{name}' does not support separate bot moves."}), 400
    state = game.apply_bot_move()
    state["session_id"] = session_id
    _log_action(f"{name}[{session_id[:8]}]", "BOT_MOVE", state)
    return jsonify(state)


@app.get("/api/game/<name>/valid_actions")
def game_valid_actions(name: str):
    """Return currently valid actions. Requires session_id parameter."""
    game, session_id = _get_game(name, require_session=True)
    if session_id is None:
        return jsonify({"error": "Missing required 'session_id' query parameter."}), 400
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    return jsonify({"valid_actions": game.valid_actions(), "session_id": session_id})


@app.get("/api/game/<name>/log")
def game_log(name: str):
    """Return the operation log for the current session. Requires session_id parameter."""
    game, session_id = _get_game(name, require_session=True)
    if session_id is None:
        return jsonify({"error": "Missing required 'session_id' query parameter."}), 400
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    log_info = game.get_log_info()
    log_info["session_id"] = session_id
    return jsonify(log_info)


@app.post("/api/game/<name>/agent_error")
def game_agent_error(name: str):
    """Record an agent error for a session (shown to frontend watchers)."""
    game, session_id = _get_game(name, require_session=True)
    if session_id is None:
        return jsonify({"error": "Missing session_id"}), 400
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    data = request.get_json(silent=True) or {}
    error_msg = data.get("error", "Unknown agent error")
    game._agent_error = error_msg
    log.warning("Agent error for game=%s session=%s: %s", name, session_id, error_msg)
    return jsonify({"ok": True})


@app.get("/api/game/<name>/rules")
def game_rules(name: str):
    """Return the game rules description. Does not require session_id."""
    if name not in GAMES:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    
    # Create a temporary game instance to get rules (rules don't depend on session state)
    game_instance = GAMES[name]()
    rules = game_instance.get_rules()
    return jsonify({"game": name, "rules": rules})


# ── Player routes ──────────────────────────────────────────────────


@app.post("/api/player/register")
def player_register():
    """Register a new player name. Returns error if name already taken."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Name cannot be empty."}), 400
    if len(name) > 20:
        return jsonify({"ok": False, "error": "Name too long (max 20 chars)."}), 400

    players = _load_players()
    # Case-insensitive duplicate check
    if name.lower() in {k.lower() for k in players}:
        return jsonify({"ok": False, "error": f"Name '{name}' is already taken."}), 409

    players[name] = {
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_players(players)
    log.info("Registered new player: %s", name)
    return jsonify({"ok": True, "name": name})


@app.post("/api/player/login")
def player_login():
    """Check if a player name exists (login). Returns ok=true if found."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Name cannot be empty."}), 400

    players = _load_players()
    # Case-insensitive lookup, return the canonical name
    for registered_name in players:
        if registered_name.lower() == name.lower():
            return jsonify({"ok": True, "name": registered_name})

    return jsonify({"ok": False, "error": f"Player '{name}' not found. Please register first."}), 404


@app.get("/api/players")
def list_players():
    """List all registered player names."""
    players = _load_players()
    return jsonify({"players": list(players.keys())})



# ── Serve frontend SPA ─────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve Vue SPA. API routes are handled above, everything else goes to index.html."""
    if path and (FRONTEND_DIST / path).exists():
        return app.send_static_file(path)
    return app.send_static_file("index.html")


# ── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=5001, debug=debug)
