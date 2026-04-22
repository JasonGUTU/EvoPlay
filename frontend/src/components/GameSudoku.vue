<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { addSessionToUrl, getSessionId, resetSessionId, setSessionIdFromUrl, tryResume } from "../utils/session.js";
import GameGuide from "./GameGuide.vue";

const props = defineProps({ playerName: { type: String, default: "" } });

const guideTitle = "How to Play Sudoku";
const guideSections = [
  { label: "Goal", text: "Fill every empty cell with numbers 1-9 so each row, column, and 3×3 box uses every number exactly once." },
  { label: "Controls", text: "Select a cell, then click a number or use your keyboard. Toggle Notes to place pencil marks instead of a final answer." },
  { label: "Rules", text: "Given cells cannot be changed. Use Erase to clear a cell and Undo to go back one step." },
];

const API = "/api/game/sudoku";
const GAME_KEY = "sudoku";
const SIZE = 9;

const sessionId = ref(null);
const board = ref([]);
const givens = ref([]);
const fixedCells = ref([]);
const notes = ref([]);
const conflicts = ref([]);
const score = ref(0);
const lives = ref(3);
const filledCells = ref(0);
const totalToFill = ref(0);
const mistakes = ref(0);
const currentLevel = ref(1);
const difficulty = ref("easy");
const maxLevel = ref(1);
const gameOver = ref(false);
const won = ref(false);
const withdrawn = ref(false);
const undoAvailable = ref(false);
const validActions = ref([]);
const error = ref("");
const agentError = ref("");
const isWatching = ref(false);
const noteMode = ref(false);
const selectedCell = ref(null);

let pollTimer = null;

