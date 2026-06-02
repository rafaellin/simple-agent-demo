# AI Agent Desktop POC

A proof-of-concept desktop AI assistant built with **LangGraph**, **FastAPI**, **Tauri**, and **React**. The agent can understand user intent through conversation and execute local PowerShell operations within a restricted workspace.

## Features

- ✅ **Intelligent Conversation**: LangGraph-based agentic architecture with multi-step reasoning
- ✅ **Safe Execution**: Approval system for potentially dangerous operations
- ✅ **Short-term & Long-term Memory**: Maintains conversation context and persistent knowledge
- ✅ **Workspace Sandbox**: All operations confined to isolated workspace directory
- ✅ **WebSocket Communication**: Real-time streaming responses
- ✅ **Desktop UI**: Native desktop experience with Tauri + React

## Memory System

The agent now includes a sophisticated memory system:

- **Short-Term Memory**: Maintains up to 50 recent messages for conversation context
- **Long-Term Memory**: Persists facts, summaries, preferences, and behavioral patterns
- **Auto-Summarization**: Automatically summarizes conversations to prevent context overflow
- **Memory Integration**: LLM receives relevant facts and patterns from memory in each prompt

See [MEMORY_GUIDE.md](./MEMORY_GUIDE.md) for detailed usage and API documentation.

## 📚 Documentation

### Memory System (New!)
- **[MEMORY.md](./MEMORY.md)** ⭐ **Complete Memory Reference** - All documentation in one file
  - Quick start (5 min)
  - Features overview
  - Python API reference
  - WebSocket API reference
  - Examples & usage
  - Troubleshooting & best practices

### Setup & Testing
- **[SETUP.md](./SETUP.md)** - Detailed setup guide
- **[test_e2e.py](./test_e2e.py)** - End-to-end tests
- **[test_memory.py](./test_memory.py)** - Memory system tests

## Project Structure

```
simple-agent-demo/
├── backend/                          # Python backend
│   ├── src/
│   │   ├── mcp/                      # MCP Server (PowerShell tool)
│   │   │   ├── tools.py              # Tool implementation
│   │   │   └── server.py             # MCP server runner
│   │   └── agent/                    # LangGraph Agent
│   │       ├── agent.py              # Main agent logic
│   │       └── gateway.py            # FastAPI WebSocket gateway
│   ├── config/                       # Configuration files
│   │   ├── config.yaml               # Main config
│   │   ├── system.md                 # System prompt
│   │   ├── tools.md                  # Tools documentation
│   │   └── skills.md                 # Agent skills
│   ├── main.py                       # Entry point
│   └── requirements.txt              # Python dependencies
│
├── frontend/                         # Tauri + React desktop app
│   ├── src/
│   │   ├── Chat.tsx                  # Chat component
│   │   ├── Chat.css                  # Chat UI styles
│   │   ├── main.tsx                  # React entry point
│   │   └── index.css                 # Global styles
│   ├── src-tauri/                    # Tauri Rust code
│   ├── tauri.conf.json               # Tauri config
│   ├── package.json                  # Node dependencies
│   └── vite.config.js                # Vite config
│
├── agent-workspace/                  # Sandbox directory for agent operations
├── SETUP.md                          # Detailed setup guide
├── test_e2e.py                       # End-to-end tests
└── README.md                         # This file
```

## Architecture

```
┌─────────────────────────────────────┐
│   Tauri Desktop App (React UI)      │
│   - Chat interface                  │
│   - Connection status               │
│   - Message history                 │
└────────────┬────────────────────────┘
             │ WebSocket (JSON)
             │ ws://127.0.0.1:8765/ws
             ▼
┌─────────────────────────────────────┐
│   FastAPI Gateway                   │
│   - WebSocket server                │
│   - Message routing                 │
│   - Agent lifecycle management      │
└────────────┬────────────────────────┘
             │ Direct Python calls
             ▼
┌─────────────────────────────────────┐
│   LangGraph Agent                   │
│   - Conversation management         │
│   - Tool calling logic              │
│   - OpenAI integration              │
└────────────┬────────────────────────┘
             │ Tool invocation
             ▼
┌─────────────────────────────────────┐
│   MCP Tool Registry                 │
│   - PowerShell execution wrapper    │
│   - Workspace path validation       │
│   - Output formatting               │
└────────────┬────────────────────────┘
             │ Subprocess execution
             ▼
    PowerShell Commands
```

## Quick Start

### 1. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 2. Configure

Set your OpenAI API key:
```bash
$env:OPENAI_API_KEY = "sk-..."
```

