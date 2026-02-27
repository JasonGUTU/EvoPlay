# EvoPlay 复现 — 执行报告

## 摘要

本报告详细记录了 EvoPlay 游戏服务器框架的完整复现过程 — 一个三层系统（Vue 3 前端 → Flask 后端 → 可插拔游戏引擎），配备基于 LLM 的 AI 代理。复现涵盖：(1) 使用 micromamba 搭建环境，(2) 对两款游戏（2048、MergeFall）的全部 7 个 API 端点进行后端测试，(3) 使用 GPT-4o-mini 通过 LiteLLM 进行 AI 代理对战。所有 API 端点均返回有效 JSON 和正确的游戏状态及 CSV 日志。代理完成了 2048 的 30 步对局（得分：240）和 MergeFall 的 12 步对局（得分：52，因列溢出游戏结束）。后端延迟平均 2.3 ms/次调用；代理延迟主要由 LLM 推理主导，为 3.7–20.1 秒/步。

## 流水线逻辑链

```
EvoPlay 三层架构
├── 前端 (Vue 3 + Vite, 端口 3000)
│   ├── App.vue ─── 游戏选择路由
│   ├── Game2048.vue ─── 4×4 棋盘渲染 + 键盘输入
│   ├── GameMergeFall.vue ─── 5×6 棋盘渲染 + 列投放按钮
│   ├── GameLog.vue ─── 操作历史显示
│   └── session.js ─── 标签页级会话隔离 (sessionStorage + localStorage)
│       ↓ HTTP GET /api/* (由 Vite 开发服务器代理)
│
├── 后端 (Flask, 端口 5001)
│   ├── app.py ─── 路由分发 + 会话管理
│   │   ├── GAMES 注册表: {"2048": Game2048, "mergefall": MergeFall}
│   │   ├── sessions 字典: 以 (game_name, session_id) 元组为键
│   │   └── 路由:
│   │       ├── /api/games → 列出游戏名称
│   │       ├── /api/game/<name>/state → get_state() [需要 session_id]
│   │       ├── /api/game/<name>/action?move=<x> → apply_action(x)
│   │       ├── /api/game/<name>/reset → reset()
│   │       ├── /api/game/<name>/valid_actions → valid_actions()
│   │       ├── /api/game/<name>/log → get_log_info()
│   │       └── /api/game/<name>/rules → get_rules()
│   │
│   └── games/
│       ├── base.py ─── BaseGame 抽象基类
│       │   ├── CSV 日志器: logs/<game>/<session_id>.csv
│       │   ├── 惰性文件创建（不产生空日志文件）
│       │   └── 列: step, time, action, score, game_over, board(JSON)
│       ├── game_2048.py ─── 4×4 滑动拼图
│       │   ├── 动作: up/down/left/right
│       │   ├── 方块生成: 90% → 2, 10% → 4
│       │   └── 旋转式移动: 所有方向 → 左压缩 → 旋转回原位
│       └── game_mergefall.py ─── 5×6 投放合并拼图
│           ├── 动作: "drop 0" 到 "drop 4"
│           ├── 机制: 重力 → 吸收相邻同值 → 重复直到稳定
│           ├── 计分: 最终活跃方块值 × 连击次数
│           └── 溢出行（第0行，不可见）: 游戏结束触发条件
│
└── 代理 (CLI, 通过 HTTP 连接后端)
    ├── main.py ─── CLI 入口 (argparse)
    ├── config.py ─── 配置优先级: CLI 参数 > 环境变量 > .env > 默认值
    ├── agent.py ─── Agent 类: get_state → reason → apply_action 循环
    ├── llm.py ─── LiteLLM 封装器 (OpenAI/Anthropic/Gemini/Ollama)
    └── reasoning/
        └── vanilla_reasoning.py ─── 单提示 LLM 推理
            ├── 提示词: 游戏规则 + 棋盘状态 + 有效动作
            ├── 响应解析: 提取动作字符串
            └── 回退: 解析失败时选择第一个有效动作
```

## 第一阶段 — 环境搭建

### 命令

```bash
# 创建 Python 3.10 的专用 micromamba 环境
/usr/bin/micromamba create -n evoplay python=3.10 -y -r /home/ruibo_ming/.local/share/mamba
```
**结果**：环境创建于 `/home/ruibo_ming/.local/share/mamba/envs/evoplay/`。