const hasSelection = computed(() => Array.isArray(selectedCell.value));
const selectedRow = computed(() => selectedCell.value?.[0] ?? -1);
const selectedCol = computed(() => selectedCell.value?.[1] ?? -1);
const DIFFICULTIES = [
  { value: "easy",   label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard",   label: "Hard" },
];

async function applyDifficulty(diff) {
  difficulty.value = diff;
  await resetGame();
}

function applyState(state) {
  if (state.session_id) sessionId.value = state.session_id;
  board.value = state.board || [];
  givens.value = state.givens || [];
  fixedCells.value = state.fixed_cells || [];
  notes.value = state.notes || [];
  conflicts.value = state.conflicts || [];
  score.value = state.score ?? 0;
  lives.value = state.lives ?? 3;
  filledCells.value = state.filled_cells ?? 0;
  totalToFill.value = state.total_to_fill ?? 0;
  mistakes.value = state.mistakes ?? 0;
  currentLevel.value = state.current_level ?? 1;
  difficulty.value = state.difficulty ?? "easy";
  maxLevel.value = state.max_level ?? 1;
  gameOver.value = !!state.game_over;
  won.value = !!state.won;
  withdrawn.value = !!state.withdrawn;
  undoAvailable.value = !!state.undo_available;
  validActions.value = state.valid_actions || [];
  agentError.value = state.agent_error || "";
  if (gameOver.value && pollTimer) stopPolling();
}

async function fetchState() {
  const sid = sessionId.value || getSessionId(GAME_KEY);
  sessionId.value = sid;
  const res = await fetch(addSessionToUrl(`${API}/state`, sid));
  const data = await res.json();
  if (data.error) {
    error.value = data.error;
    return;
  }
  applyState(data);
}

async function resetGame(newDifficulty) {
  if (newDifficulty && typeof newDifficulty === 'string') {
    difficulty.value = newDifficulty;
  }
  error.value = "";
  noteMode.value = false;
  selectedCell.value = null;
  const sid = resetSessionId(GAME_KEY);
  sessionId.value = sid;
  let url = `${API}/reset?difficulty=${difficulty.value}`;
  if (props.playerName) {
    url += `&player_name=${encodeURIComponent(props.playerName)}`;
  }
  const res = await fetch(addSessionToUrl(url, sid));
  const data = await res.json();
  if (data.error) {
    error.value = data.error;
    return;
  }
  applyState(data);
}

async function sendAction(action) {
  if (!action || isWatching.value) return;
  if (validActions.value.length > 0 && !validActions.value.includes(action)) return;
  error.value = "";
  const sid = sessionId.value || getSessionId(GAME_KEY);
  sessionId.value = sid;
  const res = await fetch(addSessionToUrl(`${API}/action?move=${encodeURIComponent(action)}`, sid));
  const data = await res.json();
  if (data.error) {
    error.value = data.error;
    return;
  }
  applyState(data);
}

function isFixed(r, c) {
  return !!fixedCells.value[r]?.[c];
}

function selectCell(r, c) {
  selectedCell.value = [r, c];
}

async function placeValue(value) {
  if (!hasSelection.value || gameOver.value || isWatching.value) return;
  const r = selectedRow.value;
  const c = selectedCol.value;
  if (isFixed(r, c)) return;
  const action = noteMode.value && board.value[r]?.[c] === 0
    ? `note_${r}_${c}_${value}`
    : `set_${r}_${c}_${value}`;
  await sendAction(action);
}

async function eraseSelected() {
  if (!hasSelection.value || gameOver.value || isWatching.value) return;
  const r = selectedRow.value;
  const c = selectedCol.value;
  if (isFixed(r, c)) return;
  await sendAction(`clear_${r}_${c}`);
}

async function undoMove() {
  if (!undoAvailable.value || gameOver.value || isWatching.value) return;
  await sendAction("undo");
}

async function giveUp() {
  if (gameOver.value || isWatching.value) return;
  await sendAction("withdraw");
}

function isSelected(r, c) {
  return selectedRow.value === r && selectedCol.value === c;
}

function isRelated(r, c) {
  if (!hasSelection.value || isSelected(r, c)) return false;
  const sr = selectedRow.value;
  const sc = selectedCol.value;
  const sameRow = sr === r;
  const sameCol = sc === c;
  const sameBox = Math.floor(sr / 3) === Math.floor(r / 3) && Math.floor(sc / 3) === Math.floor(c / 3);
  return sameRow || sameCol || sameBox;
}

function noteVisible(r, c, value) {
  return !!notes.value[r]?.[c]?.includes(value);
}

function moveSelection(dr, dc) {
  if (!hasSelection.value) {
    selectedCell.value = [0, 0];
    return;
  }
  const nextRow = Math.min(SIZE - 1, Math.max(0, selectedRow.value + dr));
  const nextCol = Math.min(SIZE - 1, Math.max(0, selectedCol.value + dc));
  selectedCell.value = [nextRow, nextCol];
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(async () => {
    if (!sessionId.value) return;
    await fetchState();
  }, 1500);
}

function stopPolling() {
  if (!pollTimer) return;
  clearInterval(pollTimer);
  pollTimer = null;
}

function onKeyDown(event) {
  if (isWatching.value) return;
  if (/^[1-9]$/.test(event.key)) {
    event.preventDefault();
    placeValue(Number(event.key));
    return;
  }
  if (event.key === "Backspace" || event.key === "Delete" || event.key === "0") {
    event.preventDefault();
    eraseSelected();
    return;
  }
  if (event.key === "n" || event.key === "N") {
    event.preventDefault();
    noteMode.value = !noteMode.value;
    return;
  }
  if (event.key === "u" || event.key === "U") {
    event.preventDefault();
    undoMove();
    return;
  }
  if (event.key === "ArrowUp") {
    event.preventDefault();
    moveSelection(-1, 0);
    return;
  }
  if (event.key === "ArrowDown") {
    event.preventDefault();
    moveSelection(1, 0);
    return;
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    moveSelection(0, -1);
    return;
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    moveSelection(0, 1);
  }
}

onMounted(async () => {
  const urlSid = setSessionIdFromUrl(GAME_KEY);
  window.addEventListener("keydown", onKeyDown);

  if (urlSid) {
    sessionId.value = urlSid;
    isWatching.value = true;
    await fetchState();
    startPolling();
    return;
  }

  const resumed = await tryResume(GAME_KEY);
  if (resumed) {
    applyState(resumed);
    return;
  }

  await resetGame();
});

onUnmounted(() => {
  window.removeEventListener("keydown", onKeyDown);
  stopPolling();
});
</script>

<template>
  <div class="wrapper">
    <div class="game-header">
      <div class="header-left">
        <GameGuide :title="guideTitle" :sections="guideSections" />
      </div>
      <div class="header-center">
        <div class="level-badge">{{ difficulty.toUpperCase() }}</div>
        <div class="level-title">Level {{ currentLevel }}</div>
      </div>
      <div class="header-right">
      </div>
    </div>

    <!-- Difficulty selector -->
    <div class="difficulty-bar">
      <button
        v-for="d in DIFFICULTIES"
        :key="d.value"
        class="diff-btn"
        :class="{ active: difficulty === d.value }"
        :disabled="isWatching"
        @click="applyDifficulty(d.value)"
      >{{ d.label }}</button>
    </div>

    <div class="top-bar">
      <div class="stat-card">
        <span class="stat-label">Level</span>
        <span class="stat-value">{{ currentLevel }}/{{ maxLevel }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Progress</span>
        <span class="stat-value">{{ progressText }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Mistakes</span>
        <span class="stat-value">{{ mistakes }}</span>
      </div>
    </div>

    <div class="sub-bar">
      <div class="lives-board">
        <span v-for="n in 3" :key="n" class="heart" :class="{ lost: n > lives }">❤️</span>
      </div>
      <span class="sub-pill">Filled {{ filledCells }}/{{ totalToFill }}</span>
      <span v-if="isWatching" class="sub-pill watch">Watching</span>
      <span v-else-if="noteMode" class="sub-pill notes">Notes On</span>
    </div>

    <div class="board">
      <div v-for="(row, r) in board" :key="r" class="board-row">
        <button
          v-for="(cell, c) in row"
          :key="`${r}-${c}`"
          type="button"
          class="cell"
          :class="{
            fixed: isFixed(r, c),
            selected: isSelected(r, c),
            related: isRelated(r, c),
            conflict: conflicts[r]?.[c],
            editable: !isFixed(r, c),
            won: won,
            'box-top': r % 3 === 0,
            'box-left': c % 3 === 0,
            'box-right': c === 8,
            'box-bottom': r === 8,
          }"
          @click="selectCell(r, c)"
        >
          <span v-if="cell !== 0" class="cell-value">{{ cell }}</span>
          <div v-else class="notes-grid">
            <span
              v-for="value in 9"
              :key="value"
              class="note"
              :class="{ visible: noteVisible(r, c, value) }"
            >
              {{ noteVisible(r, c, value) ? value : "" }}
            </span>
          </div>
        </button>
      </div>
    </div>

    <div class="toolbar">
      <button type="button" class="tool-btn" :disabled="!undoAvailable || gameOver || isWatching" @click="undoMove">
        Undo
      </button>
      <button type="button" class="tool-btn" :disabled="!hasSelection || gameOver || isWatching" @click="eraseSelected">
        Erase
      </button>
      <button
        type="button"
        class="tool-btn"
        :class="{ active: noteMode }"
        :disabled="gameOver || isWatching"
        @click="noteMode = !noteMode"
      >
        Notes
      </button>
      <button type="button" class="tool-btn" :disabled="gameOver || isWatching" @click="giveUp">
        Give Up
      </button>
      <button type="button" class="tool-btn primary" :disabled="isWatching" @click="resetGame">
        New Game
      </button>
    </div>

    <div class="numpad">
      <button
        v-for="value in 9"
        :key="value"
        type="button"
        class="num-btn"
        :disabled="!hasSelection || gameOver || isWatching"
        @click="placeValue(value)"
      >
        {{ value }}
      </button>
    </div>

    <!-- Status Banner -->
    <div v-if="won" class="banner success">
      🎉 You solved it!
    </div>
    <div v-else-if="lives <= 0" class="banner warn">
      💔 Out of lives! Game Over.
    </div>
    <div v-else-if="withdrawn" class="banner warn">
      🏳️ You gave up.
    </div>
    <div v-else-if="hasSelection" class="banner info">
      Selected row {{ selectedRow + 1 }}, col {{ selectedCol + 1 }}
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>
    <div v-if="agentError" class="agent-error">Agent Error: {{ agentError }}</div>
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

/* Difficulty */
.difficulty-bar {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 4px;
}
.diff-btn {
  padding: 5px 16px;
  border-radius: 20px;
  border: 1px solid #475569;
  background: transparent;
  color: #94a3b8;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.15s;
}
.diff-btn:hover:not(:disabled) { border-color: #60a5fa; color: #60a5fa; }
.diff-btn.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
  font-weight: 600;
}
.diff-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.top-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  width: 100%;
}

.stat-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
}

