#!/usr/bin/env python3
"""Main entry point for the AI Agent backend."""

import sys
import os
from pathlib import Path
import yaml

# Add src to path so we can import modules
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir / "src"))
sys.path.insert(0, str(backend_dir / "src" / "mcp"))
sys.path.insert(0, str(backend_dir / "src" / "agent"))

# Set environment variables if needed
if not os.environ.get("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY environment variable not set")
    print("Please set OPENAI_API_KEY before running: $env:OPENAI_API_KEY = 'sk-...'")

# Load configuration
config_file = backend_dir / "config" / "config.yaml"
try:
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
except Exception as e:
    print(f"Error loading config: {e}")
    config = {}

from agent.gateway import run_gateway


if __name__ == "__main__":
    print("Starting AI Agent Gateway...")
    
    gateway_config = config.get("gateway", {})
    host = gateway_config.get("host", "127.0.0.1")
    port = gateway_config.get("port", 8765)
    
    print(f"WebSocket server running at ws://{host}:{port}")
    run_gateway(host=host, port=port)
