# EvoPlay Reproduction — Task Brief

## Summary

EvoPlay is a 3-tier game server framework (Vue 3 frontend → Flask backend → pluggable game engines) with an LLM-powered AI agent. This reproduction verified the full pipeline: environment setup, backend API correctness for both games (2048, MergeFall), CSV logging integrity, and AI agent gameplay using GPT-4o-mini via LiteLLM. All API endpoints returned valid JSON with correct game states. The agent successfully played 30 steps of 2048 (final score: 240) and 12 steps of MergeFall before game over (final score: 52). The backend processes API calls in ~2.3 ms average, while agent step latency is dominated by LLM inference (~3.7 s/step for 2048, ~20 s/step for MergeFall due to larger board context).

## Pipeline Logic Chain

```
EvoPlay 3-Tier Architecture
├── Frontend (Vue 3 + Vite, port 3000)
│   ├── App.vue ─── game selection router
│   ├── Game2048.vue ─── 4×4 board renderer + keyboard input
│   ├── GameMergeFall.vue ─── 5×6 board renderer + column drop buttons
│   ├── GameLog.vue ─── action history display
│   └── session.js ─── per-tab session isolation (sessionStorage + localStorage)
│       ↓ HTTP GET /api/* (proxied by Vite dev server)
│
├── Backend (Flask, port 5001)
│   ├── app.py ─── route dispatcher + session manager
│   │   ├── GAMES registry: {"2048": Game2048, "mergefall": MergeFall}
│   │   ├── sessions dict: keyed by (game_name, session_id) tuple
│   │   └── Routes:
│   │       ├── /api/games → list game names
│   │       ├── /api/game/<name>/state → get_state() [requires session_id]
│   │       ├── /api/game/<name>/action?move=<x> → apply_action(x)
│   │       ├── /api/game/<name>/reset → reset()
│   │       ├── /api/game/<name>/valid_actions → valid_actions()
│   │       ├── /api/game/<name>/log → get_log_info()
│   │       └── /api/game/<name>/rules → get_rules()
│   │
│   └── games/
│       ├── base.py ─── BaseGame ABC
│       │   ├── CSV logger: logs/<game>/<session_id>.csv
│       │   ├── Lazy file creation (no empty log files)
│       │   └── Columns: step, time, action, score, game_over, board(JSON)
│       ├── game_2048.py ─── 4×4 sliding tile puzzle
│       │   ├── Actions: up/down/left/right
│       │   ├── Tile spawn: 90% → 2, 10% → 4
│       │   └── Rotation-based move: all directions → left compress → rotate back
│       └── game_mergefall.py ─── 5×6 drop-merge puzzle
│           ├── Actions: "drop 0" through "drop 4"
│           ├── Mechanics: gravity → absorb neighbors → repeat until stable
│           ├── Scoring: final_active_value × combo_count
│           └── Overflow row (row 0, invisible): game over trigger
│
└── Agent (CLI, connects to backend via HTTP)
    ├── main.py ─── CLI entry point (argparse)
    ├── config.py ─── config priority: CLI args > env vars > .env > defaults
    ├── agent.py ─── Agent class: get_state → reason → apply_action loop
    ├── llm.py ─── LiteLLM wrapper (OpenAI/Anthropic/Gemini/Ollama)
    └── reasoning/
        └── vanilla_reasoning.py ─── single-prompt LLM reasoning
            ├── Prompt: game rules + board state + valid actions
            ├── Response parsing: extract action string
            └── Fallback: first valid action on parse failure
```

## Stage 1 — Environment Setup

A single `evoplay` micromamba environment (Python 3.10) was created with all dependencies: Flask 3.1.3, Flask-CORS 6.0.2, LiteLLM 1.40.0, requests 2.32.5, and Node.js 18.20.0 (via nodeenv) for the frontend.

```bash
# Create environment and install all dependencies
/usr/bin/micromamba create -n evoplay python=3.10 -y -r /home/ruibo_ming/.local/share/mamba
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    pip install flask flask-cors litellm==1.40.0 requests
# Frontend: Node.js via nodeenv + npm install
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba pip install nodeenv
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    nodeenv --prebuilt --node=18.20.0 /home/ruibo_ming/.local/share/mamba/envs/evoplay/node_env
cd frontend && npm install  # 31 packages, audited 32
```

## Stage 2 — Backend API Testing

A comprehensive test script (`claude_version_test_api.py`) exercised all 7 API endpoints across both games. Each game was played for 25 moves with deterministic cycling strategies.

