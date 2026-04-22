<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { getSessionId, addSessionToUrl, setSessionIdFromUrl, tryResume } from "../utils/session.js";
import GameGuide from "./GameGuide.vue";

defineProps({ playerName: { type: String, default: "" } });

const guideTitle = "How to Play Circle the Cat";
const guideSections = [
  { label: "Goal", text: "Trap the cat by placing walls so it cannot escape the board." },
  { label: "Controls", text: "Click any empty interior cell to place a wall. The cat will then make its move." },
  { label: "Rules", text: "You and the cat take turns. If the cat reaches the boundary, you lose. If the cat has no path to the boundary, you win!" },
];

const API = "/api/game/circlecat";
const sessionId = ref(null);

const board = ref([]);
const gameOver = ref(false);
const won = ref(false);
const score = ref(0);
const catPos = ref([5, 5]);
const validActions = ref([]);
const error = ref("");
const agentError = ref("");
const isThinking = ref(false);
const difficulty = ref("hard");
const isWatching = ref(false);
let pollTimer = null;

const DIFFICULTIES = [
  { value: "hard", label: "Hard", desc: "Smart cat (BFS pathfinding)" },
];

// ── API ───────────────────────────────────────────────────────────────

async function fetchState() {
  const urlSid = setSessionIdFromUrl("circlecat");
  const sid = urlSid || getSessionId("circlecat");
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
    const data = await res.json();
    applyState(data);
    if (data.game_over) stopPolling();
  }, 1000);
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function placeWall(r, c) {
  if (gameOver.value || isThinking.value || isWatching.value) return;
  if (!validActions.value.includes(`${r} ${c}`)) return;
  isThinking.value = true;
  error.value = "";
  const sid = sessionId.value || getSessionId("circlecat");
  const res = await fetch(addSessionToUrl(`${API}/action?move=${r}%20${c}`, sid));
  const data = await res.json();
  if (data.error) { error.value = data.error; isThinking.value = false; return; }
  applyState(data);
  isThinking.value = false;
}

async function resetGame(newDifficulty) {
  if (newDifficulty) difficulty.value = newDifficulty;
  error.value = "";
  isThinking.value = false;
  const sid = sessionId.value || getSessionId("circlecat");
  const res = await fetch(addSessionToUrl(`${API}/reset?difficulty=${difficulty.value}`, sid));
  applyState(await res.json());
}

function applyState(state) {
  if (state.session_id) sessionId.value = state.session_id;
  board.value = state.board || [];
  gameOver.value = state.game_over;
  won.value = state.won;
  score.value = state.score;
  catPos.value = state.cat_pos || [5, 5];
  validActions.value = state.valid_actions || [];
  if (state.difficulty) difficulty.value = state.difficulty;
  agentError.value = state.agent_error || "";
}

// ── Helpers ───────────────────────────────────────────────────────────

function cellClass(r, c) {
  const cell = board.value[r]?.[c];
  if (cell === "1") return "cell-wall";
  if (cell === "C") return "cell-cat";
  // No exit cells in visible board — outer ring is hidden
  if (validActions.value.includes(`${r} ${c}`)) return "cell-empty cell-clickable";
  return "cell-empty";
}

function isClickable(r, c) {
  return !gameOver.value && !isThinking.value && !isWatching.value && validActions.value.includes(`${r} ${c}`);
}

function rowOffset(r) {
  // Odd rows shift left in hex layout
  return r % 2 === 1;
}

onMounted(async () => {
  const urlSid = setSessionIdFromUrl("circlecat");
  if (!urlSid) {
    const resumed = await tryResume("circlecat");
    if (resumed) {
      sessionId.value = resumed.session_id;
      applyState(resumed);
      return;
    }
  }
  fetchState();
});
onUnmounted(stopPolling);
</script>

