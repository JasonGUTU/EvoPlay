<script setup>
import { ref, onMounted } from "vue";
import Game2048 from "./components/Game2048.vue";
import GameMergeFall from "./components/GameMergeFall.vue";

const games = ref([]);
const selectedGame = ref("2048");

onMounted(async () => {
  try {
    const res = await fetch("/api/games");
    const data = await res.json();
    games.value = data.games;
  } catch (e) {
    console.error("Failed to fetch games list", e);
  }
});
</script>

<template>
  <div class="app">
    <header>
      <h1>EvoPlay</h1>
      <nav>
        <label>Game:
          <select v-model="selectedGame">
            <option v-for="g in games" :key="g" :value="g">{{ g }}</option>
          </select>
        </label>
      </nav>
    </header>

    <main>
      <Game2048 v-if="selectedGame === '2048'" />
      <GameMergeFall v-else-if="selectedGame === 'mergefall'" />
    </main>
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

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #e2e8f0;
}

select {
  padding: 6px 12px;
  border-radius: 6px;
  border: 2px solid #475569;
  font-size: 1rem;
  background: #1e293b;
  color: #e2e8f0;
}
</style>
