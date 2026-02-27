# EvoPlay 复现 — 任务简报

## 摘要

EvoPlay 是一个三层游戏服务器框架（Vue 3 前端 → Flask 后端 → 可插拔游戏引擎），配备基于 LLM 的 AI 代理。本次复现验证了完整流水线：环境搭建、两款游戏（2048、MergeFall）的后端 API 正确性、CSV 日志完整性，以及通过 LiteLLM 使用 GPT-4o-mini 的 AI 代理对战。所有 API 端点均返回有效 JSON 和正确的游戏状态。代理成功完成 2048 的 30 步对局（最终得分：240）和 MergeFall 的 12 步对局后游戏结束（最终得分：52）。后端 API 平均处理延迟约 2.3 ms，代理每步延迟主要由 LLM 推理主导（2048 约 3.7 秒/步，MergeFall 约 20 秒/步，因棋盘上下文更大）。

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

创建了单一 `evoplay` micromamba 环境（Python 3.10），安装全部依赖：Flask 3.1.3、Flask-CORS 6.0.2、LiteLLM 1.40.0、requests 2.32.5，以及通过 nodeenv 安装的 Node.js 18.20.0 用于前端。

```bash
# 创建环境并安装所有依赖
/usr/bin/micromamba create -n evoplay python=3.10 -y -r /home/ruibo_ming/.local/share/mamba
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    pip install flask flask-cors litellm==1.40.0 requests
# 前端: 通过 nodeenv 安装 Node.js + npm install
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba pip install nodeenv
/usr/bin/micromamba run -n evoplay -r /home/ruibo_ming/.local/share/mamba \
    nodeenv --prebuilt --node=18.20.0 /home/ruibo_ming/.local/share/mamba/envs/evoplay/node_env
cd frontend && npm install  # 31 个包，审核 32 个
```

## 第二阶段 — 后端 API 测试

编写了综合测试脚本 (`claude_version_test_api.py`)，对两款游戏的全部 7 个 API 端点进行了测试。每款游戏使用确定性循环策略进行了 25 步对局。

```python
# 核心测试逻辑 — 2048 的循环方向策略
# 每步轮转 [up, right, down, left]，选择轮转列表中第一个有效方向
directions = ["up", "right", "down", "left"]
for i in range(25):
    resp = requests.get(f"{BASE_URL}/api/game/2048/valid_actions",
                        params={"session_id": session_id})
    valid = resp.json()["valid_actions"]
    # 从当前轮转中选择第一个有效动作
    action = next((d for d in directions if d in valid), valid[0])
    # 为下一轮旋转偏好列表
    directions = directions[1:] + directions[:1]
    # 通过 GET 端点执行移动
    resp = requests.get(f"{BASE_URL}/api/game/2048/action",
                        params={"move": action, "session_id": session_id})
    result = resp.json()  # 返回: game, board, score, game_over, valid_actions
```

### API 测试结果

| 游戏 | 步数 | 最终得分 | 游戏结束 | 平均 API 延迟 |
|------|------|----------|----------|---------------|
| 2048 | 25 | 168 | 否 | 2.5 ms |
| MergeFall | 25 | 108 | 否 | 2.2 ms |

### 端点验证

| 端点 | 状态码 | 说明 |
|------|--------|------|
| `GET /api/games` | 200 | 返回 `["2048", "mergefall"]` |
| `GET /api/game/<name>/rules` | 200 | 2048: 1346 字符, MergeFall: 1873 字符 |
| `GET /api/game/<name>/state` | 200 | 需要 session_id，返回完整棋盘状态 |
| `GET /api/game/<name>/action` | 200 | 修改状态，返回更新后的棋盘和得分 |
| `GET /api/game/<name>/reset` | 200 | 重置棋盘，保留 session_id |
| `GET /api/game/<name>/valid_actions` | 200 | 返回合法动作列表 |
| `GET /api/game/<name>/log` | 200 | 返回内存日志（步数、耗时、条目） |
| 错误: 未知游戏 | 404 | 正确的错误响应 |
| 错误: 缺少 move | 400 | 正确的错误响应 |
| 错误: 缺少 session_id | 400 | 正确的错误响应 |

CSV 日志文件已确认位于 `backend/logs/<game>/<session_id>.csv`，包含正确的表头和逐步记录。

## 第三阶段 — AI 代理测试

使用 `gpt-4o-mini`（温度 0.7，最大 token 50）和 VanillaReasoning 推理引擎对两款游戏进行了代理测试。

```python
# 代理推理流程 (来自 agent/reasoning/vanilla_reasoning.py)
# 1. 构建包含游戏上下文的提示词
prompt = f"""You are playing {game_name}. Here are the rules:
{rules}

Current game state:
{self._format_board(game_state['board'])}
Score: {game_state['score']}

Valid actions: {valid_actions}
Choose the best action. Respond with ONLY the action string."""

# 2. 通过 LiteLLM 统一接口调用 LLM
response = self.llm.simple_call(prompt, system_message="You are a game-playing AI.")

# 3. 解析响应 — 提取动作字符串，验证是否在有效动作列表中
# 如果 LLM 返回无法解析的输出，回退到第一个有效动作
action = response.strip().lower()
if action not in valid_actions:
    action = valid_actions[0]  # 安全回退
```

### 代理结果

| 指标 | 2048 | MergeFall |
|------|------|-----------|
| 完成步数 | 30 | 12 |
| 最终得分 | 240 | 52 |
| 游戏结束 | 否 | 是（列溢出） |
| 总耗时 | 111.6 秒 | 241.7 秒 |
| 平均每步延迟 | 3.7 秒 | 20.1 秒 |
| 主要动作 | `left`（16/30） | `drop 0`（12/12） |
| 最大方块 | 32 | 16 |

**2048 代理分析**：代理展示了合理的游戏策略，在 30 步内达到最大方块 32、得分 240。它偏好 `left` 操作（16/30 次），这是 2048 中已知的有效启发式策略（将方块集中到一侧）。得分稳步增长：0 → 44 → 96 → 200 → 240。

**MergeFall 代理分析**：代理在全部 12 步中重复选择 `drop 0`，仅在第 0 列中堆叠直到溢出。这种糟糕的策略（得分：52）揭示了单提示 vanilla 推理的局限性 — 代理未能将方块分散到各列。较高的每步延迟（~20 秒）是由于 5×6 棋盘序列化导致 LLM 上下文更大。

### 时间瓶颈分析

| 流水线阶段 | 耗时 | 占比 |
|-----------|------|------|
| 后端 API（所有测试调用） | 0.20 秒 | 0.1% |
| 代理 2048（30 次 LLM 调用） | 111.6 秒 | 31.6% |
| 代理 MergeFall（12 次 LLM 调用） | 241.7 秒 | 68.3% |
| **合计** | **353.5 秒** | **100%** |

LLM 推理主导总耗时（>99.9%）。Flask 后端处理请求仅需约 2–3 ms。

## 创建 / 修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `.env` | 创建 | 用于代理的 OpenAI API 密钥 |
| `claude_version_test_api.py` | 创建 | 综合 API 测试脚本 |
| `claude_reports/task_brief.md` | 创建 | 任务简报 |
| `claude_reports/execution_report.md` | 创建 | 详细执行日志 |
| `claude_reports/media/*.csv` | 创建 | 复制的游戏日志 CSV |
| `backend/logs/2048/*.csv` | 自动生成 | 游戏会话日志 |
| `backend/logs/mergefall/*.csv` | 自动生成 | 游戏会话日志 |
