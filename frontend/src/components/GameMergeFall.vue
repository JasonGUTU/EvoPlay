<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from "vue";
import GameLog from "./GameLog.vue";
import { getSessionId, resetSessionId, addSessionToUrl, setSessionIdFromUrl } from "../utils/session.js";

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
const lastGain = ref(0);
const prevScore = ref(0);
const gainKey = ref(0);
const dropping = ref(false);

// Animation state: per-cell flags
// cellAnim[r][c] = "drop" | "merge" | "pop" | ""
const cellAnim = ref([]);
// Particles for explosion effect: [{r, c, id}]
const particles = reactive([]);
let particleId = 0;

function initAnimGrid() {
  cellAnim.value = Array.from({ length: height.value }, () =>
    Array(width.value).fill("")
  );
}

// ── API helpers ────────────────────────────────────────────────────

async function fetchState() {
  // Check if session_id is provided in URL, if so, use it
  const urlSessionId = setSessionIdFromUrl("mergefall");
  const sid = urlSessionId || getSessionId("mergefall");
  sessionId.value = sid;
  const url = addSessionToUrl(`${API}/state`, sid);
  const res = await fetch(url);
  const data = await res.json();
  if (data.session_id) {
    sessionId.value = data.session_id;
  }
  applyState(data, false);
}

async function dropInColumn(col) {
  if (dropping.value) return;
  dropping.value = true;
  error.value = "";
  prevScore.value = score.value;

  const oldBoard = board.value.map((row) => [...row]);

  const sid = sessionId.value || getSessionId("mergefall");
  const url = addSessionToUrl(`${API}/action?move=drop ${col}`, sid);
  const res = await fetch(url);
  const data = await res.json();
  if (data.error) {
    error.value = data.error;
  }
  if (data.session_id) {
    sessionId.value = data.session_id;
  }
  const gain = data.score - prevScore.value;
  lastGain.value = gain;
  if (gain > 0) gainKey.value++;

  applyState(data, true, oldBoard, col);
  logRef.value?.fetchLog();

  // Allow next action after animations settle
  setTimeout(() => {
    dropping.value = false;
  }, 350);
}

async function resetGame() {
  error.value = "";
  lastGain.value = 0;
  particles.splice(0);
  // Reset session ID to get a fresh game instance
  const sid = resetSessionId("mergefall");
  sessionId.value = sid;
  const url = addSessionToUrl(`${API}/reset`, sid);
  const res = await fetch(url);
  const data = await res.json();
  if (data.session_id) {
    sessionId.value = data.session_id;
  }
  applyState(data, false);
  logRef.value?.fetchLog();
}

function applyState(state, animate = false, oldBoard = null, dropCol = -1) {
  const newBoard = state.board;
  width.value = state.width;
  height.value = state.height;
  score.value = state.score;
  nextTile.value = state.next_tile;
  gameOver.value = state.game_over;
  validActions.value = state.valid_actions || [];

  initAnimGrid();

  if (animate && oldBoard) {
    // Detect changes
    for (let r = 0; r < height.value; r++) {
      for (let c = 0; c < width.value; c++) {
        const oldVal = oldBoard[r]?.[c] ?? 0;
        const newVal = newBoard[r][c];

        if (oldVal === 0 && newVal !== 0) {
          // New tile appeared — could be drop or gravity settle
          cellAnim.value[r][c] = c === dropCol ? "drop" : "pop";
        } else if (oldVal !== 0 && newVal !== 0 && newVal > oldVal) {
          // Value increased — this is a merge result
          cellAnim.value[r][c] = "merge";
        } else if (oldVal !== 0 && newVal === 0) {
          // Tile disappeared — was absorbed, spawn particles
          spawnParticles(r, c, oldVal);
        }
      }
    }
  }

  board.value = newBoard;

  // Clear animation classes after they finish
  if (animate) {
    setTimeout(() => {
      initAnimGrid();
    }, 500);
  }
}

// ── Particle explosion ─────────────────────────────────────────────

