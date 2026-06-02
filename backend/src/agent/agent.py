import json
import logging
from typing import Any, Literal
from pathlib import Path
from datetime import datetime

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain.chat_models import ChatOpenAI

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from memory import MemoryManager

logger = logging.getLogger(__name__)


class ApprovalCheckpoint:
    """Checkpoint that captures graph state at approval point."""
    
    def __init__(self, iteration: int, messages: list, pending_approval: dict):
        self.iteration = iteration
        self.messages = messages
        self.pending_approval = pending_approval
        self.timestamp = datetime.now()
    
    def __repr__(self) -> str:
        return f"ApprovalCheckpoint(iter={self.iteration}, cmd={self.pending_approval.get('command', 'unknown')[:30]}...)"


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: list
    user_message: str
    max_iterations: int
    iteration: int
    pending_approval: dict | None
    approval_given: bool


class ConfigLoader:
    """Load configuration from YAML and markdown files."""

    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)

    def load_system_prompt(self) -> str:
        """Load system prompt from system.md."""
        system_file = self.config_dir / "system.md"
        if system_file.exists():
            return system_file.read_text(encoding="utf-8")
        return "You are a helpful AI assistant."

    def load_tools_info(self) -> str:
        """Load tools information from tools.md."""
        tools_file = self.config_dir / "tools.md"
        if tools_file.exists():
            return tools_file.read_text(encoding="utf-8")
        return ""

    def load_skills_info(self) -> str:
        """Load skills information from skills.md."""
        skills_file = self.config_dir / "skills.md"
        if skills_file.exists():
            return skills_file.read_text(encoding="utf-8")
        return ""


class MCPClient:
    """Communicate with MCP server via subprocess."""

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self._tool_cache = None

    def _execute_tool(self, tool_name: str, arguments: dict) -> dict[str, Any]:
        """Execute a tool by calling the MCP server directly."""
        from mcp.tools import MCPToolRegistry
        
        registry = MCPToolRegistry(self.workspace_path)
        return registry.call_tool(tool_name, arguments)

    def list_tools(self) -> list[dict[str, Any]]:
        """List available tools."""
        if self._tool_cache is None:
            from mcp.tools import MCPToolRegistry
            
            registry = MCPToolRegistry(self.workspace_path)
            tools_dict = registry.get_tools()
            self._tool_cache = [
                {
                    "name": name,
                    "description": info.get("description", ""),
                    "input_schema": info.get("parameters", {}),
                }
                for name, info in tools_dict.items()
            ]
        return self._tool_cache

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool and return string result."""
        result = self._execute_tool(tool_name, arguments)
        return json.dumps(result, ensure_ascii=False)


class Agent:
    """LangGraph-based agent for handling conversations."""

    def __init__(self, config_dir: str, workspace_path: str, api_key: str):
        self.config = ConfigLoader(config_dir)
        self.mcp_client = MCPClient(workspace_path)
        self.api_key = api_key
        self.workspace_path = workspace_path
        self.checkpoint = None
        
        # Initialize memory system
        self.memory = MemoryManager(workspace_path)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=api_key,
            model="gpt-4o-mini",
            temperature=0.7,
        )
        
        # Build system prompt
        self.system_prompt = self._build_system_prompt()
        self.message_history = []
        
        # Track pending approvals
        self.pending_approval = None
        self.approval_was_given = False
        
        # Build the LangGraph
        self.graph = self._build_graph()

    def _build_system_prompt(self) -> str:
        """Build the system prompt including tools info and memory context."""
        system = self.config.load_system_prompt()
        tools_info = self.config.load_tools_info()
        skills_info = self.config.load_skills_info()
        memory_context = self.memory.get_context_for_llm()
        
        prompt = f"""
{system}

## Available Tools
{tools_info}

## Skills
{skills_info}

## Memory Context
{memory_context if memory_context else "No prior facts or patterns stored yet."}

