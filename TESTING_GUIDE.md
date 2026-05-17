# Testing Guide - AI Agent POC

## Prerequisites

Before testing, ensure all requirements are installed:

### Backend Requirements
```bash
cd backend
pip install -r requirements.txt
```

Dependencies:
- python-3.10+
- langchain-openai
- fastapi
- uvicorn
- pyyaml
- websockets (via fastapi)

### Frontend Requirements
```bash
cd frontend
npm install
```

Dependencies:
- react ^18.2.0
- react-dom ^18.2.0
- vite ^5.0.0
- @tauri-apps/api (for future Tauri builds)
- @tauri-apps/cli (for future Tauri builds)

## Environment Setup

### 1. Set OpenAI API Key (Required for agent functionality)

**PowerShell:**
```powershell
$env:OPENAI_API_KEY = "sk-your-api-key-here"
```

**Command Prompt (CMD):**
```cmd
set OPENAI_API_KEY=sk-your-api-key-here
```

**Bash/Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

### 2. Verify Workspace Directory Exists

The workspace should be created automatically, but you can verify:
- Location: `f:/work/code/simple-agent-demo/agent-workspace/`
- Will be auto-created if missing
- All file operations are restricted to this directory

## Testing Procedures

### Phase 1: Unit Tests

Run end-to-end tests to verify all components:

```bash
python test_e2e.py
```

This will test:
1. **PowerShell Executor** - Direct PowerShell execution
   - Get current location
   - List files
   - Create test file
   - Read test file
   - Path validation (escape prevention)

2. **MCP Tools** - Tool registry
   - List available tools
   - Call execute_powershell tool

3. **Agent** - LangGraph agent (requires OpenAI API key)
   - Agent initialization
   - Message streaming
   - Tool invocation

**Expected output:**
```
AI Agent POC - End-to-End Test
========================================

=== Testing PowerShell Executor ===
Test 1: Get current directory
Success: True
Output: [workspace path]
...

=== Testing MCP Tool Registry ===
Available tools:
  - execute_powershell: Execute PowerShell command within workspace
...

=== Testing Agent ===
Initializing agent...
Agent initialized successfully

Sending test message to agent...
Response 1: text
Response 2: tool_start
Response 3: tool_result
...
```

### Phase 2: Backend Integration Test

**Terminal 1 - Start Backend:**
```bash
cd backend
python main.py
```

Expected output:
```
Starting AI Agent Gateway...
WebSocket server running at ws://127.0.0.1:8765

[Backend logs will appear here]
```

**Terminal 2 - Test WebSocket Connection:**

Using Node.js/Python WebSocket client or browser:

```python
import asyncio
import websockets
import json

async def test():
    uri = "ws://127.0.0.1:8765/ws"
    async with websockets.connect(uri) as ws:
        # Send test message
        await ws.send(json.dumps({
            "type": "chat",
            "data": "列出当前目录的文件"
        }))
        
        # Receive responses
        while True:
            try:
                response = await ws.recv()
                print(json.loads(response))
            except:
                break

asyncio.run(test())
```

### Phase 3: Frontend Integration Test

**Terminal 3 - Start Frontend (after backend is running):**
```bash
cd frontend
npm run dev
```

Expected output:
```
  VITE v5.x.x  ready in 123 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

**Browser Test:**
1. Open http://localhost:5173
2. Should see:
   - Chat interface with message history
   - Connection status (green indicator = connected)
   - Input textarea and Send button
   - Empty state message

3. Try sending messages:
   - "List files in workspace"
   - "Create test.txt"
   - "What files are here?"

### Phase 4: Complete End-to-End Flow

**Setup:**
1. Terminal 1: Backend running (`python backend/main.py`)
2. Terminal 2: Frontend running (`npm run dev`)
3. Browser: http://localhost:5173 open

**Test Scenario 1: Simple File Listing**
```
User: "列出当前目录的文件"
      (Chinese: "List files in current directory")

Expected flow:
1. User message appears in chat
2. Loading indicator shows
3. Agent decides to use PowerShell tool
4. Tool status: "⚙️ Executing: execute_powershell"
5. Tool result: file listing
6. Agent responds with formatted list
7. Conversation ends
```

**Test Scenario 2: File Creation**
```
User: "创建一个叫 hello.txt 的文件，内容是 Hello World"
      (Chinese: "Create a file called hello.txt with content Hello World")

