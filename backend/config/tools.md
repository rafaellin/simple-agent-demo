# MCP Tools

## execute_powershell

**服务**: Local MCP Server

**功能**: 在workspace内执行PowerShell命令

**约束**: 
- 仅操作 `f:/work/code/simple-agent-demo/agent-workspace` 路径下的文件和目录
- 禁止路径穿越（../ 或绝对路径超出范围）

**参数**:
- `command` (string): PowerShell命令

**返回**:
- `output` (string): 命令执行的标准输出
- `error` (string): 如有错误，返回错误信息
- `exit_code` (int): 命令退出码

**示例**:
- `Get-ChildItem -Path .`
- `New-Item -ItemType File -Name test.txt`
- `Get-Content test.txt`
