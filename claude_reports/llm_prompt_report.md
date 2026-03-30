# EvoPlay LLM Prompt 报告

本报告记录 EvoPlay 平台中 8 个游戏调用大语言模型时，给模型提供了哪些信息，以及这些信息的具体形式。每个游戏均附带一个**真实完整 prompt 示例**，即实际传给模型的 System Message + User Prompt。

---

## 1. 通用 Prompt 结构

每次调用 LLM 时，发送两部分信息：**System Message** 和 **User Prompt**。

### System Message（固定不变）

```
You are a game-playing AI agent. Respond with only the action string.
```

### User Prompt（每步动态生成）

由以下 4 个信息块拼接而成：

| 信息块 | 内容 | 来源 |
|--------|------|------|
| **游戏规则** | 游戏目标、玩法、操作格式 | 每个游戏的 `get_rules()` 方法，固定文本 |
| **当前棋盘** | 数字矩阵，空格分隔 | `get_state()` 返回的 `board` 字段 |
| **当前分数** | 单个数字或字符串 | `get_state()` 返回的 `score` 字段 |
| **合法操作列表** | 逗号分隔的字符串列表 | `valid_actions()` 方法的返回值 |

MergeFall 额外提供一个信息：**下一个方块的数值**（`next_tile`）。

完整模板（代码位于 `agent/reasoning/vanilla_reasoning.py`）：

```
You are playing the game "{游戏名}".

GAME RULES:
{规则全文}

Current board:
{棋盘矩阵}
Score: {分数}
{额外信息（如有）}
IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[{合法操作列表}]

Pick the best action. Respond with ONLY the action string, nothing else.
```

---

## 2. 各游戏完整 Prompt 示例

以下每个游戏给出一个**真实场景**下传给模型的完整输入（System Message + User Prompt），与代码实际拼接结果一致。

---

### 2.1 2048

**场景描述**：游戏中局，已有若干方块，分数 24，只有三个方向可移动。

**System Message：**

```
You are a game-playing AI agent. Respond with only the action string.
```

**User Prompt：**

```
You are playing the game "2048".

GAME RULES:
2048 Game Rules

OBJECTIVE:
The goal is to slide numbered tiles on a 4x4 grid to combine them and create a tile with the number 2048. You win when you reach 2048, but you can continue playing to achieve higher scores.

GAMEPLAY:
- You start with a 4x4 grid containing two tiles (either 2 or 4).
- On each turn, you slide all tiles in one of four directions: up, down, left, or right.
- When you slide, all tiles move as far as possible in that direction until they hit the edge or another tile.
- If two tiles with the same number collide while moving, they merge into a single tile with double the value.
- After each move, a new tile (either 2 or 4) appears in a random empty cell.

AVAILABLE ACTIONS:
You can choose one of four directions:
- "up": Slide all tiles upward
- "down": Slide all tiles downward
- "left": Slide all tiles to the left
- "right": Slide all tiles to the right

Note: Only actions that would actually change the board state are valid. If a direction would not move any tiles, that action is not available.

GAME OVER CONDITIONS:
The game ends when:
1. The board is completely filled with tiles, AND
2. No valid moves are possible (no tiles can merge in any direction)

When the game is over, you cannot make any more moves. Your final score is the sum of all merged tile values.


Current board:
0 0 2 0
0 0 0 0
0 4 0 2
0 0 2 4
Score: 24

IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[up, down, left]

Pick the best action. Respond with ONLY the action string, nothing else.
```

**模型不知道的信息**：
- 当前难度设置（Easy/Medium/Hard 影响的是新方块出 4 的概率）
- 下一步会生成什么方块、生成在哪个位置

---

### 2.2 MergeFall

**场景描述**：游戏中局，底部有一些方块，下一个要掉落的方块是 4，分数 36。

**System Message：**

```
You are a game-playing AI agent. Respond with only the action string.
```

**User Prompt：**