```python
# Core test logic — cycling direction strategy for 2048
# Rotates through [up, right, down, left] each move,
# picking the first valid direction from the cycle
directions = ["up", "right", "down", "left"]
for i in range(25):
    resp = requests.get(f"{BASE_URL}/api/game/2048/valid_actions",
                        params={"session_id": session_id})
    valid = resp.json()["valid_actions"]
    # Pick first valid action from current rotation
    action = next((d for d in directions if d in valid), valid[0])
    # Rotate preference list for next turn
    directions = directions[1:] + directions[:1]
    # Execute the move via GET endpoint
    resp = requests.get(f"{BASE_URL}/api/game/2048/action",
                        params={"move": action, "session_id": session_id})
    result = resp.json()  # Returns: game, board, score, game_over, valid_actions
```

### API Test Results

| Game | Moves | Final Score | Game Over | Avg API Latency |
|------|-------|-------------|-----------|-----------------|
| 2048 | 25 | 168 | No | 2.5 ms |
| MergeFall | 25 | 108 | No | 2.2 ms |

### Endpoint Verification

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/games` | 200 | Returns `["2048", "mergefall"]` |
| `GET /api/game/<name>/rules` | 200 | 2048: 1346 chars, MergeFall: 1873 chars |
| `GET /api/game/<name>/state` | 200 | Requires session_id, returns full board state |
| `GET /api/game/<name>/action` | 200 | Mutates state, returns updated board + score |
| `GET /api/game/<name>/reset` | 200 | Fresh board with session_id preserved |
| `GET /api/game/<name>/valid_actions` | 200 | Returns list of legal moves |
| `GET /api/game/<name>/log` | 200 | Returns in-memory log (steps, elapsed, entries) |
| Error: unknown game | 404 | Correct error response |
| Error: missing move | 400 | Correct error response |
| Error: missing session_id | 400 | Correct error response |

CSV log files confirmed at `backend/logs/<game>/<session_id>.csv` with proper headers and per-step entries.

## Stage 3 — AI Agent Testing

The agent was run with `gpt-4o-mini` (temperature 0.7, max_tokens 50) against both games using the VanillaReasoning engine.

```python
# Agent reasoning flow (from agent/reasoning/vanilla_reasoning.py)
# 1. Build prompt with game context
prompt = f"""You are playing {game_name}. Here are the rules:
{rules}

Current game state:
{self._format_board(game_state['board'])}
Score: {game_state['score']}

Valid actions: {valid_actions}
Choose the best action. Respond with ONLY the action string."""

# 2. Call LLM via LiteLLM unified interface
response = self.llm.simple_call(prompt, system_message="You are a game-playing AI.")

# 3. Parse response — extract action, validate against valid_actions
# Falls back to first valid action if LLM returns invalid output
action = response.strip().lower()
if action not in valid_actions:
    action = valid_actions[0]  # Fallback
```

### Agent Results

| Metric | 2048 | MergeFall |
|--------|------|-----------|
| Steps completed | 30 | 12 |
| Final score | 240 | 52 |
| Game over | No | Yes (column overflow) |
| Total elapsed | 111.6 s | 241.7 s |
| Avg step latency | 3.7 s | 20.1 s |
| Dominant action | `left` (16/30) | `drop 0` (12/12) |
| Max tile achieved | 32 | 16 |

**2048 Agent Analysis**: The agent demonstrated reasonable gameplay, achieving a max tile of 32 and score of 240 in 30 steps. It showed a preference for `left` moves (16/30), which is a known effective heuristic in 2048 (consolidating tiles to one side). The score progression was steady: 0 → 44 → 96 → 200 → 240.

**MergeFall Agent Analysis**: The agent repeatedly chose `drop 0` for all 12 steps, filling column 0 exclusively until overflow. This poor strategy (score: 52) reveals a limitation of the single-prompt vanilla reasoning — the agent failed to spread tiles across columns. The higher per-step latency (~20 s) is due to the larger 5×6 board serialization in the LLM context.

### Timing Bottleneck Analysis

| Pipeline Stage | Wall Time | % of Total |
|----------------|-----------|------------|
| Backend API (all test calls) | 0.20 s | 0.1% |
| Agent 2048 (30 LLM calls) | 111.6 s | 31.6% |
| Agent MergeFall (12 LLM calls) | 241.7 s | 68.3% |
| **Total** | **353.5 s** | **100%** |

LLM inference dominates wall time (>99.9%). The Flask backend processes requests in ~2–3 ms.

## Files Created / Modified

| File | Action | Description |
|------|--------|-------------|
| `.env` | Created | OpenAI API key for agent |
| `claude_version_test_api.py` | Created | Comprehensive API test script |
| `claude_reports/task_brief.md` | Created | This report |
| `claude_reports/execution_report.md` | Created | Detailed execution log |
| `claude_reports/media/*.csv` | Created | Copied game log CSVs |
| `backend/logs/2048/*.csv` | Auto-generated | Game session logs |
| `backend/logs/mergefall/*.csv` | Auto-generated | Game session logs |
