"""EvoPlay – lightweight game server for humans and AI agents."""

from __future__ import annotations

import logging
import json
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from games.game_2048 import Game2048
from games.game_mergefall import MergeFall

# ── Logging ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("evoplay")

# ── App setup ───────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

# Registry: add more games here.
GAMES: dict[str, type] = {
    "2048": Game2048,
    "mergefall": MergeFall,
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
        sessions[key] = GAMES[name]()
        log.info("Created new session for game '%s' with session_id '%s'", name, session_id)
    
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
    state["session_id"] = session_id  # Include session_id in response
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
    state["session_id"] = session_id  # Include session_id in response
    _log_action(f"{name}[{session_id[:8]}]", move, state)
    return jsonify(state)


@app.get("/api/game/<name>/reset")
def game_reset(name: str):
    """Reset the game and return the fresh state."""
    game, session_id = _get_game(name)
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    state = game.reset()
    state["session_id"] = session_id  # Include session_id in response
    _log_action(f"{name}[{session_id[:8]}]", "RESET", state)
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


# ── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