When you need to perform file operations or execute commands, use the available PowerShell tools.
Always respond in Chinese if the user writes in Chinese, otherwise in English.
"""
        return prompt.strip()

    def _build_graph(self):
        """Build the LangGraph state graph."""
        
        # Define the graph
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("call_model", self._call_model_node)
        graph.add_node("check_tool", self._check_tool_node)
        graph.add_node("execute_tools", self._execute_tools_node)
        
        # Add edges
        graph.add_edge(START, "call_model")
        graph.add_conditional_edges(
            "call_model",
            self._should_continue,
            {
                "check_tool": "check_tool",
                "end": END,
            },
        )
        graph.add_conditional_edges(
            "check_tool",
            self._should_execute_tool,
            {
                "execute_tools": "execute_tools",
                "end": END,
            },
        )
        graph.add_edge("execute_tools", "call_model")
        
        # Compile the graph
        return graph.compile()

    def _is_file_removal_command(self, command: str) -> tuple[bool, str]:
        """
        Check if a PowerShell command is a file removal operation.
        Returns (is_removal, description)
        """
        command_lower = command.lower().strip()
        
        # Check for common file removal patterns
        removal_patterns = [
            ("remove-item", "Remove-Item"),
            ("rm ", "Remove-Item (rm)"),
            ("del ", "Delete (del)"),
            ("erase ", "Erase"),
            ("rmdir ", "Remove Directory (rmdir)"),
        ]
        
        for pattern, description in removal_patterns:
            if pattern in command_lower:
                return True, description
        
        return False, ""

    def _check_tool_node(self, state: AgentState) -> dict:
        """Node that checks tool calls for dangerous operations."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # Check if last message has tool calls
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call.get("name") or tool_call.get("type")
                tool_args = tool_call.get("args") or tool_call.get("arguments") or {}
                
                # If it's a PowerShell tool, check the command
                if tool_name == "execute_powershell":
                    command = tool_args.get("command", "")
                    is_removal, removal_type = self._is_file_removal_command(command)
                    
                    if is_removal:
                        # Store approval info and mark as pending
                        self.pending_approval = {
                            "tool_call": tool_call,
                            "tool_name": tool_name,
                            "tool_args": tool_args,
                            "command": command,
                            "removal_type": removal_type,
                        }
                        # Create checkpoint at this point
                        self.checkpoint = ApprovalCheckpoint(
                            iteration=state["iteration"],
                            messages=messages.copy(),
                            pending_approval=self.pending_approval.copy(),
                        )
                        logger.info(f"Checkpoint created: {self.checkpoint}")
                        
                        
                        return {
                            "messages": messages,
                            "pending_approval": self.pending_approval,
                            "approval_given": False,
                        }
        
        # No dangerous operations detected, proceed normally
        return {
            "messages": messages,
            "pending_approval": None,
            "approval_given": False,
        }

    def _should_execute_tool(self, state: AgentState) -> Literal["execute_tools", "end"]:
        """Conditional edge: should we execute tool or wait for approval?"""
        # If there's a pending approval and user hasn't approved, stop
        if state.get("pending_approval") and not state.get("approval_given"):
            return "end"
        
        return "execute_tools"

    def _call_model_node(self, state: AgentState) -> dict:
        """Node that calls the LLM model."""
        logger.info(f"Agent iteration {state['iteration']}")
        
        # Build tools schema
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_powershell",
                    "description": "Execute PowerShell command in workspace",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "PowerShell command to execute",
                            }
                        },
                        "required": ["command"],
                    },
                },
            }
        ]
        
        # Build messages for LLM
        messages_for_llm = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                messages_for_llm.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                if msg.content:
                    messages_for_llm.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, ToolMessage):
                messages_for_llm.append({"role": "tool", "content": msg.content})
        
        # Call LLM with tools
        try:
            response = self.llm.bind_tools(tools).invoke(messages_for_llm)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise
        
        # Add response to messages
        messages = state["messages"] + [response]
        
        return {
            "messages": messages,
            "iteration": state["iteration"] + 1,
        }

    def _execute_tools_node(self, state: AgentState) -> dict:
        """Node that executes tools."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # Process tool calls
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            tool_calls = last_message.tool_calls
            for tool_call in tool_calls:
                logger.info(f"Executing tool: {tool_call}")
                
                tool_name = tool_call.get("name") or tool_call.get("type")
                tool_args = tool_call.get("args") or tool_call.get("arguments") or {}
                tool_id = tool_call.get("id", f"call_{state['iteration']}")
                
                # Execute tool
                try:
                    tool_result = self.process_tool_call(tool_name, tool_args)
                except Exception as e:
                    tool_result = json.dumps({"error": str(e)})
                
                # Add tool message to history
                messages = messages + [
                    ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_id,
                    )
                ]
        
        return {"messages": messages}

    def _should_continue(self, state: AgentState) -> Literal["execute_tools", "end"]:
        """Conditional edge: should we execute tools or end?"""
        # Check max iterations
        if state["iteration"] >= state["max_iterations"]:
            logger.info("Max iterations reached")
            return "end"
        
        # Check if last message has tool calls
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "execute_tools"
        
        return "end"

    def process_tool_call(self, tool_name: str, arguments: dict) -> str:
        """Process a tool call from the agent."""
        logger.info(f"Agent calling tool: {tool_name}")
        result = self.mcp_client.call_tool(tool_name, arguments)
        logger.info(f"Tool result: {result}")
        return result
    
    def _auto_summarize_conversation(self) -> None:
        """Automatically summarize conversation when threshold is reached."""
        try:
            recent_messages = self.memory.short_term.get_all_messages()
            if not recent_messages:
                return
            
            # Create a simple summary from recent messages
            user_messages = [m for m in recent_messages if m["role"] == "user"]
            assistant_messages = [m for m in recent_messages if m["role"] == "assistant"]
            
            summary = f"Conversation with {len(user_messages)} user messages and {len(assistant_messages)} assistant responses. "
            
            if user_messages:
                summary += f"Topics discussed: {', '.join([m['content'][:50] for m in user_messages[:3]])}"
            
            # Store summary in long-term memory
            summary_id = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.memory.create_summary(summary_id, summary)
            
            # Clear short-term memory after summarization
            self.memory.short_term.clear()
            
            logger.info(f"Auto-summarized conversation: {summary_id}")
        except Exception as e:
            logger.error(f"Error auto-summarizing conversation: {e}")

    def stream_response(self, user_message: str):
        """Stream agent response using LangGraph."""
        # Check if we're resuming with approval
        is_resuming = bool(self.checkpoint)
        
        if not is_resuming:
            # Add user message to history and memory
            self.message_history.append(HumanMessage(content=user_message))
            self.memory.add_message("user", user_message, metadata={"type": "user_input"})
        
        # Initialize state
        if is_resuming:
            # Restore from checkpoint
            logger.info(f"Resuming from checkpoint: {self.checkpoint}")
            initial_state = {
                "messages": self.checkpoint.messages.copy(),
                "user_message": "",
                "max_iterations": 5,
                "iteration": self.checkpoint.iteration,
                "pending_approval": self.checkpoint.pending_approval.copy() if not self.approval_was_given else None,
                "approval_given": self.approval_was_given,
            }
        else:
            # Fresh start
            initial_state = {
                "messages": self.message_history.copy(),
                "user_message": user_message,
                "max_iterations": 5,
                "iteration": 0,
                "pending_approval": None,
                "approval_given": False,
            }
        
        try:
            # Stream through the graph
            for output in self.graph.stream(initial_state):
                # output is a dict like {"call_model": {...}} or {"check_tool": {...}}
                node_name = list(output.keys())[0]
                node_output = output[node_name]
                
                logger.info(f"Node '{node_name}' executed")
                
                # Check if there's a pending approval
                if node_output.get("pending_approval"):
                    pending = node_output["pending_approval"]
                    self.pending_approval = pending
                    yield {
                        "type": "approval_request",
                        "data": {
                            "command": pending["command"],
                            "removal_type": pending["removal_type"],
                            "message": f"⚠️ About to execute {pending['removal_type']} command. Do you want to proceed?",
                        },
                    }
                    # Stop streaming, wait for approval
                    return
                
                # Extract and yield messages from this node
                if "messages" in node_output:
                    new_messages = node_output["messages"]
                    
                    # Yield appropriate message types based on content
                    for msg in new_messages:
                        if isinstance(msg, AIMessage):
                            # Yield text content if present
                            if msg.content:
                                yield {
                                    "type": "text",
                                    "data": msg.content,
                                }
                                # Add AI response to memory
                                self.memory.add_message("assistant", msg.content, 
                                                      metadata={"type": "ai_response"})
                            # Yield tool calls if present
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tool_call in msg.tool_calls:
                                    tool_name = tool_call.get("name") or tool_call.get("type")
                                    tool_args = tool_call.get("args") or tool_call.get("arguments") or {}
                                    yield {
                                        "type": "tool_start",
                                        "data": {"tool": tool_name, "args": tool_args},
                                    }
                        
                        elif isinstance(msg, ToolMessage):
                            yield {
                                "type": "tool_result",
                                "data": msg.content,
                            }
                            # Add tool result to memory
                            self.memory.add_message("tool", msg.content, 
                                                  metadata={"type": "tool_result"})
                    
                    # Update local history
                    self.message_history = new_messages
        
        except Exception as e:
            logger.error(f"Error in stream_response: {e}", exc_info=True)
            yield {
                "type": "error",
                "data": f"Error: {str(e)}",
            }
        finally:
            # Clear approval state if stream completed
            self.approval_was_given = False
            self.checkpoint = None
            self.pending_approval = None
            
            # Check if we should summarize the conversation
            if self.memory.should_summarize():
                self._auto_summarize_conversation()
            
            # Signal end of conversation
            yield {
                "type": "end",
                "data": "Conversation completed",
            }
    
    def resume_with_approval(self) -> None:
        """Signal approval for the pending dangerous operation.
        The graph will resume with approval_given=True and execute through _execute_tools_node.
        """
        if not self.checkpoint:
            logger.warning("No checkpoint to resume from")
            return
        
        logger.info(f"Approving operation: {self.checkpoint.pending_approval['command']}")
        
        # Set flag to indicate approval was given
        # stream_response() will check this when resuming
        self.approval_was_given = True
    
    def reject_pending_approval(self) -> None:
        """Reject the pending approval request."""
        if self.checkpoint:
            logger.info(f"Rejected: {self.checkpoint.pending_approval['command']}")
            self.checkpoint = None
            self.pending_approval = None
            self.approval_was_given = False
        else:
            logger.warning("No pending approval to reject")
    
    def get_message_history(self) -> list[dict]:
        """Get formatted message history."""
        history = []
        for msg in self.message_history:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        return history

    def reset_conversation(self):
        """Reset conversation history and clear any pending approvals."""
        self.message_history = []
        self.pending_approval = None
        self.checkpoint = None
        logger.info("Conversation reset")
    
    # Memory management methods
    def add_fact_to_memory(self, fact_id: str, fact: str, category: str = "general", 
                          confidence: float = 1.0) -> None:
        """Store a fact in long-term memory."""
        self.memory.long_term.add_fact(fact_id, fact, category, confidence)
        logger.info(f"Added fact to memory: {fact_id}")
    
    def retrieve_memory_fact(self, fact_id: str) -> dict:
        """Retrieve a fact from long-term memory."""
        fact = self.memory.long_term.get_fact(fact_id)
        return fact or {"error": f"Fact '{fact_id}' not found"}
    
    def set_memory_preference(self, key: str, value: Any) -> None:
        """Store a user preference in memory."""
        self.memory.long_term.set_preference(key, value)
        logger.info(f"Set preference: {key}")
    
    def get_memory_preferences(self) -> dict:
        """Get all stored preferences."""
        return self.memory.long_term.get_all_preferences()
    
    def get_memory_stats(self) -> dict:
        """Get current memory statistics."""
        stats = self.memory.get_memory_stats()
        stats["message_history_length"] = len(self.message_history)
        return stats
    
    def get_memory_summary(self) -> dict:
        """Get a summary of agent memory."""
        return {
            "stats": self.get_memory_stats(),
            "recent_summaries": self.memory.long_term.get_summaries(limit=3),
            "common_patterns": self.memory.long_term.get_common_patterns(limit=3),
            "stored_facts": len(self.memory.long_term.get_all_facts()),
            "user_preferences": self.get_memory_preferences()
        }
