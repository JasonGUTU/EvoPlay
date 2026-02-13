"""EvoPlay – lightweight game server for humans and AI agents."""

from __future__ import annotations

import logging
import json
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

# Active game sessions keyed by game name (single-player for now).
sessions: dict[str, object] = {}


def _get_game(name: str):
    """Return the active session for *name*, creating one if needed."""
    if name not in sessions:
        if name not in GAMES:
            return None
        sessions[name] = GAMES[name]()
        log.info("Created new session for game '%s'", name)
    return sessions[name]


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
    """Return current state without modifying it."""
    game = _get_game(name)
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    state = game.get_state()
    return jsonify(state)


@app.get("/api/game/<name>/action")
def game_action(name: str):
    """
    Apply an action via query parameter.

    Examples:
        GET /api/game/2048/action?move=up
        GET /api/game/2048/action?move=left
    """
    game = _get_game(name)
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404

    move = request.args.get("move")
    if not move:
        return jsonify({"error": "Missing 'move' query parameter."}), 400

    state = game.apply_action(move)
    _log_action(name, move, state)
    return jsonify(state)


@app.get("/api/game/<name>/reset")
def game_reset(name: str):
    """Reset the game and return the fresh state."""
    game = _get_game(name)
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    state = game.reset()
    _log_action(name, "RESET", state)
    return jsonify(state)


@app.get("/api/game/<name>/valid_actions")
def game_valid_actions(name: str):
    """Return currently valid actions."""
    game = _get_game(name)
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    return jsonify({"valid_actions": game.valid_actions()})


@app.get("/api/game/<name>/log")
def game_log(name: str):
    """Return the operation log for the current session."""
    game = _get_game(name)
    if game is None:
        return jsonify({"error": f"Unknown game: {name}"}), 404
    return jsonify(game.get_log_info())


# ── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