.stat-label {
  font-size: 0.72rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.stat-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: #f8fafc;
}

.sub-bar {
  width: 100%;
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.sub-pill {
  padding: 6px 12px;
  border-radius: 999px;
  background: #132033;
  border: 1px solid #2b3d57;
  color: #cbd5e1;
  font-size: 0.82rem;
}

.sub-pill.watch {
  color: #93c5fd;
  border-color: #2563eb;
}

.sub-pill.notes {
  color: #86efac;
  border-color: #16a34a;
}

.lives-board {
  display: flex;
  gap: 4px;
}

.heart {
  font-size: 1.1rem;
  transition: opacity 0.3s;
}

.heart.lost {
  opacity: 0.2;
  filter: grayscale(100%);
}

.board {
  width: min(100%, 468px);
  aspect-ratio: 1;
  display: grid;
  grid-template-rows: repeat(9, 1fr);
  background: #0f172a;
  border-radius: 12px;
  overflow: hidden;
}

.board-row {
  display: grid;
  grid-template-columns: repeat(9, 1fr);
}

.cell {
  position: relative;
  background: #f8fafc;
  border: none;
  border-top: 1px solid #cbd5e1;
  border-left: 1px solid #cbd5e1;
  color: #0f172a;
  padding: 0;
  cursor: pointer;
  min-width: 0;
  min-height: 0;
}

.cell.box-top {
  border-top: 2px solid #334155;
}

.cell.box-left {
  border-left: 2px solid #334155;
}

.cell.box-right {
  border-right: 2px solid #334155;
}

.cell.box-bottom {
  border-bottom: 2px solid #334155;
}

.cell.fixed {
  background: #e2e8f0;
  color: #0f172a;
  font-weight: 800;
}

.cell.editable {
  color: #0f172a;
}

.cell.related {
  background: #dbeafe;
}

.cell.selected {
  background: #93c5fd;
}

.cell.conflict {
  background: #fecaca;
  color: #991b1b;
}

.cell.won {
  background: #dcfce7;
}

.cell-value {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: clamp(1rem, 4vw, 2rem);
  font-weight: 700;
}

.notes-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(3, 1fr);
  width: 100%;
  height: 100%;
  padding: 3px;
}

