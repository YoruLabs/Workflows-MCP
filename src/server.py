"""
Workflows MCP Server

A Model Context Protocol server that enables AI agents to programmatically
create, manage, and execute Python workflow scripts.

Author: YoruLabs
License: MIT
"""

import asyncio
import os
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("workflows-mcp")

# Configuration
WORKFLOWS_DIR = os.environ.get("WORKFLOWS_DIR", os.path.join(os.path.dirname(__file__), "..", "workflows"))
Path(WORKFLOWS_DIR).mkdir(parents=True, exist_ok=True)


def get_workflow_path(name: str) -> Path:
    """Get the full path for a workflow file."""
    # Sanitize the name to prevent directory traversal
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
    # Allow passing params as JSON via command line
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


@mcp.tool()
def create_workflow(name: str, description: str, code: str) -> dict:
    """
    Create a new Python workflow script.
    
    Args:
        name: The name of the workflow (will be used as filename, e.g., "meeting_review_to_slack")
        description: A description of what the workflow does
        code: The Python code for the workflow. Must include a `run(params: dict = None) -> dict` function.
    
    Returns:
        dict: Status of the operation with the file path
    
    Example code structure:
        def run(params: dict = None) -> dict:
            params = params or {}
            # Your workflow logic here
            return {"status": "success", "result": "..."}
    """
    try:
        workflow_path = get_workflow_path(name)
        
        # Check if workflow already exists
        if workflow_path.exists():
            return {
                "status": "error",
                "message": f"Workflow '{name}' already exists. Use update_workflow to modify it."
            }
        
        # Generate the full script
        script_content = generate_workflow_script(name, description, code)
        
        # Write the file
        workflow_path.write_text(script_content)
        
        return {
            "status": "success",
            "message": f"Workflow '{name}' created successfully",
            "path": str(workflow_path),
            "name": name
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create workflow: {str(e)}"
        }


def _run_workflow_subprocess(workflow_path: str, params_json: str, cwd: str, timeout: int) -> dict:
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


@mcp.tool()
async def execute_workflow(name: str, params: dict = None) -> dict:
    """
    Execute a workflow script by name.
    
    Args:
        name: The name of the workflow to execute
        params: Optional dictionary of parameters to pass to the workflow's run() function
    
    Returns:
        dict: The result of the workflow execution
    """
    try:
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {
                "status": "error",
                "message": f"Workflow '{name}' not found"
            }
        
        # Prepare the command
        params_json = json.dumps(params or {})
        
        # Execute the workflow in a separate thread to avoid blocking the event loop
        try:
            result = await asyncio.to_thread(
                _run_workflow_subprocess,
                str(workflow_path),
                params_json,
                WORKFLOWS_DIR,
                300  # 5 minute timeout
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": f"Workflow '{name}' timed out after 5 minutes"
            }
        
        # Parse the output
        output = result["stdout"]
        error = result["stderr"]
        
        if result["return_code"] != 0:
            return {
                "status": "error",
                "message": f"Workflow execution failed",
                "error": error,
                "output": output,
                "return_code": result["return_code"]
            }
        
        # Try to parse output as JSON
        try:
            output_data = json.loads(output) if output else {}
        except json.JSONDecodeError:
            output_data = {"raw_output": output}
        
        return {
            "status": "success",
            "message": f"Workflow '{name}' executed successfully",
            "result": output_data,
            "stderr": error if error else None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to execute workflow: {str(e)}"
        }


@mcp.tool()
def list_workflows() -> dict:
    """
    List all available workflow scripts.
    
    Returns:
        dict: List of workflows with their metadata
    """
    try:
        workflows = []
        workflows_path = Path(WORKFLOWS_DIR)
        
        for file in workflows_path.glob("*.py"):
            # Read the file to extract metadata
            content = file.read_text()
            
            # Extract description from docstring
            description = ""
            lines = content.split("\n")
            for line in lines:
                if line.startswith("Description:"):
                    description = line.replace("Description:", "").strip()
                    break
            
            workflows.append({
                "name": file.stem,
                "path": str(file),
                "description": description,
                "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
        
        return {
            "status": "success",
            "count": len(workflows),
            "workflows": workflows
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list workflows: {str(e)}"
        }


@mcp.tool()
def read_workflow(name: str) -> dict:
    """
    Read the source code of a workflow script.
    
    Args:
        name: The name of the workflow to read
    
    Returns:
        dict: The workflow source code and metadata
    """
    try:
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {
                "status": "error",
                "message": f"Workflow '{name}' not found"
            }
        
        content = workflow_path.read_text()
        
        return {
            "status": "success",
            "name": name,
            "path": str(workflow_path),
            "content": content
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to read workflow: {str(e)}"
        }


@mcp.tool()
def update_workflow(name: str, description: str = None, code: str = None) -> dict:
    """
    Update an existing workflow script.
    
    Args:
        name: The name of the workflow to update
        description: New description (optional, keeps existing if not provided)
        code: New Python code (optional, keeps existing if not provided)
    
    Returns:
        dict: Status of the operation
    """
    try:
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {
                "status": "error",
                "message": f"Workflow '{name}' not found. Use create_workflow to create it."
            }
        
        # Read existing content to preserve metadata if needed
        existing_content = workflow_path.read_text()
        
        # Extract existing description if not provided
        if description is None:
            for line in existing_content.split("\n"):
                if line.startswith("Description:"):
                    description = line.replace("Description:", "").strip()
                    break
            description = description or "No description"
        
        # If no new code provided, extract existing code
        if code is None:
            # Find the code after the imports
            lines = existing_content.split("\n")
            code_start = 0
            for i, line in enumerate(lines):
                if line.startswith("def run(") or line.startswith("async def run("):
                    code_start = i
                    break
            
            # Extract from run function to before if __name__
            code_lines = []
            for i in range(code_start, len(lines)):
                if lines[i].startswith('if __name__'):
                    break
                code_lines.append(lines[i])
            code = "\n".join(code_lines)
        
        # Generate updated script
        script_content = generate_workflow_script(name, description, code)
        
        # Write the file
        workflow_path.write_text(script_content)
        
        return {
            "status": "success",
            "message": f"Workflow '{name}' updated successfully",
            "path": str(workflow_path)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update workflow: {str(e)}"
        }


@mcp.tool()
def delete_workflow(name: str) -> dict:
    """
    Delete a workflow script.
    
    Args:
        name: The name of the workflow to delete
    
    Returns:
        dict: Status of the operation
    """
    try:
        workflow_path = get_workflow_path(name)
        
        if not workflow_path.exists():
            return {
                "status": "error",
                "message": f"Workflow '{name}' not found"
            }
        
        workflow_path.unlink()
        
        return {
            "status": "success",
            "message": f"Workflow '{name}' deleted successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to delete workflow: {str(e)}"
        }


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