```
You are playing the game "mergefall".

GAME RULES:
MergeFall Game Rules

OBJECTIVE:
Drop numbered tiles into columns to create chains of merges and combos. Your goal is to achieve the highest score possible by strategically placing tiles and triggering cascading merges.

GAMEPLAY:
- You have a 5x6 grid (5 columns, 6 visible rows).
- Each turn, you choose a column (0-4) to drop the next tile into.
- The tile falls down the column and lands on top of existing tiles or at the bottom.
- After dropping, the game automatically resolves merges and gravity:
  1. Gravity: All tiles fall down to fill empty spaces.
  2. Merging: If the dropped tile has any adjacent tiles (up/down/left/right) with the same value, it absorbs all such neighbors in its immediate 4-neighborhood.
  3. The merged tile's value upgrades based on how many tiles were absorbed.
  4. After merging, gravity applies again, and the process repeats until no more merges are possible.
- Your score increases based on the final merged tile value multiplied by the combo count.

AVAILABLE ACTIONS:
You can drop a tile into any of the 5 columns using the format "drop <column_number>":
- "drop 0": Drop into the leftmost column (column 0)
- "drop 1": Drop into the second column (column 1)
- "drop 2": Drop into the middle column (column 2)
- "drop 3": Drop into the fourth column (column 3)
- "drop 4": Drop into the rightmost column (column 4)

You can also use just the number: "0", "1", "2", "3", or "4" as shorthand.

GAME OVER CONDITIONS:
The game ends when:
- After dropping a tile and resolving all merges, any tile remains in the overflow row (above the visible 6 rows).
- This happens when a column becomes completely full and cannot accommodate the dropped tile.

Note: Even if a column looks full, dropping into it might trigger merges that clear space. However, if the column is truly full (including the overflow row), the game ends immediately.


Current board:
0 0 0 0 0
0 0 0 0 0
0 0 0 0 0
0 0 0 0 0
0 4 0 0 0
2 8 2 0 0
Score: 36

Next tile to drop: 4

IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[drop 0, drop 1, drop 2, drop 3, drop 4]

Pick the best action. Respond with ONLY the action string, nothing else.
```

**模型不知道的信息**：
- 当前难度设置（影响生成方块的数值分布）
- 未来会生成什么方块（只知道当前这一个 next_tile）

---

### 2.3 Four in a Row

**场景描述**：游戏进行了几步，LLM（玩家 1）和 Bot（玩家 2）各下了几子。

**System Message：**

```
You are a game-playing AI agent. Respond with only the action string.
```

**User Prompt：**

```
You are playing the game "fourinarow".

GAME RULES:
Four in a Row (Connect Four) Game Rules

OBJECTIVE:
Drop pieces into a 6-row × 7-column vertical grid. First player to connect 4 of their pieces in a row (horizontally, vertically, or diagonally) wins.

PLAYERS:
- You are player 1 (displayed as "1" on the board). You move first each turn.
- The bot is player 2 (displayed as "2" on the board). It moves automatically after you.

BOARD:
- The board is a 6×7 grid. Row 0 is the top, row 5 is the bottom.
- Empty cells are 0, your pieces are 1, bot pieces are 2.
- Pieces obey gravity: they fall to the lowest empty cell in the chosen column.

AVAILABLE ACTIONS:
- You will be given a list of valid columns. You MUST pick exactly one from that list — do NOT invent your own.
- Choose a column number from 0 to 6 (e.g., "3" to drop in the center column).
- A column is only valid if it is not completely filled (row 0 is not occupied).

GAME OVER CONDITIONS:
- You win if you connect 4 of your pieces in any direction.
- Bot wins if it connects 4 of its pieces.
- Draw if the board is completely filled with no winner.

Respond with ONLY the column number (e.g., "3").


Current board:
0 0 0 0 0 0 0
0 0 0 0 0 0 0
0 0 0 0 0 0 0
0 0 0 0 0 0 0
0 0 0 1 0 0 0
0 0 2 1 2 0 0
Score: 0

IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[0, 1, 2, 3, 4, 5, 6]

Pick the best action. Respond with ONLY the action string, nothing else.
```

**模型不知道的信息**：
- Bot 使用的算法和搜索深度（Easy = 规则启发，Medium = Minimax 深度 3，Hard = 深度 5）
- Bot 的下一步落子位置

---

### 2.4 Othello 6×6

**场景描述**：游戏开局，棋盘中央有初始 4 子，LLM 执黑先手，有 4 个合法落子位置。

**System Message：**

```
You are a game-playing AI agent. Respond with only the action string.
```

**User Prompt：**

```
You are playing the game "othello6".

GAME RULES:
Othello 6×6 (Mini Reversi) Game Rules

OBJECTIVE:
Place pieces on a 6×6 board to outflank and flip your opponent's pieces. The player with the most pieces when the game ends wins.

PLAYERS:
- You are Black (displayed as "1" on the board). You move first.
- The bot is White (displayed as "2" on the board). It moves automatically after you.

BOARD:
- 6×6 grid. Empty cells are 0, your pieces are 1, bot pieces are 2.
- The game starts with 4 pieces in the center: two of each color in a diagonal pattern.

HOW FLIPPING WORKS:
- When you place a piece, ALL straight lines (horizontal, vertical, diagonal) from that piece through one or more consecutive opponent pieces to another one of your pieces will flip those opponent pieces to your color.
- You MUST flip at least one opponent piece — you cannot place a piece that flips nothing.

AVAILABLE ACTIONS:
- You will be given a list of valid moves. You MUST pick exactly one from that list — do NOT invent your own position.
- Action format: "row col" (0-indexed). For example, "1 3" means row 1, column 3.
- Only positions that flip at least one opponent piece are valid moves.

GAME OVER CONDITIONS:
- The game ends when neither player has a valid move (usually when the board is full).
- The player with more pieces wins. Equal counts result in a draw.

Respond with ONLY "row col" (e.g., "1 3").


Current board:
0 0 0 0 0 0
0 0 0 0 0 0
0 0 2 1 0 0
0 0 1 2 0 0
0 0 0 0 0 0
0 0 0 0 0 0
Score: 2:2

IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[1 2, 2 1, 3 4, 4 3]

Pick the best action. Respond with ONLY the action string, nothing else.
```

