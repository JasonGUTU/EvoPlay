<script setup>
import { ref, onMounted } from "vue";
import { getSessionId, addSessionToUrl, setSessionIdFromUrl } from "../utils/session.js";

const API = "/api/game/fourinarow";
const sessionId = ref(null);

const board = ref([]);
const gameOver = ref(false);
const won = ref(false);
const winner = ref(null);
const validActions = ref([]);
const lastBotCol = ref(null);
const error = ref("");
const hoverCol = ref(null);
const isThinking = ref(false);
const difficulty = ref("hard");

const ROWS = 6;
const COLS = 7;

const DIFFICULTIES = [
  { value: "easy",   label: "Easy",   desc: "Casual fun" },
  { value: "medium", label: "Medium", desc: "Some challenge" },
  { value: "hard",   label: "Hard",   desc: "Near-perfect" },
];

// ── API ───────────────────────────────────────────────────────────────

async function fetchState() {
  const urlSid = setSessionIdFromUrl("fourinarow");
  const sid = urlSid || getSessionId("fourinarow");
  sessionId.value = sid;
  const res = await fetch(addSessionToUrl(`${API}/state`, sid));
  applyState(await res.json());
}

async function dropPiece(col) {
  if (gameOver.value || isThinking.value) return;
  if (!validActions.value.includes(String(col))) return;
  isThinking.value = true;
  error.value = "";
  const sid = sessionId.value || getSessionId("fourinarow");
  const res = await fetch(addSessionToUrl(`${API}/action?move=${col}`, sid));
  const data = await res.json();
  if (data.error) error.value = data.error;
  applyState(data);
  isThinking.value = false;
}

async function resetGame(newDifficulty) {
  if (newDifficulty) difficulty.value = newDifficulty;
  error.value = "";
  lastBotCol.value = null;
  isThinking.value = false;
  const sid = sessionId.value || getSessionId("fourinarow");
  const res = await fetch(addSessionToUrl(`${API}/reset?difficulty=${difficulty.value}`, sid));
  applyState(await res.json());
}

function applyState(state) {
  if (state.session_id) sessionId.value = state.session_id;
  board.value = state.board || [];
  gameOver.value = state.game_over;
  won.value = state.won;
  winner.value = state.winner;
  validActions.value = state.valid_actions || [];
  if (state.difficulty) difficulty.value = state.difficulty;
  if (state.last_bot_col !== null && state.last_bot_col !== undefined) {
    lastBotCol.value = state.last_bot_col;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────

function discColor(val) {
  if (val === 1) return "#ef4444";  // human — red
  if (val === 2) return "#facc15";  // bot   — yellow
  return null;
}

function isBotLastCol(c) {
  return lastBotCol.value === c && !gameOver.value;
}

onMounted(fetchState);
</script>

<template>
  <div class="wrapper">

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

    <!-- Status -->
    <div class="status">
      <template v-if="gameOver">
        <span v-if="winner === 'human'" class="msg-win">You win! 🎉</span>
        <span v-else-if="winner === 'bot'" class="msg-lose">Bot wins! 🤖</span>
        <span v-else class="msg-draw">Draw!</span>
      </template>
      <span v-else-if="isThinking" class="msg-think">Bot is thinking…</span>
      <span v-else class="msg-turn">Your turn — click a column</span>
    </div>

    <!-- Drop arrows -->
    <div class="arrows">
      <div
        v-for="c in COLS"
        :key="c"
        class="arrow-cell"
        @click="dropPiece(c - 1)"
        @mouseenter="hoverCol = c - 1"
        @mouseleave="hoverCol = null"
      >
        <span
          v-if="hoverCol === c - 1 && !gameOver && !isThinking && validActions.includes(String(c - 1))"
          class="arrow"
        >▼</span>
      </div>
    </div>

    <!-- Board -->
    <div class="board">
      <div v-for="(row, r) in board" :key="r" class="row">
        <div
          v-for="(cell, c) in row"
          :key="c"
          class="cell"
          :class="{
            'cell-hover': hoverCol === c && !gameOver && !isThinking && validActions.includes(String(c)),
            'cell-bot-last': isBotLastCol(c),
          }"
          @click="dropPiece(c)"
          @mouseenter="hoverCol = c"
          @mouseleave="hoverCol = null"
        >
          <div
            class="disc"
            :class="{ filled: cell !== 0 }"
            :style="cell !== 0 ? { background: discColor(cell) } : {}"
          />
        </div>
      </div>
    </div>

    <!-- Controls -->
    <div class="controls">
      <button class="btn-reset" @click="resetGame()">New Game</button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <!-- Legend -->
    <div class="legend">
      <span><span class="dot red" /> You (Red)</span>
      <span><span class="dot yellow" /> Bot (Yellow)</span>
    </div>

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
  border: 1px solid #475569;
  background: transparent;
  color: #64748b;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.15s;
}
.diff-btn:hover {
  border-color: #94a3b8;
  color: #e2e8f0;
}
.diff-btn.active {
  background: #1d4ed8;
  border-color: #3b82f6;
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
.msg-draw  { color: #94a3b8; }
.msg-turn  { color: #e2e8f0; }
.msg-think { color: #facc15; }

/* Drop arrows row */
.arrows {
  display: flex;
  gap: 4px;
}
.arrow-cell {
  width: 52px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.arrow {
  color: #ef4444;
  font-size: 0.95rem;
}

/* Board */
.board {
  background: #1d4ed8;
  border-radius: 12px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}
.row {
  display: flex;
  gap: 4px;
}
.cell {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.1s;
}
.cell.cell-hover {
  background: #1e293b;
}
.cell.cell-bot-last {
  box-shadow: inset 0 0 0 3px rgba(251, 191, 36, 0.6);
}
.disc {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #0f172a;
  transition: background 0.12s;
}
.disc.filled {
  box-shadow: inset 0 -3px 6px rgba(0, 0, 0, 0.35);
}

/* Controls */
.controls {
  margin-top: 4px;
}
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

/* Legend */
.legend {
  display: flex;
  gap: 20px;
  font-size: 0.85rem;
  color: #94a3b8;
}
.dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}
.dot.red    { background: #ef4444; }
.dot.yellow { background: #facc15; }
</style>
