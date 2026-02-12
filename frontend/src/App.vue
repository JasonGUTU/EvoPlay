<script setup>
import { ref, onMounted } from "vue";
import Game2048 from "./components/Game2048.vue";

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
  background: #faf8ef;
  color: #776e65;
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
  color: #776e65;
}

select {
  padding: 6px 12px;
  border-radius: 6px;
  border: 2px solid #bbada0;
  font-size: 1rem;
  background: #fff;
  color: #776e65;
}
</style>
