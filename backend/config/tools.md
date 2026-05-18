# MCP Tools

## execute_powershell

**Service**: Local MCP Server

**Function**: Execute PowerShell commands within workspace

**Constraints**: 
- Only operates on files and directories within `f:/work/code/simple-agent-demo/agent-workspace`
- Path traversal is prohibited (../ or absolute paths outside the allowed range)

**Parameters**:
- `command` (string): PowerShell command to execute

**Returns**:
- `output` (string): Standard output from command execution
- `error` (string): Error message if any error occurs
- `exit_code` (int): Command exit code

**Examples**:
- `Get-ChildItem -Path .`
- `New-Item -ItemType File -Name test.txt`
- `Get-Content test.txt`
