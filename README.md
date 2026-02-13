# EvoPlay

EvoPlay is a lightweight game server framework that supports interactions between human players and AI agents. The project uses a frontend-backend separation architecture, providing a unified game interface and logging functionality.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Code Architecture](#code-architecture)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Adding New Games](#adding-new-games)
- [Project Structure](#project-structure)

## Project Overview

EvoPlay is a game platform that currently supports the following games:

- **2048**: Classic sliding number puzzle game
- **MergeFall**: Drop-and-merge elimination game

Project Features:
- 🎮 Unified game interface, easy to extend with new games
- 📊 Automatic game logging (JSONL format)
- 🔄 Session-based multi-instance management
- 🌐 RESTful API design
- 💻 Modern Vue 3 frontend interface

## Code Architecture

### Overall Architecture

```
┌─────────────────┐
│   Frontend      │  Vue 3 + Vite
│   (Port 3000)   │  └─ Components: Game2048, GameMergeFall, GameLog
└────────┬────────┘
         │ HTTP/API
         │
┌────────▼────────┐
│   Backend       │  Flask (Port 5001)
│   app.py        │  └─ Routes: /api/games, /api/game/<name>/...
└────────┬────────┘
         │
┌────────▼────────┐
│   Games Layer   │  BaseGame (Abstract Base Class)
│   games/        │  ├─ Game2048
│                 │  └─ MergeFall
└─────────────────┘
```

### Core Components Breakdown

#### 1. Backend Architecture (`backend/`)

**`app.py` - Flask Application Main File**
- **Purpose**: Provides RESTful API services
- **Core Features**:
  - Game Registry (`GAMES`): Manages all available games
  - Session Management (`sessions`): Stores game instances using `(game_name, session_id)` as keys
  - API Routes: Provides interfaces for game state, actions, reset, etc.
  - CORS Support: Allows cross-origin requests from frontend

**Key Functions**:
- `_get_session_id()`: Extracts or generates session_id from request
- `_get_game()`: Gets or creates game instance
- `_log_action()`: Logs game action

**`games/base.py` - Game Base Class**
- **Purpose**: Defines abstract interface that all games must implement
- **Interface Methods**:
  - `get_state()`: Returns current game state as JSON-friendly dict
  - `apply_action(action)`: Executes action and returns new state
  - `reset()`: Resets game to initial state
  - `valid_actions()`: Returns list of currently executable actions

**Built-in Features**:
- Automatic Logging: Each game session automatically writes to `logs/<game_name>/<timestamp>.jsonl`
- Log Metadata: Records steps, elapsed time, action history, etc.

**`games/game_2048.py` - 2048 Game Implementation**
- **Inherits**: `BaseGame`
- **Game Logic**:
  - 4x4 grid, slide and merge identical numbers
  - Supports four directions: up, down, left, right
  - Auto-generates new tiles (90% chance of 2, 10% chance of 4)
  - Detects game over and win conditions (reaching 2048)

**`games/game_mergefall.py` - MergeFall Game Implementation**
- **Inherits**: `BaseGame`
- **Game Logic**:
  - 5x6 grid, drop-and-merge elimination
  - Action format: `"drop <column>"` (e.g., "drop 0")
  - Supports chain merging and combo scoring
  - Dynamically generates next tile (based on current maximum tile value)

#### 2. Frontend Architecture (`frontend/`)

**`src/App.vue` - Main Application Component**
- **Purpose**: Application entry point, manages game selection and routing
- **Features**:
  - Game list display
  - Game switching navigation
  - Fetches available games list from backend

**`src/components/Game2048.vue` - 2048 Game Component**
- **Features**:
  - Game interface rendering
  - Keyboard event handling (arrow keys)
  - Backend API interaction
  - Displays score, game state, action log

**`src/components/GameMergeFall.vue` - MergeFall Game Component**
- **Features**: Similar to Game2048, but customized for MergeFall game logic

**`src/components/GameLog.vue` - Game Log Component**
- **Features**: Displays game action history

**`src/utils/session.js` - Session Management Utility**
- **Features**:
  - Uses localStorage to store session_id for each game
  - Generates and manages session_id
  - URL parameter handling

**`vite.config.js` - Vite Configuration**
- **Features**:
  - Development server configuration (port 3000)
  - API Proxy: `/api` requests proxied to `http://localhost:5001`

### Data Flow

```
User Action
  ↓
Frontend Component (Game2048.vue / GameMergeFall.vue)
  ↓
fetch API Call
  ↓
Vite Proxy (/api → localhost:5001)
  ↓
Flask Route Handler (app.py)
  ↓
Game Instance (Game2048 / MergeFall)
  ↓
State Update + Logging
  ↓
Return JSON Response
  ↓
Frontend Updates UI
```

### Session Management Mechanism

1. **Frontend**: Uses `session.js` to store session_id for each game in localStorage
2. **Backend**: Uses `(game_name, session_id)` tuple as key to store game instances
3. **Multi-instance**: Each browser tab/device can have independent game sessions
4. **Persistence**: Session ID saved in browser localStorage, can continue game after page refresh

### Logging System

- **Location**: `backend/logs/<game_name>/<timestamp>.jsonl`
- **Format**: JSON Lines (one JSON object per line)
- **Content**: Step number, timestamp, action, score, game state, board state
- **Usage**: Can be used for game replay, AI training data analysis, etc.

## Quick Start

### Requirements

- **Python**: 3.8+
- **Node.js**: 16+
- **npm** or **yarn**

### Installation Steps

#### 1. Clone the Project

```bash
git clone <repository-url>
cd EvoPlay
```

#### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Or use a virtual environment (recommended):

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Install Frontend Dependencies

```bash
cd ../frontend
npm install
```

### Running the Project

#### Method 1: Start Separately (Recommended for Development)

**Terminal 1 - Start Backend Server**:
```bash
cd backend
python app.py
```

Backend will start at `http://localhost:5001`.

**Terminal 2 - Start Frontend Development Server**:
```bash
cd frontend
npm run dev
```

Frontend will start at `http://localhost:3000`.

Open your browser and visit `http://localhost:3000` to start playing.

#### Method 2: Using Scripts (Optional)

You can create startup scripts to automate this process:

**`start.sh` (macOS/Linux)**:
```bash
#!/bin/bash
# Start backend
cd backend && python app.py &
BACKEND_PID=$!

# Start frontend
cd frontend && npm run dev &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop both servers"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
```

**`start.bat` (Windows)**:
```batch
@echo off
start "Backend" cmd /k "cd backend && python app.py"
start "Frontend" cmd /k "cd frontend && npm run dev"
```

### Verify Installation

1. Open browser and visit `http://localhost:3000`
2. You should see the game selection interface
3. Click on any game, it should load and operate normally

## API Documentation

### Base URL

```
http://localhost:5001
```

### Endpoints

#### 1. Get Game List

```http
GET /api/games
```

**Response**:
```json
{
  "games": ["2048", "mergefall"]
}
```

#### 2. Get Game State

```http
GET /api/game/<name>/state?session_id=<session_id>
```

**Parameters**:
- `name`: Game name (e.g., "2048", "mergefall")
- `session_id`: Session ID (required)

**Response Example (2048)**:
```json
{
  "game": "2048",
  "board": [[2, 4, 0, 0], [0, 2, 4, 0], ...],
  "score": 100,
  "game_over": false,
  "won": false,
  "valid_actions": ["up", "down", "left", "right"],
  "session_id": "s_1234567890_abc123"
}
```

#### 3. Execute Game Action

```http
GET /api/game/<name>/action?move=<action>&session_id=<session_id>
```

**Parameters**:
- `name`: Game name
- `move`: Action command
  - 2048: `"up"`, `"down"`, `"left"`, `"right"`
  - MergeFall: `"drop 0"`, `"drop 1"`, ... (0-4)
- `session_id`: Session ID (optional, will be auto-generated if not provided)

**Response**: Same as game state response

#### 4. Reset Game

```http
GET /api/game/<name>/reset?session_id=<session_id>
```

**Parameters**:
- `name`: Game name
- `session_id`: Session ID (optional)

**Response**: Reset game state

#### 5. Get Valid Actions

```http
GET /api/game/<name>/valid_actions?session_id=<session_id>
```

**Parameters**:
- `name`: Game name
- `session_id`: Session ID (required)

**Response**:
```json
{
  "valid_actions": ["up", "down", "left", "right"],
  "session_id": "s_1234567890_abc123"
}
```

#### 6. Get Game Log

```http
GET /api/game/<name>/log?session_id=<session_id>
```

**Parameters**:
- `name`: Game name
- `session_id`: Session ID (required)

**Response**:
```json
{
  "steps": 42,
  "elapsed_seconds": 120.5,
  "log": [
    {
      "step": 1,
      "time": 0.0,
      "action": "up",
      "score": 4,
      "game_over": false,
      "board": [[...]]
    },
    ...
  ],
  "session_id": "s_1234567890_abc123"
}
```

## Adding New Games

### Step 1: Create Game Class

Create a new file in `backend/games/` directory, for example `game_snake.py`:

```python
from .base import BaseGame
from typing import Any

class SnakeGame(BaseGame):
    name = "snake"
    
    def __init__(self):
        # Initialize game state
        self.board = []
        self.score = 0
        self.game_over = False
        self._reset_log()
        self.reset()
    
    def get_state(self) -> dict[str, Any]:
        return {
            "game": self.name,
            "board": self.board,
            "score": self.score,
            "game_over": self.game_over,
            "valid_actions": self.valid_actions(),
        }
    
    def apply_action(self, action: str) -> dict[str, Any]:
        # Implement game logic
        # ...
        state = self.get_state()
        self._record_log(action, state)
        return state
    
    def reset(self) -> dict[str, Any]:
        # Reset to initial state
        # ...
        self._reset_log()
        return self.get_state()
    
    def valid_actions(self) -> list[str]:
        # Return list of valid actions
        return ["up", "down", "left", "right"]
```

### Step 2: Register Game

In `backend/app.py`:

```python
from games.game_snake import SnakeGame

GAMES: dict[str, type] = {
    "2048": Game2048,
    "mergefall": MergeFall,
    "snake": SnakeGame,  # Add your game here
}
```

### Step 3: Create Frontend Component

Create `GameSnake.vue` in `frontend/src/components/`, refer to `Game2048.vue` structure.

### Step 4: Add to Main App

In `frontend/src/App.vue`:

```vue
<script setup>
import GameSnake from "./components/GameSnake.vue";
// ...

const gameInfo = {
  // ...
  snake: {
    title: "Snake",
    desc: "Classic snake game",
    icon: "🐍",
  },
};
</script>

<template>
  <!-- ... -->
  <GameSnake v-else-if="currentGame === 'snake'" />
</template>
```

## Project Structure

```
EvoPlay/
├── backend/                 # Backend service
│   ├── app.py              # Flask application main file
│   ├── requirements.txt     # Python dependencies
│   ├── games/              # Game implementations
│   │   ├── __init__.py
│   │   ├── base.py         # Game base class
│   │   ├── game_2048.py    # 2048 game
│   │   └── game_mergefall.py # MergeFall game
│   └── logs/               # Game logs directory
│       ├── 2048/
│       └── mergefall/
│
├── frontend/               # Frontend application
│   ├── package.json        # Node.js dependencies
│   ├── vite.config.js      # Vite configuration
│   ├── index.html          # HTML entry point
│   └── src/
│       ├── main.js         # Vue application entry
│       ├── App.vue         # Main application component
│       ├── components/     # Game components
│       │   ├── Game2048.vue
│       │   ├── GameMergeFall.vue
│       │   └── GameLog.vue
│       └── utils/
│           └── session.js  # Session management utility
│
└── README.md               # Project documentation
```

## Development Tips

### Debugging

- **Backend**: Flask runs in debug mode by default, auto-reloads on code changes
- **Frontend**: Vite supports Hot Module Replacement (HMR), changes take effect immediately
- **Logs**: Check JSONL files in `backend/logs/` directory to understand game history

### Common Issues

1. **Port already in use**: Modify port number in `app.py` or port configuration in `vite.config.js`
2. **CORS errors**: Ensure `flask-cors` is installed and CORS is enabled in `app.py`
3. **Session lost**: Check if browser localStorage was cleared

### Performance Optimization

- For production, consider using Gunicorn to run Flask application
- Frontend: use `npm run build` to build production version
- Consider adding Redis for session persistence (currently in-memory storage)

## License

[Add your license information]

## Contributing

Issues and Pull Requests are welcome!
