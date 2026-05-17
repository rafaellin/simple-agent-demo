# Quick Start Reference

## 1️⃣ Install Requirements

```bash
# Python backend
cd backend
pip install -r requirements.txt

# Node.js frontend
cd frontend
npm install
```

## 2️⃣ Set Environment Variable

```powershell
$env:OPENAI_API_KEY = "sk-your-api-key-here"
```

## 3️⃣ Run Backend

```bash
cd backend
python main.py
```

Expected: `WebSocket server running at ws://127.0.0.1:8765`

## 4️⃣ Run Frontend (New Terminal)

```bash
cd frontend
npm run dev
```

Expected: `Local: http://localhost:5173`

## 5️⃣ Open in Browser

```
http://localhost:5173
```

Should see:
- Chat interface
- Green connection status
- Message input box

## ✅ Test It

Send a message:
```
列出当前目录的文件
(Chinese: List files in current directory)
```

Or in English:
```
What files are in the workspace?
```

## 📊 Complete Data Flow

```
You type message
    ↓
[Frontend] sends via WebSocket
    ↓
[Gateway] routes to Agent
    ↓
[Agent] calls OpenAI LLM
    ↓
[LLM] decides to use PowerShell tool
    ↓
[MCP] validates path & executes
    ↓
[PowerShell] runs command in workspace
    ↓
[Result] streams back to chat
    ↓
You see answer
```

## 🔧 Troubleshoot

| Problem | Fix |
|---------|-----|
| WebSocket fails | Backend not running on port 8765 |
| Agent doesn't respond | OPENAI_API_KEY not set |
| Commands fail | Workspace directory doesn't exist |
| Port 5173 in use | Kill Node: `npm run dev -- --port 5174` |

## 📁 Key Files

- **Backend Config**: `backend/config/config.yaml`
- **System Prompt**: `backend/config/system.md`
- **Chat UI**: `frontend/src/Chat.jsx`
- **Tests**: `test_e2e.py`

## 🎯 Test Commands

```python
# In PowerShell while backend is running:
python test_e2e.py
```

Tests:
- PowerShell execution
- Tool registry
- Agent streaming

## 📝 Notes

- Workspace: `agent-workspace/` (auto-created)
- All operations restricted to workspace
- Max 5 tool calls per request
- Supports Chinese & English
- Chat history only in memory (current session)

## 🚀 Build Desktop App (Tauri)

```bash
cd frontend
npm run tauri build

# Produces exe in: src-tauri/target/release/
```

---

**Status**: ✅ Ready to test  
**All code**: ✅ Complete  
**Documentation**: ✅ Included
