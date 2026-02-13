<script setup>
import { ref, watch, nextTick } from "vue";
import { addSessionToUrl } from "../utils/session.js";

const props = defineProps({
  gameName: { type: String, required: true },
  sessionId: { type: String, default: null },
});

const steps = ref(0);
const elapsed = ref(0);
const logEntries = ref([]);
const expanded = ref(false);
const logListRef = ref(null);

// Poll log from server after each action
async function fetchLog() {
  try {
    let url = `/api/game/${props.gameName}/log`;
    if (props.sessionId) {
      url = addSessionToUrl(url, props.sessionId);
    }
    const res = await fetch(url);
    const data = await res.json();
    steps.value = data.steps;
    elapsed.value = data.elapsed_seconds;
    logEntries.value = data.log;

    // Auto-scroll to bottom when expanded
    if (expanded.value) {
      await nextTick();
      if (logListRef.value) {
        logListRef.value.scrollTop = logListRef.value.scrollHeight;
      }
    }
  } catch (e) {
    // silent
  }
}

// Expose fetchLog so parent components can call it
defineExpose({ fetchLog });

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function toggle() {
  expanded.value = !expanded.value;
  if (expanded.value) {
    nextTick(() => {
      if (logListRef.value) {
        logListRef.value.scrollTop = logListRef.value.scrollHeight;
      }
    });
  }
}
</script>

<template>
  <div class="game-log">
    <!-- Stats bar (always visible) -->
    <div class="stats-bar" @click="toggle">
      <div class="stat">
        <span class="stat-label">Steps</span>
        <span class="stat-value">{{ steps }}</span>
      </div>
      <div class="stat">
        <span class="stat-label">Time</span>
        <span class="stat-value">{{ formatTime(elapsed) }}</span>
      </div>
      <button class="toggle-btn">
        {{ expanded ? '▲ Hide Log' : '▼ Show Log' }}
      </button>
    </div>

    <!-- Log list (collapsible) -->
    <div v-show="expanded" class="log-list" ref="logListRef">
      <div v-if="logEntries.length === 0" class="log-empty">
        No actions yet
      </div>
      <div
        v-for="entry in logEntries"
        :key="entry.step"
        class="log-entry"
        :class="{ 'game-over-entry': entry.game_over }"
      >
        <span class="log-step">#{{ entry.step }}</span>
        <span class="log-time">{{ formatTime(entry.time) }}</span>
        <span class="log-action">{{ entry.action }}</span>
        <span class="log-score">{{ entry.score }} pts</span>
        <span v-if="entry.game_over" class="log-tag">OVER</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.game-log {
  margin-top: 16px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #334155;
}

/* ── Stats bar ─────────────────────────────────────── */

.stats-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  background: #1e293b;
  cursor: pointer;
  user-select: none;
}

.stats-bar:hover {
  background: #1a2536;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #64748b;
}

.stat-value {
  font-size: 1.05rem;
  font-weight: 700;
  color: #e2e8f0;
}

.toggle-btn {
  margin-left: auto;
  padding: 4px 10px;
  border: 1px solid #475569;
  border-radius: 6px;
  background: transparent;
  color: #94a3b8;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.15s;
}

.toggle-btn:hover {
  border-color: #e2e8f0;
  color: #e2e8f0;
}

/* ── Log list ──────────────────────────────────────── */

.log-list {
  max-height: 220px;
  overflow-y: auto;
  background: #0f172a;
  border-top: 1px solid #334155;
}

.log-empty {
  padding: 14px;
  text-align: center;
  color: #475569;
  font-size: 0.85rem;
}

.log-entry {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 14px;
  font-size: 0.8rem;
  border-bottom: 1px solid #1e293b;
  color: #94a3b8;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-entry.game-over-entry {
  background: rgba(248, 113, 113, 0.08);
}

.log-step {
  color: #475569;
  font-weight: 600;
  min-width: 32px;
}

.log-time {
  color: #64748b;
  min-width: 40px;
  font-variant-numeric: tabular-nums;
}

.log-action {
  color: #e2e8f0;
  font-weight: 600;
  flex: 1;
}

.log-score {
  color: #4ade80;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.log-tag {
  background: #f87171;
  color: #fff;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
}

/* Scrollbar */
.log-list::-webkit-scrollbar {
  width: 4px;
}

.log-list::-webkit-scrollbar-track {
  background: #0f172a;
}

.log-list::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 2px;
}
</style>
