<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import GameLog from "./GameLog.vue";
import { getSessionId, resetSessionId, addSessionToUrl, setSessionIdFromUrl } from "../utils/session.js";

defineProps({ playerName: { type: String, default: "" } });

const API = "/api/game/nuts_bolts";
const logRef = ref(null);
const sessionId = ref(null);

const board = ref([]);
const score = ref(0);
const gameOver = ref(false);
const won = ref(false);
const validActions = ref([]);
const undosRemaining = ref(0);
const selectedScrew = ref(null);
const currentLevel = ref(1);
const maxLevel = ref(1);
const screwCapacity = ref(3);
const error = ref("");
const lastAction = ref("");

// ── API helpers ────────────────────────────────────────────────────

async function fetchState() {
  const urlSessionId = setSessionIdFromUrl("nuts_bolts");
  const sid = urlSessionId || getSessionId("nuts_bolts");
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

async function sendAction(actionStr) {
  lastAction.value = actionStr;
  error.value = "";
  const sid = sessionId.value || getSessionId("nuts_bolts");
  const url = addSessionToUrl(`${API}/action?move=${actionStr}`, sid);
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
  // Use current session ID to reset current level instead of creating a new session (which would drop to level 1)
  const sid = sessionId.value || getSessionId("nuts_bolts");
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
  undosRemaining.value = state.undos_remaining || 0;
  selectedScrew.value = state.selected_screw;
  currentLevel.value = state.current_level || 1;
  maxLevel.value = state.max_level || 1;
  screwCapacity.value = state.screw_capacity || 3;
  
  if (state.game_over) {
    stopPolling();
  } else {
    startPolling();
  }
}

// ── Interaction Logic ──────────────────────────────────────────────

const localSelected = ref(null);

function handleScrewClick(index) {
  if (gameOver.value) return;

  if (localSelected.value === null) {
    // First click: select source screw (only if it has moves as source)
    const hasMove = validActions.value.some(a => a.startsWith(`move_${index}_`));
    if (hasMove) {
      localSelected.value = index;
    }
  } else if (localSelected.value === index) {
    // Click same screw: deselect
    localSelected.value = null;
  } else {
    // Second click: try move from localSelected to index
    const action = `move_${localSelected.value}_${index}`;
    if (validActions.value.includes(action)) {
      sendAction(action);
    }
    localSelected.value = null;
  }
}

function handleUndo() {
  if (canUndo.value) {
    sendAction("undo");
  }
}

const canUndo = computed(() => {
  return validActions.value.includes("undo");
});

// Polling interval to check for state changes
let pollingInterval = null;
const POLLING_INTERVAL_MS = 1000; 

function startPolling() {
  if (!pollingInterval && !gameOver.value) {
    pollingInterval = setInterval(async () => {
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
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});

// ── Visual Helpers ─────────────────────────────────────────────────

const SECREWS_CAPACITY = 4;

const colorMap = {
  'r': '#ef4444', // red
  'y': '#f59e0b', // yellow
  'b': '#3b82f6', // blue
  'g': '#22c55e', // green
  'o': '#f97316', // orange
  'p': '#ec4899', // pink
  'c': '#06b6d4', // cyan
  'v': '#7c3aed', // deep purple (violet-700)
  'm': '#d946ef', // pinkish purple (fuchsia-500)
  'n': '#a97142', // brown/bronze
  's': '#94a3b8', // silver
  't': '#0d9488', // teal (blueish green)
  'k': '#15803d', // dark green (green-700)
  'd': '#d4b996', // sand/beige
  'l': '#84cc16'  // lime
};

const screwContainerStyle = computed(() => {
  if (screwCapacity.value >= 8) {
    return { height: '300px' };
  }
  if (screwCapacity.value >= 6) {
    return { height: '240px' };
  }
  return {};
});

const screwPegStyle = computed(() => {
  if (screwCapacity.value >= 8) {
    return { height: '260px' };
  }
  if (screwCapacity.value >= 6) {
    return { height: '200px' };
  }
  return {};
});

const nutsStackStyle = computed(() => {
  if (screwCapacity.value >= 8) {
    return { height: '260px' };
  }
  if (screwCapacity.value >= 6) {
    return { height: '200px' };
  }
  return {};
});

function nutStyle(color, isTop, isSelectedScrew) {
  return {
    backgroundColor: colorMap[color] || '#cbd5e1',
    // Subtly highlight the top nut of the selected screw
    transform: isTop && isSelectedScrew ? 'translateY(-8px) scale(1.05)' : 'none',
    boxShadow: isTop && isSelectedScrew ? '0 4px 12px rgba(0,0,0,0.3)' : 'inset 0 -3px 0 rgba(0,0,0,0.2)',
    zIndex: isTop && isSelectedScrew ? 10 : 1
  };
}
</script>

<template>
  <div class="game-nuts-bolts">
    
    <div class="level-indicator">
      <h3>Level {{ currentLevel }}</h3>
    </div>

    <!-- Info bar -->
    <div class="info-bar">
      <div class="score-box">
        <span class="label">Score</span>
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
          class="undo-btn" 
          :disabled="!canUndo" 
          @click="handleUndo"
          :title="`Undos remaining: ${undosRemaining}`"
        >
          Undo ({{ undosRemaining }})
        </button>
        <button class="reset-btn" @click="resetGame">Restart</button>
      </div>
    </div>

    <!-- Status Messages -->
    <div v-if="won" class="banner won">You Won!</div>
    <div v-if="gameOver && !won" class="banner over">Game Over</div>
    <div v-if="error" class="banner error">{{ error }}</div>

    <!-- Game Board -->
    <div class="board-container">
      <div 
        class="screws-grid" 
        :style="{ maxWidth: currentLevel >= 10 ? '370px' : (currentLevel >= 9 ? '540px' : (currentLevel === 8 ? '540px' : (currentLevel >= 7 ? '440px' : (currentLevel === 6 ? '540px' : (currentLevel === 5 ? '440px' : (currentLevel === 4 ? '340px' : '280px')))))) }"
      >
        <!-- Loop over each screw -->
        <div 
          v-for="(screw, idx) in board" 
          :key="idx" 
          class="screw-container"
          :class="{
            'is-selected': localSelected === idx,
            'is-valid-target': localSelected !== null && localSelected !== idx && validActions.includes(`move_${localSelected}_${idx}`)
          }"
          :style="screwContainerStyle"
          @click="handleScrewClick(idx)"
        >
          <!-- Base/Platform -->
          <div class="screw-base"></div>
          
          <!-- The visual screw peg -->
          <div class="screw-peg" :style="screwPegStyle"></div>
          
          <!-- Nuts stacked from bottom to top -->
          <div class="nuts-stack" :style="nutsStackStyle">
            <!-- Empty spacers if capacity is not met, so nuts always sit at bottom -->
            <div 
              v-for="emptySlot in (screwCapacity - screw.length)" 
              :key="'empty-'+emptySlot" 
              class="nut-slot empty"
            ></div>
            
            <!-- Actual Nuts (reversed visually if we build CSS top-down, or flex column reverse) -->
            <!-- We'll use flex column reverse in CSS so index 0 is at bottom -->
            <div class="actual-nuts">
              <div 
                v-for="(color, nutIdx) in screw" 
                :key="'nut-'+idx+'-'+nutIdx" 
                class="nut"
                :style="nutStyle(color, nutIdx === screw.length - 1, localSelected === idx)"
              >
                <!-- Optional: add visual ridges to nuts -->
                <div class="nut-ridge"></div>
                <div class="nut-ridge"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="instructions">
      <p>Tap a screw to select the top nut, then tap another screw to move it.</p>
      <p>Nuts must be moved onto matching colors or empty screws.</p>
    </div>

    <!-- Log -->
    <GameLog ref="logRef" game-name="nuts_bolts" :session-id="sessionId" />
  </div>
</template>

<style scoped>
.info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.score-box {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.score-box .label {
  font-size: 0.75rem;
  color: #94a3b8;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.score-box .value {
  font-size: 1.5rem;
  color: #f8fafc;
  font-weight: 700;
}

.actions {
  display: flex;
  gap: 12px;
}

button {
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid transparent;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
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

.undo-btn {
  background: #334155;
  color: #f1f5f9;
}

.undo-btn:hover:not(:disabled) {
  background: #475569;
}

.undo-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reset-btn {
  background: #ef4444;
  color: white;
}

.reset-btn:hover {
  background: #dc2626;
}

.banner {
  text-align: center;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-weight: 700;
  font-size: 1.1rem;
  animation: popIn 0.3s ease-out;
}

@keyframes popIn {
  0% { transform: scale(0.9); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
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

.banner.error {
  background: #ef4444;
  color: white;
}

/* Board Layout */
.board-container {
  background: #0f172a;
  border-radius: 12px;
  padding: 24px 16px;
  margin-bottom: 24px;
}

.screws-grid {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 20px;
  /* Dynamically adjust max-width in JS or just allow wrapping */
  /* max-width: 280px; -> moved to inline style */
  margin: 0 auto;
}

/* Individual Screw */
.screw-container {
  position: relative;
  width: 70px;
  height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  cursor: pointer;
  border-radius: 8px;
  transition: background-color 0.2s;
  padding-bottom: 10px;
}

.screw-container:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.screw-container.is-selected {
  background-color: rgba(147, 197, 253, 0.1);
}

.screw-container.is-valid-target {
  background-color: rgba(16, 185, 129, 0.1);
}

/* Background Peg */
.screw-peg {
  position: absolute;
  bottom: 20px;
  width: 20px;
  height: 140px;
  border-radius: 10px 10px 0 0;
  z-index: 0;
  /* Add subtle thread texture and match base color */
  background-image: repeating-linear-gradient(
    170deg,
    transparent,
    transparent 8px,
    rgba(0,0,0,0.1) 8px,
    rgba(0,0,0,0.1) 10px
  ), linear-gradient(180deg, #cbd5e1 0%, #94a3b8 100%);
}

/* Base */
.screw-base {
  position: absolute;
  bottom: 0;
  width: 60px;
  height: 20px;
  background: linear-gradient(180deg, #cbd5e1 0%, #94a3b8 100%);
  border-radius: 50%;
  z-index: 1;
  box-shadow: 0 4px 6px rgba(0,0,0,0.5);
}

/* Nuts Stack Container */
.nuts-stack {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 140px; /* matches peg height roughly */
  display: flex;
  flex-direction: column-reverse; /* Bottom nut is first in DOM */
  align-items: center;
  justify-content: flex-start; /* Because of column-reverse, this aligns to bottom */
  padding-bottom: 5px; /* sit slightly above base center */
}

.actual-nuts {
  display: flex;
  flex-direction: column-reverse; /* Keep visually stacked correctly */
  width: 100%;
  align-items: center;
}

/* Visual Nut */
.nut {
  width: 56px;
  height: 28px;
  border-radius: 6px;
  margin-bottom: 2px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: inset 0 -3px 0 rgba(0,0,0,0.2), 0 2px 4px rgba(0,0,0,0.3);
}

/* Nut details (hexagonal illusion) */
.nut-ridge {
  width: 2px;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.2);
}

.instructions {
  text-align: center;
  color: #94a3b8;
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 20px;
}
</style>
