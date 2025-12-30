"""
MCP HTTP Server for Skills

Implements the Model Context Protocol over HTTP with SSE (Server-Sent Events)
for integration with Manus and other MCP-compatible clients.

Based on the Agent Skills specification: https://agentskills.io/specification
"""

import os
import json
import asyncio
import subprocess
import sys
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import uvicorn

# Configuration
SKILLS_DIR = os.environ.get("SKILLS_DIR", os.path.join(os.path.dirname(__file__), "..", "skills"))
Path(SKILLS_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Skills MCP Server",
    description="A Model Context Protocol server for discovering, loading, and executing Agent Skills",
    version="0.2.0"
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


def convert_string_booleans(obj: Any) -> Any:
    """
    Recursively convert string 'true'/'false' values to actual booleans.
    """
    if isinstance(obj, dict):
        return {key: convert_string_booleans(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_string_booleans(item) for item in obj]
    elif isinstance(obj, str):
        if obj.lower() == 'true':
            return True
        elif obj.lower() == 'false':
            return False
        return obj
    else:
        return obj


def parse_skill_frontmatter(content: str) -> tuple:
    """Parse YAML frontmatter from SKILL.md content."""
    frontmatter = {}
    body = content
    
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
            except yaml.YAMLError:
                pass
    
    return frontmatter, body


def get_skill_path(name: str) -> Path:
    """Get the full path for a skill directory."""
    safe_name = "".join(c for c in name if c.isalnum() or c in "_-").lower()
    return Path(SKILLS_DIR) / safe_name


def validate_skill_name(name: str) -> tuple:
    """Validate skill name according to Agent Skills spec."""
    if not name:
        return False, "Name cannot be empty"
    if len(name) > 64:
        return False, "Name must be 64 characters or less"
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
        return False, "Name must be lowercase alphanumeric with hyphens"
    if '--' in name:
        return False, "Name cannot contain consecutive hyphens"
    return True, ""


def list_skill_resources(skill_path: Path) -> dict:
    """List all resources available in a skill directory."""
    resources = {"scripts": [], "references": [], "assets": []}
    
    for resource_type in resources.keys():
        resource_dir = skill_path / resource_type
        if resource_dir.exists():
            resources[resource_type] = [f.name for f in resource_dir.iterdir() if f.is_file()]
    
    return resources


# MCP Tool Definitions
MCP_TOOLS = [
    {
        "name": "list_skills",
        "description": "START HERE: List all available skills with their name and description. This is the first tool to call when using Skills MCP. It returns the name and description of each skill (first level of progressive disclosure). After finding a relevant skill, use `get_skill` to load its full instructions.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_skill",
        "description": "SECOND STEP: Load a skill's full SKILL.md content and metadata. Call this after finding a skill via `list_skills`. This loads the full instructions (second level of progressive disclosure). After loading the skill, use `execute_skill_script` to run any scripts mentioned in the instructions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The skill name (e.g., 'data-analysis')"
                },
                "include_resources": {
                    "type": "boolean",
                    "description": "Whether to list available scripts/references/assets (default: true)"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "get_skill_resource",
        "description": "OPTIONAL: Load a specific resource file from a skill (reference docs, assets). Use this to load additional documentation or assets referenced in the skill's instructions (third level of progressive disclosure).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "The skill name"
                },
                "resource_path": {
                    "type": "string",
                    "description": "Relative path to resource (e.g., 'references/api.md')"
                }
            },
            "required": ["skill_name", "resource_path"]
        }
    },
    {
        "name": "execute_skill_script",
        "description": "THIRD STEP: Execute a pre-built script from a skill's scripts/ directory. Call this after loading a skill with `get_skill` to run one of its scripts. The skill's instructions will tell you which scripts are available and what parameters they accept.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "The skill name (e.g., 'data-analysis')"
                },
                "script_name": {
                    "type": "string",
                    "description": "Name of script file in scripts/ directory (e.g., 'analyze.py')"
                },
                "params": {
                    "type": "object",
                    "description": "Optional parameters to pass to the script's run() function"
                }
            },
            "required": ["skill_name", "script_name"]
        }
    }
]


