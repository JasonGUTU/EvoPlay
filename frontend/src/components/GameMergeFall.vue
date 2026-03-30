<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from "vue";
import GameLog from "./GameLog.vue";
import { getSessionId, resetSessionId, addSessionToUrl, setSessionIdFromUrl } from "../utils/session.js";

defineProps({ playerName: { type: String, default: "" } });

const API = "/api/game/mergefall";
const logRef = ref(null);
const sessionId = ref(null);

const board = ref([]);
const width = ref(5);
const height = ref(6);
const score = ref(0);
const nextTile = ref(2);
const gameOver = ref(false);
const validActions = ref([]);
const error = ref("");
const agentError = ref("");
const lastGain = ref(0);
const prevScore = ref(0);
const gainKey = ref(0);
const dropping = ref(false);
const difficulty = ref("hard");

const DIFFICULTIES = [
  { value: "easy",   label: "Easy",   desc: "Tiles cluster together" },
  { value: "medium", label: "Medium", desc: "More variety" },
  { value: "hard",   label: "Hard",   desc: "Wild tile spawns" },
];

// Animation state per cell: { type: "" | "drop" | "flash" | "absorb" | "merge" | "gravity", flyX, flyY }
const cellAnim = ref([]);

function initAnimGrid() {
  cellAnim.value = Array.from({ length: height.value }, () =>
    Array.from({ length: width.value }, () => ({ type: "", flyX: 0, flyY: 0 }))
  );
}

