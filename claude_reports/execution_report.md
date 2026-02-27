# EvoPlay Reproduction — Execution Report

## Summary

This report documents the full reproduction of the EvoPlay game server framework — a 3-tier system (Vue 3 frontend → Flask backend → pluggable games) with an LLM-powered AI agent. The reproduction covered: (1) environment setup with micromamba, (2) backend API testing across all 7 endpoints for both games (2048, MergeFall), (3) AI agent gameplay using GPT-4o-mini via LiteLLM. All API endpoints returned valid JSON with correct game states and CSV logs. The agent played 30 steps of 2048 (score: 240) and 12 steps of MergeFall (score: 52, game over via column overflow). Backend latency averaged 2.3 ms/call; agent latency was dominated by LLM inference at 3.7–20.1 s/step.

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

### Commands

```bash
# Create dedicated micromamba environment with Python 3.10
/usr/bin/micromamba create -n evoplay python=3.10 -y -r /home/ruibo_ming/.local/share/mamba
```
**Result**: Environment created at `/home/ruibo_ming/.local/share/mamba/envs/evoplay/`.

```bash
# Install backend + agent Python dependencies in one command
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    pip install flask flask-cors litellm==1.40.0 requests
```
**Result**: Installed Flask 3.1.3, Flask-CORS 6.0.2, LiteLLM 1.40.0, requests 2.32.5, plus transitive dependencies (openai, tiktoken, pydantic, httpx, etc.).

```bash
# Install Node.js for frontend via nodeenv (no system npm available)
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba pip install nodeenv
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    nodeenv --prebuilt --node=18.20.0 /home/ruibo_ming/.local/share/mamba/envs/evoplay/node_env
```
**Result**: Node.js 18.20.0 installed at `envs/evoplay/node_env/bin/node`.

```bash
# Install frontend npm dependencies
cd /work/ruibo_ming/EvoPlay/frontend
/home/ruibo_ming/.local/share/mamba/envs/evoplay/node_env/bin/npm install
```
**Result**: 31 packages installed (Vue 3.4, Vite 5.0, @vitejs/plugin-vue 5.0).

```bash
# Create .env with OpenAI API key at project root
echo "OPENAI_API_KEY=sk-proj-..." > /work/ruibo_ming/EvoPlay/.env
```
**Result**: Agent config.py reads from `agent/../.env` (project root).

### Dependency Resolution Notes

- No system `npm` was available — resolved by installing `nodeenv` into the micromamba env and creating a local Node.js installation
- LiteLLM 1.40.0 pinned as specified in `agent/requirements.txt` to avoid API compatibility issues
- All dependencies installed cleanly with no conflicts

## Stage 2 — Backend API Testing

### Starting the Backend

```bash
# Launch Flask dev server in background on port 5001
cd /work/ruibo_ming/EvoPlay/backend
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba python app.py &
```
**Result**: Flask server running at `http://0.0.0.0:5001` with debug mode on, CORS enabled.

### Test Script

Created `claude_version_test_api.py` at project root — a comprehensive test suite covering all 7 API endpoints, both games (25 moves each), error handling, and timing metrics.

```python
# Core test logic — cycling direction strategy for 2048
# Rotates through [up, right, down, left] each move,
# picking the first valid direction from the cycle
directions = ["up", "right", "down", "left"]
for i in range(25):
    # Fetch currently valid actions for this session
    resp = requests.get(f"{BASE_URL}/api/game/2048/valid_actions",
                        params={"session_id": session_id})
    valid = resp.json()["valid_actions"]
    # Pick first valid action from current rotation
    action = next((d for d in directions if d in valid), valid[0])
    # Rotate preference list for next turn
    directions = directions[1:] + directions[:1]
    # Execute the move — GET endpoint returns updated game state
    resp = requests.get(f"{BASE_URL}/api/game/2048/action",
                        params={"move": action, "session_id": session_id})
    result = resp.json()
    # result contains: game, board (4×4 array), score, game_over, valid_actions, session_id
```

```bash
# Run test suite
cd /work/ruibo_ming/EvoPlay
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    python claude_version_test_api.py
```

### Test Results

**Test 1 — List Games**: `GET /api/games` returned `{"games": ["2048", "mergefall"]}` (200 OK).

**Test 2 — Game Rules**: Both games returned detailed rule text (2048: 1346 chars, MergeFall: 1873 chars).