# Tool Handlers
def handle_list_skills() -> dict:
    """List all available skills."""
    try:
        skills = []
        skills_path = Path(SKILLS_DIR)
        
        for skill_dir in skills_path.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            
            content = skill_md.read_text()
            frontmatter, _ = parse_skill_frontmatter(content)
            
            skills.append({
                "name": frontmatter.get("name", skill_dir.name),
                "description": frontmatter.get("description", "No description provided"),
                "path": str(skill_dir)
            })
        
        return {
            "status": "success",
            "count": len(skills),
            "skills": skills,
            "hint": "Use get_skill(name) to load full instructions for a specific skill"
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to list skills: {str(e)}"}


def handle_get_skill(name: str, include_resources: bool = True) -> dict:
    """Load a skill's full content."""
    try:
        is_valid, error = validate_skill_name(name)
        if not is_valid:
            return {"status": "error", "message": f"Invalid skill name: {error}"}
        
        skill_path = get_skill_path(name)
        skill_md = skill_path / "SKILL.md"
        
        if not skill_path.exists() or not skill_md.exists():
            return {"status": "error", "message": f"Skill '{name}' not found"}
        
        content = skill_md.read_text()
        frontmatter, body = parse_skill_frontmatter(content)
        
        result = {
            "status": "success",
            "name": frontmatter.get("name", name),
            "description": frontmatter.get("description", "No description"),
            "instructions": body,
            "metadata": frontmatter.get("metadata", {}),
        }
        
        if "license" in frontmatter:
            result["license"] = frontmatter["license"]
        if "compatibility" in frontmatter:
            result["compatibility"] = frontmatter["compatibility"]
        
        if include_resources:
            result["resources"] = list_skill_resources(skill_path)
            result["hint"] = "Use execute_skill_script(skill_name, script_name, params) to run a script"
        
        return result
    except Exception as e:
        return {"status": "error", "message": f"Failed to load skill: {str(e)}"}


def handle_get_skill_resource(skill_name: str, resource_path: str) -> dict:
    """Load a specific resource from a skill."""
    try:
        is_valid, error = validate_skill_name(skill_name)
        if not is_valid:
            return {"status": "error", "message": f"Invalid skill name: {error}"}
        
        skill_path = get_skill_path(skill_name)
        if not skill_path.exists():
            return {"status": "error", "message": f"Skill '{skill_name}' not found"}
        
        resource_path = resource_path.lstrip("/")
        if ".." in resource_path:
            return {"status": "error", "message": "Invalid resource path"}
        
        allowed_prefixes = ["references/", "assets/", "scripts/"]
        if not any(resource_path.startswith(prefix) for prefix in allowed_prefixes):
            return {"status": "error", "message": f"Resource must be in one of: {allowed_prefixes}"}
        
        full_path = skill_path / resource_path
        if not full_path.exists():
            return {"status": "error", "message": f"Resource '{resource_path}' not found"}
        
        return {
            "status": "success",
            "skill_name": skill_name,
            "resource_path": resource_path,
            "content": full_path.read_text(),
            "size_bytes": full_path.stat().st_size
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to load resource: {str(e)}"}


async def handle_execute_skill_script(skill_name: str, script_name: str, params: dict = None) -> dict:
    """Execute a script from a skill."""
    try:
        is_valid, error = validate_skill_name(skill_name)
        if not is_valid:
            return {"status": "error", "message": f"Invalid skill name: {error}"}
        
        skill_path = get_skill_path(skill_name)
        if not skill_path.exists():
            return {"status": "error", "message": f"Skill '{skill_name}' not found"}
        
        if "/" in script_name or "\\" in script_name or ".." in script_name:
            return {"status": "error", "message": "Invalid script name"}
        
        script_path = skill_path / "scripts" / script_name
        if not script_path.exists():
            scripts_dir = skill_path / "scripts"
            available = []
            if scripts_dir.exists():
                available = [f.name for f in scripts_dir.iterdir() if f.suffix == ".py"]
            return {
                "status": "error",
                "message": f"Script '{script_name}' not found",
                "available_scripts": available
            }
        
        params = convert_string_booleans(params or {})
        params_json = json.dumps(params)
        
        try:
            result = await asyncio.to_thread(
                lambda: subprocess.run(
                    [sys.executable, str(script_path), params_json],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(skill_path)
                )
            )
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": f"Script '{script_name}' timed out"}
        
        if result.returncode != 0:
            return {
                "status": "error",
                "message": "Script execution failed",
                "error": result.stderr.strip(),
                "output": result.stdout.strip()
            }
        
        try:
            output_data = json.loads(result.stdout.strip()) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            output_data = {"raw_output": result.stdout.strip()}
        
        return {
            "status": "success",
            "message": f"Script '{script_name}' executed successfully",
            "skill_name": skill_name,
            "script_name": script_name,
            "result": output_data
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute script: {str(e)}"}


async def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """Route tool calls to appropriate handlers."""
    if tool_name == "list_skills":
        return handle_list_skills()
    elif tool_name == "get_skill":
        return handle_get_skill(
            arguments.get("name", ""),
            arguments.get("include_resources", True)
        )
    elif tool_name == "get_skill_resource":
        return handle_get_skill_resource(
            arguments.get("skill_name", ""),
            arguments.get("resource_path", "")
        )
    elif tool_name == "execute_skill_script":
        return await handle_execute_skill_script(
            arguments.get("skill_name", ""),
            arguments.get("script_name", ""),
            arguments.get("params")
        )
    else:
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}


# HTTP Endpoints
@app.get("/")
async def root():
    return {"name": "Skills MCP Server", "version": "0.2.0", "protocol": "MCP"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Main MCP endpoint for JSON-RPC requests."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
        )
    
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "skills-mcp", "version": "0.2.0"}
            },
            "id": request_id
        })
    
    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {"tools": MCP_TOOLS},
            "id": request_id
        })
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result = await handle_tool_call(tool_name, arguments)
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
            "id": request_id
        })
    
    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Method not found: {method}"},
            "id": request_id
        })


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for streaming responses."""
    session_id = str(uuid.uuid4())
    sessions[session_id] = asyncio.Queue()
    
    async def event_generator():
        yield {"event": "endpoint", "data": f"/mcp/messages/{session_id}"}
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(sessions[session_id].get(), timeout=30)
                    yield {"event": "message", "data": json.dumps(message)}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            sessions.pop(session_id, None)
    
    return EventSourceResponse(event_generator())


@app.post("/mcp/messages/{session_id}")
async def mcp_messages(session_id: str, request: Request):
    """Handle MCP messages for a specific session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    if method == "initialize":
        response = {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "skills-mcp", "version": "0.2.0"}
            },
            "id": request_id
        }
    elif method == "tools/list":
        response = {
            "jsonrpc": "2.0",
            "result": {"tools": MCP_TOOLS},
            "id": request_id
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result = await handle_tool_call(tool_name, arguments)
        response = {
            "jsonrpc": "2.0",
            "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
            "id": request_id
        }
    else:
        response = {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Method not found: {method}"},
            "id": request_id
        }
    
    await sessions[session_id].put(response)
    return JSONResponse({"status": "accepted"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
