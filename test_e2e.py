#!/usr/bin/env python3
"""Simple test script to verify end-to-end connectivity."""

import json
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir / "src"))
sys.path.insert(0, str(backend_dir / "src" / "mcp"))
sys.path.insert(0, str(backend_dir / "src" / "agent"))

from mcp.tools import MCPToolRegistry, PowerShellExecutor


def test_powershell_executor():
    """Test PowerShell execution."""
    print("\n=== Testing PowerShell Executor ===")
    
    workspace = "f:/work/code/simple-agent-demo/agent-workspace"
    executor = PowerShellExecutor(workspace)
    
    # Test 1: Get current directory
    print("\nTest 1: Get current directory")
    result = executor.execute('Get-Location')
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
    if result['error']:
        print(f"Error: {result['error']}")
    
    # Test 2: List files
    print("\nTest 2: List files in workspace")
    result = executor.execute('Get-ChildItem -Path .')
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
    
    # Test 3: Create a test file
    print("\nTest 3: Create test file")
    result = executor.execute('New-Item -ItemType File -Name test.txt -Value "Hello World"')
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
    
    # Test 4: Read the file
    print("\nTest 4: Read test file")
    result = executor.execute('Get-Content test.txt')
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
    
    # Test 5: Path escape attempt (should fail)
    print("\nTest 5: Try to access parent directory (should fail)")
    result = executor.execute('Get-ChildItem -Path ..')
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")


def test_mcp_tools():
    """Test MCP tool registry."""
    print("\n=== Testing MCP Tool Registry ===")
    
    workspace = "f:/work/code/simple-agent-demo/agent-workspace"
    registry = MCPToolRegistry(workspace)
    
    print("\nAvailable tools:")
    tools = registry.get_tools()
    for name, info in tools.items():
        print(f"  - {name}: {info.get('description', 'N/A')}")
    
    print("\nCalling execute_powershell tool:")
    result = registry.call_tool("execute_powershell", {"command": "Write-Host 'MCP Tool Test'"})
    print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")


async def test_agent():
    """Test the agent (requires OpenAI API key)."""
    print("\n=== Testing Agent ===")
    
    import os
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Skipping agent test - OPENAI_API_KEY not set")
        return
    
    try:
        from agent import Agent
        
        print("Initializing agent...")
        config_dir = str(Path(__file__).parent / "backend" / "config")
        workspace_path = "f:/work/code/simple-agent-demo/agent-workspace"
        
        agent = Agent(config_dir, workspace_path, api_key)
        print("Agent initialized successfully")
        
        print("\nSending test message to agent...")
        count = 0
        for response in agent.stream_response("当前目录里有什么文件？"):
            count += 1
            print(f"Response {count}: {response['type']}")
            if response['type'] == 'text':
                print(f"  Text: {response['data'][:100]}...")
            elif response['type'] == 'tool_start':
                print(f"  Tool: {response['data']['tool']}")
            elif response['type'] == 'tool_result':
                print(f"  Result: {response['data'][:100]}...")
    
    except ImportError as e:
        print(f"Error: Could not import Agent: {e}")
    except Exception as e:
        print(f"Error during agent test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("AI Agent POC - End-to-End Test")
    print("=" * 40)
    
    try:
        test_powershell_executor()
    except Exception as e:
        print(f"PowerShell executor test failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_mcp_tools()
    except Exception as e:
        print(f"MCP tools test failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_agent()
    except Exception as e:
        print(f"Agent test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 40)
    print("Test completed")