**模型不知道的信息**：
- Bot 使用的评估函数（Easy = 随机，Medium = 位置权重矩阵，Hard = 位置权重 + 行动力）
- Bot 的搜索深度和具体策略

---

### 2.5 Tic Tac Toe

**场景描述**：游戏中局，LLM（X=1）和 Bot（O=2）各下了两步，还有 5 个空位。

**System Message：**

```
You are a game-playing AI agent. Respond with only the action string.
```

**User Prompt：**

```
You are playing the game "tictactoe".

GAME RULES:
Tic Tac Toe Game Rules

OBJECTIVE:
Place your marks on a 3×3 grid. First player to get 3 in a row (horizontally, vertically, or diagonally) wins.

PLAYERS:
- You are X (displayed as "1" on the board). You move first.
- The bot is O (displayed as "2" on the board). It moves automatically after you.

BOARD:
- 3×3 grid. Empty cells are 0, your marks are 1, bot marks are 2.
- Positions are referenced by row and column (0-indexed):
    (0,0) | (0,1) | (0,2)
    ------+-------+------
    (1,0) | (1,1) | (1,2)
    ------+-------+------
    (2,0) | (2,1) | (2,2)

AVAILABLE ACTIONS:
- You will be given a list of valid positions. You MUST pick exactly one from that list — do NOT invent your own.
- Action format: "row col" (e.g., "1 1" for the center cell).
- You can only place on empty cells (value 0).

GAME OVER CONDITIONS:
- You win by getting 3 of your marks in a row (any direction).
- Bot wins by getting 3 of its marks in a row.
- Draw if all 9 cells are filled with no winner.

Respond with ONLY "row col" (e.g., "1 1").


Current board:
1 0 2
0 1 0
0 0 2
Score: 0

IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[0 1, 1 0, 1 2, 2 0, 2 1]

Pick the best action. Respond with ONLY the action string, nothing else.
```

**模型不知道的信息**：
- Bot 使用的算法（Easy = 随机，Medium = 赢/堵启发，Hard = 完整 Minimax 不可战胜）

---

### 2.6 Sliding Puzzle

**场景描述**：8-puzzle 游戏开局，方块被打乱，空格（0）在中间，已走 3 步。

**System Message：**

```
You are a game-playing AI agent. Respond with only the action string.
```

**User Prompt：**

```
You are playing the game "sliding_puzzle".

GAME RULES:
Sliding Puzzle (8-Puzzle) Game Rules

OBJECTIVE:
Arrange the numbered tiles 1-8 in order by sliding them into the empty space. The goal state is:
  1 2 3
  4 5 6
  7 8 _
where _ is the empty space (shown as 0 on the board).

GAMEPLAY:
- The board is a 3×3 grid with tiles numbered 1-8 and one empty space (0).
- Each turn, you slide one tile adjacent to the empty space into it.
- The direction you choose refers to which direction a tile moves INTO the empty space:
  - "up": the tile BELOW the blank slides up
  - "down": the tile ABOVE the blank slides down
  - "left": the tile to the RIGHT of the blank slides left
  - "right": the tile to the LEFT of the blank slides right

AVAILABLE ACTIONS:
- You will be given a list of valid directions. You MUST pick exactly one from that list.
- Directions: "up", "down", "left", "right"
- Not all directions are available every turn (depends on blank position).

GAME OVER CONDITIONS:
- You win when all tiles are in the goal arrangement.
- There is no losing — only the number of moves matters (lower is better).

Respond with ONLY the direction (e.g., "up").


Current board:
1 2 3
4 0 6
7 5 8
Score: 3

IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[up, down, left, right]

Pick the best action. Respond with ONLY the action string, nothing else.
```

**模型不知道的信息**：
- 最优解的步数
- 当前难度设置（影响初始打乱的步数）

---

### 2.7 Nuts and Bolts

**场景描述**：Level 1，5 根螺丝（容量 3），3 根装有混色螺母，2 根空。模型需要选择移动操作。

**System Message：**

```
You are a game-playing AI agent. Respond with only the action string.
```

**User Prompt：**