function setAnim(r, c, type, flyX = 0, flyY = 0) {
  if (cellAnim.value[r]) {
    cellAnim.value[r][c] = { type, flyX, flyY };
    cellAnim.value = [...cellAnim.value];
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── API helpers ────────────────────────────────────────────────────

async function fetchState(isPolling = false) {
  const urlSessionId = setSessionIdFromUrl("mergefall");
  const sid = urlSessionId || getSessionId("mergefall");
  sessionId.value = sid;
  const url = addSessionToUrl(`${API}/state`, sid);
  const res = await fetch(url);
  const data = await res.json();
  if (data.session_id) sessionId.value = data.session_id;

  if (isPolling && data.pre_merge_board) {
    const oldBoard = board.value.map(row => [...row]);
    await animateFullSequence(oldBoard, data.pre_merge_board, data.board, data.drop_pos, data);
  } else {
    applyStateDirect(data);
  }
  logRef.value?.fetchLog();
}

async function dropInColumn(col) {
  if (dropping.value) return;
  dropping.value = true;
  error.value = "";
  prevScore.value = score.value;
  lastUserActionTime = Date.now();

  const oldBoard = board.value.map(row => [...row]);

  const sid = sessionId.value || getSessionId("mergefall");
  const url = addSessionToUrl(`${API}/action?move=drop ${col}`, sid);
  const res = await fetch(url);
  const data = await res.json();
  if (data.error) error.value = data.error;
  if (data.session_id) sessionId.value = data.session_id;

  const preMerge = data.pre_merge_board || oldBoard;
  const dropPos = data.drop_pos || null;

  await animateFullSequence(oldBoard, preMerge, data.board, dropPos, data);

  const gain = data.score - prevScore.value;
  lastGain.value = gain;
  if (gain > 0) gainKey.value++;

  logRef.value?.fetchLog();
  dropping.value = false;
}

// ── Frontend merge simulation (mirrors backend logic) ──────────

function ceilLog2(n) {
  let p = 0;
  let v = 1;
  while (v < n) { v *= 2; p++; }
  return p;
}

function simGravity(b, h, w) {
  // Apply gravity: tiles fall to bottom. Returns new board + active pos
  const nb = b.map(row => [...row]);
  let activePos = null;
  for (let c = 0; c < w; c++) {
    const vals = [];
    for (let r = 0; r < h; r++) {
      if (nb[r][c] !== 0) vals.push(nb[r][c]);
    }
    // Fill from bottom
    let rr = h - 1;
    for (let i = vals.length - 1; i >= 0; i--) {
      nb[rr][c] = vals[i];
      if (vals[i] < 0) activePos = [rr, c]; // negative = active
      rr--;
    }
    for (let r = rr; r >= 0; r--) nb[r][c] = 0;
  }
  return { board: nb, activePos };
}

function simMergeChain(preMergeBoard) {
  // Simulate the full merge chain, returning intermediate snapshots
  // Each snapshot: { board (before this step's merge), absorbed: [{r,c}], activePos, newValue }
  const h = preMergeBoard.length;
  const w = preMergeBoard[0].length;

  // Find the active tile (the dropped one) — it's the tile at drop_pos
  // We mark it as negative to track it
  let b = preMergeBoard.map(row => [...row]);

  // Find active position: look for any cell, use dropPos
  // Actually we need to find which cell is the "active" one
  // Since we don't have negative markers in the visible board,
  // we'll just simulate from scratch

  const steps = [];

  // Find the dropped tile position from dropPos (passed separately)
  return steps; // Will be populated by animateFullSequence
}

function syncBoard(simBoard, h, w) {
  // Update board cells individually to avoid full-array replacement flicker
  for (let r = 0; r < h; r++) {
    for (let c = 0; c < w; c++) {
      board.value[r][c] = Math.abs(simBoard[r][c]);
    }
  }
}

function getCellSize() {
  // Get actual cell size from DOM for accurate fly animations
  const cell = document.querySelector('.mergefall .cell');
  if (cell) {
    const rect = cell.getBoundingClientRect();
    return { w: rect.width + 5, h: rect.height + 5 }; // +5 for gap
  }
  return { w: 62, h: 62 };
}

async function animateFullSequence(oldBoard, preMergeBoard, finalBoard, dropPos, stateData) {
  const h = preMergeBoard.length;
  const w = preMergeBoard[0].length;

  // ── Phase 1: Drop ── show new tile sliding down
  initAnimGrid();
  board.value = preMergeBoard.map(row => [...row]);
  updateMeta(stateData);

  if (dropPos) {
    const [dr, dc] = dropPos;
    setAnim(dr, dc, "drop");
  }
  await sleep(350);

  // ── Simulate merge chain step by step ──
  // Use negative values to track active tile (mirrors backend)
  let simBoard = preMergeBoard.map(row => [...row]);
  let activePos = dropPos ? [dropPos[0], dropPos[1]] : null;

  if (activePos) {
    // Mark active tile as negative
    simBoard[activePos[0]][activePos[1]] = -simBoard[activePos[0]][activePos[1]];
  }

  // Run merge chain with animation for each step
  while (activePos) {
    // Apply gravity first
    const gResult = simGravity(simBoard, h, w);
    simBoard = gResult.board;
    activePos = gResult.activePos;

    if (!activePos) break;

    const [ar, ac] = activePos;
    const activeVal = Math.abs(simBoard[ar][ac]);
    if (activeVal === 0) break;

    // Find same-value neighbors
    const neighbors = [];
    for (const [dr, dc] of [[-1,0],[1,0],[0,-1],[0,1]]) {
      const nr = ar + dr, nc = ac + dc;
      if (nr >= 0 && nr < h && nc >= 0 && nc < w) {
        if (Math.abs(simBoard[nr][nc]) === activeVal) {
          neighbors.push([nr, nc]);
        }
      }
    }

    if (neighbors.length === 0) break;

    // Sync board cells individually (avoid full replacement flicker)
    const cs = getCellSize();
    syncBoard(simBoard, h, w);
    initAnimGrid();

    // Animate: neighbors fly toward active tile
    for (const [nr, nc] of neighbors) {
      const flyX = (ac - nc) * cs.w;
      const flyY = (ar - nr) * cs.h;
      setAnim(nr, nc, "absorb", flyX, flyY);
    }
    await sleep(300);

    // Execute merge: remove neighbors, upgrade active tile
    // First clear absorbed cells individually (they already flew away visually)
    for (const [nr, nc] of neighbors) {
      simBoard[nr][nc] = 0;
      board.value[nr][nc] = 0;
    }
    const n = 1 + neighbors.length;
    const newVal = activeVal * (1 << ceilLog2(n));
    simBoard[ar][ac] = -newVal; // keep active marker

    // Update only the merge target cell, then animate
    initAnimGrid();
    board.value[ar][ac] = newVal;
    setAnim(ar, ac, "merge");
    await sleep(300);

    // Check for gravity — show tiles falling
    const beforeGravity = simBoard.map(row => [...row]);
    const gResult2 = simGravity(simBoard, h, w);
    simBoard = gResult2.board;
    activePos = gResult2.activePos;

    // Detect which tiles moved down and animate
    let hasGravityMove = false;
    initAnimGrid();
    for (let c2 = 0; c2 < w; c2++) {
      for (let r2 = h - 1; r2 >= 0; r2--) {
        const newVal2 = Math.abs(simBoard[r2][c2]);
        const oldVal2 = Math.abs(beforeGravity[r2][c2]);
        if (newVal2 !== 0 && oldVal2 === 0) {
          for (let pr = r2 - 1; pr >= 0; pr--) {
            if (Math.abs(beforeGravity[pr][c2]) === newVal2) {
              setAnim(r2, c2, "gravity", 0, -(r2 - pr) * cs.h);
              hasGravityMove = true;
              break;
            }
          }
        }
      }
    }

    syncBoard(simBoard, h, w);
    if (hasGravityMove) await sleep(300);

    // Continue loop — check for more merges
  }

  // ── Final: apply actual server state (ensures consistency)
  initAnimGrid();
  applyStateDirect(stateData);
}

async function resetGame(newDifficulty) {
  if (newDifficulty) difficulty.value = newDifficulty;
  error.value = "";
  lastGain.value = 0;
  const sid = resetSessionId("mergefall");
  sessionId.value = sid;
  const url = addSessionToUrl(`${API}/reset?difficulty=${difficulty.value}`, sid);
  const res = await fetch(url);
  const data = await res.json();
  if (data.session_id) sessionId.value = data.session_id;
  applyStateDirect(data);
  logRef.value?.fetchLog();
}

function updateMeta(state) {
  width.value = state.width;
  height.value = state.height;
  score.value = state.score;
  nextTile.value = state.next_tile;
  gameOver.value = state.game_over;
  validActions.value = state.valid_actions || [];
  if (state.difficulty) difficulty.value = state.difficulty;
  agentError.value = state.agent_error || "";
}

function applyStateDirect(state) {
  board.value = state.board;
  updateMeta(state);
  initAnimGrid();

  if (state.game_over) {
    stopPolling();
  } else {
    startPolling();
  }
}

// ── Which columns are droppable ────────────────────────────────────

function canDrop(col) {
  return !dropping.value && validActions.value.includes(`drop ${col}`);
}

// ── Keyboard ───────────────────────────────────────────────────────

function onKeyDown(e) {
  if (gameOver.value || dropping.value) return;
  const num = parseInt(e.key);
  if (num >= 1 && num <= width.value) {
    const col = num - 1;
    if (canDrop(col)) {
      e.preventDefault();
      dropInColumn(col);
    }
  }
}

// ── Polling ────────────────────────────────────────────────────────

let pollingInterval = null;
const POLLING_INTERVAL_MS = 1000;
let lastUserActionTime = 0;
const USER_ACTION_COOLDOWN_MS = 500;

function startPolling() {
  if (!pollingInterval && !gameOver.value) {
    pollingInterval = setInterval(async () => {
      if (Date.now() - lastUserActionTime < USER_ACTION_COOLDOWN_MS) return;
      if (dropping.value) return;
      if (!gameOver.value) {
        await fetchState(true);
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

// ── Tile colours ───────────────────────────────────────────────────

const tileColors = {
  0:    { bg: "transparent", fg: "transparent" },
  2:    { bg: "#f87171", fg: "#fff" },
  4:    { bg: "#c084fc", fg: "#fff" },
  8:    { bg: "#fbbf24", fg: "#fff" },
  16:   { bg: "#4ade80", fg: "#fff" },
  32:   { bg: "#60a5fa", fg: "#fff" },
  64:   { bg: "#f472b6", fg: "#fff" },
  128:  { bg: "#a78bfa", fg: "#fff" },
  256:  { bg: "#34d399", fg: "#fff" },
  512:  { bg: "#fb923c", fg: "#fff" },
  1024: { bg: "#e879f9", fg: "#fff" },
  2048: { bg: "#facc15", fg: "#fff" },
  4096: { bg: "#2dd4bf", fg: "#fff" },
};

function tileStyle(value) {
  const c = tileColors[value] || { bg: "#475569", fg: "#fff" };
  return {
    backgroundColor: c.bg,
    color: c.fg,
    fontSize: value >= 1024 ? "0.85rem" : value >= 128 ? "1rem" : "1.2rem",
  };
}

function nextTileStyle() {
  const c = tileColors[nextTile.value] || { bg: "#475569", fg: "#fff" };
  return { backgroundColor: c.bg, color: c.fg };
}
</script>

<template>
  <div class="mergefall" tabindex="0">
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

    <!-- Score bar -->
    <div class="info-bar">
      <div class="score-box">
        <span class="label">Score</span>
        <span class="value">{{ score }}</span>
      </div>
      <div class="next-tile-box">
        <span class="label">Next</span>
        <div class="next-tile" :style="nextTileStyle()">{{ nextTile }}</div>
      </div>
      <button class="reset-btn" @click="resetGame">New Game</button>
    </div>

    <!-- Gain popup -->
    <div v-if="lastGain > 0 && !gameOver" class="gain-popup" :key="gainKey">
      +{{ lastGain }}
    </div>

    <!-- Status -->
    <div v-if="gameOver" class="banner over">Game Over!</div>
    <div v-if="error && !gameOver" class="banner error">{{ error }}</div>
    <div v-if="agentError" class="agent-error">Agent Error: {{ agentError }}</div>

    <!-- Column drop buttons -->
    <div class="drop-buttons" :style="{ '--cols': width }">
      <button
        v-for="c in width"
        :key="c - 1"
        class="drop-btn"
        :disabled="!canDrop(c - 1)"
        @click="dropInColumn(c - 1)"
      >
        <span class="arrow-down">&#9660;</span>
      </button>
    </div>

    <!-- Board -->
    <div class="board" :style="{ '--cols': width, '--rows': height }">
      <template v-for="(row, r) in board" :key="r">
        <div
          v-for="(cell, c) in row"
          :key="`${r}-${c}`"
          class="cell"
          :class="{
            empty: cell === 0,
            'anim-drop': cellAnim[r]?.[c]?.type === 'drop',
            'anim-absorb': cellAnim[r]?.[c]?.type === 'absorb',
            'anim-merge': cellAnim[r]?.[c]?.type === 'merge',
            'anim-gravity': cellAnim[r]?.[c]?.type === 'gravity',
          }"
          :style="{
            ...(cell !== 0 ? tileStyle(cell) : {}),
            '--fly-x': (cellAnim[r]?.[c]?.flyX || 0) + 'px',
            '--fly-y': (cellAnim[r]?.[c]?.flyY || 0) + 'px',
          }"
          @click="canDrop(c) && dropInColumn(c)"
        >
          <span v-if="cell !== 0">{{ cell }}</span>
        </div>
      </template>
    </div>

    <!-- Hint -->
    <p class="hint">Click a column or press 1-5 to drop</p>

    <!-- Log -->
    <GameLog ref="logRef" game-name="mergefall" :session-id="sessionId" />
  </div>
</template>

<style scoped>
.mergefall {
  outline: none;
  position: relative;
}

/* Difficulty */
.difficulty-bar {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 12px;
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
  background: #475569;
  border-color: #64748b;
  color: #fff;
  font-weight: 600;
}

/* ── Info bar ──────────────────────────────────────────────────── */

.info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 10px;
}

.score-box {
  background: #334155;
  border-radius: 8px;
  padding: 8px 18px;
  color: #fff;
  text-align: center;
  min-width: 90px;
}

.score-box .label,
.next-tile-box .label {
  display: block;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #94a3b8;
  margin-bottom: 2px;
}

.score-box .value {
  display: block;
  font-size: 1.4rem;
  font-weight: 700;
}

.next-tile-box {
  text-align: center;
}

.next-tile {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  font-weight: 700;
  font-size: 1.2rem;
  color: #fff;
}

.reset-btn {
  padding: 10px 18px;
  border: none;
  border-radius: 8px;
  background: #475569;
  color: #f1f5f9;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.reset-btn:hover { background: #334155; }

/* ── Gain popup ────────────────────────────────────────────────── */

.gain-popup {
  text-align: center;
  font-size: 1.1rem;
  font-weight: 700;
  color: #4ade80;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  pointer-events: none;
  animation: fadeUp 1s ease-out forwards;
}

@keyframes fadeUp {
  0% { opacity: 1; transform: translateX(-50%) translateY(0); }
  100% { opacity: 0; transform: translateX(-50%) translateY(-20px); }
}

/* ── Banners ───────────────────────────────────────────────────── */

.banner {
  text-align: center;
  padding: 10px;
  border-radius: 8px;
  margin-bottom: 10px;
  font-weight: 700;
  font-size: 1.1rem;
}

.banner.over { background: #f87171; color: #fff; }
.banner.error { background: #fbbf24; color: #1e293b; }

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

/* ── Drop buttons ──────────────────────────────────────────────── */

.drop-buttons {
  display: grid;
  grid-template-columns: repeat(var(--cols, 5), 1fr);
  gap: 5px;
  margin-bottom: 4px;
  padding: 0 8px;
}

.drop-btn {
  padding: 6px 0;
  border: none;
  border-radius: 6px 6px 0 0;
  background: #1e293b;
  color: #475569;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s;
}

.drop-btn:not(:disabled):hover { color: #4ade80; }
.drop-btn:disabled { opacity: 0.2; cursor: not-allowed; }

.arrow-down { font-size: 0.7rem; }

/* ── Board ─────────────────────────────────────────────────────── */

.board {
  display: grid;
  grid-template-columns: repeat(var(--cols, 5), 1fr);
  grid-template-rows: repeat(var(--rows, 6), 1fr);
  gap: 5px;
  background: #1e293b;
  border-radius: 10px;
  padding: 8px;
  position: relative;
}

.cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-weight: 700;
  user-select: none;
  cursor: pointer;
  min-height: 54px;
  transition: background-color 0.15s;
}

.cell.empty { background: #334155; cursor: default; }
.cell:not(.empty):hover { filter: brightness(1.1); }

/* ── Drop ── tile slides down smoothly ──────────────────────────── */

.anim-drop {
  animation: tileDrop 0.3s ease-out forwards;
}

@keyframes tileDrop {
  0% {
    opacity: 0;
    transform: translateY(-60px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ── Absorb ── tiles fly toward absorber and shrink ────────────── */

.anim-absorb {
  animation: tileAbsorb 0.25s ease-in forwards;
}

@keyframes tileAbsorb {
  0% {
    transform: translate(0, 0) scale(1);
    opacity: 1;
  }
  100% {
    transform: translate(var(--fly-x, 0), var(--fly-y, 0)) scale(0.15);
    opacity: 0;
  }
}

/* ── Merge ── subtle pulse on value upgrade ──────────────────────── */

.anim-merge {
  animation: tileMerge 0.25s ease-out forwards;
}

@keyframes tileMerge {
  0% {
    transform: scale(1);
  }
  40% {
    transform: scale(1.08);
  }
  100% {
    transform: scale(1);
  }
}

/* ── Gravity ── tiles slide down naturally ─────────────────────── */

.anim-gravity {
  animation: tileGravity 0.2s ease-in forwards;
}

@keyframes tileGravity {
  0% {
    transform: translateY(var(--fly-y, -20px));
  }
  100% {
    transform: translateY(0);
  }
}

/* ── Hint ──────────────────────────────────────────────────────── */

.hint {
  text-align: center;
  margin-top: 14px;
  font-size: 0.85rem;
  color: #64748b;
}
</style>