function spawnParticles(r, c, value) {
  const color = (tileColors[value] || { bg: "#475569" }).bg;
  for (let i = 0; i < 6; i++) {
    const id = particleId++;
    particles.push({ r, c, id, color, index: i });
    // Remove after animation
    setTimeout(() => {
      const idx = particles.findIndex((p) => p.id === id);
      if (idx !== -1) particles.splice(idx, 1);
    }, 600);
  }
}

// ── Which columns are droppable ────────────────────────────────────

function canDrop(col) {
  return !dropping.value && validActions.value.includes(`drop ${col}`);
}

// ── Keyboard: 1-5 keys to drop into columns ───────────────────────

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

onMounted(() => {
  fetchState();
  window.addEventListener("keydown", onKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", onKeyDown);
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

// ── Particle position (relative to board grid) ─────────────────────

function particleStyle(p) {
  // Each particle flies in a different direction
  const angles = [0, 60, 120, 180, 240, 300];
  const angle = angles[p.index % 6];
  const rad = (angle * Math.PI) / 180;
  const dist = 30 + Math.random() * 15;
  const tx = Math.cos(rad) * dist;
  const ty = Math.sin(rad) * dist;
  return {
    "--tx": `${tx}px`,
    "--ty": `${ty}px`,
    backgroundColor: p.color,
    gridRow: p.r + 1,
    gridColumn: p.c + 1,
  };
}
</script>

<template>
  <div class="mergefall" tabindex="0">
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
            'anim-drop': cellAnim[r]?.[c] === 'drop',
            'anim-merge': cellAnim[r]?.[c] === 'merge',
            'anim-pop': cellAnim[r]?.[c] === 'pop',
          }"
          :style="cell !== 0 ? tileStyle(cell) : {}"
          @click="canDrop(c) && dropInColumn(c)"
        >
          <span v-if="cell !== 0">{{ cell }}</span>
        </div>
      </template>

      <!-- Explosion particles (overlaid on grid) -->
      <div
        v-for="p in particles"
        :key="p.id"
        class="particle"
        :style="particleStyle(p)"
      ></div>
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

.reset-btn:hover {
  background: #334155;
}

/* ── Gain popup ────────────────────────────────────────────────── */

.gain-popup {
  text-align: center;
  font-size: 1.1rem;
  font-weight: 700;
  color: #4ade80;
  margin-bottom: 6px;
  animation: fadeUp 1s ease-out forwards;
}

@keyframes fadeUp {
  0% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; transform: translateY(-20px); }
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

.drop-btn:not(:disabled):hover {
  color: #4ade80;
  background: #1e293b;
}

.drop-btn:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}

.arrow-down {
  font-size: 0.7rem;
}

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

.cell.empty {
  background: #334155;
  cursor: default;
}

.cell:not(.empty):hover {
  filter: brightness(1.1);
}

/* ── Drop animation ────────────────────────────────────────────── */

.anim-drop {
  animation: tileDrop 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

@keyframes tileDrop {
  0% {
    opacity: 0;
    transform: translateY(-80px) scale(0.8);
  }
  60% {
    opacity: 1;
    transform: translateY(4px) scale(1.02);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* ── Merge (scale bump + glow) ─────────────────────────────────── */

.anim-merge {
  animation: tileMerge 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

@keyframes tileMerge {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.5);
  }
  40% {
    transform: scale(1.3);
    box-shadow: 0 0 16px 6px rgba(255, 255, 255, 0.4);
  }
  70% {
    transform: scale(0.95);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0);
  }
}

/* ── Pop-in (gravity settle) ───────────────────────────────────── */

.anim-pop {
  animation: tilePop 0.25s ease-out forwards;
}

@keyframes tilePop {
  0% {
    opacity: 0.5;
    transform: scale(0.6);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

/* ── Explosion particles ───────────────────────────────────────── */

.particle {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  pointer-events: none;
  z-index: 10;
  /* Center in the grid cell */
  place-self: center;
  animation: particleFly 0.5s ease-out forwards;
}

@keyframes particleFly {
  0% {
    opacity: 1;
    transform: translate(0, 0) scale(1);
  }
  100% {
    opacity: 0;
    transform: translate(var(--tx, 20px), var(--ty, -20px)) scale(0.3);
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
