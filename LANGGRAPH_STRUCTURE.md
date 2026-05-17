# LangGraph Structure

## Agent Graph Architecture

```
                    ┌─────────────────┐
                    │     START       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────────────────┐
                    │   call_model Node           │
                    │ (LLM with tool binding)     │
                    │                             │
                    │ - System prompt             │
                    │ - Message history           │
                    │ - Tool schema               │
                    │ → Returns AIMessage         │
                    └────────┬────────────────────┘
                             │
                             ▼
            ┌────────────────────────────────────┐
            │  should_continue (Conditional)     │
            └────────────┬──────────┬────────────┘
                         │          │
              ┌──────────┴─┐        └─────────────┐
              │ Has tools  │                      │ No tools
              │ & < 5 iter │                      │ or >= 5 iter
              ▼            │                      │
      ┌──────────────────────────┐              │
      │ execute_tools Node       │              │
      │                          │              │
      │ - Extract tool calls     │              │
      │ - Validate path safety   │              │
      │ - Run PowerShell         │              │
      │ - Collect results        │              │
      │ → Returns ToolMessages   │              │
      └──────────────┬───────────┘              │
                     │                          │
                     └──────────┬────────────────┘
                                │
                                ▼
                         (back to call_model)
                                │
                                └─[loop up to 5 times]
                                │
                                ▼
                    ┌─────────────────────┐
                    │       END           │
                    └─────────────────────┘
```

## State Type Definition

```python
class AgentState(TypedDict):
    """State for the agent graph."""
    messages: list              # All messages in conversation
    user_message: str           # Original user message
    max_iterations: int         # Maximum tool calls (default 5)
    iteration: int              # Current iteration count
```

## Node Definitions

### 1. `call_model` Node

**Purpose**: Call the LLM with the current state

**Input**: AgentState with accumulated messages

**Process**:
1. Build tool schema for PowerShell execution
2. Construct message list for LLM:
   - System prompt first
   - All messages from state (user, assistant, tool)
3. Call `self.llm.bind_tools(tools).invoke(messages)`
4. Add LLM response to messages

**Output**: AgentState with new AIMessage added

```python
def _call_model_node(self, state: AgentState) -> dict:
    # Build messages_for_llm
    # Call LLM with tools
    # Add response to messages
    # Return updated state
```

### 2. `execute_tools` Node

**Purpose**: Execute PowerShell tools if LLM requested them

**Input**: AgentState with AIMessage containing tool_calls

**Process**:
1. Extract tool_calls from last message
2. For each tool call:
   - Get tool name and arguments
   - Call `process_tool_call()` which:
     - Validates workspace path
     - Executes PowerShell command
     - Returns JSON result
   - Create ToolMessage with result
3. Add all ToolMessages to messages

**Output**: AgentState with new ToolMessages added

```python
def _execute_tools_node(self, state: AgentState) -> dict:
    # Get last message and tool calls
    # For each tool call:
    #   - Execute tool
    #   - Create ToolMessage
    # Return state with tool results added
```

### 3. `should_continue` Conditional Edge

**Purpose**: Route to END or back to call_model

**Decision Logic**:
```
IF iteration >= max_iterations:
    RETURN "end"
ELIF last_message has tool_calls:
    RETURN "execute_tools"
ELSE:
    RETURN "end"
```

**Prevents**:
- Infinite loops (max 5 iterations)
- Unnecessary tool execution

## Message Flow Example

### User: "Create a file test.txt"

```
Initial State:
  messages: [HumanMessage("Create a file test.txt")]
  iteration: 0

↓ call_model node

State after call_model:
  messages: [
    HumanMessage("Create a file test.txt"),
    AIMessage(
      content="I'll create that file...",
      tool_calls=[{"name": "execute_powershell", "args": {"command": "New-Item..."}}]
    )
  ]
  iteration: 1

↓ should_continue → "execute_tools" (has tool calls)

State after execute_tools:
  messages: [
    HumanMessage("Create a file test.txt"),
    AIMessage(...tool_calls...),
    ToolMessage(content='{"success": true, "output": "..."}')
  ]
  iteration: 1

↓ should_continue → "execute_tools" (still has unprocessed tool calls?)
  OR "end" (no more tools needed)

If "end": → END state
  Final messages: [HumanMessage, AIMessage, ToolMessage, maybe another AIMessage]
```

## Key Differences from Manual Loop

| Aspect | Before | After (LangGraph) |
|--------|--------|-------------------|
| **Structure** | Manual while loop | StateGraph with nodes/edges |
| **State Management** | self.message_history | AgentState dict |
| **Routing** | if/else logic | Conditional edges |
| **Streaming** | Generator yields | Graph.stream() iterator |
| **Visibility** | Implicit | Explicit nodes |
| **Testability** | Coupled | Each node testable |
| **Extensibility** | Add more if/else | Add new nodes |

## Execution Flow in Gateway

```python
# In gateway.py
for response in agent.stream_response(user_message):
    # response is yielded from stream_response()
    # which internally calls: self.graph.stream(initial_state)
    # and yields appropriate message types
```

### What stream_response() does:

1. **Initialize**: Create AgentState with user message
2. **Execute**: `self.graph.stream(initial_state)`
   - Returns iterator over node executions
   - Each iteration is: `{"node_name": node_output}`
3. **Transform**: Convert node outputs to WebSocket message types:
   - AIMessage with content → `{"type": "text", "data": "..."}`
   - AIMessage with tool_calls → `{"type": "tool_start", ...}`
   - ToolMessage → `{"type": "tool_result", ...}`
4. **Yield**: Send to WebSocket client
5. **Finally**: Yield `{"type": "end"}` to signal completion

## Graph Compilation

```python
# In __init__:
self.graph = self._build_graph()  # Returns CompiledGraph

# In _build_graph:
graph = StateGraph(AgentState)
graph.add_node("call_model", self._call_model_node)
graph.add_node("execute_tools", self._execute_tools_node)
graph.add_edge(START, "call_model")
graph.add_conditional_edges("call_model", self._should_continue, {...})
graph.add_edge("execute_tools", "call_model")
return graph.compile()
```

## Advantages of This Approach

✅ **Explicit State**: AgentState clearly defines what's in play
✅ **Clear Flow**: Graph visualization shows exact routing
✅ **Scalable**: Easy to add new nodes (e.g., logging, validation)
✅ **Debuggable**: Each node output is visible
✅ **Interruptible**: Can pause/resume graph execution
✅ **Standard**: Uses LangGraph best practices
✅ **Traceable**: LangGraph provides built-in logging

## Testing Individual Nodes

```python
# Test just the call_model node
state = {
    "messages": [HumanMessage("test")],
    "user_message": "test",
    "max_iterations": 5,
    "iteration": 0,
}
result = agent._call_model_node(state)

# Test routing logic
should_end = agent._should_continue(state)
```