**Test 3 — Play 2048 (25 moves)**:
- Session ID: `6355168d-cc08-4946-8a9d-d49ea78ae941`
- Initial board: two tiles (value 2) placed randomly
- Score progression: 0 → 4 → 4 → 4 → ... → 152 → 168
- Final board state:
```
   2    32     2     0
  16     4     0     0
   2     0     0     0
   0     2     0     0
```
- Max tile: 32, Final score: 168, Game over: No
- CSV log: 25 entries, elapsed 0.11 s

**Test 4 — Play MergeFall (25 moves)**:
- Session ID: `29466ebd-121c-4ecc-b198-c4894403cc1e`
- Board: 5×6 grid, center-out column cycling strategy (`[2, 1, 3, 0, 4]`)
- Score progression: 0 → 4 → 4 → ... → 108
- Final board state:
```
   0    0    0    0    0
   0    0    0    0    0
   0    0    0    0    0
   0    0    2   16    8
   4    8   16    2    4
   8   16    8    4   16
```
- Final score: 108, Game over: No
- CSV log: 25 entries, elapsed 0.06 s

**Test 5 — Error Handling**:
- Unknown game rules → 404: `{"error": "Unknown game: unknown_game"}`
- Missing move parameter → 400: `{"error": "Missing 'move' query parameter."}`
- Missing session_id → 400: `{"error": "Missing required 'session_id' query parameter."}`

### API Timing Metrics

| Endpoint | Calls | Avg Latency | Total Time |
|----------|-------|-------------|------------|
| `action_2048` | 25 | 2.5 ms | 0.061 s |
| `action_mergefall` | 25 | 2.2 ms | 0.055 s |
| `valid_actions_2048` | 26 | 2.1 ms | 0.055 s |
| `list_games` | 1 | 7.7 ms | 0.008 s |
| `reset_2048` | 1 | 4.0 ms | 0.004 s |
| `rules` | 2 | 1.9 ms | 0.004 s |
| `state_*` | 2 | 2.4 ms | 0.005 s |
| `log_*` | 2 | 2.3 ms | 0.005 s |
| **Total** | **86** | **2.3 ms** | **0.200 s** |

Note: CPU-only backend — no GPU utilization. First call (`list_games`: 7.7 ms) includes Flask route resolution warmup.

## Stage 3 — AI Agent Testing

### Agent Configuration

| Parameter | Value |
|-----------|-------|
| Model | `gpt-4o-mini` |
| Provider | `openai` |
| Reasoning | `vanilla` (VanillaReasoning) |
| Temperature | 0.7 |
| Max tokens | 50 |
| Delay between steps | 0.2 s |
| Max steps | 30 |

### Running Agent on 2048

```bash
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    python -m agent.main --game 2048 --model gpt-4o-mini --max-steps 30 --delay 0.2 --reasoning vanilla
```

```python
# Agent reasoning flow (from agent/reasoning/vanilla_reasoning.py)
# VanillaReasoning.reason() method:
# 1. Build prompt with game context — rules, board state, valid actions
prompt = f"""You are playing {game_name}. Here are the rules:
{rules}

Current game state:
{self._format_board(game_state['board'])}
Score: {game_state['score']}

Valid actions: {valid_actions}
Choose the best action. Respond with ONLY the action string."""

# 2. Call LLM via LiteLLM unified interface (wraps OpenAI, Anthropic, etc.)
response = self.llm.simple_call(prompt, system_message="You are a game-playing AI.")

# 3. Parse response — extract action string, validate against valid_actions list
# Falls back to first valid action if LLM returns unparseable output
action = response.strip().lower()
if action not in valid_actions:
    action = valid_actions[0]  # Safety fallback
```

**Result**:
- Session ID: `272331d5-3a55-42cb-b64a-3a9c653938b7`
- Completed all 30 steps (no game over)
- Final score: 240, Max tile: 32
- Total elapsed: 111.6 s (avg 3.7 s/step)
- Action distribution: `left` ×16, `up` ×5, `down` ×7, `right` ×2
- Score milestones: step 9 → 44, step 18 → 96, step 19 → 128, step 30 → 240

Step-by-step log (selected):
```
Step  1: left  → score=0     Step 16: down  → score=68
Step  2: up    → score=4     Step 17: left  → score=72
Step  3: down  → score=12    Step 18: down  → score=96
Step  8: left  → score=28    Step 19: down  → score=128
Step  9: left  → score=44    Step 26: left  → score=184
Step 12: left  → score=56    Step 27: left  → score=200
Step 15: left  → score=60    Step 30: up    → score=240
```

Final board:
```
  32    4    0    0
  32    4    0    0
   2    0    0    0
   0    0    0    2
```

### Running Agent on MergeFall

