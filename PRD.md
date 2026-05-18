# AI Agent Desktop Showcase - Requirements Document (v0.1)

## Overview

**Value Proposition**: A LangGraph-based desktop AI assistant that understands user intent through conversation and executes local PowerShell tools to manipulate the file system.

**Target Users**: Individual developers showcasing Agent technology capabilities.

**Use Cases**: Users interact with the Agent through a desktop application. The Agent decides whether local file operations are needed (within a restricted workspace) based on the conversation, then returns results to the user.

---

## Architecture Overview

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
│  │  │  (Only workspace-configured     │    │    │
│  │  │   paths)                        │    │    │
│  │  └────────────────────────────────┘    │    │
│  └────────────────────────────────────────┘    │
└────────────────────────────────────────────────┘
```

**Communication Protocols**:
- Tauri Frontend ↔ Python Gateway: **WebSocket** following **AG-UI Protocol**
- Agent ↔ MCP Server: **stdio** (standard MCP protocol)
- LLM Calls: **Cloud API** (HTTP)

---

## Functional Requirements

### 3.1 Agent Conversation Module

| ID | Requirement | Description |
|------|-----|------|
| F-01 | Multi-turn Conversation | Support context-aware multi-turn conversations |
| F-02 | Streaming Output | LLM responses streamed to frontend via WebSocket |
| F-03 | Tool Invocation Visualization | Show "Executing: xxx" status when Agent calls PowerShell |
| F-04 | Error Handling | Display friendly error messages when execution fails |
| F-05 | Termination Condition | End when ① user request fulfilled OR ② max iterations reached (default 5) |

### 3.2 Local Tool Capabilities (MCP Server)

| ID | Requirement | Description |
|------|-----|------|
| F-06 | PowerShell Execution | MCP Server provides PowerShell execution tool |
| F-07 | Workspace Constraint | Only operate on files within configured workspace path |
| F-08 | Path Safety | Resolved absolute paths must be within workspace |
| F-09 | Execution Logging | Log each tool invocation with command and result |

### 3.3 Configuration System

| ID | Requirement | Description |
|------|-----|------|
| F-10 | system.md | Agent's System Prompt |
| F-11 | tools.md | Declare available MCP tools and usage |
| F-12 | skills.md | Define Agent's skills/capabilities |
| F-13 | config.yaml | Global configuration (see section 5) |

### 3.4 Desktop Application (Tauri)

| ID | Requirement | Description |
|------|-----|------|
| F-14 | Chat Interface | Bubble-style chat UI |
| F-15 | Settings Page | Configure LLM API Key, workspace path |
| F-16 | Connection Status | Show WebSocket status (connected/disconnected/reconnecting) |
| F-17 | Message History | Keep current session messages in memory, no persistence yet |

---

## Non-Functional Requirements

| ID | Requirement | Description |
|------|-----|------|
| NF-01 | First Response Time | Begin streaming < 3 seconds after message sent |
| NF-02 | Security | PowerShell only works within workspace, prevent path traversal |
| NF-03 | Compatibility | Windows 10+ (PowerShell 5.1+) |
| NF-04 | Single User | PoC phase: single user, single session only |

---

## Configuration Design

### 5.1 config.yaml

```yaml
# LLM Configuration
llm:
  provider: "openai"            # openai | anthropic | etc.
  api_key: "${LLM_API_KEY}"     # Read from environment variable
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 4096

# Agent Configuration
agent:
  max_iterations: 5             # Max tool call iterations
  system_prompt: "system.md"    # Path relative to config directory
  tools_config: "tools.md"
  skills_config: "skills.md"

# MCP Server Configuration
mcp:
  name: "powershell-executor"
  command: "powershell.exe"
  args: ["-NoProfile", "-Command"]

# Workspace Configuration
workspace:
  path: "C:/Users/xxx/agent-workspace"  # Root directory for operations

# Gateway Configuration
gateway:
  host: "127.0.0.1"
  port: 8765
```

### 5.2 system.md Example

```markdown
# System Prompt

You are an AI assistant with local file operation capabilities.
You can execute operations in the user's workspace using PowerShell tools.

## Core Rules
- Verify file existence before operating
- Request user confirmation for delete/modify operations
- Always work within the allowed workspace range
```

### 5.3 tools.md Example

```markdown
# MCP Tools

## powershell_executor
- **Service**: Local MCP Server
- **Tool Name**: execute_powershell
- **Function**: Execute PowerShell commands within workspace
- **Constraint**: Only operate on files under {{workspace.path}}
```

### 5.4 skills.md Example

```markdown
# Agent Skills

## file_operation
- **Trigger**: User requests file-related operations
- **Flow**: Understand intent → Generate PowerShell command → Call MCP tool → Interpret result
- **Examples**:
  - "List files in current directory"
  - "Create a new README.md file"
  - "Convert output.txt content to uppercase"
```

---

## Technology Stack

| Layer | Technology | Version |
|---|------|----------|
| Desktop Shell | Tauri | v2.x |
| Frontend UI | React/Vue + TypeScript | - |
| Agent Framework | LangGraph | ≥ 0.2 |
| LLM Calls | langchain-openai / Native SDK | - |
| Gateway | FastAPI + uvicorn | - |
| WebSocket | AG-UI Protocol | - |
| MCP Server | mcp (Python SDK) | ≥ 1.0 |
| Config Parsing | PyYAML | - |

---

## Development Phases

| Phase | Content | Deliverable |
|------|------|----------|
| Phase 1 | Python Agent + Gateway + MCP | Command-line conversable Agent |
| Phase 2 | Tauri shell + integration | Desktop window with conversation |
| Phase 3 | Configuration system + security hardening | Complete PoC |
| Phase 4 | UI polish + documentation | Presentable showcase |

---

## Implementation Status

✅ Phase 1-3 Complete
- LangGraph StateGraph implementation with proper node structure
- FastAPI WebSocket gateway with streaming support  
- MCP tools with PowerShell execution and path validation
- Configuration system with YAML + markdown files
- React desktop chat interface
- End-to-end testing suite

Phase 4 in progress:
- UI refinements
- Documentation completion
- Ready for testing after requirement installation
