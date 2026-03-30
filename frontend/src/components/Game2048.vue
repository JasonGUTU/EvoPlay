<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from "vue";
import GameLog from "./GameLog.vue";
import { getSessionId, resetSessionId, addSessionToUrl, setSessionIdFromUrl } from "../utils/session.js";

defineProps({ playerName: { type: String, default: "" } });

const API = "/api/game/2048";
const logRef = ref(null);
const sessionId = ref(null);

const board = ref([]);
const score = ref(0);
const gameOver = ref(false);
const won = ref(false);
const validActions = ref([]);
const error = ref("");
const agentError = ref("");
const lastAction = ref("");
const difficulty = ref("hard");
const maxTile = ref(0);

// Tile animation state
let tileIdCounter = 0;
const tiles = ref([]); // {id, value, row, col, merged, isNew}
const isAnimating = ref(false);

const DIFFICULTIES = [
  { value: "easy",   label: "Easy",   desc: "Only 2s spawn" },
  { value: "medium", label: "Medium", desc: "90% 2s, 10% 4s" },
  { value: "hard",   label: "Hard",   desc: "50% 2s, 50% 4s" },
];

// ── Tile management ──────────────────────────────────────────────

function boardToTiles(b) {
  const result = [];
  for (let r = 0; r < 4; r++) {
    for (let c = 0; c < 4; c++) {
      if (b[r][c] !== 0) {
        result.push({ id: ++tileIdCounter, value: b[r][c], row: r, col: c, merged: false, isNew: false });
      }
    }
  }
  return result;
}

function simulateMove(oldBoard, direction) {
  // Returns { newBoard, movements: [{fromR, fromC, toR, toC, value, merged, mergedValue}], changed }
  const b = oldBoard.map(row => [...row]);
  const movements = [];
  let changed = false;

  function processLine(line, indices) {
    // line: array of {value, origIdx}
    // Returns processed line with merge info
    const nonZero = line.filter(x => x.value !== 0);
    const result = [];
    let i = 0;
    while (i < nonZero.length) {
      if (i + 1 < nonZero.length && nonZero[i].value === nonZero[i + 1].value) {
        // Merge
        result.push({ value: nonZero[i].value * 2, sources: [nonZero[i], nonZero[i + 1]], merged: true });
        i += 2;
      } else {
        result.push({ value: nonZero[i].value, sources: [nonZero[i]], merged: false });
        i++;
      }
    }
    return result;
  }

  if (direction === "left" || direction === "right") {
    for (let r = 0; r < 4; r++) {
      let line = [];
      for (let c = 0; c < 4; c++) {
        line.push({ value: b[r][c], row: r, col: c });
      }
      if (direction === "right") line.reverse();
      const processed = processLine(line);
      // Map back to positions
      const newRow = new Array(4).fill(0);
      let pos = 0;
      for (const item of processed) {
        const targetC = direction === "right" ? 3 - pos : pos;
        newRow[targetC] = item.value;
        for (const src of item.sources) {
          if (src.row !== r || src.col !== targetC) changed = true;
          movements.push({
            fromR: src.row, fromC: src.col,
            toR: r, toC: targetC,
            value: src.value,
            merged: item.merged,
            mergedValue: item.value,
          });
        }
        if (item.merged) changed = true;
        pos++;
      }
      if (!changed) {
        for (let c = 0; c < 4; c++) {
          if (b[r][c] !== newRow[c]) changed = true;
        }
      }
      b[r] = newRow;
    }
  } else {
    for (let c = 0; c < 4; c++) {
      let line = [];
      for (let r = 0; r < 4; r++) {
        line.push({ value: b[r][c], row: r, col: c });
      }
      if (direction === "down") line.reverse();
      const processed = processLine(line);
      const newCol = new Array(4).fill(0);
      let pos = 0;
      for (const item of processed) {
        const targetR = direction === "down" ? 3 - pos : pos;
        newCol[targetR] = item.value;
        for (const src of item.sources) {
          if (src.row !== targetR || src.col !== c) changed = true;
          movements.push({
            fromR: src.row, fromC: src.col,
            toR: targetR, toC: c,
            value: src.value,
            merged: item.merged,
            mergedValue: item.value,
          });
        }
        if (item.merged) changed = true;
        pos++;
      }
      if (!changed) {
        for (let r = 0; r < 4; r++) {
          if (b[r][c] !== newCol[r]) changed = true;
        }
      }
      for (let r = 0; r < 4; r++) b[r][c] = newCol[r];
    }
  }

  return { newBoard: b, movements, changed };
}