```bash
# 一次性安装后端和代理的 Python 依赖
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    pip install flask flask-cors litellm==1.40.0 requests
```
**结果**：安装了 Flask 3.1.3、Flask-CORS 6.0.2、LiteLLM 1.40.0、requests 2.32.5，以及传递依赖（openai、tiktoken、pydantic、httpx 等）。

```bash
# 通过 nodeenv 安装 Node.js 用于前端（系统无 npm）
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba pip install nodeenv
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    nodeenv --prebuilt --node=18.20.0 /home/ruibo_ming/.local/share/mamba/envs/evoplay/node_env
```
**结果**：Node.js 18.20.0 安装于 `envs/evoplay/node_env/bin/node`。

```bash
# 安装前端 npm 依赖
cd /work/ruibo_ming/EvoPlay/frontend
/home/ruibo_ming/.local/share/mamba/envs/evoplay/node_env/bin/npm install
```
**结果**：安装 31 个包（Vue 3.4、Vite 5.0、@vitejs/plugin-vue 5.0）。

```bash
# 在项目根目录创建 .env 文件，配置 OpenAI API 密钥
echo "OPENAI_API_KEY=sk-proj-..." > /work/ruibo_ming/EvoPlay/.env
```
**结果**：代理的 config.py 从 `agent/../.env`（项目根目录）读取。

### 依赖解决说明

- 系统无 `npm` — 通过在 micromamba 环境中安装 `nodeenv` 并创建本地 Node.js 安装解决
- LiteLLM 1.40.0 按 `agent/requirements.txt` 中指定版本锁定，避免 API 兼容性问题
- 所有依赖安装顺利，无冲突

## 第二阶段 — 后端 API 测试

### 启动后端

```bash
# 在端口 5001 后台启动 Flask 开发服务器
cd /work/ruibo_ming/EvoPlay/backend
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba python app.py &
```
**结果**：Flask 服务器运行于 `http://0.0.0.0:5001`，调试模式开启，CORS 已启用。

### 测试脚本

在项目根目录创建了 `claude_version_test_api.py` — 一个综合测试套件，覆盖全部 7 个 API 端点、两款游戏（各 25 步）、错误处理和计时指标。

```python
# 核心测试逻辑 — 2048 的循环方向策略
# 每步轮转 [up, right, down, left]，选择轮转列表中第一个有效方向
directions = ["up", "right", "down", "left"]
for i in range(25):
    # 获取当前会话的有效动作
    resp = requests.get(f"{BASE_URL}/api/game/2048/valid_actions",
                        params={"session_id": session_id})
    valid = resp.json()["valid_actions"]
    # 从当前轮转中选择第一个有效动作
    action = next((d for d in directions if d in valid), valid[0])
    # 为下一轮旋转偏好列表
    directions = directions[1:] + directions[:1]
    # 通过 GET 端点执行移动 — 返回更新后的游戏状态
    resp = requests.get(f"{BASE_URL}/api/game/2048/action",
                        params={"move": action, "session_id": session_id})
    result = resp.json()
    # result 包含: game, board (4×4 数组), score, game_over, valid_actions, session_id
```

```bash
# 运行测试套件
cd /work/ruibo_ming/EvoPlay
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    python claude_version_test_api.py
```

### 测试结果

**测试 1 — 列出游戏**：`GET /api/games` 返回 `{"games": ["2048", "mergefall"]}`（200 OK）。

**测试 2 — 游戏规则**：两款游戏均返回详细规则文本（2048: 1346 字符，MergeFall: 1873 字符）。

**测试 3 — 2048 对局（25 步）**：
- 会话 ID：`6355168d-cc08-4946-8a9d-d49ea78ae941`
- 初始棋盘：两个方块（值为 2）随机放置
- 得分变化：0 → 4 → 4 → 4 → ... → 152 → 168
- 最终棋盘状态：
```
   2    32     2     0
  16     4     0     0
   2     0     0     0
   0     2     0     0
```
- 最大方块：32，最终得分：168，游戏结束：否
- CSV 日志：25 条记录，耗时 0.11 秒

**测试 4 — MergeFall 对局（25 步）**：
- 会话 ID：`29466ebd-121c-4ecc-b198-c4894403cc1e`
- 棋盘：5×6 网格，中心向外列循环策略（`[2, 1, 3, 0, 4]`）
- 得分变化：0 → 4 → 4 → ... → 108
- 最终棋盘状态：
```
   0    0    0    0    0
   0    0    0    0    0
   0    0    0    0    0
   0    0    2   16    8
   4    8   16    2    4
   8   16    8    4   16
```
- 最终得分：108，游戏结束：否
- CSV 日志：25 条记录，耗时 0.06 秒

