<script setup>
import { ref, onMounted } from "vue";
import { getSessionId, addSessionToUrl, setSessionIdFromUrl } from "../utils/session.js";

const API = "/api/game/tictactoe";
const sessionId = ref(null);

const board = ref([]);
const gameOver = ref(false);
const won = ref(false);
const winner = ref(null);
const winningLine = ref(null);
const lastBotMove = ref(null);
const validActions = ref([]);
const error = ref("");
const isThinking = ref(false);
const difficulty = ref("hard");

const DIFFICULTIES = [
  { value: "easy",   label: "Easy",   desc: "Random moves" },
  { value: "medium", label: "Medium", desc: "Wins & blocks" },
  { value: "hard",   label: "Hard",   desc: "Perfect play" },
];

// ── API ───────────────────────────────────────────────────────────────

async function fetchState() {
  const urlSid = setSessionIdFromUrl("tictactoe");
  const sid = urlSid || getSessionId("tictactoe");
  sessionId.value = sid;
  const res = await fetch(addSessionToUrl(`${API}/state`, sid));
  applyState(await res.json());
}

async function placeMark(r, c) {
  if (gameOver.value || isThinking.value) return;
  if (!validActions.value.includes(`${r} ${c}`)) return;
  isThinking.value = true;
  error.value = "";
  const sid = sessionId.value || getSessionId("tictactoe");

  // Phase 1: human move
  const res1 = await fetch(addSessionToUrl(`${API}/action?move=${r}%20${c}`, sid));
  const data1 = await res1.json();
  if (data1.error) { error.value = data1.error; isThinking.value = false; return; }
  applyState(data1);

  if (!data1.bot_pending) { isThinking.value = false; return; }

  // Phase 2: bot move after short pause
  await new Promise(resolve => setTimeout(resolve, 450));
  const res2 = await fetch(addSessionToUrl(`${API}/bot_move`, sid));
  const data2 = await res2.json();
  applyState(data2);
  isThinking.value = false;
}

async function resetGame(newDifficulty) {
  if (newDifficulty) difficulty.value = newDifficulty;
  error.value = "";
  isThinking.value = false;
  const sid = sessionId.value || getSessionId("tictactoe");
  const res = await fetch(addSessionToUrl(`${API}/reset?difficulty=${difficulty.value}`, sid));
  applyState(await res.json());
}

function applyState(state) {
  if (state.session_id) sessionId.value = state.session_id;
  board.value = state.board || [];
  gameOver.value = state.game_over;
  won.value = state.won;
  winner.value = state.winner;
  winningLine.value = state.winning_line || null;
  lastBotMove.value = state.last_bot_move || null;
  validActions.value = state.valid_actions || [];
  if (state.difficulty) difficulty.value = state.difficulty;
}

// ── Helpers ───────────────────────────────────────────────────────────

function isWinningCell(r, c) {
  return winningLine.value?.some(([wr, wc]) => wr === r && wc === c);
}

function isBotLastMove(r, c) {
  return lastBotMove.value && lastBotMove.value[0] === r && lastBotMove.value[1] === c && !gameOver.value;
}

function isClickable(r, c) {
  return !gameOver.value && !isThinking.value && validActions.value.includes(`${r} ${c}`);
}

onMounted(fetchState);
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
    <div class="status">
      <template v-if="gameOver">
        <span v-if="winner === 'human'" class="msg-win">You win! 🎉</span>
        <span v-else-if="winner === 'bot'" class="msg-lose">Bot wins!</span>
        <span v-else class="msg-draw">Draw!</span>
      </template>
      <span v-else-if="isThinking" class="msg-think">Bot is thinking…</span>
      <span v-else class="msg-turn">Your turn — place an X</span>
    </div>

    <!-- Board -->
    <div class="board">
      <div v-for="(row, r) in board" :key="r" class="board-row">
        <div
          v-for="(cell, c) in row"
          :key="c"
          class="cell"
          :class="{
            'cell-clickable': isClickable(r, c),
            'cell-winning': isWinningCell(r, c),
            'cell-bot-last': isBotLastMove(r, c),
          }"
          @click="placeMark(r, c)"
        >
          <span v-if="cell === 1" class="mark x">X</span>
          <span v-else-if="cell === 2" class="mark o">O</span>
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
      <span class="mark x" style="font-size:1rem">X</span> You &nbsp;
      <span class="mark o" style="font-size:1rem">O</span> Bot
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
.msg-draw  { color: #94a3b8; }
.msg-turn  { color: #e2e8f0; }
.msg-think { color: #a78bfa; }

/* Board */
.board {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: #1e293b;
  padding: 12px;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
.board-row { display: flex; gap: 6px; }

.cell {
  width: 100px;
  height: 100px;
  background: #0f172a;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, box-shadow 0.15s;
  position: relative;
}
.cell.cell-clickable {
  cursor: pointer;
}
.cell.cell-clickable:hover {
  background: #1e293b;
}
.cell.cell-winning {
  background: #1e1b4b;
  box-shadow: inset 0 0 0 2px #a78bfa;
}
.cell.cell-bot-last {
  box-shadow: inset 0 0 0 2px rgba(251, 191, 36, 0.5);
}

/* Marks */
.mark {
  font-size: 3rem;
  font-weight: 900;
  line-height: 1;
  user-select: none;
}
.mark.x { color: #ef4444; }
.mark.o { color: #facc15; }

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

/* Legend */
.legend {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: #94a3b8;
}
</style>