Expected flow:
1. Agent calls PowerShell tool with New-Item command
2. Tool output shown
3. Agent confirms file creation
4. All happens in agent-workspace/
```

**Test Scenario 3: File Reading**
```
User: "读取 hello.txt 的内容"
      (Chinese: "Read the content of hello.txt")

Expected flow:
1. Agent executes Get-Content command
2. Tool result shows file contents
3. Agent returns content to user
```

**Test Scenario 4: Error Handling**
```
User: "列出 C:\\Windows 下的文件"
      (Chinese: "List files in C:\\Windows")

Expected behavior:
1. Agent attempts operation
2. Path validation blocks access (outside workspace)
3. Error message returned to user
4. Conversation continues gracefully
```

## Troubleshooting

### Issue: WebSocket Connection Failed

**Symptoms:**
- Connection status shows "Disconnected"
- Console error: "WebSocket connection failed"

**Solutions:**
1. Ensure backend is running: `python backend/main.py`
2. Check port 8765 is not in use: `netstat -ano | findstr :8765`
3. Check firewall settings allow localhost:8765
4. Verify no proxy is interfering

### Issue: Tool Execution Fails

**Symptoms:**
- "⚙️ Executing" status shows but no result
- Error message in chat

**Solutions:**
1. Verify `agent-workspace` directory exists
2. Check PowerShell is available: `powershell.exe -Command "Get-Location"`
3. Check file permissions in workspace
4. Review backend logs for error details

### Issue: Agent Not Responding

**Symptoms:**
- Message sent but no response
- No loading indicator

**Solutions:**
1. Check `OPENAI_API_KEY` is set: `$env:OPENAI_API_KEY`
2. Verify API key is valid (check OpenAI account)
3. Check internet connection
4. Review backend logs for API errors
5. Verify rate limits not exceeded

### Issue: Frontend Not Loading

**Symptoms:**
- Blank page or error at http://localhost:5173

**Solutions:**
1. Ensure frontend dependencies installed: `npm install`
2. Check Vite dev server is running
3. Clear browser cache and reload
4. Check for JavaScript errors in browser console
5. Try different port: `npm run dev -- --port 5174`

## Performance Testing

### Load Testing
Monitor agent responsiveness with multiple requests:

```bash
# Send multiple concurrent messages
for i in {1..5}; do
  # Send message in background
  python -c "
import asyncio, websockets, json
async def test():
    async with websockets.connect('ws://127.0.0.1:8765/ws') as ws:
        await ws.send(json.dumps({'type': 'chat', 'data': 'List files'}))
        async for msg in ws:
            print(msg)
            break
asyncio.run(test())
  " &
done
```

### Memory Usage
Monitor resource consumption:
```bash
# PowerShell
Get-Process python | Select-Object Name, WorkingSet, Threads
```

## Test Results Template

```markdown
# Test Results - [Date]

## Environment
- Python: [version]
- Node: [version]
- OS: Windows 10/11
- OpenAI API: [model name]

## Unit Tests
- [ ] PowerShell Executor: PASS/FAIL
- [ ] MCP Tool Registry: PASS/FAIL
- [ ] Agent Streaming: PASS/FAIL

## Integration Tests
- [ ] Backend startup: PASS/FAIL
- [ ] WebSocket connection: PASS/FAIL
- [ ] Frontend loads: PASS/FAIL

## End-to-End Tests
- [ ] File listing: PASS/FAIL
- [ ] File creation: PASS/FAIL
- [ ] File reading: PASS/FAIL
- [ ] Error handling: PASS/FAIL
- [ ] Multi-turn conversation: PASS/FAIL

## Issues Found
[List any bugs or issues]

## Performance
- First response time: [ms]
- Tool execution time: [ms]
- Avg message latency: [ms]
```

## Success Criteria

✓ All unit tests pass
✓ Backend starts without errors
✓ Frontend loads in browser
✓ WebSocket connection established (green indicator)
✓ Messages are sent and received
✓ Agent calls tools when appropriate
✓ Tool results displayed in chat
✓ File operations work in workspace
✓ Path validation prevents escape
✓ Error messages are user-friendly
✓ Conversation can continue after errors
✓ Multi-turn conversations work
✓ Both Chinese and English supported

## Next Steps

Once testing is complete:
1. Review any issues or bugs
2. Check performance metrics
3. Plan improvements for Phase 2
4. Consider Tauri build for desktop app
5. Add persistent storage if needed
