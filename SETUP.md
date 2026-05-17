# Setup Instructions

## Prerequisites

- Python 3.10+
- Node.js 18+
- Rust (for Tauri build)
- PowerShell 5.1+
- OpenAI API key

## Backend Setup

```bash
# 1. Install Python dependencies
cd backend
pip install -r requirements.txt

# 2. Set environment variable with your OpenAI API key
$env:OPENAI_API_KEY = "your-api-key-here"

# 3. Create workspace directory
mkdir agent-workspace

# 4. Run the gateway
python main.py
```

The gateway will start on `ws://127.0.0.1:8765`

## Frontend Setup

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Development mode (web preview)
npm run dev

# 3. Build Tauri app (requires Rust)
npm run tauri build
```

## Testing End-to-End Flow

1. Start the Python backend gateway:
   ```bash
   cd backend
   python main.py
   ```

2. In another terminal, start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Open http://localhost:5173 in your browser

4. Try these commands:
   - "列出当前目录的文件" (List files in current directory)
   - "创建一个文件 test.txt" (Create a file named test.txt)
   - "读取 test.txt 内容" (Read content of test.txt)

## Architecture

```
Frontend (React + Tauri)
    ↓ WebSocket (JSON)
Gateway (FastAPI)
    ↓ subprocess
Agent (LangGraph + OpenAI)
    ↓ tool calls
MCP Server (PowerShell)
    ↓ executes
PowerShell Commands
```

## Key Components

- **MCP Server**: Provides PowerShell execution tool in `backend/src/mcp/`
- **Agent**: LangGraph-based AI agent in `backend/src/agent/agent.py`
- **Gateway**: FastAPI WebSocket server in `backend/src/agent/gateway.py`
- **Frontend**: React chat UI in `frontend/src/`

## Troubleshooting

### WebSocket Connection Failed
- Make sure the backend is running on port 8765
- Check firewall settings
- Verify OPENAI_API_KEY is set

### Tool Execution Failed
- Check that `agent-workspace` directory exists
- Ensure PowerShell 5.1+ is available
- Check workspace path in `backend/config/config.yaml`

### LLM API Errors
- Verify your OpenAI API key is valid
- Check your account has available quota
- Make sure you're using the correct API endpoint

## Next Steps

- Customize system prompt in `backend/config/system.md`
- Add more tools in `backend/src/mcp/tools.py`
- Enhance UI in `frontend/src/`
- Build final Tauri app with `npm run tauri build`
