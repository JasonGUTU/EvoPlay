<script setup>
import { ref, onMounted } from "vue";
import Game2048 from "./components/Game2048.vue";
import GameMergeFall from "./components/GameMergeFall.vue";
import GameNutsBolts from "./components/GameNutsBolts.vue";
import GameSokoban from "./components/GameSokoban.vue";
import GameFourInARow from "./components/GameFourInARow.vue";
import GameOthello6 from "./components/GameOthello6.vue";
import GameSlidingPuzzle from "./components/GameSlidingPuzzle.vue";
import GameTicTacToe from "./components/GameTicTacToe.vue";
import GameCircleCat from "./components/GameCircleCat.vue";

const games = ref([]);
const currentGame = ref(null); // null = home menu
const isWatchMode = ref(false); // true when viewing via session_id URL (no login needed)

// ── Player login state ──────────────────────────────
const playerName = ref(localStorage.getItem("evoplay_player") || "");
const isLoggedIn = ref(false);
const loginInput = ref("");
const loginError = ref("");
const loginMode = ref("login"); // "login" | "register"
const loginLoading = ref(false);

async function handleLogin() {
  const name = loginInput.value.trim();
  if (!name) { loginError.value = "Please enter your name."; return; }
  loginLoading.value = true;
  loginError.value = "";
  try {
    const endpoint = loginMode.value === "register" ? "/api/player/register" : "/api/player/login";
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    const data = await res.json();
    if (data.ok) {
      playerName.value = data.name;
      localStorage.setItem("evoplay_player", data.name);
      isLoggedIn.value = true;
    } else {
      loginError.value = data.error || "Unknown error";
    }
  } catch (e) {
    loginError.value = "Server connection failed.";
  }
  loginLoading.value = false;
}

function handleLogout() {
  playerName.value = "";
  localStorage.removeItem("evoplay_player");
  isLoggedIn.value = false;
  currentGame.value = null;
  loginInput.value = "";
  loginError.value = "";
  loginMode.value = "login";
}

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
  nuts_bolts: {
    title: "Nuts & Bolts",
    desc: "Sort the colored nuts onto matching screws!",
    icon: "🔩",
  },
  sokoban: {
    title: "Sokoban",
    desc: "Push crates to their designated goals!",
    icon: "📦",
  },
  fourinarow: {
    title: "Four in a Row",
    desc: "Drop pieces, get 4 in a line — beat the bot!",
    icon: "🔴",
  },
  othello6: {
    title: "Othello 6×6",
    desc: "Mini Othello — faster games on a smaller board!",
    icon: "🟤",
  },
  tictactoe: {
    title: "Tic Tac Toe",
    desc: "Get 3 in a row — can you beat the perfect bot?",
    icon: "❌",
  },
  sliding_puzzle: {
    title: "Sliding Puzzle",
    desc: "Slide tiles to arrange numbers 1-8 in order!",
    icon: "🧩",
  },
  circlecat: {
    title: "Circle the Cat",
    desc: "Place walls on a hex grid to trap the cat!",
    icon: "🐱",
  },
};

const categories = [
  {
    label: "2ⁿ Games",
    games: ["2048", "mergefall"],
  },
  {
    label: "Puzzle Games",
    games: ["nuts_bolts", "sokoban"],
  },
  {
    label: "1v1 vs Bot",
    games: ["fourinarow", "othello6", "tictactoe", "circlecat"],
  },
  {
    label: "Not Sure",
    games: ["sliding_puzzle"],
  },
];

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

    // Auto-login if player name saved in localStorage
    const saved = localStorage.getItem("evoplay_player");
    if (saved) {
      const loginRes = await fetch("/api/player/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: saved }),
      });
      const loginData = await loginRes.json();
      if (loginData.ok) {
        playerName.value = loginData.name;
        isLoggedIn.value = true;
      } else {
        localStorage.removeItem("evoplay_player");
      }
    }

    // Check URL parameters for game and session_id
    const params = new URLSearchParams(window.location.search);
    const urlGame = params.get("game");
    const urlSessionId = params.get("session_id");

    // If session_id is in URL, enter watch mode (bypass login)
    if (urlSessionId && urlGame && games.value.includes(urlGame)) {
      isWatchMode.value = true;
      currentGame.value = urlGame;
    } else if (urlGame && games.value.includes(urlGame)) {
      currentGame.value = urlGame;
    }
  } catch (e) {
    console.error("Failed to fetch games list", e);
  }
});
</script>

