"""
EvoPlay Backend API Test Script
Tests all API endpoints for 2048 and MergeFall games.
Captures game states, scores, logs, and timing metrics.
"""

import json
import time
import requests
import sys

BASE_URL = "http://localhost:5001"

# ── Timing & metrics ──────────────────────────────────────────────
metrics = {}


def timed_request(label, url, params=None):
    """Make a GET request and record timing."""
    start = time.time()
    resp = requests.get(url, params=params)
    elapsed = time.time() - start
    metrics.setdefault(label, []).append(elapsed)
    return resp


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_board_2048(board):
    """Pretty-print a 2048 board."""
    for row in board:
        print("  " + "  ".join(f"{v:>4}" for v in row))


def print_board_mergefall(board):
    """Pretty-print a MergeFall board."""
    for row in board:
        print("  " + "  ".join(f"{v:>3}" for v in row))


# ── Test 1: List Games ────────────────────────────────────────────
def test_list_games():
    print_section("Test 1: List Available Games")
    resp = timed_request("list_games", f"{BASE_URL}/api/games")
    data = resp.json()
    print(f"  Status: {resp.status_code}")
    print(f"  Games: {data['games']}")
    assert resp.status_code == 200
    assert "2048" in data["games"]
    assert "mergefall" in data["games"]
    print("  ✓ PASSED")
    return data


# ── Test 2: Game Rules ────────────────────────────────────────────
def test_game_rules():
    print_section("Test 2: Game Rules")
    for game_name in ["2048", "mergefall"]:
        resp = timed_request("rules", f"{BASE_URL}/api/game/{game_name}/rules")
        data = resp.json()
        print(f"\n  [{game_name}] Status: {resp.status_code}")
        print(f"  [{game_name}] Rules length: {len(data['rules'])} chars")
        print(f"  [{game_name}] First 100 chars: {data['rules'][:100]}...")
        assert resp.status_code == 200
        assert len(data["rules"]) > 50
    print("\n  ✓ PASSED")


# ── Test 3: Play 2048 ────────────────────────────────────────────
def test_play_2048():
    print_section("Test 3: Play 2048 (25 moves)")

    # Reset game to get a fresh session
    resp = timed_request("reset_2048", f"{BASE_URL}/api/game/2048/reset")
    data = resp.json()
    session_id = data["session_id"]
    print(f"  Session ID: {session_id}")
    print(f"  Initial score: {data['score']}")
    print(f"  Initial board:")
    print_board_2048(data["board"])

    # Verify state endpoint
    resp = timed_request("state_2048", f"{BASE_URL}/api/game/2048/state",
                         params={"session_id": session_id})
    state = resp.json()
    assert state["game"] == "2048"
    assert state["score"] == data["score"]
    print(f"\n  State endpoint verified ✓")

    # Verify valid_actions endpoint
    resp = timed_request("valid_actions_2048", f"{BASE_URL}/api/game/2048/valid_actions",
                         params={"session_id": session_id})
    va = resp.json()
    print(f"  Valid actions: {va['valid_actions']}")
    assert len(va["valid_actions"]) > 0

    # Play 25 moves with a simple strategy: cycle through directions
    directions = ["up", "right", "down", "left"]
    move_count = 0
    game_over = False
    scores = [data["score"]]
    actions_taken = []

    for i in range(25):
        if game_over:
            break

        # Pick the first valid action from our preferred order
        resp = timed_request("valid_actions_2048", f"{BASE_URL}/api/game/2048/valid_actions",
                             params={"session_id": session_id})
        valid = resp.json()["valid_actions"]
        if not valid:
            break

        # Use cycling strategy
        action = None
        for d in directions:
            if d in valid:
                action = d
                break
        if action is None:
            action = valid[0]

        # Rotate direction preference
        directions = directions[1:] + directions[:1]

        resp = timed_request("action_2048", f"{BASE_URL}/api/game/2048/action",
                             params={"move": action, "session_id": session_id})
        result = resp.json()
        move_count += 1
        scores.append(result["score"])
        actions_taken.append(action)
        game_over = result["game_over"]

        if i < 3 or i == 24 or game_over:
            print(f"\n  Move {move_count}: {action} → score={result['score']}, game_over={result['game_over']}")
            print_board_2048(result["board"])

    print(f"\n  Total moves: {move_count}")
    print(f"  Final score: {scores[-1]}")
    print(f"  Game over: {game_over}")
    print(f"  Actions: {actions_taken}")
    print(f"  Score progression: {scores[:5]}...{scores[-3:]}")

    # Check game log
    resp = timed_request("log_2048", f"{BASE_URL}/api/game/2048/log",
                         params={"session_id": session_id})
    log_data = resp.json()
    print(f"\n  Log steps: {log_data.get('steps', 'N/A')}")
    print(f"  Elapsed seconds: {log_data.get('elapsed_seconds', 'N/A')}")
    log_entries = log_data.get("log", [])
    print(f"  Log entries count: {len(log_entries)}")
    if log_entries:
        print(f"  First entry: {log_entries[0]}")
        print(f"  Last entry: {log_entries[-1]}")

    print("\n  ✓ PASSED")
    return {
        "session_id": session_id,
        "moves": move_count,
        "final_score": scores[-1],
        "game_over": game_over,
        "actions": actions_taken,
        "scores": scores,
    }


