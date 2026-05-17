import json
import logging
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from tools import MCPToolRegistry

logger = logging.getLogger(__name__)


def create_mcp_server(workspace_path: str) -> Server:
    """Create and configure MCP server."""
    server = Server("powershell-executor")
    registry = MCPToolRegistry(workspace_path)

    @server.list_tools()
    async def list_tools():
        """List available tools."""
        tools_dict = registry.get_tools()
        return [
            types.Tool(
                name=name,
                description=info.get("description", ""),
                inputSchema=info.get("parameters", {}),
            )
            for name, info in tools_dict.items()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> Any:
        """Call a tool."""
        logger.info(f"MCP call_tool: {name} with args: {arguments}")
        result = registry.call_tool(name, arguments)
        
        # Return result as string for MCP protocol
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    return server


async def run_mcp_server(workspace_path: str):
    """Run MCP server using stdio transport."""
    server = create_mcp_server(workspace_path)
    async with stdio_server(server) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    import sys
    
    logging.basicConfig(level=logging.INFO)
    workspace = "f:/work/code/simple-agent-demo/agent-workspace"
    asyncio.run(run_mcp_server(workspace))
