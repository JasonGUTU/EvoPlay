<script setup>
import { ref, onMounted } from "vue";
import Game2048 from "./components/Game2048.vue";
import GameMergeFall from "./components/GameMergeFall.vue";

const games = ref([]);
const currentGame = ref(null); // null = home menu

const gameInfo = {
  "2048": {
    title: "2048",
    desc: "Slide tiles, merge same numbers, reach 2048!",
    icon: "🔢",
  },
  mergefall: {
    title: "MergeFall",
    desc: "Drop numbers into columns, chain merges, score combos!",
    icon: "💥",
  },
};

function selectGame(name) {
  currentGame.value = name;
}

function goHome() {
  currentGame.value = null;
}

onMounted(async () => {
  try {
    const res = await fetch("/api/games");
    const data = await res.json();
    games.value = data.games;
    
    // Check URL parameters for game and session_id
    const params = new URLSearchParams(window.location.search);
    const urlGame = params.get("game");
    const urlSessionId = params.get("session_id");
    
    // If game is specified in URL, select it
    if (urlGame && games.value.includes(urlGame)) {
      currentGame.value = urlGame;
    }
  } catch (e) {
    console.error("Failed to fetch games list", e);
  }
});
</script>

<template>
  <div class="app">
    <!-- ── Home menu ──────────────────────────────────── -->
    <template v-if="currentGame === null">
      <header class="home-header">
        <h1>EvoPlay</h1>
        <p class="subtitle">Pick a game to play</p>
      </header>

      <div class="game-grid">
        <button
          v-for="g in games"
          :key="g"
          class="game-card"
          @click="selectGame(g)"
        >
          <span class="game-icon">{{ gameInfo[g]?.icon || '🎮' }}</span>
          <span class="game-title">{{ gameInfo[g]?.title || g }}</span>
          <span class="game-desc">{{ gameInfo[g]?.desc || '' }}</span>
        </button>
      </div>
    </template>

    <!-- ── Game view ──────────────────────────────────── -->
    <template v-else>
      <header class="game-header">
        <button class="back-btn" @click="goHome">&larr; Home</button>
        <h2>{{ gameInfo[currentGame]?.title || currentGame }}</h2>
      </header>

      <main>
        <Game2048 v-if="currentGame === '2048'" />
        <GameMergeFall v-else-if="currentGame === 'mergefall'" />
      </main>
    </template>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: #0f172a;
  color: #e2e8f0;
}

.app {
  max-width: 520px;
  margin: 0 auto;
  padding: 20px;
}

/* ── Home menu ────────────────────────────────────── */

.home-header {
  text-align: center;
  margin-bottom: 32px;
  padding-top: 24px;
}

.home-header h1 {
  font-size: 2.4rem;
  font-weight: 800;
  color: #e2e8f0;
  letter-spacing: -0.02em;
}

.subtitle {
  margin-top: 6px;
  font-size: 1rem;
  color: #64748b;
}

.game-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.game-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 24px 20px;
  background: #1e293b;
  border: 2px solid #334155;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.game-card:hover {
  border-color: #4ade80;
  background: #1a2536;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}

.game-icon {
  font-size: 2.2rem;
}

.game-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #f1f5f9;
}

.game-desc {
  font-size: 0.85rem;
  color: #94a3b8;
  line-height: 1.4;
}

/* ── Game header ──────────────────────────────────── */

.game-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.game-header h2 {
  font-size: 1.4rem;
  font-weight: 700;
  color: #e2e8f0;
}

.back-btn {
  padding: 6px 14px;
  border: 1px solid #475569;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.back-btn:hover {
  border-color: #e2e8f0;
  color: #e2e8f0;
}
</style>
