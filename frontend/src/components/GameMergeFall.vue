<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";

const API = "/api/game/mergefall";

const board = ref([]);
const width = ref(5);
const height = ref(6);
const score = ref(0);
const nextTile = ref(2);
const gameOver = ref(false);
const validActions = ref([]);
const error = ref("");
const lastCombo = ref(0);
const lastGain = ref(0);
const prevScore = ref(0);

// ── API helpers ────────────────────────────────────────────────────

async function fetchState() {
  const res = await fetch(`${API}/state`);
  applyState(await res.json());
}

async function dropInColumn(col) {
  error.value = "";
  prevScore.value = score.value;
  const res = await fetch(`${API}/action?move=drop ${col}`);
  const data = await res.json();
  if (data.error) {
    error.value = data.error;
  }
  const gain = data.score - prevScore.value;
  lastGain.value = gain;
  applyState(data);
}

async function resetGame() {
  error.value = "";
  lastGain.value = 0;
  const res = await fetch(`${API}/reset`);
  applyState(await res.json());
}

function applyState(state) {
  board.value = state.board;
  width.value = state.width;
  height.value = state.height;
  score.value = state.score;
  nextTile.value = state.next_tile;
  gameOver.value = state.game_over;
  validActions.value = state.valid_actions || [];
}

// ── Which columns are droppable ────────────────────────────────────

function canDrop(col) {
  return validActions.value.includes(`drop ${col}`);
}

// ── Keyboard: 1-5 keys to drop into columns ───────────────────────

function onKeyDown(e) {
  if (gameOver.value) return;
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

// ── Tile colours (same 2048 palette extended) ──────────────────────

const tileColors = {
  0:    { bg: "transparent", fg: "transparent" },
  2:    { bg: "#f87171", fg: "#fff" },      // red
  4:    { bg: "#c084fc", fg: "#fff" },      // purple
  8:    { bg: "#fbbf24", fg: "#fff" },      // amber
  16:   { bg: "#4ade80", fg: "#fff" },      // green
  32:   { bg: "#60a5fa", fg: "#fff" },      // blue
  64:   { bg: "#f472b6", fg: "#fff" },      // pink
  128:  { bg: "#a78bfa", fg: "#fff" },      // violet
  256:  { bg: "#34d399", fg: "#fff" },      // emerald
  512:  { bg: "#fb923c", fg: "#fff" },      // orange
  1024: { bg: "#e879f9", fg: "#fff" },      // fuchsia
  2048: { bg: "#facc15", fg: "#fff" },      // yellow
  4096: { bg: "#2dd4bf", fg: "#fff" },      // teal
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
  return {
    backgroundColor: c.bg,
    color: c.fg,
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
    <div v-if="lastGain > 0 && !gameOver" class="gain-popup">
      +{{ lastGain }}
    </div>

    <!-- Status -->
    <div v-if="gameOver" class="banner over">Game Over!</div>
    <div v-if="error && !gameOver" class="banner error">{{ error }}</div>

    <!-- Column drop buttons -->
    <div class="drop-buttons">
      <button
        v-for="c in width"
        :key="c - 1"
        class="drop-btn"
        :disabled="!canDrop(c - 1)"
        @click="dropInColumn(c - 1)"
      >
        {{ c }}
      </button>
    </div>

    <!-- Board -->
    <div class="board" :style="{ '--cols': width }">
      <template v-for="(row, r) in board" :key="r">
        <div
          v-for="(cell, c) in row"
          :key="`${r}-${c}`"
          class="cell"
          :class="{ empty: cell === 0 }"
          :style="cell !== 0 ? tileStyle(cell) : {}"
          @click="canDrop(c) && dropInColumn(c)"
        >
          <span v-if="cell !== 0">{{ cell }}</span>
        </div>
      </template>
    </div>

    <!-- Hint -->
    <p class="hint">Click a column or press 1-5 to drop</p>
  </div>
</template>

<style scoped>
.mergefall {
  outline: none;
}

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

.gain-popup {
  text-align: center;
  font-size: 1.1rem;
  font-weight: 700;
  color: #4ade80;
  margin-bottom: 6px;
  animation: fadeUp 0.8s ease-out forwards;
}

@keyframes fadeUp {
  0% {
    opacity: 1;
    transform: translateY(0);
  }
  100% {
    opacity: 0;
    transform: translateY(-16px);
  }
}

.banner {
  text-align: center;
  padding: 10px;
  border-radius: 8px;
  margin-bottom: 10px;
  font-weight: 700;
  font-size: 1.1rem;
}

.banner.over {
  background: #f87171;
  color: #fff;
}

.banner.error {
  background: #fbbf24;
  color: #1e293b;
}

.drop-buttons {
  display: grid;
  grid-template-columns: repeat(var(--cols, 5), 1fr);
  gap: 6px;
  margin-bottom: 6px;
}

.drop-buttons {
  --cols: 5;
}

.drop-btn {
  padding: 8px 0;
  border: 2px dashed #475569;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.drop-btn:not(:disabled):hover {
  border-color: #4ade80;
  color: #4ade80;
  background: rgba(74, 222, 128, 0.08);
}

.drop-btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.board {
  display: grid;
  grid-template-columns: repeat(var(--cols, 5), 1fr);
  gap: 5px;
  background: #1e293b;
  border-radius: 10px;
  padding: 8px;
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
  transition: background-color 0.15s, transform 0.15s;
  min-height: 54px;
}

.cell.empty {
  background: #334155;
  cursor: default;
}

.cell:not(.empty):hover {
  transform: scale(1.04);
}

.hint {
  text-align: center;
  margin-top: 14px;
  font-size: 0.85rem;
  color: #64748b;
}
</style>
