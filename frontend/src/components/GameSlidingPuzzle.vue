<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import { getSessionId, resetSessionId, addSessionToUrl, setSessionIdFromUrl } from "../utils/session.js";

defineProps({ playerName: { type: String, default: "" } });

const API = "/api/game/sliding_puzzle";
const sessionId = ref(null);

const board = ref([]);
const moves = ref(0);
const gameOver = ref(false);
const won = ref(false);
const validActions = ref([]);
const error = ref("");
const difficulty = ref("medium");
const isWatching = ref(false);
let pollTimer = null;

const DIFFICULTIES = [
  { value: "easy",   label: "Easy",   desc: "10 shuffles" },
  { value: "medium", label: "Medium", desc: "30 shuffles" },
  { value: "hard",   label: "Hard",   desc: "80 shuffles" },
];

// ── API ───────────────────────────────────────────────────────────────

async function fetchState() {
  const urlSid = setSessionIdFromUrl("sliding_puzzle");
  const sid = urlSid || getSessionId("sliding_puzzle");
  sessionId.value = sid;
  if (urlSid) { isWatching.value = true; startPolling(); }
  const res = await fetch(addSessionToUrl(`${API}/state`, sid));
  applyState(await res.json());
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(async () => {
    const sid = sessionId.value;
    if (!sid) return;
    const res = await fetch(addSessionToUrl(`${API}/state`, sid));
    applyState(await res.json());
    if (gameOver.value) stopPolling();
  }, 1000);
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function clickTile(r, c) {
  if (gameOver.value || isWatching.value) return;
  // Check if tile is adjacent to blank
  const br = blankPos.value[0];
  const bc = blankPos.value[1];
  const dr = Math.abs(r - br);
  const dc = Math.abs(c - bc);
  if (!((dr === 1 && dc === 0) || (dr === 0 && dc === 1))) return;

  error.value = "";
  const sid = sessionId.value || getSessionId("sliding_puzzle");
  const res = await fetch(addSessionToUrl(`${API}/action?move=${r}%20${c}`, sid));
  const data = await res.json();
  if (data.error) error.value = data.error;
  applyState(data);
}

async function resetGame(newDifficulty) {
  if (newDifficulty) difficulty.value = newDifficulty;
  error.value = "";
  const sid = resetSessionId("sliding_puzzle");
  sessionId.value = sid;
  const res = await fetch(addSessionToUrl(`${API}/reset?difficulty=${difficulty.value}`, sid));
  applyState(await res.json());
}

function applyState(state) {
  if (state.session_id) sessionId.value = state.session_id;
  board.value = state.board || [];
  moves.value = state.moves ?? 0;
  gameOver.value = state.game_over;
  won.value = state.won;
  validActions.value = state.valid_actions || [];
  if (state.difficulty) difficulty.value = state.difficulty;
}

// ── Helpers ───────────────────────────────────────────────────────────

const blankPos = computed(() => {
  for (let r = 0; r < board.value.length; r++) {
    for (let c = 0; c < (board.value[r]?.length || 0); c++) {
      if (board.value[r][c] === 0) return [r, c];
    }
  }
  return [2, 2];
});

function isAdjacent(r, c) {
  const br = blankPos.value[0];
  const bc = blankPos.value[1];
  const dr = Math.abs(r - br);
  const dc = Math.abs(c - bc);
  return (dr === 1 && dc === 0) || (dr === 0 && dc === 1);
}

function isCorrect(r, c, val) {
  if (val === 0) return true;
  return val === r * 3 + c + 1;
}

// Keyboard support
function onKeyDown(e) {
  if (gameOver.value || isWatching.value) return;
  const keyMap = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right" };
  const dir = keyMap[e.key];
  if (dir && validActions.value.includes(dir)) {
    e.preventDefault();
    const sid = sessionId.value || getSessionId("sliding_puzzle");
    fetch(addSessionToUrl(`${API}/action?move=${dir}`, sid))
      .then(res => res.json())
      .then(data => {
        if (data.error) error.value = data.error;
        applyState(data);
      });
  }
}

onMounted(() => {
  fetchState();
  window.addEventListener("keydown", onKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", onKeyDown);
  stopPolling();
});
</script>

<template>
  <div class="wrapper">
    <!-- Difficulty -->
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

    <!-- Status -->
    <div class="status-bar">
      <div class="moves-box">
        <span class="label">Moves</span>
        <span class="value">{{ moves }}</span>
      </div>
      <div v-if="won" class="result-win">Solved!</div>
      <div v-else-if="isWatching" class="result-watch">Watching...</div>
      <button class="btn-reset" @click="resetGame()">New Game</button>
    </div>

    <!-- Board -->
    <div class="board">
      <div v-for="(row, r) in board" :key="r" class="board-row">
        <div
          v-for="(cell, c) in row"
          :key="c"
          class="tile"
          :class="{
            'tile-blank': cell === 0,
            'tile-correct': cell !== 0 && isCorrect(r, c, cell) && !won,
            'tile-normal': cell !== 0 && !isCorrect(r, c, cell) && !won,
            'tile-clickable': cell !== 0 && isAdjacent(r, c) && !gameOver && !isWatching,
            'tile-won': cell !== 0 && won,
          }"
          @click="cell !== 0 && clickTile(r, c)"
        >
          <span v-if="cell !== 0" class="tile-num">{{ cell }}</span>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <p class="hint">Click a tile or use arrow keys</p>
  </div>
</template>

<style scoped>
.wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

/* Difficulty */
.difficulty-bar {
  display: flex;
  gap: 8px;
}
.diff-btn {
  padding: 5px 16px;
  border-radius: 20px;
  border: 1px solid #7c3aed;
  background: transparent;
  color: #a78bfa;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.15s;
}
.diff-btn:hover { border-color: #a78bfa; color: #e2e8f0; }
.diff-btn.active {
  background: #7c3aed;
  border-color: #8b5cf6;
  color: #fff;
  font-weight: 600;
}

/* Status */
.status-bar {
  display: flex;
  align-items: center;
  gap: 16px;
}
.moves-box {
  background: #1e293b;
  border-radius: 10px;
  padding: 8px 20px;
  text-align: center;
}
.moves-box .label {
  display: block;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #64748b;
}
.moves-box .value {
  display: block;
  font-size: 1.4rem;
  font-weight: 700;
  color: #e2e8f0;
}
.result-win {
  font-size: 1.1rem;
  font-weight: 700;
  color: #4ade80;
}
.result-watch {
  font-size: 0.9rem;
  color: #38bdf8;
}
.btn-reset {
  padding: 8px 20px;
  background: #334155;
  border: 1px solid #475569;
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-reset:hover { background: #475569; }

/* Board */
.board {
  background: #581c87;
  border-radius: 12px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}
.board-row {
  display: flex;
  gap: 6px;
}
.tile {
  width: 90px;
  height: 90px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 2rem;
  color: #334155;
  background: #e2e8f0;
  box-shadow: inset 0 -4px 0 rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.15);
  transition: transform 0.15s, background 0.15s;
  user-select: none;
  position: relative;
}
.tile-num {
  text-shadow: 0 1px 2px rgba(0,0,0,0.1);
}
.tile-blank {
  background: #475569;
  box-shadow: inset 0 4px 8px rgba(0,0,0,0.3);
}
.tile-normal {
  background: #e2e8f0;
  color: #334155;
}
.tile-correct {
  background: #f59e0b;
  color: #fff;
}
.tile-clickable {
  cursor: pointer;
}
.tile-clickable:hover {
  transform: scale(1.05);
  filter: brightness(1.1);
}
.tile-won {
  background: #4ade80 !important;
  color: #fff !important;
}

.error-msg {
  color: #f87171;
  font-size: 0.85rem;
}

.hint {
  font-size: 0.85rem;
  color: #64748b;
}
</style>
