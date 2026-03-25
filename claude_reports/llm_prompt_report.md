# EvoPlay LLM Prompt 报告

本报告记录 EvoPlay 平台中各游戏调用大语言模型时使用的 prompt 结构。所有游戏共享同一套 prompt 框架（定义在 `agent/reasoning/vanilla_reasoning.py`），但各游戏通过 `get_rules()` 提供不同的规则文本。

---

## 1. Prompt 框架

### 1.1 System Message

```
You are a game-playing AI agent. Respond with only the action string.
```

**说明**：System message 极简，仅告知模型角色和输出格式要求。

### 1.2 User Prompt 模板

```
You are playing the game "{game_name}".

GAME RULES:
{rules}

Current board:
{formatted_board}
Score: {score}

IMPORTANT: You MUST choose exactly one action from this list (copy it exactly):
[{valid_actions}]

Pick the best action. Respond with ONLY the action string, nothing else.
```

**说明**：

- `{game_name}`：游戏名称，如 `"othello6"`, `"tictactoe"` 等
- `{rules}`：由各游戏的 `get_rules()` 方法返回，包含完整的规则描述、棋盘说明、可用操作格式和策略提示
- `{formatted_board}`：当前棋盘状态，2D 棋盘以空格分隔的数字矩阵呈现（如 `0 0 1\n0 2 0\n1 0 0`）
- `{score}`：当前分数
- `{valid_actions}`：合法操作列表，逗号分隔（如 `1 2, 3 4, 4 3`）
- 末尾强调"必须从列表中选择"和"只返回 action 字符串"

### 1.3 输出验证与 Fallback

模型返回后，系统执行以下验证：

1. `strip()` 去除首尾空白
2. 检查是否在 `valid_actions` 列表中
3. 若匹配失败，fallback 到 `valid_actions[0]`（列表第一个合法操作）
4. 记录 `raw_response`、`parsed_action`、`fallback` 到 `llm_logs/` CSV 文件

---

## 2. 各游戏 Rules Prompt

### 2.1 2048

**游戏类型**：单人滑块合并游戏（4×4 棋盘）

**动作空间**：`["up", "down", "left", "right"]` 的子集（仅包含能改变棋盘的方向）

**Rules Prompt**：

```
2048 Game Rules

OBJECTIVE:
The goal is to slide numbered tiles on a 4x4 grid to combine them and create a tile with the number 2048. You win when you reach 2048, but you can continue playing to achieve higher scores.

GAMEPLAY:
- You start with a 4x4 grid containing two tiles (either 2 or 4).
- On each turn, you slide all tiles in one of four directions: up, down, left, or right.
- When you slide, all tiles move as far as possible in that direction until they hit the edge or another tile.
- If two tiles with the same number collide while moving, they merge into a single tile with double the value.
- After each move, a new tile (either 2 with 90% probability or 4 with 10% probability) appears in a random empty cell.

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
```

**Prompt 特点**：
- 动作空间最小（最多 4 个方向），模型出错概率低
- 没有对手，纯策略优化问题
- 模型需要理解"合并"和"重力"机制来做出好的决策

---

### 2.2 MergeFall

**游戏类型**：单人掉落合并游戏（5×6 棋盘）

**动作空间**：`["drop 0", "drop 1", "drop 2", "drop 3", "drop 4"]`

**Rules Prompt**：

```
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
```

**Prompt 特点**：
- 动作空间固定为 5 个列，格式为 `"drop N"`
- 合并机制较复杂（链式吸收 + 重力），模型需要推理多步连锁反应
- 额外说明了 shorthand 格式（纯数字也可以），提高模型兼容性

---

### 2.3 Othello 6×6

**游戏类型**：双人对弈（6×6 棋盘，LLM 执黑 vs Minimax Bot 执白）

**动作空间**：动态变化，格式为 `"row col"`（如 `"2 3"`），每步通常 3-10 个合法位置

**Rules Prompt**：

```
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

STRATEGY TIPS:
- Corners (0 0, 0 5, 5 0, 5 5) are extremely valuable — they can never be flipped once taken.
- Avoid placing pieces on squares adjacent to empty corners (especially diagonal neighbors).
- Mobility matters: keep more moves available for yourself while restricting your opponent.

GAME OVER CONDITIONS:
- The game ends when neither player has a valid move (usually when the board is full).
- The player with more pieces wins. Equal counts result in a draw.

Respond with ONLY "row col" (e.g., "1 3").
```

**Prompt 特点**：
- 明确强调"必须从给定的合法位置列表中选择"，防止模型凭空想象位置
- 包含策略提示（角落价值、避开 X-square、mobility），引导模型做出更好的决策
- 6×6 棋盘比 8×8 更适合 LLM：board 信息更短，token 消耗更少，模型更容易理解全局局面
- 翻转机制用自然语言描述（8 个方向夹击），是 prompt 中最复杂的规则部分

---

### 2.4 Tic Tac Toe

**游戏类型**：双人对弈（3×3 棋盘，LLM 执 X vs Minimax Bot 执 O）

**动作空间**：动态变化，格式为 `"row col"`（如 `"1 1"`），最多 9 个位置

**Rules Prompt**：

```
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

STRATEGY TIPS:
- The center (1 1) is the strongest opening move.
- Corners (0 0, 0 2, 2 0, 2 2) are the second best positions.
- Try to create a "fork" — two ways to win simultaneously — so the opponent can only block one.

GAME OVER CONDITIONS:
- You win by getting 3 of your marks in a row (any direction).
- Bot wins by getting 3 of its marks in a row.
- Draw if all 9 cells are filled with no winner.

Respond with ONLY "row col" (e.g., "1 1").
```

