# Agent Skills

## file_operation

**触发**: 用户请求文件相关操作

**流程**: 
1. 理解用户意图（创建、读取、修改、删除文件）
2. 生成合适的PowerShell命令
3. 调用MCP工具执行
4. 解释结果给用户

**示例命令**:
- "列出当前目录的文件" → `Get-ChildItem -Path .`
- "创建一个新文件 test.txt" → `New-Item -ItemType File -Name test.txt`
- "读取 README.md 内容" → `Get-Content README.md`
- "删除 old.txt" → `Remove-Item old.txt`
- "创建目录 data" → `New-Item -ItemType Directory -Name data`

## info_query

**触发**: 用户查询信息

**流程**:
1. 使用PowerShell命令获取系统或文件信息
2. 整理结果并返回

**示例**:
- "当前目录是什么？" → `Get-Location`
- "workspace里有什么文件？" → `Get-ChildItem -Path . -Recurse`