<template>
  <div class="app">
    <!-- ── Login screen (skip in watch mode) ─────────── -->
    <template v-if="!isLoggedIn && !isWatchMode">
      <div class="login-wrapper">
        <div class="login-card">
          <h1 class="login-title">EvoPlay</h1>
          <p class="login-subtitle">Enter your name to start playing</p>

          <div class="login-tabs">
            <button
              class="tab-btn"
              :class="{ active: loginMode === 'login' }"
              @click="loginMode = 'login'; loginError = ''"
            >Login</button>
            <button
              class="tab-btn"
              :class="{ active: loginMode === 'register' }"
              @click="loginMode = 'register'; loginError = ''"
            >Register</button>
          </div>

          <form class="login-form" @submit.prevent="handleLogin">
            <input
              v-model="loginInput"
              class="login-input"
              type="text"
              :placeholder="loginMode === 'register' ? 'Choose a unique name' : 'Your registered name'"
              maxlength="20"
              autofocus
            />
            <button class="login-btn" type="submit" :disabled="loginLoading">
              {{ loginLoading ? '...' : (loginMode === 'register' ? 'Register' : 'Login') }}
            </button>
          </form>

          <div v-if="loginError" class="login-error">{{ loginError }}</div>
        </div>
      </div>
    </template>

    <!-- ── Home menu ──────────────────────────────────── -->
    <template v-else-if="currentGame === null">
      <header class="home-header">
        <div class="home-top-bar">
          <h1>EvoPlay</h1>
          <div class="player-badge">
            <span class="player-name">{{ playerName }}</span>
            <button class="logout-btn" @click="handleLogout">Logout</button>
          </div>
        </div>
        <p class="subtitle">Pick a game to play</p>
      </header>

      <div class="categories">
        <div v-for="cat in categories" :key="cat.label" class="category">
          <div class="category-label">{{ cat.label }}</div>
          <div class="category-grid">
            <template v-if="cat.games.length > 0">
              <button
                v-for="g in cat.games"
                :key="g"
                class="game-card"
                @click="selectGame(g)"
              >
                <span class="game-icon">{{ gameInfo[g]?.icon || '🎮' }}</span>
                <span class="game-title">{{ gameInfo[g]?.title || g }}</span>
                <span class="game-desc">{{ gameInfo[g]?.desc || '' }}</span>
              </button>
            </template>
            <div v-else class="empty-slot">
              <span class="empty-icon">🔒</span>
              <span class="empty-text">More games coming...</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Game view ──────────────────────────────────── -->
    <template v-else>
      <header class="game-header">
        <button class="back-btn" @click="goHome">&larr; Home</button>
        <h2>{{ gameInfo[currentGame]?.title || currentGame }}</h2>
        <span v-if="isWatchMode" class="watch-tag">Watching</span>
        <span v-else class="player-tag">{{ playerName }}</span>
      </header>

      <main>
        <Game2048 v-if="currentGame === '2048'" :player-name="playerName" />
        <GameMergeFall v-else-if="currentGame === 'mergefall'" :player-name="playerName" />
        <GameNutsBolts v-else-if="currentGame === 'nuts_bolts'" :player-name="playerName" />
        <GameSokoban v-else-if="currentGame === 'sokoban'" :player-name="playerName" />
        <GameFourInARow v-else-if="currentGame === 'fourinarow'" :player-name="playerName" />
        <GameOthello6 v-else-if="currentGame === 'othello6'" :player-name="playerName" />
        <GameTicTacToe v-else-if="currentGame === 'tictactoe'" :player-name="playerName" />
        <GameSlidingPuzzle v-else-if="currentGame === 'sliding_puzzle'" :player-name="playerName" />
        <GameCircleCat v-else-if="currentGame === 'circlecat'" :player-name="playerName" />
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
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

/* ── Login screen ─────────────────────────────────── */

.login-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
}

.login-card {
  width: 100%;
  max-width: 360px;
  background: #1e293b;
  border: 2px solid #334155;
  border-radius: 16px;
  padding: 36px 28px;
  text-align: center;
}

.login-title {
  font-size: 2.2rem;
  font-weight: 800;
  color: #e2e8f0;
  letter-spacing: -0.02em;
}

.login-subtitle {
  margin-top: 6px;
  margin-bottom: 24px;
  font-size: 0.9rem;
  color: #64748b;
}

.login-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  background: #0f172a;
  border-radius: 10px;
  padding: 3px;
}

.tab-btn {
  flex: 1;
  padding: 8px 0;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.tab-btn.active {
  background: #334155;
  color: #f1f5f9;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.login-input {
  width: 100%;
  padding: 12px 14px;
  border: 2px solid #334155;
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 1rem;
  outline: none;
  transition: border-color 0.15s;
}

.login-input:focus {
  border-color: #4ade80;
}

.login-input::placeholder {
  color: #475569;
}

.login-btn {
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: #166534;
  color: #fff;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
}

.login-btn:hover:not(:disabled) {
  background: #15803d;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-error {
  margin-top: 12px;
  font-size: 0.85rem;
  color: #f87171;
}

/* ── Home menu ────────────────────────────────────── */

.home-header {
  text-align: center;
  margin-bottom: 32px;
  padding-top: 24px;
}

.home-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.home-top-bar h1 {
  font-size: 2.4rem;
  font-weight: 800;
  color: #e2e8f0;
  letter-spacing: -0.02em;
}

.player-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 20px;
  padding: 5px 6px 5px 14px;
}

.player-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #4ade80;
}

.logout-btn {
  padding: 4px 10px;
  border: 1px solid #475569;
  border-radius: 14px;
  background: transparent;
  color: #94a3b8;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.15s;
}

.logout-btn:hover {
  border-color: #f87171;
  color: #f87171;
}

.player-tag {
  margin-left: auto;
  font-size: 0.8rem;
  color: #4ade80;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 3px 10px;
}

.watch-tag {
  margin-left: auto;
  font-size: 0.8rem;
  color: #38bdf8;
  background: #1e293b;
  border: 1px solid #0ea5e9;
  border-radius: 12px;
  padding: 3px 10px;
}

.subtitle {
  margin-top: 6px;
  font-size: 1rem;
  color: #64748b;
}

.categories {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.category-label {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #475569;
  margin-bottom: 10px;
  padding-left: 2px;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.game-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 18px 12px;
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
  font-size: 1.8rem;
}

.game-title {
  font-size: 1rem;
  font-weight: 700;
  color: #f1f5f9;
}

.game-desc {
  font-size: 0.75rem;
  color: #94a3b8;
  line-height: 1.4;
}

.empty-slot {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 18px 12px;
  border: 2px dashed #1e293b;
  border-radius: 14px;
  grid-column: 1 / -1;
}

.empty-icon {
  font-size: 1.6rem;
  opacity: 0.4;
}

.empty-text {
  font-size: 0.8rem;
  color: #334155;
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