.note {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: clamp(0.34rem, 1.5vw, 0.68rem);
  color: transparent;
}

.note.visible {
  color: #475569;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  width: 100%;
}

.tool-btn,
.num-btn {
  border: 1px solid #475569;
  border-radius: 10px;
  background: #1e293b;
  color: #e2e8f0;
  cursor: pointer;
  transition: all 0.15s;
}

.tool-btn {
  padding: 10px 14px;
  min-width: 88px;
  font-size: 0.92rem;
}

.tool-btn.primary {
  background: #14532d;
  border-color: #16a34a;
}

.tool-btn.active {
  background: #1d4ed8;
  border-color: #60a5fa;
}

.tool-btn:disabled,
.num-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.numpad {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(9, 1fr);
  gap: 8px;
}

.num-btn {
  padding: 12px 0;
  font-size: 1.25rem;
  font-weight: 700;
}

.tool-btn:not(:disabled):hover,
.num-btn:not(:disabled):hover {
  border-color: #94a3b8;
  transform: translateY(-1px);
}

.banner {
  width: 100%;
  border-radius: 12px;
  padding: 10px 14px;
  text-align: center;
  font-weight: 600;
}

.banner.success {
  background: #14532d;
  color: #dcfce7;
}

.banner.warn {
  background: #7c2d12;
  color: #ffedd5;
}

.banner.info {
  background: #1e293b;
  color: #cbd5e1;
  border: 1px solid #334155;
}

.error-msg,
.agent-error {
  width: 100%;
  border-radius: 10px;
  padding: 10px 12px;
  text-align: center;
}

.error-msg {
  background: #7f1d1d;
  color: #fecaca;
}

.agent-error {
  background: #451a03;
  color: #fdba74;
}

@media (max-width: 520px) {
  .top-bar {
    grid-template-columns: 1fr;
  }

  .numpad {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