Update workspace path in `backend/config/config.yaml` if needed.

### 3. Run Backend

```bash
cd backend
python main.py
```

You should see:
```
Starting AI Agent Gateway on 127.0.0.1:8765
WebSocket server running at ws://127.0.0.1:8765/ws
```

### 4. Run Frontend (Development)

In another terminal:
```bash
cd frontend
npm run dev
```

Open http://localhost:5173 in your browser.

### 5. Test End-to-End

Try these commands in the chat:
- **Chinese**: "列出当前目录的文件" (List current directory files)
- **Chinese**: "创建一个文件 test.md" (Create a file named test.md)  
- **Chinese**: "读取 README.md 内容" (Read README.md content)
- **English**: "List all files in the workspace"
- **English**: "Create a directory named 'data'"

## Features Implemented

### MVP (Phase 1 Complete)
- [x] Multi-turn conversations with context
- [x] PowerShell command execution in sandboxed workspace
- [x] Stream-based message delivery via WebSocket
- [x] Tool invocation visibility (shows when agent is executing commands)
- [x] Error handling with user-friendly messages
- [x] Config-driven system setup

### Future Enhancements (Phase 2+)
- [ ] Persistent chat history (DB storage)
- [ ] File upload/preview
- [ ] Multiple agent modes
- [ ] Custom tool registration
- [ ] Agent reasoning visualization
- [ ] Tauri-native window decorations

## Configuration

### config.yaml

```yaml
# LLM Configuration
llm:
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4o-mini"
  temperature: 0.7
  max_tokens: 2048

# Agent Settings
agent:
  max_iterations: 5  # Maximum tool calls per request

# Workspace Safety
workspace:
  path: "f:/work/code/simple-agent-demo/agent-workspace"

# Gateway
gateway:
  host: "127.0.0.1"
  port: 8765
```

### system.md

Customize the agent's personality and rules by editing `backend/config/system.md`.

### tools.md & skills.md

Document available tools and agent capabilities in these markdown files. The agent reads these at startup to understand what it can do.

## API

### WebSocket Protocol

**Send Message:**
```json
{
  "type": "chat",
  "data": "User message here"
}
```

**Responses:**
```json
{
  "type": "text",
  "data": "Agent response text"
}
```

```json
{
  "type": "tool_start",
  "data": {"tool": "execute_powershell", "args": {"command": "..."}}
}
```

```json
{
  "type": "tool_result",
  "data": "{\"success\": true, \"output\": \"...\", ...}"
}
```

## Troubleshooting

### WebSocket Connection Failed
- Verify backend is running on port 8765
- Check Windows firewall settings
- Ensure no other service is using port 8765

### OpenAI API Errors
- Verify `OPENAI_API_KEY` is set correctly
- Check your OpenAI account has available credit
- Model `gpt-4o-mini` is available in your account

### PowerShell Execution Fails
- Ensure Windows PowerShell 5.1+ is installed
- Check `agent-workspace` directory exists and is accessible
- Try running PowerShell commands manually first

### Agent Doesn't Respond
- Check backend logs for errors
- Verify LLM API key is valid
- Try a simpler request first

## Development

### Adding New Tools

1. Implement tool in `backend/src/mcp/tools.py`
2. Register in `MCPToolRegistry.call_tool()`
3. Document in `backend/config/tools.md`
4. Agent will automatically discover the tool

### Testing

Run end-to-end tests:
```bash
python test_e2e.py
```

This tests:
- PowerShell command execution
- MCP tool registry
- Agent response generation

## Security Notes

- **Sandbox**: All file operations are restricted to `agent-workspace`
- **Path Validation**: Absolute paths outside workspace are rejected
- **Timeout**: Commands timeout after 30 seconds
- **API Key**: Store in environment variable, never in code
- **WebSocket**: For local development only (localhost)

## Building for Production

### Build Tauri App

```bash
cd frontend
npm run tauri build
```

This creates:
- Windows installer (.msi)
- Portable executable (.exe)

### Production Checklist
- [ ] Update system.md with production rules
- [ ] Secure OPENAI_API_KEY storage (use env vars or secure store)
- [ ] Set proper workspace path
- [ ] Configure firewall for WebSocket if needed
- [ ] Test with real user workflows
- [ ] Set reasonable timeout/iteration limits

## License

MIT

## Contributing

Contributions welcome! Areas of interest:
- Additional MCP tools (file, network, etc.)
- UI/UX improvements
- Agent reasoning visualization  
- Performance optimization
- Documentation

See issues for current tasks.
