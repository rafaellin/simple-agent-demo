# Agent Skills

## file_operation

**Trigger**: User requests file-related operations

**Flow**: 
1. Understand user intent (create, read, modify, delete files)
2. Generate appropriate PowerShell commands
3. Invoke MCP tool to execute
4. Explain results to user

**Example Commands**:
- "List files in current directory" → `Get-ChildItem -Path .`
- "Create a new file test.txt" → `New-Item -ItemType File -Name test.txt`
- "Read content of README.md" → `Get-Content README.md`
- "Delete old.txt" → `Remove-Item old.txt`
- "Create directory data" → `New-Item -ItemType Directory -Name data`

## info_query

**Trigger**: User queries information

**Flow**:
1. Use PowerShell commands to get system or file information
2. Organize and return results

**Examples**:
- "What is the current directory?" → `Get-Location`
- "What files are in the workspace?" → `Get-ChildItem -Path . -Recurse`
