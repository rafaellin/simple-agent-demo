很好，这些补充让需求清晰了很多。我帮你把这些零散的点整合成一份结构化的需求文档。

---

## AI Agent Showcase - 需求文档 (v0.1)

### 1. 项目概述

**一句话价值**：一个基于LangGraph的桌面AI助手，能够通过对话理解用户意图，调用本地PowerShell工具操作文件系统。

**目标用户**：个人开发者，作为Agent技术能力的作品展示。

**使用场景**：用户通过桌面应用与Agent对话，Agent根据对话内容决定是否需要操作本地文件（在受限workspace内），返回结果给用户。

---

### 2. 架构概览

```
┌─────────────────────────────────────────────────┐
│                  Tauri Desktop App               │
│  ┌───────────┐  ┌───────────┐  ┌──────────────┐ │
│  │ Chat View │  │ Settings  │  │ Log Panel    │ │
│  └─────┬─────┘  └───────────┘  └──────────────┘ │
│        │ WebSocket (AG-UI Protocol)              │
└────────┼────────────────────────────────────────┘
         │
┌────────┴────────────────────────────────────────┐
│              Python Agent Gateway                │
│  ┌─────────────────────────────────────────┐    │
│  │         WebSocket Server (FastAPI)       │    │
│  └──────────────────┬──────────────────────┘    │
│                     │                            │
│  ┌──────────────────┴──────────────────────┐    │
│  │         LangGraph Agent Runtime          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌───────┐ │    │
│  │  │ system.md │  │tools.md  │  │skills │ │    │
│  │  │ (prompt)  │  │(MCP reg) │  │.md    │ │    │
│  │  └──────────┘  └─────┬────┘  └───────┘ │    │
│  └──────────────────────┼─────────────────┘    │
│                         │                       │
│  ┌──────────────────────┴─────────────────┐    │
│  │         Local MCP Server                │    │
│  │  ┌────────────────────────────────┐    │    │
│  │  │     PowerShell Tool             │    │    │
│  │  │  (仅操作配置的workspace路径)     │    │    │
│  │  └────────────────────────────────┘    │    │
│  └────────────────────────────────────────┘    │
└────────────────────────────────────────────────┘
```

**通信协议**：
- Tauri前端 ↔ Python Gateway：**WebSocket**，遵循 **AG-UI 协议**
- Agent ↔ MCP Server：**stdio**（标准MCP协议）
- LLM调用：**云端API**（HTTP）

---

### 3. 功能需求

#### 3.1 Agent对话模块

| 编号 | 需求 | 说明 |
|------|------|------|
| F-01 | 多轮对话 | 支持上下文保持的多轮对话 |
| F-02 | 流式输出 | LLM回复通过WebSocket流式推送到前端 |
| F-03 | 工具调用可视化 | 当Agent调用PowerShell工具时，前端显示“正在执行: xxx”状态 |
| F-04 | 错误处理 | Agent执行出错时，向用户展示友好错误信息 |
| F-05 | 终止条件 | ①用户需求已达成 OR ②达到最大迭代次数(默认5) |

#### 3.2 本地工具能力 (MCP Server)

| 编号 | 需求 | 说明 |
|------|------|------|
| F-06 | PowerShell执行 | MCP Server提供PS执行工具 |
| F-07 | workspace约束 | 仅允许操作配置文件中指定的workspace路径内文件 |
| F-08 | 路径安全 | 解析后的绝对路径必须在workspace范围内 |
| F-09 | 执行日志 | 记录每次工具调用的命令与结果 |

#### 3.3 Harness配置体系

| 编号 | 需求 | 说明 |
|------|------|------|
| F-10 | system.md | 存放Agent的System Prompt |
| F-11 | tools.md | 声明可用的MCP工具及使用说明 |
| F-12 | skills.md | 定义Agent的skill/能力模块 |
| F-13 | config.yaml | 全局配置（见第5节） |

#### 3.4 桌面应用 (Tauri)

| 编号 | 需求 | 说明 |
|------|------|------|
| F-14 | 对话界面 | 消息气泡式聊天UI |
| F-15 | 基础设置页 | 配置LLM API Key、workspace路径 |
| F-16 | 连接状态 | 显示WebSocket连接状态（已连接/断开/重连中） |
| F-17 | 消息历史 | 当前会话的消息保持在内存，暂不做持久化 |

---

### 4. 非功能需求

| 编号 | 需求 | 说明 |
|------|------|------|
| NF-01 | 首次响应时间 | 消息发送后 < 3秒开始流式返回 |
| NF-02 | 安全性 | PowerShell仅在workspace内生效，禁止路径穿越 |
| NF-03 | 兼容性 | Windows 10+（PowerShell 5.1+） |
| NF-04 | 单用户 | PoC阶段仅支持单用户、单会话 |

---

### 5. 配置文件设计

#### 5.1 config.yaml

```yaml
# LLM配置
llm:
  provider: "openai"            # openai | anthropic | etc.
  api_key: "${LLM_API_KEY}"     # 从环境变量读取
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 4096

# Agent配置
agent:
  max_iterations: 5             # 最大工具调用迭代次数
  system_prompt: "system.md"    # 相对于config目录的路径
  tools_config: "tools.md"
  skills_config: "skills.md"

# MCP Server配置
mcp:
  name: "powershell-executor"
  command: "powershell.exe"
  args: ["-NoProfile", "-Command"]

# Workspace配置
workspace:
  path: "C:/Users/xxx/agent-workspace"  # 限制操作的根目录

# Gateway配置
gateway:
  host: "127.0.0.1"
  port: 8765
```

#### 5.2 system.md 示例

```markdown
# System Prompt

你是一个具备本地文件操作能力的AI助手。
你可以通过PowerShell工具在用户的workspace中执行操作。

## 核心规则
- 操作前先确认文件是否存在
- 删除/修改操作需先向用户确认
- 始终在允许的workspace范围内工作
```

#### 5.3 tools.md 示例

```markdown
# MCP Tools

## powershell_executor
- **服务**：Local MCP Server
- **工具名**：execute_powershell
- **功能**：在workspace内执行PowerShell命令
- **约束**：仅操作 {{workspace.path}} 路径下的文件
```

#### 5.4 skills.md 示例

```markdown
# Agent Skills

## file_operation
- **触发**：用户请求文件相关操作
- **流程**：理解意图 → 生成PS命令 → 调用MCP工具 → 解读结果
- **示例**：
  - "列出当前目录文件"
  - "创建一个新的README.md"
  - "把output.txt的内容转为大写"
```

---

### 6. 技术栈

| 层 | 技术 | 版本要求 |
|---|------|----------|
| 桌面壳 | Tauri | v2.x |
| 前端UI | React/Vue + TypeScript | - |
| Agent框架 | LangGraph | ≥ 0.2 |
| LLM调用 | langchain-openai / 原生SDK | - |
| Gateway | FastAPI + uvicorn | - |
| WebSocket | AG-UI协议 | - |
| MCP Server | mcp (Python SDK) | ≥ 1.0 |
| 配置解析 | PyYAML | - |

---

### 7. 开发阶段划分

| 阶段 | 内容 | 可交付物 |
|------|------|----------|
| Phase 1 | Python Agent + Gateway + MCP | 命令行可对话的Agent |
| Phase 2 | Tauri壳 + 通信对接 | 桌面窗口可对话 |
| Phase 3 | 配置体系完善 + 安全加固 | 完整的PoC |
| Phase 4 | UI打磨 + 文档 | 可展示的作品 |

---

这份需求文档你觉得哪些地方还需要调整？确认后可以开始Phase 1的开发。