// ── API helpers ────────────────────────────────────────────────────

async function fetchState() {
  const urlSessionId = setSessionIdFromUrl("2048");
  const sid = urlSessionId || getSessionId("2048");
  sessionId.value = sid;
  const url = addSessionToUrl(`${API}/state`, sid);
  const res = await fetch(url);
  const data = await res.json();
  if (data.session_id) {
    sessionId.value = data.session_id;
  }
  applyState(data);
  logRef.value?.fetchLog();
}

async function sendAction(move) {
  if (isAnimating.value) return;
  lastAction.value = move;
  error.value = "";
  lastUserActionTime = Date.now();

  // Step 1: Simulate move locally for animation
  const oldBoard = board.value.map(row => [...row]);
  const { movements, changed } = simulateMove(oldBoard, move);

  if (!changed) return; // No change, don't send

  isAnimating.value = true;

  // Step 2: Create animated tiles from movements
  const animTiles = [];
  const mergedPositions = new Set();

  for (const m of movements) {
    const tile = {
      id: ++tileIdCounter,
      value: m.value,
      row: m.fromR, col: m.fromC,       // Start position
      targetRow: m.toR, targetCol: m.toC, // End position
      merged: m.merged,
      mergedValue: m.mergedValue,
      isNew: false,
    };
    animTiles.push(tile);
    if (m.merged) {
      mergedPositions.add(`${m.toR},${m.toC}`);
    }
  }

  // Set tiles at start positions
  tiles.value = animTiles.map(t => ({ ...t, row: t.row, col: t.col }));

  // Step 3: Trigger slide animation (move to target positions)
  await nextTick();
  requestAnimationFrame(() => {
    tiles.value = animTiles.map(t => ({ ...t, row: t.targetRow, col: t.targetCol }));
  });

  // Step 4: After slide completes, send to backend and apply real state
  setTimeout(async () => {
    const sid = sessionId.value || getSessionId("2048");
    const url = addSessionToUrl(`${API}/action?move=${move}`, sid);
    const res = await fetch(url);
    const data = await res.json();
    if (data.error) {
      error.value = data.error;
    }
    if (data.session_id) {
      sessionId.value = data.session_id;
    }

    // Apply backend state and find new tiles
    const serverBoard = data.board;
    const localBoard = simulateMove(oldBoard, move).newBoard;

    // Build tiles from server board, mark new spawned tiles
    const finalTiles = [];
    for (let r = 0; r < 4; r++) {
      for (let c = 0; c < 4; c++) {
        if (serverBoard[r][c] !== 0) {
          const wasInLocal = localBoard[r][c] === serverBoard[r][c];
          const isMerged = mergedPositions.has(`${r},${c}`);
          finalTiles.push({
            id: ++tileIdCounter,
            value: serverBoard[r][c],
            row: r, col: c,
            merged: isMerged,
            isNew: !wasInLocal, // New tile spawned by backend
          });
        }
      }
    }

    tiles.value = finalTiles;
    board.value = serverBoard;
    score.value = data.score;
    gameOver.value = data.game_over;
    won.value = data.won;
    validActions.value = data.valid_actions || [];
    if (data.difficulty) difficulty.value = data.difficulty;
    if (data.max_tile !== undefined) maxTile.value = data.max_tile;
    agentError.value = data.agent_error || "";

    if (data.game_over) {
      stopPolling();
    }

    // Clear animation flags after pop animation
    setTimeout(() => {
      tiles.value = tiles.value.map(t => ({ ...t, merged: false, isNew: false }));
      isAnimating.value = false;
    }, 200);

    logRef.value?.fetchLog();
  }, 150); // Match CSS transition duration
}

async function resetGame(newDifficulty) {
  if (newDifficulty) difficulty.value = newDifficulty;
  lastAction.value = "";
  error.value = "";
  const sid = resetSessionId("2048");
  sessionId.value = sid;
  const url = addSessionToUrl(`${API}/reset?difficulty=${difficulty.value}`, sid);
  const res = await fetch(url);
  const data = await res.json();
  if (data.session_id) {
    sessionId.value = data.session_id;
  }
  applyState(data);
  logRef.value?.fetchLog();
}

