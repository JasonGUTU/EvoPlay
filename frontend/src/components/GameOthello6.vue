<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import { getSessionId, addSessionToUrl, setSessionIdFromUrl } from "../utils/session.js";

defineProps({ playerName: { type: String, default: "" } });

const API = "/api/game/othello6";
const sessionId = ref(null);

const board = ref([]);
const gameOver = ref(false);
const won = ref(false);
const winner = ref(null);
const validMoves = ref([]);   // [[r,c], ...]
const validActions = ref([]);
const humanCount = ref(2);
const botCount = ref(2);
const error = ref("");
const agentError = ref("");
const passMessage = ref("");
const hoverCell = ref(null);   // [r, c]
const isThinking = ref(false);
const difficulty = ref("hard");
const isWatching = ref(false);
const animCells = ref(new Set());
const newCells = ref(new Set());
let pollTimer = null;

const SIZE = 6;

const DIFFICULTIES = [
  { value: "easy",   label: "Easy",   desc: "Random moves" },
  { value: "medium", label: "Medium", desc: "Positional strategy" },
  { value: "hard",   label: "Hard",   desc: "Positional + mobility" },
];

// ── API ───────────────────────────────────────────────────────────────

async function fetchState() {
  const urlSid = setSessionIdFromUrl("othello6");
  const sid = urlSid || getSessionId("othello6");
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

async function placeDisc(r, c) {
  if (gameOver.value || isThinking.value || isWatching.value) return;
  if (!isValidMove(r, c)) return;
  isThinking.value = true;
  error.value = "";
  const sid = sessionId.value || getSessionId("othello6");

  // Phase 1: human move
  const res1 = await fetch(addSessionToUrl(`${API}/action?move=${r}%20${c}`, sid));
  const data1 = await res1.json();
  if (data1.error) { error.value = data1.error; isThinking.value = false; return; }
  applyState(data1);

  if (!data1.bot_pending) { isThinking.value = false; return; }

  // Phase 2: bot moves (may loop if human has to pass multiple times)
  await botMoveLoop(sid);
  isThinking.value = false;
}

async function resetGame(newDifficulty) {
  if (newDifficulty) difficulty.value = newDifficulty;
  error.value = "";
  hoverCell.value = null;
  isThinking.value = false;
  const sid = sessionId.value || getSessionId("othello6");
  const res = await fetch(addSessionToUrl(`${API}/reset?difficulty=${difficulty.value}`, sid));
  applyState(await res.json());
}

function applyState(state) {
  if (state.session_id) sessionId.value = state.session_id;
  const newBoard = state.board || [];
  const oldBoard = board.value;

  const flipped = new Set();
  const placed = new Set();
  if (oldBoard.length === newBoard.length && oldBoard.length > 0) {
    for (let r = 0; r < SIZE; r++) {
      for (let c = 0; c < SIZE; c++) {
        const o = oldBoard[r][c];
        const n = newBoard[r][c];
        if (o !== n) {
          const key = `${r},${c}`;
          if (o !== 0 && n !== 0) {
            flipped.add(key);
          } else if (o === 0 && n !== 0) {
            placed.add(key);
          }
        }
      }
    }
  }
  animCells.value = flipped;
  newCells.value = placed;
  if (flipped.size > 0 || placed.size > 0) {
    setTimeout(() => { animCells.value = new Set(); newCells.value = new Set(); }, 500);
  }

  board.value = newBoard;
  gameOver.value = state.game_over;
  won.value = state.won;
  winner.value = state.winner;
  validMoves.value = state.valid_moves || [];
  validActions.value = state.valid_actions || [];
  humanCount.value = state.human_count ?? 2;
  botCount.value = state.bot_count ?? 2;
  if (state.difficulty) difficulty.value = state.difficulty;
  agentError.value = state.agent_error || "";

  // Auto-pass when human has no valid moves but game isn't over
  if (!state.game_over && !isWatching.value && !isThinking.value
      && validActions.value.length === 1 && validActions.value[0] === "pass") {
    setTimeout(() => autoPass(), 600);
  }
}

async function autoPass() {
  if (gameOver.value || isThinking.value) return;
  isThinking.value = true;

  // Show pass message
  passMessage.value = "You have no valid moves — pass!";

  const sid = sessionId.value || getSessionId("othello6");

  // Wait so user can read the message
  await new Promise(resolve => setTimeout(resolve, 800));

  // Send pass action
  const res1 = await fetch(addSessionToUrl(`${API}/action?move=pass`, sid));
  const data1 = await res1.json();
  applyState(data1);

  passMessage.value = "";

  if (!data1.bot_pending) { isThinking.value = false; return; }

  // Bot may need to play multiple turns if human keeps having no moves
  await botMoveLoop(sid);
  isThinking.value = false;
}

async function botMoveLoop(sid) {
  // Keep letting bot play as long as it has pending moves
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 500));

    const res = await fetch(addSessionToUrl(`${API}/bot_move`, sid));
    const data = await res.json();
    applyState(data);

    // Wait for flip animation to complete
    await new Promise(resolve => setTimeout(resolve, 600));

    if (data.game_over) break;

    // Check if human still needs to pass
    if (validActions.value.length === 1 && validActions.value[0] === "pass") {
      passMessage.value = "You have no valid moves — pass!";
      await new Promise(resolve => setTimeout(resolve, 800));

      const passRes = await fetch(addSessionToUrl(`${API}/action?move=pass`, sid));
      const passData = await passRes.json();
      applyState(passData);
      passMessage.value = "";

      if (!passData.bot_pending) break;
      // Continue loop — bot plays again
    } else {
      // Human has moves, stop the loop
      break;
    }
  }
}

