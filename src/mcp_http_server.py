"""
MCP HTTP Server for Workflows

Implements the Model Context Protocol over HTTP with SSE (Server-Sent Events)
for integration with Manus and other MCP-compatible clients.
"""

import os
import json
import asyncio
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import uvicorn

# Configuration
WORKFLOWS_DIR = os.environ.get("WORKFLOWS_DIR", os.path.join(os.path.dirname(__file__), "..", "workflows"))
Path(WORKFLOWS_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Workflows MCP Server",
    description="A Model Context Protocol server for creating and executing Python workflow scripts",
    version="0.1.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for SSE sessions
sessions: Dict[str, asyncio.Queue] = {}


def get_workflow_path(name: str) -> Path:
    """Get the full path for a workflow file."""
    safe_name = "".join(c for c in name if c.isalnum() or c in "_-").lower()
    return Path(WORKFLOWS_DIR) / f"{safe_name}.py"


def generate_workflow_script(name: str, description: str, code: str) -> str:
    """Generate a complete workflow script with metadata."""
    template = f'''"""
Workflow: {name}
Description: {description}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Any, Dict, Optional

{code}

if __name__ == "__main__":
    params = {{}}
    if len(sys.argv) > 1:
        try:
            params = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print("Warning: Could not parse params as JSON")
    
    result = run(params)
    print(json.dumps(result, indent=2, default=str))
'''
    return template


# MCP Tool Definitions
MCP_TOOLS = [
    {
        "name": "create_workflow",
        "description": "Create a new Python workflow script. The code parameter must include a `run(params: dict = None) -> dict` function that serves as the entry point.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the workflow (will be used as filename, e.g., 'meeting_review_to_slack')"
                },
                "description": {
                    "type": "string",
                    "description": "A description of what the workflow does"
                },
                "code": {
                    "type": "string",
                    "description": "The Python code for the workflow. Must include a `run(params: dict = None) -> dict` function."
                }
            },
            "required": ["name", "description", "code"]
        }
    },
    {
        "name": "execute_workflow",
        "description": "Execute a workflow script by name with optional parameters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the workflow to execute"
                },
                "params": {
                    "type": "object",
                    "description": "Optional dictionary of parameters to pass to the workflow's run() function"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "list_workflows",
        "description": "List all available workflow scripts with their metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "read_workflow",
        "description": "Read the source code of a workflow script.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the workflow to read"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "update_workflow",
        "description": "Update an existing workflow script's description or code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the workflow to update"
                },
                "description": {
                    "type": "string",
                    "description": "New description (optional)"
                },
                "code": {
                    "type": "string",
                    "description": "New Python code (optional)"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "delete_workflow",
        "description": "Delete a workflow script.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the workflow to delete"
                }
            },
            "required": ["name"]
        }
    }
]


# Tool implementations
def tool_create_workflow(arguments: dict) -> dict:
    """Create a new workflow."""
    try:
        name = arguments.get("name")
        description = arguments.get("description", "")
        code = arguments.get("code", "")
        
        if not name:
            return {"error": "Workflow name is required"}
        
        workflow_path = get_workflow_path(name)
        
        if workflow_path.exists():
            return {"error": f"Workflow '{name}' already exists. Use update_workflow to modify it."}
        
        script_content = generate_workflow_script(name, description, code)
        workflow_path.write_text(script_content)
        
        return {
            "status": "success",
            "message": f"Workflow '{name}' created successfully",
            "path": str(workflow_path),
            "name": name
        }
    except Exception as e:
        return {"error": str(e)}


def _run_workflow_subprocess_sync(workflow_path: str, params_json: str, cwd: str, timeout: int) -> dict:
    """
    Run the workflow subprocess synchronously.
    This function is designed to be called via asyncio.to_thread() to avoid blocking the event loop.
    
    Args:
        workflow_path: Path to the workflow script
        params_json: JSON string of parameters
        cwd: Working directory for the subprocess
        timeout: Timeout in seconds
    
    Returns:
        dict: Result containing stdout, stderr, and return_code
    """
    result = subprocess.run(
        [sys.executable, workflow_path, params_json],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd
    )
    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "return_code": result.returncode
    }


