import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import yaml

from agent import Agent

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Gateway")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent: Agent = None


def load_config():
    """Load configuration from YAML file."""
    config_file = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load config file: {e}")
        return {}


@app.on_event("startup")
async def startup():
    """Initialize agent on startup."""
    global agent
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set - agent will not function")
    
    config = load_config()
    config_dir = str(Path(__file__).parent.parent.parent / "config")
    workspace_path = config.get("workspace", {}).get("path", "agent-workspace")
    
    # Create workspace if it doesn't exist
    workspace_dir = Path(workspace_path)
    try:
        workspace_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workspace directory ensured at: {workspace_path}")
    except Exception as e:
        logger.error(f"Failed to create workspace directory: {e}")
    
    try:
        agent = Agent(config_dir, workspace_path, api_key or "sk-test")
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "agent_ready": agent is not None,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for agent chat."""
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()
            logger.info(f"Received: {message}")
            
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({
                        "type": "error",
                        "data": "Invalid JSON format",
                    })
                )
                continue
            
            message_type = data.get("type")
            message_content = data.get("data", "")
            
            if message_type == "chat":
                try:
                    # Stream agent response with approval handling
                    for response in agent.stream_response(message_content):
                        # If approval is needed, send it and wait for response
                        if response.get("type") == "approval_request":
                            await websocket.send_text(json.dumps(response))
                            
                            # Wait for user approval/rejection
                            approval_message = await websocket.receive_text()
                            approval_data = json.loads(approval_message)
                            
                            if approval_data.get("type") == "approve":
                                logger.info("User approved tool execution")
                                agent.resume_with_approval()
                                # Continue streaming the rest of the conversation
                                for resume_response in agent.stream_response(""):
                                    await websocket.send_text(json.dumps(resume_response))
                                break
                            elif approval_data.get("type") == "reject":
                                logger.info("User rejected tool execution")
                                agent.pending_approval = None
                                await websocket.send_text(
                                    json.dumps({
                                        "type": "text",
                                        "data": "Tool execution cancelled by user",
                                    })
                                )
                                await websocket.send_text(
                                    json.dumps({
                                        "type": "end",
                                        "data": "Conversation ended",
                                    })
                                )
                                break
                        else:
                            # Regular response, send to client
                            await websocket.send_text(json.dumps(response))
                except Exception as e:
                    logger.error(f"Error streaming response: {e}", exc_info=True)
                    await websocket.send_text(
                        json.dumps({
                            "type": "error",
                            "data": f"Error: {str(e)}",
                        })
                    )
            
            elif message_type == "reset":
                # Reset conversation
                if agent:
                    agent.reset_conversation()
                await websocket.send_text(
                    json.dumps({
                        "type": "reset",
                        "data": "Conversation reset",
                    })
                )
            
            elif message_type == "history":
                # Get message history
                if agent:
                    history = agent.get_message_history()
                    await websocket.send_text(
                        json.dumps({
                            "type": "history",
                            "data": history,
                        })
                    )
            
            else:
                await websocket.send_text(
                    json.dumps({
                        "type": "error",
                        "data": f"Unknown message type: {message_type}",
                    })
                )
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_text(
                json.dumps({
                    "type": "error",
                    "data": f"Server error: {str(e)}",
                })
            )
        except:
            pass


def run_gateway(host: str = "127.0.0.1", port: int = 8765):
    """Run the gateway server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    print(f"Starting AI Agent Gateway on {host}:{port}")
    print(f"WebSocket URL: ws://{host}:{port}/ws")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    run_gateway()