function applyState(state) {
  board.value = state.board;
  score.value = state.score;
  gameOver.value = state.game_over;
  won.value = state.won;
  validActions.value = state.valid_actions || [];
  if (state.difficulty) difficulty.value = state.difficulty;
  if (state.max_tile !== undefined) maxTile.value = state.max_tile;
  agentError.value = state.agent_error || "";

  // Rebuild tiles from board (no animation)
  tiles.value = boardToTiles(state.board);

  if (state.game_over) {
    stopPolling();
  } else {
    startPolling();
  }
}

// ── Keyboard handling ──────────────────────────────────────────────

const keyMap = {
  ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right",
  w: "up", s: "down", a: "left", d: "right",
};

function onKeyDown(e) {
  const move = keyMap[e.key];
  if (move && validActions.value.includes(move)) {
    e.preventDefault();
    sendAction(move);
  }
}

// ── Polling ──────────────────────────────────────────────────────

let pollingInterval = null;
const POLLING_INTERVAL_MS = 1000;
let lastUserActionTime = 0;
const USER_ACTION_COOLDOWN_MS = 500;

function startPolling() {
  if (!pollingInterval && !gameOver.value) {
    pollingInterval = setInterval(async () => {
      if (Date.now() - lastUserActionTime < USER_ACTION_COOLDOWN_MS) return;
      if (isAnimating.value) return;
      if (!gameOver.value) {
        await fetchState();
      } else {
        stopPolling();
      }
    }, POLLING_INTERVAL_MS);
  }
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}

onMounted(() => {
  fetchState();
  window.addEventListener("keydown", onKeyDown);
  startPolling();
});

onUnmounted(() => {
  window.removeEventListener("keydown", onKeyDown);
  stopPolling();
});

// ── Tile colours ───────────────────────────────────────────────────

const tileColors = {
  0: { bg: "#cdc1b4", fg: "#cdc1b4" },
  2: { bg: "#eee4da", fg: "#776e65" },
  4: { bg: "#ede0c8", fg: "#776e65" },
  8: { bg: "#f2b179", fg: "#f9f6f2" },
  16: { bg: "#f59563", fg: "#f9f6f2" },
  32: { bg: "#f67c5f", fg: "#f9f6f2" },
  64: { bg: "#f65e3b", fg: "#f9f6f2" },
  128: { bg: "#edcf72", fg: "#f9f6f2" },
  256: { bg: "#edcc61", fg: "#f9f6f2" },
  512: { bg: "#edc850", fg: "#f9f6f2" },
  1024: { bg: "#edc53f", fg: "#f9f6f2" },
  2048: { bg: "#edc22e", fg: "#f9f6f2" },
};

function tileStyle(tile) {
  const c = tileColors[tile.value] || { bg: "#3c3a32", fg: "#f9f6f2" };
  // Grid has 4 cells with 8px gaps, inside 8px padding
  // Use the grid-cell positions: each cell is at (col/4) of the inner area
  // Inner area = 100% - 16px padding (8px each side)
  // Cell width = (innerWidth - 3*8px gap) / 4
  // Cell left = padding + col * (cellWidth + gap)
  // Simplified: position as percentage of board including padding
  const cellPercent = 'calc((100% - 40px) / 4)'; // (board - 2*padding - 3*gaps) / 4 = (100% - 16px - 24px) / 4
  const topVal = `calc(8px + ${tile.row} * (((100% - 16px - 24px) / 4) + 8px))`;
  const leftVal = `calc(8px + ${tile.col} * (((100% - 16px - 24px) / 4) + 8px))`;
  return {
    backgroundColor: c.bg,
    color: c.fg,
    fontSize: tile.value >= 1024 ? "1.4rem" : tile.value >= 128 ? "1.6rem" : "1.9rem",
    top: topVal,
    left: leftVal,
    width: 'calc((100% - 16px - 24px) / 4)',
    height: 'calc((100% - 16px - 24px) / 4)',
  };
}
</script>

