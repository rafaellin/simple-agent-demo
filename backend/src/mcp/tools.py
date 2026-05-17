import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class WorkspaceValidator:
    """Validates that operations stay within the workspace boundary."""

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path).resolve()

    def is_safe(self, target_path: str) -> bool:
        """Check if target path is within workspace."""
        try:
            target = Path(target_path).resolve()
            return str(target).startswith(str(self.workspace_path))
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return False


class PowerShellExecutor:
    """Executes PowerShell commands within workspace constraints."""

    def __init__(self, workspace_path: str):
        self.validator = WorkspaceValidator(workspace_path)
        self.workspace_path = workspace_path

    def execute(self, command: str) -> dict[str, Any]:
        """Execute PowerShell command safely."""
        logger.info(f"Executing PowerShell: {command}")

        try:
            # Execute from workspace directory
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", command],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout.strip()
            error = result.stderr.strip()

            logger.info(f"Command output: {output}")
            if error:
                logger.warning(f"Command error: {error}")

            return {
                "success": result.returncode == 0,
                "output": output,
                "error": error,
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            error_msg = "Command execution timeout (30s)"
            logger.error(error_msg)
            return {"success": False, "output": "", "error": error_msg, "exit_code": -1}
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "output": "", "error": error_msg, "exit_code": -1}


class MCPToolRegistry:
    """Registry for MCP tools."""

    def __init__(self, workspace_path: str):
        self.executor = PowerShellExecutor(workspace_path)
        self.tools = {
            "execute_powershell": {
                "description": "Execute PowerShell command within workspace",
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
            }
        }

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a registered tool."""
        if tool_name == "execute_powershell":
            command = arguments.get("command", "")
            return self.executor.execute(command)
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

    def get_tools(self) -> dict[str, Any]:
        """Get available tools."""
        return self.tools