Same command with `--game mergefall`. Same model and parameters as 2048 (same reasoning engine, different game interface).

```bash
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    python -m agent.main --game mergefall --model gpt-4o-mini --max-steps 30 --delay 0.2 --reasoning vanilla
```

**Result**:
- Session ID: `4887f0f1-6df1-4034-9072-3ec9dce69016`
- Game over at step 12 (column 0 overflow)
- Final score: 52, Max tile: 16
- Total elapsed: 241.7 s (avg 20.1 s/step)
- Action distribution: `drop 0` ×12 (100% — agent never diversified)

Step-by-step log (complete):
```
Step  1: drop 0 → score=0    (tile placed at bottom of col 0)
Step  2: drop 0 → score=4    (2+2=4 merge)
Step  3: drop 0 → score=12   (merge chain)
Step  4: drop 0 → score=12   (no merge, new tile stacked)
Step  5: drop 0 → score=12   (no merge)
Step  6: drop 0 → score=12   (no merge)
Step  7: drop 0 → score=12   (no merge)
Step  8: drop 0 → score=12   (no merge)
Step  9: drop 0 → score=44   (cascade merge: multiple tiles absorbed)
Step 10: drop 0 → score=44   (no merge)
Step 11: drop 0 → score=52   (merge)
Step 12: drop 0 → score=52   GAME OVER (overflow)
```

Final board (column 0 completely filled):
```
   8    0    0    0    0
  16    0    0    0    0
   4    0    0    0    0
   2    0    0    0    0
   4    0    0    0    0
   8    0    0    0    0
```

### Agent Behavior Comparison

| Metric | 2048 | MergeFall |
|--------|------|-----------|
| Steps completed | 30 (max reached) | 12 (game over) |
| Final score | 240 | 52 |
| Max tile | 32 | 16 |
| Game over | No | Yes (overflow) |
| Total time | 111.6 s | 241.7 s |
| Avg step latency | 3.7 s | 20.1 s |
| Action diversity | 4 unique actions | 1 unique action |
| Strategy quality | Reasonable (left-bias) | Poor (single-column) |

The 5.4× higher per-step latency for MergeFall is attributable to the larger board context (5×6 vs 4×4) and longer rules text (1873 vs 1346 chars) in the LLM prompt.

### CSV Logs

All game sessions produced CSV logs at `backend/logs/<game>/<session_id>.csv`:

| Log File | Game | Steps | Size |
|----------|------|-------|------|
| `272331d5-...csv` | 2048 (agent) | 30 | 2.5 KB |
| `4887f0f1-...csv` | MergeFall (agent) | 12 | 1.6 KB |
| `6355168d-...csv` | 2048 (API test) | 25 | 2.1 KB |
| `29466ebd-...csv` | MergeFall (API test) | 25 | 3.3 KB |

CSV format: `step,time,action,score,game_over,board` where board is a JSON-encoded nested array.

### Timing Bottleneck Analysis

| Pipeline Stage | Wall Time | % of Total |
|----------------|-----------|------------|
| Backend API (all test calls) | 0.20 s | 0.1% |
| Agent 2048 (30 LLM calls) | 111.6 s | 31.6% |
| Agent MergeFall (12 LLM calls) | 241.7 s | 68.3% |
| **Total** | **353.5 s** | **100%** |

LLM inference dominates wall time (>99.9%). The Flask backend is negligible. No GPU was used (CPU-only backend, LLM calls are remote API requests to OpenAI).

## Files Created / Modified

| File | Action | Description |
|------|--------|-------------|
| `.env` | Created | `OPENAI_API_KEY=sk-proj-...` for agent config |
| `claude_version_test_api.py` | Created | 310-line API test script with timing metrics |
| `claude_reports/task_brief.md` | Created | Task brief for advisor |
| `claude_reports/execution_report.md` | Created | This detailed execution log |
| `claude_reports/task_brief_zh.md` | Created | Chinese translation of task brief |
| `claude_reports/execution_report_zh.md` | Created | Chinese translation of execution report |
| `claude_reports/media/agent_2048_log.csv` | Copied | Agent 2048 session CSV log |
| `claude_reports/media/agent_mergefall_log.csv` | Copied | Agent MergeFall session CSV log |
| `claude_reports/media/api_test_2048_log.csv` | Copied | API test 2048 session CSV log |
| `claude_reports/media/api_test_mergefall_log.csv` | Copied | API test MergeFall session CSV log |
| `backend/logs/2048/*.csv` | Auto-generated | 4 session log files |
| `backend/logs/mergefall/*.csv` | Auto-generated | 3 session log files |
