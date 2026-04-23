<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { getSessionId, resetSessionId } from "../utils/session";
import GameLog from "./GameLog.vue";
import GameGuide from "./GameGuide.vue";

const props = defineProps({
  playerName: {
    type: String,
    required: true,
  },
});

const gameId = "crossnumber";

// State
const state = ref({
  grid: [],
  row_targets: [],
  col_targets: [],
  cell_states: [], // 0 = unknown, 1 = confirm, -1 = erase
  rows: 0,
  cols: 0,
  score: 0,
  lives: 3,
  game_over: false,
  won: false,
  withdrawn: false,
  valid_actions: [],
  undo_available: false,
  current_level: 1,
  max_level: 1,
  difficulty: "easy",
});

const errorMsg = ref("");
const sessionId = ref(null);
const isLoading = ref(true);
const isWatchMode = ref(false); // True if viewing via session URL
const pollingInterval = ref(null);

// "erase" or "confirm"
const currentTool = ref("erase");

// Fetch state
async function fetchState() {
  try {
    const res = await fetch(`/api/game/${gameId}/state?session_id=${sessionId.value}`);
    const data = await res.json();
    if (data.error) {
      errorMsg.value = data.error;
    } else {
      state.value = data;
    }
  } catch (e) {
    errorMsg.value = "Failed to fetch state.";
  }
}

// Start game
async function startGame(withDifficulty = false) {
  try {
    isLoading.value = true;
    errorMsg.value = "";
    const newSessionId = resetSessionId(gameId);
    sessionId.value = newSessionId;

    let url = `/api/game/${gameId}/reset?session_id=${newSessionId}&player_name=${encodeURIComponent(props.playerName)}`;
    if (withDifficulty) {
      url += `&difficulty=${state.value.difficulty}`;
    }
    const res = await fetch(url);
    const data = await res.json();
    if (data.error) {
      errorMsg.value = data.error;
    } else {
      await fetchState();
    }
  } catch (e) {
    errorMsg.value = "Failed to start game.";
  } finally {
    isLoading.value = false;
  }
}

const DIFFICULTIES = [
  { value: "easy",   label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard",   label: "Hard" },
];

async function applyDifficulty(diff) {
  state.value.difficulty = diff;
  await startGame(true);
}

// Send action
async function sendAction(actionStr) {
  if (isWatchMode.value) return;
  if (!state.value.valid_actions.includes(actionStr)) {
    console.warn("Invalid action:", actionStr);
    return;
  }

  try {
    errorMsg.value = "";
    const res = await fetch(`/api/game/${gameId}/action?move=${encodeURIComponent(actionStr)}&session_id=${sessionId.value}`);
    const data = await res.json();
    if (data.error) {
      errorMsg.value = data.error;
    } else {
      state.value = data;
    }
  } catch (e) {
    errorMsg.value = "Failed to send action.";
  }
}

function handleCellClick(r, c) {
  if (state.value.game_over || isWatchMode.value) return;

  const currentCellState = state.value.cell_states[r][c];
  
  // If clicking with the same tool on an already marked cell, clear it
  if (currentTool.value === "erase" && currentCellState === -1) {
    sendAction(`clear_${r}_${c}`);
    return;
  }
  if (currentTool.value === "confirm" && currentCellState === 1) {
    sendAction(`clear_${r}_${c}`);
    return;
  }

  // Otherwise, apply the tool
  if (currentTool.value === "erase") {
    sendAction(`erase_${r}_${c}`);
  } else {
    sendAction(`confirm_${r}_${c}`);
  }
}

// Compute row and column sums for visual feedback
function getRowSum(r) {
  if (!state.value.cell_states || state.value.cell_states.length === 0) return 0;
  let sum = 0;
  for (let c = 0; c < state.value.cols; c++) {
    if (state.value.cell_states[r][c] === 1) {
      sum += state.value.grid[r][c];
    }
  }
  return sum;
}

function getColSum(c) {
  if (!state.value.cell_states || state.value.cell_states.length === 0) return 0;
  let sum = 0;
  for (let r = 0; r < state.value.rows; r++) {
    if (state.value.cell_states[r][c] === 1) {
      sum += state.value.grid[r][c];
    }
  }
  return sum;
}

// Polling for watch mode
function startPolling() {
  if (pollingInterval.value) return;
  pollingInterval.value = setInterval(() => {
    fetchState();
  }, 2000);
}

function stopPolling() {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
    pollingInterval.value = null;
  }
}