async def tool_execute_workflow_async(arguments: dict) -> dict:
    """Execute a workflow asynchronously."""
    try:
        name = arguments.get("name")
        params = arguments.get("params", {})
        
        if not name:
            return {"error": "Workflow name is required"}
        
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {"error": f"Workflow '{name}' not found"}
        
        params_json = json.dumps(params)
        
        # Execute the workflow in a separate thread to avoid blocking the event loop
        try:
            result = await asyncio.to_thread(
                _run_workflow_subprocess_sync,
                str(workflow_path),
                params_json,
                WORKFLOWS_DIR,
                300  # 5 minute timeout
            )
        except subprocess.TimeoutExpired:
            return {"error": "Workflow timed out after 5 minutes"}
        
        output = result["stdout"]
        error = result["stderr"]
        
        if result["return_code"] != 0:
            return {
                "error": "Workflow execution failed",
                "stderr": error,
                "stdout": output
            }
        
        try:
            output_data = json.loads(output) if output else {}
        except json.JSONDecodeError:
            output_data = {"raw_output": output}
        
        return {
            "status": "success",
            "message": f"Workflow '{name}' executed successfully",
            "result": output_data
        }
    except Exception as e:
        return {"error": str(e)}


def tool_list_workflows(arguments: dict) -> dict:
    """List all workflows."""
    try:
        workflows = []
        workflows_path = Path(WORKFLOWS_DIR)
        
        for file in workflows_path.glob("*.py"):
            content = file.read_text()
            description = ""
            for line in content.split("\n"):
                if line.startswith("Description:"):
                    description = line.replace("Description:", "").strip()
                    break
            
            workflows.append({
                "name": file.stem,
                "description": description,
                "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
        
        return {"workflows": workflows, "count": len(workflows)}
    except Exception as e:
        return {"error": str(e)}


def tool_read_workflow(arguments: dict) -> dict:
    """Read a workflow's source code."""
    try:
        name = arguments.get("name")
        
        if not name:
            return {"error": "Workflow name is required"}
        
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {"error": f"Workflow '{name}' not found"}
        
        content = workflow_path.read_text()
        
        return {"name": name, "content": content}
    except Exception as e:
        return {"error": str(e)}


def tool_update_workflow(arguments: dict) -> dict:
    """Update an existing workflow."""
    try:
        name = arguments.get("name")
        description = arguments.get("description")
        code = arguments.get("code")
        
        if not name:
            return {"error": "Workflow name is required"}
        
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {"error": f"Workflow '{name}' not found"}
        
        existing_content = workflow_path.read_text()
        
        if description is None:
            for line in existing_content.split("\n"):
                if line.startswith("Description:"):
                    description = line.replace("Description:", "").strip()
                    break
            description = description or "No description"
        
        if code is None:
            lines = existing_content.split("\n")
            code_start = 0
            for i, line in enumerate(lines):
                if line.startswith("def run("):
                    code_start = i
                    break
            
            code_lines = []
            for i in range(code_start, len(lines)):
                if lines[i].startswith('if __name__'):
                    break
                code_lines.append(lines[i])
            code = "\n".join(code_lines)
        
        script_content = generate_workflow_script(name, description, code)
        workflow_path.write_text(script_content)
        
        return {"status": "success", "message": f"Workflow '{name}' updated successfully"}
    except Exception as e:
        return {"error": str(e)}


def tool_delete_workflow(arguments: dict) -> dict:
    """Delete a workflow."""
    try:
        name = arguments.get("name")
        
        if not name:
            return {"error": "Workflow name is required"}
        
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {"error": f"Workflow '{name}' not found"}
        
        workflow_path.unlink()
        
        return {"status": "success", "message": f"Workflow '{name}' deleted successfully"}
    except Exception as e:
        return {"error": str(e)}


# Sync tool handlers (for non-blocking operations)
TOOL_HANDLERS_SYNC = {
    "create_workflow": tool_create_workflow,
    "list_workflows": tool_list_workflows,
    "read_workflow": tool_read_workflow,
    "update_workflow": tool_update_workflow,
    "delete_workflow": tool_delete_workflow,
}

# Async tool handlers (for potentially blocking operations)
TOOL_HANDLERS_ASYNC = {
    "execute_workflow": tool_execute_workflow_async,
}


def create_jsonrpc_response(id: Any, result: Any) -> dict:
    """Create a JSON-RPC 2.0 response."""
    return {
        "jsonrpc": "2.0",
        "id": id,
        "result": result
    }


def create_jsonrpc_error(id: Any, code: int, message: str) -> dict:
    """Create a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "id": id,
        "error": {
            "code": code,
            "message": message
        }
    }


async def handle_jsonrpc_request(request: dict) -> dict:
    """Handle a JSON-RPC request."""
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")
    
    if method == "initialize":
        return create_jsonrpc_response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "workflows-mcp",
                "version": "0.1.0"
            }
        })
    
    elif method == "notifications/initialized":
        return None  # No response for notifications
    
    elif method == "tools/list":
        return create_jsonrpc_response(req_id, {
            "tools": MCP_TOOLS
        })
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Check if it's an async tool
        if tool_name in TOOL_HANDLERS_ASYNC:
            result = await TOOL_HANDLERS_ASYNC[tool_name](arguments)
        elif tool_name in TOOL_HANDLERS_SYNC:
            result = TOOL_HANDLERS_SYNC[tool_name](arguments)
        else:
            return create_jsonrpc_error(req_id, -32601, f"Tool '{tool_name}' not found")
        
        return create_jsonrpc_response(req_id, {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        })
    
    elif method == "ping":
        return create_jsonrpc_response(req_id, {})
    
    else:
        return create_jsonrpc_error(req_id, -32601, f"Method '{method}' not found")


@app.get("/")
async def root():
    """Health check and server info."""
    return {
        "name": "Workflows MCP Server",
        "version": "0.1.0",
        "status": "running",
        "mcp_endpoints": {
            "sse": "GET /sse",
            "messages": "POST /messages"
        }
    }


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP protocol."""
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    sessions[session_id] = queue
    
    async def event_generator():
        # Send the endpoint event first
        yield {
            "event": "endpoint",
            "data": f"/messages?session_id={session_id}"
        }
        
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield {
                        "event": "message",
                        "data": json.dumps(message)
                    }
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {
                        "event": "ping",
                        "data": ""
                    }
        finally:
            sessions.pop(session_id, None)
    
    return EventSourceResponse(event_generator())


@app.post("/messages")
async def messages_endpoint(request: Request, session_id: str = None):
    """Handle MCP messages."""
    try:
        body = await request.json()
    except:
        return JSONResponse(
            status_code=400,
            content=create_jsonrpc_error(None, -32700, "Parse error")
        )
    
    response = await handle_jsonrpc_request(body)
    
    if response is None:
        return JSONResponse(content={"status": "ok"})
    
    # If we have a session, also send via SSE
    if session_id and session_id in sessions:
        await sessions[session_id].put(response)
    
    return JSONResponse(content=response)


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Direct MCP endpoint (Streamable HTTP)."""
    try:
        body = await request.json()
    except:
        return JSONResponse(
            status_code=400,
            content=create_jsonrpc_error(None, -32700, "Parse error")
        )
    
    response = await handle_jsonrpc_request(body)
    
    if response is None:
        return JSONResponse(content={"status": "ok"})
    
    return JSONResponse(content=response)


# Keep the REST API endpoints for backward compatibility
@app.get("/tools")
async def list_tools_rest():
    """List all available MCP tools (REST API)."""
    return {"tools": MCP_TOOLS}


@app.get("/workflows")
async def list_workflows_rest():
    """List all workflows (REST API)."""
    return tool_list_workflows({})


@app.post("/workflows/{name}/execute")
async def execute_workflow_rest(name: str, request: Request):
    """Execute a workflow (REST API)."""
    try:
        body = await request.json()
    except:
        body = {}
    
    return await tool_execute_workflow_async({"name": name, "params": body.get("params", {})})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
