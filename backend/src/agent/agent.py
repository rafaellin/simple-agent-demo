import json
import logging
from typing import Any
from pathlib import Path

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain.chat_models import ChatOpenAI

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage

logger = logging.getLogger(__name__)


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
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=api_key,
            model="gpt-4o-mini",
            temperature=0.7,
        )
        
        # Build system prompt
        self.system_prompt = self._build_system_prompt()
        self.message_history = []

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

    def process_tool_call(self, tool_name: str, arguments: dict) -> str:
        """Process a tool call from the agent."""
        logger.info(f"Agent calling tool: {tool_name}")
        result = self.mcp_client.call_tool(tool_name, arguments)
        logger.info(f"Tool result: {result}")
        return result

    def stream_response(self, user_message: str):
        """Stream agent response to user message (generator for compatibility)."""
        self.message_history.append(HumanMessage(content=user_message))
        
        iteration = 0
        max_iterations = 5
        
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
        
        try:
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"Agent iteration {iteration}")
                
                # Build messages for LLM
                messages = [
                    {"role": "system", "content": self.system_prompt},
                ]
                
                for msg in self.message_history:
                    if isinstance(msg, HumanMessage):
                        messages.append({"role": "user", "content": msg.content})
                    elif isinstance(msg, AIMessage):
                        if msg.content:
                            messages.append({"role": "assistant", "content": msg.content})
                    elif isinstance(msg, ToolMessage):
                        messages.append({"role": "tool", "content": msg.content})
                
                # Get LLM response with tools
                try:
                    response = self.llm.bind_tools(tools).invoke(messages)
                except Exception as e:
                    logger.error(f"LLM error: {e}")
                    yield {
                        "type": "error",
                        "data": f"LLM error: {str(e)}",
                    }
                    break
                
                # Stream the response text
                if response.content:
                    yield {
                        "type": "text",
                        "data": response.content,
                    }
                
                # Check if tool was called
                if not hasattr(response, 'tool_calls') or not response.tool_calls:
                    # No more tool calls, we're done
                    self.message_history.append(AIMessage(content=response.content or ""))
                    break
                
                # Process tool calls
                self.message_history.append(response)
                
                for tool_call in response.tool_calls:
                    logger.info(f"Tool call: {tool_call}")
                    tool_name = tool_call.get("name") or tool_call.get("type")
                    tool_args = tool_call.get("args") or tool_call.get("arguments") or {}
                    tool_id = tool_call.get("id", f"call_{iteration}")
                    
                    # Yield tool execution status
                    yield {
                        "type": "tool_start",
                        "data": {"tool": tool_name, "args": tool_args},
                    }
                    
                    # Execute tool
                    try:
                        tool_result = self.process_tool_call(tool_name, tool_args)
                    except Exception as e:
                        tool_result = json.dumps({"error": str(e)})
                    
                    # Yield tool result
                    yield {
                        "type": "tool_result",
                        "data": tool_result,
                    }
                    
                    # Add tool result to history
                    self.message_history.append(
                        ToolMessage(
                            content=tool_result,
                            tool_call_id=tool_id,
                        )
                    )
        finally:
            # Signal end of conversation
            yield {
                "type": "end",
                "data": "Conversation completed",
            }
    
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
