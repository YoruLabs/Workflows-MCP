"""
HTTP Server for Workflows MCP

Exposes the MCP server via HTTP with SSE (Server-Sent Events) support
for remote access from mobile devices and other clients.
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import the workflow functions
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Configuration
WORKFLOWS_DIR = os.environ.get("WORKFLOWS_DIR", os.path.join(os.path.dirname(__file__), "..", "workflows"))
Path(WORKFLOWS_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Workflows MCP Server",
    description="A Model Context Protocol server for creating and executing Python workflow scripts",
    version="0.1.0"
)

# Enable CORS for mobile access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/")
async def root():
    """Health check and server info."""
    return {
        "name": "Workflows MCP Server",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "list_tools": "GET /tools",
            "call_tool": "POST /tools/{tool_name}",
            "list_workflows": "GET /workflows",
            "execute_workflow": "POST /workflows/{name}/execute"
        }
    }


@app.get("/tools")
async def list_tools():
    """List all available MCP tools."""
    tools = [
        {
            "name": "create_workflow",
            "description": "Create a new Python workflow script",
            "parameters": {
                "name": "string - The name of the workflow",
                "description": "string - Description of what the workflow does",
                "code": "string - Python code with a run(params) function"
            }
        },
        {
            "name": "execute_workflow",
            "description": "Execute a workflow by name",
            "parameters": {
                "name": "string - The name of the workflow to execute",
                "params": "object - Optional parameters to pass to the workflow"
            }
        },
        {
            "name": "list_workflows",
            "description": "List all available workflow scripts",
            "parameters": {}
        },
        {
            "name": "read_workflow",
            "description": "Read the source code of a workflow",
            "parameters": {
                "name": "string - The name of the workflow to read"
            }
        },
        {
            "name": "update_workflow",
            "description": "Update an existing workflow",
            "parameters": {
                "name": "string - The name of the workflow to update",
                "description": "string - New description (optional)",
                "code": "string - New Python code (optional)"
            }
        },
        {
            "name": "delete_workflow",
            "description": "Delete a workflow script",
            "parameters": {
                "name": "string - The name of the workflow to delete"
            }
        }
    ]
    return {"tools": tools}


@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    """Call an MCP tool by name."""
    try:
        body = await request.json()
    except:
        body = {}
    
    if tool_name == "create_workflow":
        return await create_workflow_handler(body)
    elif tool_name == "execute_workflow":
        return await execute_workflow_handler(body)
    elif tool_name == "list_workflows":
        return await list_workflows_handler()
    elif tool_name == "read_workflow":
        return await read_workflow_handler(body)
    elif tool_name == "update_workflow":
        return await update_workflow_handler(body)
    elif tool_name == "delete_workflow":
        return await delete_workflow_handler(body)
    else:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")


@app.get("/workflows")
async def list_workflows_handler():
    """List all available workflow scripts."""
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
                "path": str(file),
                "description": description,
                "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
        
        return {"status": "success", "count": len(workflows), "workflows": workflows}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/workflows/{name}/execute")
async def execute_workflow_endpoint(name: str, request: Request):
    """Execute a specific workflow."""
    try:
        body = await request.json()
    except:
        body = {}
    
    return await execute_workflow_handler({"name": name, "params": body.get("params", {})})


async def create_workflow_handler(body: dict):
    """Handle create_workflow tool call."""
    try:
        name = body.get("name")
        description = body.get("description", "")
        code = body.get("code", "")
        
        if not name:
            return {"status": "error", "message": "Workflow name is required"}
        
        workflow_path = get_workflow_path(name)
        
        if workflow_path.exists():
            return {"status": "error", "message": f"Workflow '{name}' already exists"}
        
        script_content = generate_workflow_script(name, description, code)
        workflow_path.write_text(script_content)
        
        return {
            "status": "success",
            "message": f"Workflow '{name}' created successfully",
            "path": str(workflow_path),
            "name": name
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def execute_workflow_handler(body: dict):
    """Handle execute_workflow tool call."""
    import subprocess
    
    try:
        name = body.get("name")
        params = body.get("params", {})
        
        if not name:
            return {"status": "error", "message": "Workflow name is required"}
        
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {"status": "error", "message": f"Workflow '{name}' not found"}
        
        params_json = json.dumps(params)
        
        result = subprocess.run(
            [sys.executable, str(workflow_path), params_json],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=WORKFLOWS_DIR
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode != 0:
            return {
                "status": "error",
                "message": "Workflow execution failed",
                "error": error,
                "output": output
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
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Workflow timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def read_workflow_handler(body: dict):
    """Handle read_workflow tool call."""
    try:
        name = body.get("name")
        
        if not name:
            return {"status": "error", "message": "Workflow name is required"}
        
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {"status": "error", "message": f"Workflow '{name}' not found"}
        
        content = workflow_path.read_text()
        
        return {
            "status": "success",
            "name": name,
            "path": str(workflow_path),
            "content": content
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def update_workflow_handler(body: dict):
    """Handle update_workflow tool call."""
    try:
        name = body.get("name")
        description = body.get("description")
        code = body.get("code")
        
        if not name:
            return {"status": "error", "message": "Workflow name is required"}
        
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {"status": "error", "message": f"Workflow '{name}' not found"}
        
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
        
        return {
            "status": "success",
            "message": f"Workflow '{name}' updated successfully",
            "path": str(workflow_path)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def delete_workflow_handler(body: dict):
    """Handle delete_workflow tool call."""
    try:
        name = body.get("name")
        
        if not name:
            return {"status": "error", "message": "Workflow name is required"}
        
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {"status": "error", "message": f"Workflow '{name}' not found"}
        
        workflow_path.unlink()
        
        return {"status": "success", "message": f"Workflow '{name}' deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