<template>
  <div class="wrapper">
    <GameGuide :title="guideTitle" :sections="guideSections" />

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
    <div class="status">
      <template v-if="gameOver">
        <span v-if="won" class="msg-win">You trapped the cat!</span>
        <span v-else class="msg-lose">The cat escaped!</span>
      </template>
      <span v-else-if="isThinking" class="msg-think">Cat is moving...</span>
      <span v-else class="msg-turn">Click an empty cell to place a wall</span>
    </div>

    <!-- Hex Board -->
    <div class="hex-board">
      <div
        v-for="(row, r) in board"
        :key="r"
        class="hex-row"
        :class="{ 'hex-row-offset': rowOffset(r) }"
      >
        <div
          v-for="(cell, c) in row"
          :key="c"
          class="hex-cell"
          :class="cellClass(r, c)"
          @click="isClickable(r, c) && placeWall(r, c)"
          :title="`(${r}, ${c})`"
        >
          <span v-if="cell === 'C'" class="cat-icon">🐱</span>
          <span v-else-if="cell === '1'" class="wall-icon"></span>
          <!-- boundary exits don't need a label -->
        </div>
      </div>
    </div>

    <!-- Controls -->
    <div class="controls">
      <button class="btn-reset" @click="resetGame()">New Game</button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="agentError" class="agent-error">Agent Error: {{ agentError }}</div>

    <!-- Legend -->
    <div class="legend">
      <span class="legend-item"><span class="swatch swatch-empty"></span> Empty</span>
      <span class="legend-item"><span class="swatch swatch-wall"></span> Wall</span>
      <span class="legend-item"><span class="swatch swatch-cat"></span> Cat</span>
    </div>
  </div>
</template>

<style scoped>
.wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}

/* Difficulty */
.difficulty-bar { display: flex; gap: 8px; }
.diff-btn {
  padding: 5px 16px;
  border-radius: 20px;
  border: 1px solid #475569;
  background: transparent;
  color: #64748b;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.15s;
}
.diff-btn:hover { border-color: #94a3b8; color: #e2e8f0; }
.diff-btn.active {
  background: #7c3aed;
  border-color: #a78bfa;
  color: #fff;
  font-weight: 600;
}

/* Status */
.status {
  font-size: 1.05rem;
  font-weight: 600;
  min-height: 28px;
  text-align: center;
}
.msg-win   { color: #4ade80; }
.msg-lose  { color: #f87171; }
.msg-turn  { color: #e2e8f0; }
.msg-think { color: #a78bfa; }

/* Hex Board */
.hex-board {
  display: flex;
  flex-direction: column;
  background: #1e293b;
  padding: 14px 12px 14px 8px;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  overflow: hidden;
}

.hex-row {
  display: flex;
  gap: 3px;
  margin-top: 1px;
  padding-left: 0;
}

.hex-row:first-child {
  margin-top: 0;
}

.hex-row-offset {
  padding-left: 17px;
}

.hex-cell {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  transition: all 0.15s;
  user-select: none;
  border: 2px solid transparent;
}

/* Cell types */
.cell-empty {
  background: #334155;
  border-color: #475569;
}

.cell-clickable {
  cursor: pointer;
}

.cell-clickable:hover {
  background: #6366f1;
  border-color: #818cf8;
  transform: scale(1.1);
}

.cell-wall {
  background: #7c3aed;
  border-color: #a78bfa;
}

.cell-cat {
  background: #fbbf24;
  border-color: #f59e0b;
}

.cell-exit {
  background: #166534;
  border-color: #4ade80;
}

.cat-icon {
  font-size: 1.1rem;
  line-height: 1;
}

.wall-icon {
  display: block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: #cbd5e1;
}

.exit-icon {
  color: #86efac;
  font-size: 0.7rem;
  font-weight: 700;
}

/* Controls */
.controls { margin-top: 4px; }
.btn-reset {
  padding: 8px 24px;
  background: #334155;
  border: 1px solid #475569;
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-reset:hover { background: #475569; }

.error {
  color: #f87171;
  font-size: 0.85rem;
}

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

/* Legend */
.legend {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 0.8rem;
  color: #94a3b8;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid #475569;
}

.swatch-empty { background: #334155; }
.swatch-wall  { background: #7c3aed; }
.swatch-cat   { background: #fbbf24; }
.swatch-exit  { background: #166534; }
</style>