onMounted(async () => {
  const params = new URLSearchParams(window.location.search);
  const urlSessionId = params.get("session_id");

  if (urlSessionId) {
    isWatchMode.value = true;
    sessionId.value = urlSessionId;
    await fetchState();
    startPolling();
    isLoading.value = false;
  } else {
    const savedSession = getSessionId(gameId);
    if (savedSession) {
      sessionId.value = savedSession;
      await fetchState();
      isLoading.value = false;
    } else {
      await startGame(true);
    }
  }
});

onUnmounted(() => {
  stopPolling();
});
</script>

<template>
  <div class="wrapper">
    <div class="game-header">
      <div class="header-left">
        <GameGuide game-id="crossnumber" />
      </div>
      <div class="header-center">
        <div class="level-badge">{{ state.difficulty.toUpperCase() }}</div>
        <div class="level-title">Level {{ state.current_level }}</div>
        <div v-if="isWatchMode" class="watch-badge">👁️ Watch Mode</div>
      </div>
      <div class="header-right">
        <button v-if="!isWatchMode" class="icon-btn" @click="startGame" title="Restart Game">
          🔄
        </button>
      </div>
    </div>

    <!-- Difficulty selector -->
    <div class="difficulty-bar">
      <button
        v-for="d in DIFFICULTIES"
        :key="d.value"
        class="diff-btn"
        :class="{ active: state.difficulty === d.value }"
        :disabled="isWatchMode"
        @click="applyDifficulty(d.value)"
      >{{ d.label }}</button>
    </div>

    <div class="top-bar">
      <div class="stat-card">
        <span class="stat-label">Level</span>
        <span class="stat-value">{{ state.current_level }}/{{ state.max_level }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Score</span>
        <span class="stat-value">{{ state.score }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Lives</span>
        <div class="lives-board">
          <span v-for="n in 3" :key="n" class="heart" :class="{ lost: n > state.lives }">❤️</span>
        </div>
      </div>
    </div>

    <div v-if="errorMsg" class="error-msg">
      ⚠️ {{ errorMsg }}
    </div>

    <div v-if="isLoading" class="loading-state">
      Loading game...
    </div>

    <div v-else class="game-content">
      <div class="crossnumber-board-container">
        
        <!-- Top row: Empty corner + Col Targets -->
        <div class="grid-row top-targets">
          <div class="empty-corner"></div>
          <div 
            v-for="(target, c) in state.col_targets" 
            :key="'col-target-'+c"
            class="target-cell col-target"
            :class="{ 'target-met': getColSum(c) === target }"
          >
            {{ target }}
          </div>
        </div>

        <!-- Grid rows: Row Target + Cells -->
        <div 
          v-for="(row, r) in state.grid" 
          :key="'row-'+r"
          class="grid-row"
        >
          <!-- Row Target -->
          <div 
            class="target-cell row-target"
            :class="{ 'target-met': getRowSum(r) === state.row_targets[r] }"
          >
            {{ state.row_targets[r] }}
          </div>
          
          <!-- Cells -->
          <div 
            v-for="(val, c) in row" 
            :key="'cell-'+r+'-'+c"
            class="number-cell"
            :class="{
              'state-erased': state.cell_states[r][c] === -1,
              'state-confirmed': state.cell_states[r][c] === 1,
              'state-unknown': state.cell_states[r][c] === 0,
              'interactive': !state.game_over && !isWatchMode
            }"
            @click="handleCellClick(r, c)"
          >
            {{ val }}
          </div>
        </div>

      </div>

      <!-- Tools & Controls -->
      <div class="controls-panel" v-if="!isWatchMode">
        <div class="tool-toggle" :class="{ disabled: state.game_over }">
          <button 
            class="tool-btn erase-btn" 
            :class="{ active: currentTool === 'erase' }"
            @click="currentTool = 'erase'"
            :disabled="state.game_over"
          >
            ✏️ Erase
          </button>
          <button 
            class="tool-btn confirm-btn" 
            :class="{ active: currentTool === 'confirm' }"
            @click="currentTool = 'confirm'"
            :disabled="state.game_over"
          >
            ⭕ Confirm
          </button>
        </div>

        <div class="action-buttons">
          <button 
            class="action-btn undo-btn" 
            :disabled="!state.undo_available || state.game_over"
            @click="sendAction('undo')"
          >
            ↩️ Undo
          </button>
          <button 
            class="action-btn withdraw-btn" 
            :disabled="state.game_over"
            @click="sendAction('withdraw')"
          >
            🏳️ Give Up
          </button>
          <button 
            v-if="state.game_over && (state.won || state.withdrawn) && state.current_level < state.max_level"
            class="action-btn next-btn"
            @click="sendAction('next_level')"
          >
            Next Level ➡️
          </button>
        </div>
      </div>

      <!-- Status Banner -->
      <div v-if="state.won" class="status-banner success">
        🎉 Level Cleared!
      </div>
      <div v-else-if="state.lives <= 0" class="status-banner error">
        💔 Out of lives! Game Over.
      </div>
      <div v-else-if="state.withdrawn" class="status-banner error">
        🏳️ You gave up this level.
      </div>
    </div>

    <GameLog v-if="sessionId" :session-id="sessionId" :game-id="gameId" />
  </div>
</template>

<style scoped>
.wrapper {
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: center;
  width: 100%;
}

.game-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  margin-bottom: 16px;
}

