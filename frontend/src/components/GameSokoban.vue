<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import GameLog from "./GameLog.vue";
import { getSessionId, resetSessionId, addSessionToUrl, setSessionIdFromUrl } from "../utils/session.js";

defineProps({ playerName: { type: String, default: "" } });

const API = "/api/game/sokoban";
const logRef = ref(null);
const sessionId = ref(null);

const mapGrid = ref([]);
const playerPos = ref([]);
const boxes = ref([]);
const score = ref(0);
const gameOver = ref(false);
const won = ref(false);
const withdrawn = ref(false);
const validActions = ref([]);
const undoAvailable = ref(false);
const currentLevel = ref(1);
const maxLevel = ref(1);
const difficulty = ref("easy");
const error = ref("");
const lastAction = ref("");

// ── API helpers ────────────────────────────────────────────────────

async function fetchState() {
  const urlSessionId = setSessionIdFromUrl("sokoban");
  const sid = urlSessionId || getSessionId("sokoban");
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
  lastAction.value = move;
  error.value = "";
  lastUserActionTime = Date.now();
  const sid = sessionId.value || getSessionId("sokoban");
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

async function resetGame(newDifficulty) {
  if (typeof newDifficulty === 'string') difficulty.value = newDifficulty;
  lastAction.value = "";
  error.value = "";
  // Use current session ID to reset current level instead of creating a new session (which would drop to level 1)
  const sid = sessionId.value || getSessionId("sokoban");
  let url;
  if (typeof newDifficulty === 'string') {
    url = addSessionToUrl(`${API}/reset?difficulty=${difficulty.value}`, sid);
  } else {
    url = addSessionToUrl(`${API}/reset`, sid);
  }
  const res = await fetch(url);
  const data = await res.json();
  if (data.session_id) {
    sessionId.value = data.session_id;
  }
  applyState(data);
  logRef.value?.fetchLog();
}

function applyState(state) {
  if (state.board) {
    mapGrid.value = state.board.map || [];
    playerPos.value = state.board.player_pos || [];
    boxes.value = state.board.boxes || [];
  }
  score.value = state.score;
  gameOver.value = state.game_over;
  won.value = state.won;
  withdrawn.value = state.withdrawn || false;
  validActions.value = state.valid_actions || [];
  undoAvailable.value = state.undo_available || false;
  currentLevel.value = state.current_level || 1;
  maxLevel.value = state.max_level || 1;
  if (state.difficulty) difficulty.value = state.difficulty;
  
  if (state.game_over) {
    stopPolling();
  } else {
    startPolling();
  }
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

// Polling interval
let pollingInterval = null;
const POLLING_INTERVAL_MS = 1000;
let lastUserActionTime = 0;
const USER_ACTION_COOLDOWN_MS = 500;

function startPolling() {
  if (!pollingInterval && !gameOver.value) {
    pollingInterval = setInterval(async () => {
      const timeSinceLastAction = Date.now() - lastUserActionTime;
      if (timeSinceLastAction < USER_ACTION_COOLDOWN_MS) {
        return;
      }
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

// ── Visual Helpers ─────────────────────────────────────────────────

function getTileClass(r, c) {
  if (!mapGrid.value[r]) return "empty";
  const char = mapGrid.value[r][c];
  if (char === "#") return "wall";
  if (char === "O") return "obstacle"; 
  if (char === "W") return "water"; 
  if (char === ".") return "goal";
  return "floor";
}

function hasBox(r, c) {
  return boxes.value.some(box => box[0] === r && box[1] === c);
}

function isPlayer(r, c) {
  return playerPos.value[0] === r && playerPos.value[1] === c;
}

</script>

<template>
  <div class="game-sokoban game-container" tabindex="0">
    <div class="level-indicator">
      <h3>Level {{ currentLevel }}</h3>
    </div>

    <!-- Difficulty -->
    <div class="difficulty-bar" style="display: flex; justify-content: center; gap: 8px; margin-bottom: 16px;">
      <button 
        v-for="d in [{label:'Easy', value:'easy'}, {label:'Medium', value:'medium'}, {label:'Hard', value:'hard'}]"
        :key="d.value"
        :class="{ active: difficulty === d.value }"
        :style="difficulty === d.value ? 'background: #3b82f6; color: white;' : 'background: #334155; color: white;'"
        @click="resetGame(d.value)"
      >
        {{ d.label }}
      </button>
    </div>

    <!-- Info bar -->
    <div class="info-bar">
      <div class="score-box">
        <span class="label">Moves</span>
        <span class="value">{{ score }}</span>
      </div>
      
      <div class="actions">
        <button 
          v-if="won && currentLevel < maxLevel"
          class="next-level-btn"
          @click="sendAction('next_level')"
        >
          Next Level
        </button>
        <button
          v-else-if="withdrawn && currentLevel < maxLevel"
          class="next-level-btn"
          @click="sendAction('next_level')"
        >
          Next Level
        </button>
        <button 
          class="undo-btn" 
          :disabled="!validActions.includes('undo')" 
          @click="sendAction('undo')"
          title="1 Undo remaining"
        >
          Undo
        </button>
        <button class="withdraw-btn" :disabled="gameOver" @click="sendAction('withdraw')">
          Withdraw
        </button>
        <button class="reset-btn" @click="resetGame">Restart</button>
      </div>
    </div>

    <!-- Status -->
    <div v-if="won" class="banner won">You Won!</div>
    <div v-else-if="withdrawn" class="banner withdraw">Withdrawn</div>
    <div v-else-if="gameOver" class="banner over">Game Over</div>
    <div v-if="error" class="banner error">{{ error }}</div>

    <!-- Board -->
    <div class="board-container">
      <div class="grid">
        <div v-for="(row, r) in mapGrid" :key="r" class="row">
          <div v-for="(col, c) in row" :key="c" class="cell" :class="getTileClass(r, c)">
            <span v-if="isPlayer(r, c)" class="entity player">👷</span>
            <span v-else-if="hasBox(r, c)" class="entity box">📦</span>
            <span v-else-if="col === 'O'" class="entity obstacle">🪢</span>
            <span v-else-if="col === 'W'" class="entity water-obstacle">🪣</span>
            <span v-else-if="col === '.'" class="entity goal-marker">🔵</span>
          </div>
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

    <p class="hint">Use arrow keys or WASD to move and push boxes.</p>

    <!-- Log -->
    <GameLog ref="logRef" game-name="sokoban" :session-id="sessionId" />
  </div>
</template>

<style scoped>
.game-sokoban {
  outline: none;
}

.game-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  background: #1e1e1e;
  border-radius: 12px;
  color: white;
  font-family: Arial, sans-serif;
}

/* Difficulty */
.difficulty-bar button { padding: 6px 12px; border: 1px solid #555; border-radius: 4px; cursor: pointer; transition: all 0.2s ease; }
.difficulty-bar button:hover:not(.active) { background: #444 !important; }

.info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #2a2a2a;
  padding: 15px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.score-box {
  background: #1e293b;
  border-radius: 8px;
  padding: 8px 16px;
  color: #fff;
  text-align: center;
  border: 1px solid #334155;
}

.score-box .label {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #94a3b8;
}

.score-box .value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #f8fafc;
}

.actions {
  display: flex;
  gap: 8px;
}

button {
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.undo-btn {
  background: #475569;
  color: white;
}

.undo-btn:hover:not(:disabled) {
  background: #64748b;
}

.undo-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.withdraw-btn {
  background: #f59e0b;
  color: white;
}

.withdraw-btn:hover:not(:disabled) {
  background: #d97706;
}

.withdraw-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reset-btn {
  background: #ef4444;
  color: white;
}

.reset-btn:hover {
  background: #f87171;
}

.banner {
  text-align: center;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-weight: 700;
  font-size: 1.1rem;
}

.banner.won {
  background: #10b981;
  color: white;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.banner.over {
  background: #f59e0b;
  color: white;
}

.banner.withdraw {
  background: #f97316;
  color: white;
}

.banner.error {
  background: #ef4444;
  color: white;
}

.level-indicator {
  text-align: center;
  margin-bottom: 16px;
  color: #94a3b8;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.level-indicator h3 {
  font-size: 1rem;
}

.next-level-btn {
  background: #10b981;
  color: white;
  animation: pulse 2s infinite;
}

.next-level-btn:hover {
  background: #059669;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

.board-container {
  background: #84cc37; /* Grass green */
  padding: 24px;
  border-radius: 12px;
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
  box-shadow: inset 0 2px 10px rgba(0,0,0,0.1);
}

.grid {
  display: flex;
  flex-direction: column;
}

.row {
  display: flex;
}

.cell {
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  position: relative;
}

.cell.wall {
  background: #b54a2a; /* Brick red */
  border: 2px solid #8e3920;
  border-radius: 6px;
  box-shadow: inset 0 2px 0 rgba(255,255,255,0.2), inset 0 -2px 0 rgba(0,0,0,0.2);
}

.cell.floor, .cell.goal, .cell.obstacle, .cell.water {
  background: #b0ada8; /* Concrete grey */
  border: 1px solid #9c9993;
}

.entity {
  position: absolute;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  text-shadow: 0 4px 4px rgba(0,0,0,0.3);
}

.entity.goal-marker {
  font-size: 1.2rem;
  opacity: 0.6;
  text-shadow: 0 0 10px #60a5fa, 0 0 20px #60a5fa;
  z-index: 5;
}

/* Make box look nice when on goal */
.cell.goal .entity.box {
  filter: drop-shadow(0 0 10px #60a5fa);
}

.controls {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.controls-row {
  display: flex;
  gap: 8px;
}

.controls button {
  width: 72px;
  padding: 12px 0;
  background: #334155;
  color: #f8fafc;
}

.controls button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.controls button:not(:disabled):hover {
  background: #475569;
}

.hint {
  text-align: center;
  margin-top: 20px;
  font-size: 0.9rem;
  color: #94a3b8;
}
</style>