// ── Helpers ───────────────────────────────────────────────────────────

function isValidMove(r, c) {
  return validMoves.value.some(([vr, vc]) => vr === r && vc === c);
}

function isHovered(r, c) {
  return hoverCell.value && hoverCell.value[0] === r && hoverCell.value[1] === c;
}

function cellClass(r, c, cell) {
  const valid = isValidMove(r, c);
  const hovered = isHovered(r, c);
  return {
    'cell-valid': valid && !gameOver.value && !isThinking.value,
    'cell-hovered': hovered && valid && !gameOver.value && !isThinking.value,
    'cell-clickable': valid && !gameOver.value && !isThinking.value,
  };
}

onMounted(fetchState);
onUnmounted(stopPolling);
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

    <!-- Scoreboard -->
    <div class="scoreboard">
      <div class="score-side you">
        <div class="disc-icon black" />
        <div class="score-label">YOU</div>
        <div class="score-num">{{ humanCount }}</div>
      </div>
      <div class="score-vs">
        <template v-if="gameOver">
          <span v-if="winner === 'human'" class="result-win">You Win!</span>
          <span v-else-if="winner === 'bot'" class="result-lose">Bot Wins</span>
          <span v-else class="result-draw">Draw</span>
        </template>
        <template v-else-if="isThinking">
          <span class="vs-thinking">…</span>
        </template>
        <template v-else>
          <span class="vs-text">VS</span>
        </template>
      </div>
      <div class="score-side bot">
        <div class="disc-icon white" />
        <div class="score-label">BOT</div>
        <div class="score-num">{{ botCount }}</div>
      </div>
    </div>

    <!-- Board -->
    <div class="board">
      <div v-for="(row, r) in board" :key="r" class="board-row">
        <div
          v-for="(cell, c) in row"
          :key="c"
          class="cell"
          :class="cellClass(r, c, cell)"
          @click="placeDisc(r, c)"
          @mouseenter="hoverCell = [r, c]"
          @mouseleave="hoverCell = null"
        >
          <div
            v-if="cell !== 0"
            class="disc"
            :class="[
              cell === 1 ? 'black' : 'white',
              animCells.has(`${r},${c}`) ? 'disc-flip' : '',
              newCells.has(`${r},${c}`) ? 'disc-pop' : '',
            ]"
          />
          <div
            v-else-if="isValidMove(r, c) && !gameOver && !isThinking"
            class="hint"
            :class="{ 'hint-hover': isHovered(r, c) }"
          />
        </div>
      </div>
    </div>

    <!-- Controls -->
    <div class="controls">
      <button class="btn-reset" @click="resetGame()">New Game</button>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>
    <div v-if="passMessage" class="banner pass">{{ passMessage }}</div>
    <div v-if="agentError" class="agent-error">Agent Error: {{ agentError }}</div>

    <!-- Legend -->
    <div class="legend">
      <span><span class="dot black-dot" /> You (Black)</span>
      <span><span class="dot white-dot" /> Bot (White)</span>
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
.diff-btn:hover { border-color: #94a3b8; color: #e2e8f0; }
.diff-btn.active {
  background: #166534;
  border-color: #16a34a;
  color: #fff;
  font-weight: 600;
}

/* Scoreboard */
.scoreboard {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #1e293b;
  border-radius: 12px;
  padding: 10px 24px;
  min-width: 240px;
}
.score-side {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  flex: 1;
}
.score-label { font-size: 0.7rem; color: #64748b; letter-spacing: 0.08em; }
.score-num { font-size: 1.6rem; font-weight: 800; color: #f1f5f9; }
.score-vs {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 56px;
}
.vs-text { font-size: 0.85rem; color: #475569; font-weight: 700; }
.vs-thinking { font-size: 1.2rem; color: #facc15; }
.result-win  { font-size: 0.85rem; color: #4ade80; font-weight: 700; text-align: center; }
.result-lose { font-size: 0.85rem; color: #f87171; font-weight: 700; text-align: center; }
.result-draw { font-size: 0.85rem; color: #94a3b8; font-weight: 700; text-align: center; }

.disc-icon {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  box-shadow: 0 2px 6px rgba(0,0,0,0.4);
}
.disc-icon.black { background: #1a1a1a; border: 2px solid #444; }
.disc-icon.white { background: #f0f0f0; border: 2px solid #ccc; }

/* Board — larger cells for 6×6 */
.board {
  background: #166534;
  border-radius: 8px;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 0 0 2px #14532d;
}
.board-row {
  display: flex;
  gap: 2px;
}
.cell {
  width: 58px;
  height: 58px;
  background: #15803d;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: background 0.1s;
}
.cell.cell-clickable { cursor: pointer; }
.cell.cell-hovered   { background: #166534; }

/* Disc */
.disc {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  transition: transform 0.15s;
}
.disc.black {
  background: radial-gradient(circle at 35% 35%, #555, #111);
  box-shadow: 2px 3px 8px rgba(0,0,0,0.6);
}
.disc.white {
  background: radial-gradient(circle at 35% 35%, #fff, #ccc);
  box-shadow: 2px 3px 8px rgba(0,0,0,0.4);
}

/* Disc animations */
.disc-flip {
  animation: flip 0.45s ease-in-out;
}
.disc-pop {
  animation: pop 0.3s ease-out;
}
@keyframes flip {
  0%   { transform: rotateY(0deg); }
  50%  { transform: rotateY(90deg); }
  100% { transform: rotateY(0deg); }
}
@keyframes pop {
  0%   { transform: scale(0); opacity: 0; }
  60%  { transform: scale(1.15); opacity: 1; }
  100% { transform: scale(1); }
}

/* Valid move hint dot */
.hint {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.25);
  transition: all 0.1s;
}
.hint.hint-hover {
  width: 38px;
  height: 38px;
  background: rgba(0, 0, 0, 0.18);
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

.error-msg { color: #f87171; font-size: 0.85rem; }

.banner.pass {
  text-align: center;
  padding: 10px;
  border-radius: 8px;
  margin-bottom: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  background: #854d0e;
  color: #fde68a;
  border: 1px solid #a16207;
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
.black-dot { background: #1a1a1a; border: 1px solid #555; }
.white-dot { background: #f0f0f0; border: 1px solid #aaa; }
</style>