**Prompt 特点**：
- 棋盘最小（3×3），信息最精简，token 消耗最低
- 提供了可视化的位置参考图（ASCII 棋盘布局），帮助模型理解坐标映射
- 策略提示包含"fork"概念，这是井字棋中的核心高级策略
- Hard 难度的 bot 使用完整 Minimax（已解决的游戏），LLM 最好结果是平局

---

### 2.5 Four in a Row

**游戏类型**：双人对弈（6×7 棋盘，LLM 执先手 vs Minimax Bot）

**动作空间**：动态变化，格式为列号 `"0"` - `"6"`，最多 7 个选择

**Rules Prompt**：

```
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

STRATEGY TIPS:
- Control the center column (column 3) for more connection opportunities.
- Look for opportunities to create two-way threats (two ways to win).
- Block the opponent when they have 3 in a row with an open end.

GAME OVER CONDITIONS:
- You win if you connect 4 of your pieces in any direction.
- Bot wins if it connects 4 of its pieces.
- Draw if the board is completely filled with no winner.

Respond with ONLY the column number (e.g., "3").
```

**Prompt 特点**：
- 动作格式最简单（单个数字 0-6），模型格式出错概率最低
- 明确说明了重力机制（棋子下落到最低空位），这是 Four in a Row 与其他棋盘游戏的核心区别
- 策略提示覆盖了进攻（中心控制、双向威胁）和防守（阻挡三连）

---

## 3. Prompt 设计总结

### 2.6 Sokoban

**游戏类型**：单人推箱子解谜游戏（多关卡，棋盘大小随关卡变化）

**动作空间**：`["up", "down", "left", "right", "undo"]`，通关后追加 `"next_level"`

**Rules Prompt**：

```
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
```

**Prompt 特点**：
- 动作空间与 2048 类似（方向 + undo），格式简单，模型不容易出格式错误
- 棋盘表示较特殊：包含多种符号（`#` 墙壁、`O` 障碍、`W` 水障碍、`.` 目标），模型需要理解空间布局
- 有 **undo 机制**（每局 1 次），这是其他游戏没有的操作——模型理论上可以利用 undo 纠正错误推箱
- **多关卡系统**（10 关），通关后 `valid_actions` 变为 `["next_level"]`，模型需要识别并发送此指令
- 规则中强调了"不能拉箱子"和"不能推进墙或其他箱子"，这些是 Sokoban 的核心约束，也是 LLM 最容易违反的规则（但后端会做 valid_actions 过滤）
- 没有策略提示——Sokoban 的策略高度依赖具体关卡布局，通用 tips 帮助不大

---

### 2.7 Nuts & Bolts

**游戏类型**：单人颜色排序解谜游戏（多关卡，螺丝数和容量随关卡变化）

**动作空间**：`["move_A_B", ...]` 格式（从螺丝 A 移到螺丝 B），数量动态变化；另有 `"undo"` 和 `"next_level"`

**Rules Prompt**：

```
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
```

**Prompt 特点**：
- 棋盘表示是**一维列表的列表**（如 `[["r","b","g"], ["g","r","b"], [], ...]`），不是 2D 网格，模型需要理解"栈"结构（只能操作顶部元素）
- 动作格式为 `move_A_B`（实际后端格式），但 rules 中写的是旧格式 `select_X`——这是一个**已知的不一致**，实际运行时 prompt 框架中的 valid_actions 列表会显示正确的 `move_A_B` 格式，模型从列表中选择即可
- 有 **undo 机制**（每局 2 次），比 Sokoban 多一次
- **多关卡系统**（10 关），难度递增：螺丝数从 5 增到 16，容量从 3 增到 8，颜色种类从 3 增到 14
- 颜色用单字母表示（`r`=red, `b`=blue, `g`=green 等），模型需要理解颜色编码
- 这是对 LLM 最有挑战性的游戏之一：需要多步规划（类似河内塔），而单轮推理的 prompt 很难做出最优决策

---

### 3.1 共性设计

| 设计要素 | 具体做法 |
|---------|---------|
| 输出约束 | 三重强调：system message + rules 末尾 + prompt 末尾 "IMPORTANT" |
| 合法动作 | 明确列出 valid_actions 列表，强调"必须从中选择" |
| 棋盘表示 | 数字矩阵（0=空, 1=玩家, 2=对手），统一且简洁 |
| 策略引导 | 每个游戏提供 2-3 条策略 tips，降低模型盲目落子的概率 |

### 3.2 各游戏 Prompt 复杂度对比

| 游戏 | 棋盘大小 | 动作格式 | 动作空间 | 规则复杂度 | 每步 Token 消耗 |
|------|---------|---------|---------|-----------|--------------|
| Tic Tac Toe | 3×3 | `"row col"` | 1-9 | 低 | ~300 |
| Four in a Row | 6×7 | `"N"` | 1-7 | 中 | ~500 |
| Othello 6×6 | 6×6 | `"row col"` | 1-12 | 高 | ~600 |
| 2048 | 4×4 | `"direction"` | 1-4 | 中 | ~400 |
| MergeFall | 5×6 | `"drop N"` | 5 | 高 | ~500 |
| Sokoban | 可变 | `"direction"` | 4-5 | 中 | ~400 |
| Nuts & Bolts | 可变 | `"move_A_B"` | 动态 | 高 | ~500 |

### 3.3 已知问题与改进方向

1. **Fallback 偏差**：当模型输出格式错误时，fallback 到 `valid_actions[0]`，这个位置并非随机选择，可能导致系统性偏差（如 Othello 中总是偏向左上角）
2. **无历史记忆**：每步只看当前 board，不记忆之前的走法和对手的策略模式
3. **单轮推理**：没有 chain-of-thought 或多轮推理，模型只有一次机会输出答案