<template>
  <div class="game-2048" tabindex="0">
    <!-- Difficulty selector -->
    <div class="difficulty-bar">
      <button
        v-for="d in DIFFICULTIES"
        :key="d.value"
        class="diff-btn"
        :class="{ active: difficulty === d.value }"
        :title="d.desc"
        @click="resetGame(d.value)"
      >{{ d.label }}</button>
    </div>

    <!-- Score bar -->
    <div class="info-bar">
      <div class="score-box">
        <span class="label">Score</span>
        <span class="value">{{ score }}</span>
      </div>
      <button class="reset-btn" @click="resetGame()">New Game</button>
    </div>

    <!-- Status -->
    <div v-if="won" class="banner won">You reached 2048!</div>
    <div v-if="gameOver" class="banner over">Game Over</div>
    <div v-if="error" class="banner error">{{ error }}</div>
    <div v-if="agentError" class="agent-error">Agent Error: {{ agentError }}</div>

    <!-- Board -->
    <div class="board">
      <!-- Background grid cells -->
      <div class="grid-bg">
        <div v-for="i in 16" :key="'bg'+i" class="grid-cell"></div>
      </div>
      <!-- Animated tiles -->
      <div
        v-for="tile in tiles"
        :key="tile.id"
        class="tile"
        :class="{ 'tile-merged': tile.merged, 'tile-new': tile.isNew }"
        :style="tileStyle(tile)"
      >
        {{ tile.value }}
      </div>
    </div>

    <!-- Controls (for mobile / click) -->
    <div class="controls">
      <div class="controls-row">
        <button :disabled="!validActions.includes('up')" @click="sendAction('up')">Up</button>
      </div>
      <div class="controls-row">
        <button :disabled="!validActions.includes('left')" @click="sendAction('left')">Left</button>
        <button :disabled="!validActions.includes('down')" @click="sendAction('down')">Down</button>
        <button :disabled="!validActions.includes('right')" @click="sendAction('right')">Right</button>
      </div>
    </div>

    <p class="hint">Use arrow keys or WASD to play</p>

    <GameLog ref="logRef" game-name="2048" :session-id="sessionId" />
  </div>
</template>

<style scoped>
.game-2048 {
  outline: none;
}

/* Difficulty */
.difficulty-bar {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 12px;
}
.diff-btn {
  padding: 5px 16px;
  border-radius: 20px;
  border: 1px solid #bbada0;
  background: transparent;
  color: #bbada0;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.15s;
}
.diff-btn:hover { border-color: #8f7a66; color: #8f7a66; }
.diff-btn.active {
  background: #8f7a66;
  border-color: #8f7a66;
  color: #f9f6f2;
  font-weight: 600;
}

.info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.score-box {
  background: #bbada0;
  border-radius: 6px;
  padding: 8px 20px;
  color: #fff;
  text-align: center;
  min-width: 90px;
}

.score-box .label {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.score-box .value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
}

.reset-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  background: #8f7a66;
  color: #f9f6f2;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}

.reset-btn:hover { background: #776e65; }

.banner {
  text-align: center;
  padding: 10px;
  border-radius: 6px;
  margin-bottom: 12px;
  font-weight: 700;
  font-size: 1.1rem;
}
.banner.won { background: #edc22e; color: #f9f6f2; }
.banner.over { background: #f67c5f; color: #f9f6f2; }
.banner.error { background: #f44; color: #fff; }

.agent-error {
  text-align: center;
  padding: 10px;
  border-radius: 8px;
  margin-top: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  background: #7f1d1d;
  color: #fca5a5;
  border: 1px solid #991b1b;
}

/* Board */
.board {
  position: relative;
  background: #bbada0;
  border-radius: 8px;
  padding: 8px;
  aspect-ratio: 1;
}

.grid-bg {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: repeat(4, 1fr);
  gap: 8px;
  width: 100%;
  height: 100%;
}

.grid-cell {
  background: #cdc1b4;
  border-radius: 6px;
}

/* Animated tiles */
.tile {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-weight: 700;
  user-select: none;
  transition: top 0.15s ease, left 0.15s ease;
  z-index: 1;
}

.tile-merged {
  animation: tile-pop 0.2s ease;
  z-index: 2;
}

.tile-new {
  animation: tile-appear 0.2s ease;
  z-index: 2;
}

@keyframes tile-pop {
  0% { transform: scale(1); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}

@keyframes tile-appear {
  0% { transform: scale(0); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.controls {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.controls-row {
  display: flex;
  gap: 6px;
}

.controls button {
  width: 72px;
  padding: 10px 0;
  border: none;
  border-radius: 6px;
  background: #8f7a66;
  color: #f9f6f2;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
}

.controls button:disabled { opacity: 0.4; cursor: not-allowed; }
.controls button:not(:disabled):hover { background: #776e65; }

.hint {
  text-align: center;
  margin-top: 12px;
  font-size: 0.85rem;
  color: #bbada0;
}
</style>