```
You are playing the game "nuts_bolts".

GAME RULES:
Nuts and Bolts Game Rules

OBJECTIVE:
Sort all the colored nuts so that each screw contains only one color of nuts.

GAMEPLAY:
- You have 5 screws. Originally, 3 screws are filled with mixed nuts, and 2 are empty.
- Each screw can hold up to 3 nuts format Level 1 and 4 for Level 2.
- You can move the top nut from one screw to another.
- A nut can only be moved onto an empty screw, OR onto a screw where the top nut is the SAME COLOR.
- You cannot move a nut onto a full screw.
- You have 2 Undo moves available per game.

AVAILABLE ACTIONS:
- "select_X": Selects screw X (0-4 or 0-5) as a source, or moves the previously selected nut to screw X.
- "undo": Reverts the last move.
- "next_level": Go to the next level when won.


Current board:
r b g
g r b
b g r


Score: 0

IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[move_0_3, move_0_4, move_1_3, move_1_4, move_2_3, move_2_4, undo]

Pick the best action. Respond with ONLY the action string, nothing else.
```

**说明**：棋盘中每行代表一根螺丝上的螺母（从底到顶），颜色用单字母编码（r=红, b=蓝, g=绿 等）。`move_A_B` 表示把螺丝 A 顶部的螺母移到螺丝 B。

**模型不知道的信息**：
- 当前关卡和总关卡数
- 剩余 undo 次数（不在棋盘中体现）
- 螺丝容量上限

---

### 2.8 Sokoban

**场景描述**：推箱子游戏，玩家在地图中，需要把箱子推到目标位置。

**System Message：**

```
You are a game-playing AI agent. Respond with only the action string.
```

**User Prompt：**

```
You are playing the game "sokoban".

GAME RULES:
Sokoban Game Rules

OBJECTIVE:
Push all boxes onto the goal squares.

GAMEPLAY:
- You control the player character (hardhat worker).
- You can move up, down, left, or right into empty spaces.
- You can push a single box by moving into it, provided the space behind the box is empty or a goal.
- You CANNOT pull boxes.
- You CANNOT push a box into a wall, the rope obstacle, or another box.
- You have 1 Undo available per game.

AVAILABLE ACTIONS:
- "up", "down", "left", "right": Move the player or push a box.
- "undo": Reverts the last move.


Current board:
{'map': [['#', '#', '#', '#', '#'], ['#', ' ', ' ', '.', '#'], ['#', ' ', ' ', ' ', '#'], ['#', ' ', ' ', ' ', '#'], ['#', '#', '#', '#', '#']], 'player_pos': [2, 1], 'boxes': [[2, 2], [3, 2]]}
Score: 0

IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[up, down, left, right, undo]

Pick the best action. Respond with ONLY the action string, nothing else.
```

**说明**：Sokoban 的棋盘是一个字典结构（包含 `map`、`player_pos`、`boxes`），直接被 `str()` 序列化后传给模型。`map` 中 `#`=墙，` `=地板，`.`=目标格，`O`=绳索障碍，`W`=水障碍。`player_pos` 为玩家坐标 `[行, 列]`，`boxes` 为所有箱子坐标列表。

**模型不知道的信息**：
- 最优解路径
- 当前关卡编号
- 是否还有 undo 可用

---

## 3. 信息汇总对比

| 游戏 | 棋盘尺寸 | 棋盘编码 | 操作格式 | 操作数量 | 额外信息 |
|------|---------|---------|---------|---------|---------|
| 2048 | 4×4 | 0=空, 数字=方块值 | `"方向"` | 1-4 | 无 |
| MergeFall | 6×5 | 0=空, 数字=方块值 | `"drop N"` | 5 | next_tile |
| Four in a Row | 6×7 | 0=空, 1=玩家, 2=Bot | `"列号"` | 1-7 | 无 |
| Othello 6×6 | 6×6 | 0=空, 1=黑, 2=白 | `"行 列"` 或 `"pass"` | 1-12 | 无 |
| Tic Tac Toe | 3×3 | 0=空, 1=X, 2=O | `"行 列"` | 1-9 | 位置参考图 |
| Sliding Puzzle | 3×3 | 0=空, 1-8=方块编号 | `"方向"` | 2-4 | 无 |
| Nuts and Bolts | N根螺丝 | 颜色字母列表 | `"move_A_B"` | 变化 | 无 |
| Sokoban | 变化 | 字典（map+坐标） | `"方向"` 或 `"undo"` | 2-5 | 无 |

### 所有游戏共同提供的信息：
1. 游戏名称
2. 完整规则文本（固定）
3. 当前棋盘状态（每步更新）
4. 当前分数
5. 合法操作列表（每步更新）

### 所有游戏共同**不**提供的信息：
1. 历史走法记录（模型只看当前局面）
2. 对手的算法和策略
3. 当前难度设置
4. 未来的随机事件（如 2048 的新方块位置）