# ── Test 4: Play MergeFall ───────────────────────────────────────
def test_play_mergefall():
    print_section("Test 4: Play MergeFall (25 moves)")

    # Reset game
    resp = timed_request("reset_mergefall", f"{BASE_URL}/api/game/mergefall/reset")
    data = resp.json()
    session_id = data["session_id"]
    print(f"  Session ID: {session_id}")
    print(f"  Initial score: {data['score']}")
    print(f"  Next tile: {data['next_tile']}")
    print(f"  Board size: {data['width']}x{data['height']}")
    print(f"  Initial board:")
    print_board_mergefall(data["board"])

    # Verify state and valid_actions
    resp = timed_request("state_mergefall", f"{BASE_URL}/api/game/mergefall/state",
                         params={"session_id": session_id})
    state = resp.json()
    assert state["game"] == "mergefall"
    print(f"\n  State endpoint verified ✓")

    resp = timed_request("valid_actions_mergefall", f"{BASE_URL}/api/game/mergefall/valid_actions",
                         params={"session_id": session_id})
    va = resp.json()
    print(f"  Valid actions: {va['valid_actions']}")

    # Play 25 moves with a spread strategy: cycle columns
    columns = [2, 1, 3, 0, 4]  # center-out
    move_count = 0
    game_over = False
    scores = [data["score"]]
    actions_taken = []
    next_tiles = [data["next_tile"]]

    for i in range(25):
        if game_over:
            break

        action = f"drop {columns[i % len(columns)]}"
        resp = timed_request("action_mergefall", f"{BASE_URL}/api/game/mergefall/action",
                             params={"move": action, "session_id": session_id})
        result = resp.json()

        if "error" in result and result.get("game_over", False):
            game_over = True
            move_count += 1
            scores.append(result["score"])
            actions_taken.append(action)
            print(f"\n  Move {move_count}: {action} → GAME OVER (error: {result['error']})")
            break

        move_count += 1
        scores.append(result["score"])
        actions_taken.append(action)
        game_over = result.get("game_over", False)
        next_tiles.append(result.get("next_tile", 0))

        if i < 3 or i == 24 or game_over:
            print(f"\n  Move {move_count}: {action} → score={result['score']}, next={result.get('next_tile')}, game_over={game_over}")
            print_board_mergefall(result["board"])

    print(f"\n  Total moves: {move_count}")
    print(f"  Final score: {scores[-1]}")
    print(f"  Game over: {game_over}")
    print(f"  Actions: {actions_taken}")
    print(f"  Next tiles seen: {next_tiles[:10]}...")

    # Check game log
    resp = timed_request("log_mergefall", f"{BASE_URL}/api/game/mergefall/log",
                         params={"session_id": session_id})
    log_data = resp.json()
    print(f"\n  Log steps: {log_data.get('steps', 'N/A')}")
    print(f"  Elapsed seconds: {log_data.get('elapsed_seconds', 'N/A')}")
    log_entries = log_data.get("log", [])
    print(f"  Log entries count: {len(log_entries)}")
    if log_entries:
        print(f"  First entry: {log_entries[0]}")
        print(f"  Last entry: {log_entries[-1]}")

    print("\n  ✓ PASSED")
    return {
        "session_id": session_id,
        "moves": move_count,
        "final_score": scores[-1],
        "game_over": game_over,
        "actions": actions_taken,
        "scores": scores,
    }


# ── Test 5: Error Handling ────────────────────────────────────────
def test_error_handling():
    print_section("Test 5: Error Handling")

    # Unknown game (with session_id to bypass the session_id check)
    resp = requests.get(f"{BASE_URL}/api/game/unknown_game/state", params={"session_id": "test"})
    print(f"  Unknown game state → {resp.status_code}: {resp.json()}")
    assert resp.status_code in (400, 404)  # 400 if session check first, 404 if game check first

    # Unknown game rules (no session_id needed)
    resp = requests.get(f"{BASE_URL}/api/game/unknown_game/rules")
    print(f"  Unknown game rules → {resp.status_code}: {resp.json()}")
    assert resp.status_code == 404

    # Missing move param
    resp = requests.get(f"{BASE_URL}/api/game/2048/action", params={"session_id": "test"})
    print(f"  Missing move → {resp.status_code}: {resp.json()}")
    assert resp.status_code == 400

    # Missing session_id for state
    resp = requests.get(f"{BASE_URL}/api/game/2048/state")
    print(f"  Missing session_id → {resp.status_code}: {resp.json()}")
    assert resp.status_code == 400

    print("  ✓ PASSED")


# ── Metrics Summary ───────────────────────────────────────────────
def print_metrics():
    print_section("Timing Metrics Summary")
    total_time = 0
    for label, times in sorted(metrics.items()):
        avg = sum(times) / len(times)
        total = sum(times)
        total_time += total
        print(f"  {label:30s}  calls={len(times):3d}  avg={avg*1000:.1f}ms  total={total:.3f}s")
    print(f"\n  Total API call time: {total_time:.3f}s")
    print(f"  Note: This is a CPU-only backend (no GPU usage)")


# ── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("EvoPlay Backend API Test Suite")
    print(f"Backend URL: {BASE_URL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}
    try:
        test_list_games()
        test_game_rules()
        results["2048"] = test_play_2048()
        results["mergefall"] = test_play_mergefall()
        test_error_handling()
        print_metrics()

        print_section("FINAL SUMMARY")
        print(f"  All tests PASSED ✓")
        for game, r in results.items():
            print(f"  {game}: {r['moves']} moves, final score={r['final_score']}, game_over={r['game_over']}")

    except Exception as e:
        print(f"\n  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