.header-center {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.level-badge {
  background: #cbd5e1;
  color: #334155;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
  letter-spacing: 1px;
}

.level-title {
  font-size: 1.2rem;
  font-weight: 800;
  color: #8b5cf6;
}

.top-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  width: 100%;
  max-width: 600px;
  margin-bottom: 10px;
}

.stat-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.stat-label {
  font-size: 0.7rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: #f8fafc;
}

.lives-board {
  display: flex;
  gap: 4px;
  margin-right: 0px;
}

.heart {
  font-size: 1.2rem;
  transition: opacity 0.3s;
}

.heart.lost {
  opacity: 0.2;
  filter: grayscale(100%);
}

/* Difficulty */
.difficulty-bar {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: -10px;
  margin-bottom: 5px;
}
.diff-btn {
  padding: 5px 16px;
  border-radius: 20px;
  border: 1px solid #bdc3c7;
  background: transparent;
  color: #7f8c8d;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.15s;
}
.diff-btn:hover:not(:disabled) { border-color: #3498db; color: #3498db; }
.diff-btn.active {
  background: #3498db;
  border-color: #3498db;
  color: #fff;
  font-weight: 600;
}
.diff-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.score-board {
  display: flex;
  align-items: center;
  gap: 15px;
}

.score-board {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.score-label {
  font-size: 0.75rem;
  color: #7f8c8d;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.score-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #2c3e50;
}

.icon-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: background 0.2s;
}

.icon-btn:hover {
  background: #f1f2f6;
}

.error-msg {
  background: #fee2e2;
  color: #c0392b;
  padding: 12px;
  border-radius: 8px;
  font-size: 0.9rem;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: #7f8c8d;
}

.game-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 30px;
}

.crossnumber-board-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: #f8f9fa;
  padding: 20px;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.grid-row {
  display: flex;
  gap: 4px;
}

.top-targets {
  margin-bottom: 4px;
}

.empty-corner {
  width: 60px;
  height: 60px;
}

.target-cell {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  font-weight: 700;
  color: #34495e;
  background: #d6eaf8;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.target-cell.target-met {
  background: #a9dfbf;
  color: #21618c;
}

.number-cell {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 600;
  background: white;
  border: 2px solid #ecf0f1;
  border-radius: 8px;
  color: #2c3e50;
  transition: all 0.2s ease;
  user-select: none;
}

.number-cell.interactive {
  cursor: pointer;
}

.number-cell.interactive:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.number-cell.state-unknown {
  /* Default state */
}

.number-cell.state-confirmed {
  border-color: #34495e;
  border-width: 3px;
  border-radius: 50%;
  transform: scale(0.95);
  background: #fdfefe;
}

.number-cell.state-erased {
  opacity: 0.3;
  background: #ecf0f1;
  text-decoration: line-through;
}

.controls-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  width: 100%;
}

.tool-toggle {
  display: flex;
  background: #ecf0f1;
  padding: 4px;
  border-radius: 30px;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
}

.tool-toggle.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.tool-btn {
  padding: 10px 24px;
  border: none;
  background: transparent;
  border-radius: 26px;
  font-size: 1rem;
  font-weight: 600;
  color: #7f8c8d;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tool-btn.active {
  background: white;
  color: #2c3e50;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.action-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.undo-btn {
  background: #e0e0e0;
  color: #333;
}

.undo-btn:hover:not(:disabled) {
  background: #d5d5d5;
}

.withdraw-btn {
  background: #ffebee;
  color: #c62828;
}

.withdraw-btn:hover:not(:disabled) {
  background: #ffcdd2;
}

.next-btn {
  background: #27ae60;
  color: white;
}

.next-btn:hover:not(:disabled) {
  background: #2ecc71;
}

.status-banner {
  width: 100%;
  padding: 15px;
  border-radius: 8px;
  text-align: center;
  font-weight: bold;
  font-size: 1.1rem;
}

.status-banner.success {
  background: #d4edda;
  color: #155724;
}

.status-banner.error {
  background: #f8d7da;
  color: #721c24;
}

/* Responsive adjustments */
@media (max-width: 500px) {
  .empty-corner, .target-cell, .number-cell {
    width: 45px;
    height: 45px;
    font-size: 1.1rem;
  }
}
</style>