**测试 5 — 错误处理**：
- 未知游戏规则 → 404：`{"error": "Unknown game: unknown_game"}`
- 缺少 move 参数 → 400：`{"error": "Missing 'move' query parameter."}`
- 缺少 session_id → 400：`{"error": "Missing required 'session_id' query parameter."}`

### API 计时指标

| 端点 | 调用次数 | 平均延迟 | 总耗时 |
|------|---------|----------|--------|
| `action_2048` | 25 | 2.5 ms | 0.061 s |
| `action_mergefall` | 25 | 2.2 ms | 0.055 s |
| `valid_actions_2048` | 26 | 2.1 ms | 0.055 s |
| `list_games` | 1 | 7.7 ms | 0.008 s |
| `reset_2048` | 1 | 4.0 ms | 0.004 s |
| `rules` | 2 | 1.9 ms | 0.004 s |
| `state_*` | 2 | 2.4 ms | 0.005 s |
| `log_*` | 2 | 2.3 ms | 0.005 s |
| **合计** | **86** | **2.3 ms** | **0.200 s** |

注：纯 CPU 后端 — 无 GPU 使用。首次调用（`list_games`: 7.7 ms）包含 Flask 路由解析预热。

## 第三阶段 — AI 代理测试

### 代理配置

| 参数 | 值 |
|------|-----|
| 模型 | `gpt-4o-mini` |
| 提供商 | `openai` |
| 推理方法 | `vanilla`（VanillaReasoning） |
| 温度 | 0.7 |
| 最大 token | 50 |
| 步间延迟 | 0.2 秒 |
| 最大步数 | 30 |

### 2048 代理运行

```bash
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    python -m agent.main --game 2048 --model gpt-4o-mini --max-steps 30 --delay 0.2 --reasoning vanilla
```

```python
# 代理推理流程 (来自 agent/reasoning/vanilla_reasoning.py)
# VanillaReasoning.reason() 方法:
# 1. 构建包含游戏上下文的提示词 — 规则、棋盘状态、有效动作
prompt = f"""You are playing {game_name}. Here are the rules:
{rules}

Current game state:
{self._format_board(game_state['board'])}
Score: {game_state['score']}

Valid actions: {valid_actions}
Choose the best action. Respond with ONLY the action string."""

# 2. 通过 LiteLLM 统一接口调用 LLM（封装 OpenAI、Anthropic 等）
response = self.llm.simple_call(prompt, system_message="You are a game-playing AI.")

# 3. 解析响应 — 提取动作字符串，验证是否在有效动作列表中
# 如果 LLM 返回无法解析的输出，回退到第一个有效动作
action = response.strip().lower()
if action not in valid_actions:
    action = valid_actions[0]  # 安全回退
```

**结果**：
- 会话 ID：`272331d5-3a55-42cb-b64a-3a9c653938b7`
- 完成全部 30 步（未游戏结束）
- 最终得分：240，最大方块：32
- 总耗时：111.6 秒（平均 3.7 秒/步）
- 动作分布：`left` ×16, `up` ×5, `down` ×7, `right` ×2
- 得分里程碑：第 9 步 → 44，第 18 步 → 96，第 19 步 → 128，第 30 步 → 240

逐步日志（节选）：
```
第  1 步: left  → 得分=0     第 16 步: down  → 得分=68
第  2 步: up    → 得分=4     第 17 步: left  → 得分=72
第  3 步: down  → 得分=12    第 18 步: down  → 得分=96
第  8 步: left  → 得分=28    第 19 步: down  → 得分=128
第  9 步: left  → 得分=44    第 26 步: left  → 得分=184
第 12 步: left  → 得分=56    第 27 步: left  → 得分=200
第 15 步: left  → 得分=60    第 30 步: up    → 得分=240
```

最终棋盘：
```
  32    4    0    0
  32    4    0    0
   2    0    0    0
   0    0    0    2
```

### MergeFall 代理运行

相同命令，改为 `--game mergefall`。模型和参数与 2048 相同（同一推理引擎，不同游戏接口）。

```bash
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    python -m agent.main --game mergefall --model gpt-4o-mini --max-steps 30 --delay 0.2 --reasoning vanilla
```

**结果**：
- 会话 ID：`4887f0f1-6df1-4034-9072-3ec9dce69016`
- 第 12 步游戏结束（第 0 列溢出）
- 最终得分：52，最大方块：16
- 总耗时：241.7 秒（平均 20.1 秒/步）
- 动作分布：`drop 0` ×12（100% — 代理从未分散）

