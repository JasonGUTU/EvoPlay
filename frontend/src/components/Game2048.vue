<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import GameLog from "./GameLog.vue";
import { getSessionId, resetSessionId, addSessionToUrl, setSessionIdFromUrl } from "../utils/session.js";

const API = "/api/game/2048";
const logRef = ref(null);
const sessionId = ref(null);

const board = ref([]);
const score = ref(0);
const gameOver = ref(false);
const won = ref(false);
const validActions = ref([]);
const error = ref("");
const lastAction = ref("");

// ── API helpers ────────────────────────────────────────────────────

async function fetchState() {
  // Check if session_id is provided in URL, if so, use it
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
}

async function sendAction(move) {
  lastAction.value = move;
  error.value = "";
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
  applyState(data);
  logRef.value?.fetchLog();
}

async function resetGame() {
  lastAction.value = "";
  error.value = "";
  // Reset session ID to get a fresh game instance
  const sid = resetSessionId("2048");
  sessionId.value = sid;
  const url = addSessionToUrl(`${API}/reset`, sid);
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
}

// ── Keyboard handling ──────────────────────────────────────────────

const keyMap = {
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
  w: "up",
  s: "down",
  a: "left",
  d: "right",
};

function onKeyDown(e) {
  const move = keyMap[e.key];
  if (move && validActions.value.includes(move)) {
    e.preventDefault();
    sendAction(move);
  }
}

onMounted(() => {
  fetchState();
  window.addEventListener("keydown", onKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", onKeyDown);
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

function tileStyle(value) {
  const c = tileColors[value] || { bg: "#3c3a32", fg: "#f9f6f2" };
  return {
    backgroundColor: c.bg,
    color: c.fg,
    fontSize: value >= 1024 ? "1.4rem" : value >= 128 ? "1.6rem" : "1.9rem",
  };
}
</script>

<template>
  <div class="game-2048" tabindex="0">
    <!-- Score bar -->
    <div class="info-bar">
      <div class="score-box">
        <span class="label">Score</span>
        <span class="value">{{ score }}</span>
      </div>
      <button class="reset-btn" @click="resetGame">New Game</button>
    </div>

    <!-- Status -->
    <div v-if="won" class="banner won">You reached 2048!</div>
    <div v-if="gameOver" class="banner over">Game Over</div>
    <div v-if="error" class="banner error">{{ error }}</div>

    <!-- Board -->
    <div class="board">
      <div v-for="(row, r) in board" :key="r" class="row">
        <div
          v-for="(cell, c) in row"
          :key="c"
          class="cell"
          :style="tileStyle(cell)"
        >
          {{ cell || "" }}
        </div>
      </div>
    </div>

    <!-- Controls (for mobile / click) -->
    <div class="controls">
      <div class="controls-row">
        <button
          :disabled="!validActions.includes('up')"
          @click="sendAction('up')"
        >
          Up
        </button>
      </div>
      <div class="controls-row">
        <button
          :disabled="!validActions.includes('left')"
          @click="sendAction('left')"
        >
          Left
        </button>
        <button
          :disabled="!validActions.includes('down')"
          @click="sendAction('down')"
        >
          Down
        </button>
        <button
          :disabled="!validActions.includes('right')"
          @click="sendAction('right')"
        >
          Right
        </button>
      </div>
    </div>

    <!-- Hint for keyboard -->
    <p class="hint">Use arrow keys or WASD to play</p>

    <!-- Log -->
    <GameLog ref="logRef" game-name="2048" :session-id="sessionId" />
  </div>
</template>

<style scoped>
.game-2048 {
  outline: none;
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

.reset-btn:hover {
  background: #776e65;
}

.banner {
  text-align: center;
  padding: 10px;
  border-radius: 6px;
  margin-bottom: 12px;
  font-weight: 700;
  font-size: 1.1rem;
}

.banner.won {
  background: #edc22e;
  color: #f9f6f2;
}

.banner.over {
  background: #f67c5f;
  color: #f9f6f2;
}

.banner.error {
  background: #f44;
  color: #fff;
}

.board {
  background: #bbada0;
  border-radius: 8px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.row {
  display: flex;
  gap: 8px;
}

.cell {
  width: 100%;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-weight: 700;
  font-size: 1.9rem;
  user-select: none;
  transition: background-color 0.12s, transform 0.12s;
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

.controls button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.controls button:not(:disabled):hover {
  background: #776e65;
}

.hint {
  text-align: center;
  margin-top: 12px;
  font-size: 0.85rem;
  color: #bbada0;
}

.last-action {
  margin-top: 4px;
  font-style: italic;
}
</style>
