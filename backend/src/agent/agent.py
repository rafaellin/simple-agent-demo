import json
import logging
from typing import Any, Literal
from pathlib import Path

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain.chat_models import ChatOpenAI

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


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
        
        # Build the LangGraph
        self.graph = self._build_graph()

    def _build_system_prompt(self) -> str:
        """Build the system prompt including tools info."""
        system = self.config.load_system_prompt()
        tools_info = self.config.load_tools_info()
        skills_info = self.config.load_skills_info()
        
        prompt = f"""
{system}

## Available Tools
{tools_info}

## Skills
{skills_info}

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

    def stream_response(self, user_message: str):
        """Stream agent response using LangGraph."""
        # Check if we're resuming with approval
        is_resuming = bool(self.pending_approval)
        
        if not is_resuming:
            # Add user message to history
            self.message_history.append(HumanMessage(content=user_message))
        
        # Initialize state
        initial_state = {
            "messages": self.message_history.copy(),
            "user_message": user_message if not is_resuming else "",
            "max_iterations": 5,
            "iteration": 0,
            "pending_approval": self.pending_approval,
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
                    
                    # Update local history
                    self.message_history = new_messages
        
        except Exception as e:
            logger.error(f"Error in stream_response: {e}", exc_info=True)
            yield {
                "type": "error",
                "data": f"Error: {str(e)}",
            }
        finally:
            # Signal end of conversation
            yield {
                "type": "end",
                "data": "Conversation completed",
            }
    
    def resume_with_approval(self) -> None:
        """Resume streaming after user has approved a dangerous operation."""
        if not self.pending_approval:
            logger.warning("No pending approval to resume")
            return
        
        logger.info(f"Resuming with approval for: {self.pending_approval['command']}")
        
        # Execute the approved tool
        tool_name = self.pending_approval["tool_name"]
        tool_args = self.pending_approval["tool_args"]
        
        try:
            tool_result = self.process_tool_call(tool_name, tool_args)
            
            # Create tool message and add to history
            tool_message = ToolMessage(
                content=tool_result,
                tool_call_id=f"call_approved_{id(self.pending_approval)}",
            )
            self.message_history.append(tool_message)
            
            logger.info(f"Tool executed successfully: {tool_result}")
        except Exception as e:
            logger.error(f"Error executing approved tool: {e}")
            tool_message = ToolMessage(
                content=json.dumps({"error": str(e)}),
                tool_call_id=f"call_approved_{id(self.pending_approval)}",
            )
            self.message_history.append(tool_message)
        finally:
            # Clear pending approval
            self.pending_approval = None
    
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
        """Reset conversation history."""
        self.message_history = []