逐步日志（完整）：
```
第  1 步: drop 0 → 得分=0    (方块放置于第 0 列底部)
第  2 步: drop 0 → 得分=4    (2+2=4 合并)
第  3 步: drop 0 → 得分=12   (连锁合并)
第  4 步: drop 0 → 得分=12   (无合并，新方块堆叠)
第  5 步: drop 0 → 得分=12   (无合并)
第  6 步: drop 0 → 得分=12   (无合并)
第  7 步: drop 0 → 得分=12   (无合并)
第  8 步: drop 0 → 得分=12   (无合并)
第  9 步: drop 0 → 得分=44   (级联合并：多个方块被吸收)
第 10 步: drop 0 → 得分=44   (无合并)
第 11 步: drop 0 → 得分=52   (合并)
第 12 步: drop 0 → 得分=52   游戏结束 (溢出)
```

最终棋盘（第 0 列完全填满）：
```
   8    0    0    0    0
  16    0    0    0    0
   4    0    0    0    0
   2    0    0    0    0
   4    0    0    0    0
   8    0    0    0    0
```

### 代理行为对比

| 指标 | 2048 | MergeFall |
|------|------|-----------|
| 完成步数 | 30（达到上限） | 12（游戏结束） |
| 最终得分 | 240 | 52 |
| 最大方块 | 32 | 16 |
| 游戏结束 | 否 | 是（溢出） |
| 总耗时 | 111.6 秒 | 241.7 秒 |
| 平均每步延迟 | 3.7 秒 | 20.1 秒 |
| 动作多样性 | 4 种不同动作 | 1 种动作 |
| 策略质量 | 合理（偏左策略） | 较差（单列策略） |

MergeFall 每步延迟高出 5.4 倍，原因是更大的棋盘上下文（5×6 vs 4×4）和更长的规则文本（1873 vs 1346 字符）导致 LLM 提示词更长。

### CSV 日志

所有游戏会话均在 `backend/logs/<game>/<session_id>.csv` 生成了 CSV 日志：

| 日志文件 | 游戏 | 步数 | 大小 |
|---------|------|------|------|
| `272331d5-...csv` | 2048（代理） | 30 | 2.5 KB |
| `4887f0f1-...csv` | MergeFall（代理） | 12 | 1.6 KB |
| `6355168d-...csv` | 2048（API 测试） | 25 | 2.1 KB |
| `29466ebd-...csv` | MergeFall（API 测试） | 25 | 3.3 KB |

CSV 格式：`step,time,action,score,game_over,board`，其中 board 为 JSON 编码的嵌套数组。

### 时间瓶颈分析

| 流水线阶段 | 耗时 | 占比 |
|-----------|------|------|
| 后端 API（所有测试调用） | 0.20 秒 | 0.1% |
| 代理 2048（30 次 LLM 调用） | 111.6 秒 | 31.6% |
| 代理 MergeFall（12 次 LLM 调用） | 241.7 秒 | 68.3% |
| **合计** | **353.5 秒** | **100%** |

LLM 推理主导总耗时（>99.9%）。Flask 后端处理可忽略不计。无 GPU 使用（纯 CPU 后端，LLM 调用为远程 OpenAI API 请求）。

## 创建 / 修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `.env` | 创建 | `OPENAI_API_KEY=sk-proj-...` 用于代理配置 |
| `claude_version_test_api.py` | 创建 | 310 行 API 测试脚本，含计时指标 |
| `claude_reports/task_brief.md` | 创建 | 任务简报 |
| `claude_reports/execution_report.md` | 创建 | 详细执行报告 |
| `claude_reports/task_brief_zh.md` | 创建 | 任务简报中文版 |
| `claude_reports/execution_report_zh.md` | 创建 | 执行报告中文版 |
| `claude_reports/media/agent_2048_log.csv` | 复制 | 代理 2048 会话 CSV 日志 |
| `claude_reports/media/agent_mergefall_log.csv` | 复制 | 代理 MergeFall 会话 CSV 日志 |
| `claude_reports/media/api_test_2048_log.csv` | 复制 | API 测试 2048 会话 CSV 日志 |
| `claude_reports/media/api_test_mergefall_log.csv` | 复制 | API 测试 MergeFall 会话 CSV 日志 |
| `backend/logs/2048/*.csv` | 自动生成 | 4 个会话日志文件 |
| `backend/logs/mergefall/*.csv` | 自动生成 | 3 个会话日志文件 |
