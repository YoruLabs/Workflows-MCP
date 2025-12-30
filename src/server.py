"""
Skills MCP Server

A Model Context Protocol server that enables AI agents to discover, load,
and execute Agent Skills - organized folders of instructions, scripts, 
and resources that give agents additional capabilities.

Based on the Agent Skills specification: https://agentskills.io/specification

Author: YoruLabs
License: MIT
"""

import asyncio
import os
import json
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("skills-mcp")

# Configuration
SKILLS_DIR = os.environ.get("SKILLS_DIR", os.path.join(os.path.dirname(__file__), "..", "skills"))
Path(SKILLS_DIR).mkdir(parents=True, exist_ok=True)


def parse_skill_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from SKILL.md content.
    
    Args:
        content: Full content of SKILL.md file
    
    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    frontmatter = {}
    body = content
    
    # Check for YAML frontmatter (content between --- markers)
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
    # Sanitize the name to prevent directory traversal
    safe_name = "".join(c for c in name if c.isalnum() or c in "_-").lower()
    return Path(SKILLS_DIR) / safe_name


def validate_skill_name(name: str) -> tuple[bool, str]:
    """
    Validate skill name according to Agent Skills spec.
    
    Args:
        name: The skill name to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Name cannot be empty"
    
    if len(name) > 64:
        return False, "Name must be 64 characters or less"
    
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
        return False, "Name must be lowercase alphanumeric with hyphens, cannot start/end with hyphen"
    
    if '--' in name:
        return False, "Name cannot contain consecutive hyphens"
    
    return True, ""


def list_skill_resources(skill_path: Path) -> dict:
    """
    List all resources available in a skill directory.
    
    Args:
        skill_path: Path to the skill directory
    
    Returns:
        Dict with scripts, references, and assets lists
    """
    resources = {
        "scripts": [],
        "references": [],
        "assets": []
    }
    
    scripts_dir = skill_path / "scripts"
    if scripts_dir.exists():
        resources["scripts"] = [f.name for f in scripts_dir.iterdir() if f.is_file()]
    
    references_dir = skill_path / "references"
    if references_dir.exists():
        resources["references"] = [f.name for f in references_dir.iterdir() if f.is_file()]
    
    assets_dir = skill_path / "assets"
    if assets_dir.exists():
        resources["assets"] = [f.name for f in assets_dir.iterdir() if f.is_file()]
    
    return resources


@mcp.tool()
def list_skills() -> dict:
    """
    List all available skills with their name and description.
    
    START HERE: This is the first tool to call when using Skills MCP.
    It returns the name and description of each skill, which is the first
    level of progressive disclosure. Use this to discover what skills are
    available before loading or executing them.
    
    After finding a relevant skill, use `get_skill` to load its full instructions.
    
    Returns:
        dict: List of skills with name, description, and path
    
    Example response:
        {
            "status": "success",
            "count": 2,
            "skills": [
                {
                    "name": "data-analysis",
                    "description": "Analyze CSV and Excel files with pandas...",
                    "path": "/skills/data-analysis"
                },
                ...
            ]
        }
    """
    try:
        skills = []
        skills_path = Path(SKILLS_DIR)
        
        for skill_dir in skills_path.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            
            # Read and parse SKILL.md
            content = skill_md.read_text()
            frontmatter, _ = parse_skill_frontmatter(content)
            
            # Extract name and description (required fields)
            name = frontmatter.get("name", skill_dir.name)
            description = frontmatter.get("description", "No description provided")
            
            skills.append({
                "name": name,
                "description": description,
                "path": str(skill_dir)
            })
        
        return {
            "status": "success",
            "count": len(skills),
            "skills": skills,
            "hint": "Use get_skill(name) to load full instructions for a specific skill"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list skills: {str(e)}"
        }


@mcp.tool()
def get_skill(name: str, include_resources: bool = True) -> dict:
    """
    Load a skill's full SKILL.md content and metadata.
    
    SECOND STEP: Call this after finding a skill via `list_skills`.
    This loads the full instructions (second level of progressive disclosure).
    The instructions tell you how to use the skill and what scripts are available.
    
    After loading the skill, use `execute_skill_script` to run any scripts
    mentioned in the instructions.
    
    Args:
        name: The skill name (e.g., "data-analysis")
        include_resources: Whether to list available scripts/references/assets (default: True)
    
    Returns:
        dict: Skill metadata, full instructions, and available resources
    
    Example response:
        {
            "status": "success",
            "name": "data-analysis",
            "description": "Analyze CSV files...",
            "instructions": "# Data Analysis\\n\\n## How to use...",
            "resources": {
                "scripts": ["analyze.py", "visualize.py"],
                "references": ["api_reference.md"],
                "assets": ["template.json"]
            }
        }
    """
    try:
        # Validate name
        is_valid, error = validate_skill_name(name)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Invalid skill name: {error}"
            }
        
        skill_path = get_skill_path(name)
        skill_md = skill_path / "SKILL.md"
        
        if not skill_path.exists() or not skill_md.exists():
            return {
                "status": "error",
                "message": f"Skill '{name}' not found. Use list_skills() to see available skills."
            }
        
        # Read and parse SKILL.md
        content = skill_md.read_text()
        frontmatter, body = parse_skill_frontmatter(content)
        
        result = {
            "status": "success",
            "name": frontmatter.get("name", name),
            "description": frontmatter.get("description", "No description"),
            "instructions": body,
            "metadata": frontmatter.get("metadata", {}),
        }
        
        # Add optional fields if present
        if "license" in frontmatter:
            result["license"] = frontmatter["license"]
        
        if "compatibility" in frontmatter:
            result["compatibility"] = frontmatter["compatibility"]
        
        if "allowed-tools" in frontmatter:
            result["allowed_tools"] = frontmatter["allowed-tools"]
        
        # List available resources
        if include_resources:
            result["resources"] = list_skill_resources(skill_path)
            result["hint"] = "Use execute_skill_script(skill_name, script_name, params) to run a script"
        
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load skill: {str(e)}"
        }


@mcp.tool()
def get_skill_resource(skill_name: str, resource_path: str) -> dict:
    """
    Load a specific resource file from a skill (reference docs, assets, etc.).
    
    OPTIONAL: Use this to load additional documentation or assets referenced
    in the skill's instructions. This is the third level of progressive disclosure.
    
    Args:
        skill_name: The skill name (e.g., "data-analysis")
        resource_path: Relative path to resource (e.g., "references/api.md" or "assets/template.json")
    
    Returns:
        dict: Resource content and metadata
    """
    try:
        # Validate skill name
        is_valid, error = validate_skill_name(skill_name)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Invalid skill name: {error}"
            }
        
        skill_path = get_skill_path(skill_name)
        
        if not skill_path.exists():
            return {
                "status": "error",
                "message": f"Skill '{skill_name}' not found"
            }
        
        # Sanitize and validate resource path (prevent directory traversal)
        resource_path = resource_path.lstrip("/")
        if ".." in resource_path:
            return {
                "status": "error",
                "message": "Invalid resource path"
            }
        
        # Only allow access to specific directories
        allowed_prefixes = ["references/", "assets/", "scripts/"]
        if not any(resource_path.startswith(prefix) for prefix in allowed_prefixes):
            return {
                "status": "error",
                "message": f"Resource must be in one of: {allowed_prefixes}"
            }
        
        full_path = skill_path / resource_path
        
        if not full_path.exists():
            return {
                "status": "error",
                "message": f"Resource '{resource_path}' not found in skill '{skill_name}'"
            }
        
        # Read the resource
        content = full_path.read_text()
        
        return {
            "status": "success",
            "skill_name": skill_name,
            "resource_path": resource_path,
            "content": content,
            "size_bytes": len(content)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load resource: {str(e)}"
        }


def _run_script_subprocess(script_path: str, params_json: str, cwd: str, timeout: int) -> dict:
    """
    Run the script subprocess synchronously.
    This function is designed to be called via asyncio.to_thread() to avoid blocking the event loop.
    
    Args:
        script_path: Path to the script file
        params_json: JSON string of parameters
        cwd: Working directory for the subprocess
        timeout: Timeout in seconds
    
    Returns:
        dict: Result containing stdout, stderr, and return_code
    """
    result = subprocess.run(
        [sys.executable, script_path, params_json],
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
async def execute_skill_script(
    skill_name: str, 
    script_name: str, 
    params: dict = None
) -> dict:
    """
    Execute a pre-built script from a skill's scripts/ directory.
    
    THIRD STEP: Call this after loading a skill with `get_skill` to run
    one of its scripts. The skill's instructions will tell you which
    scripts are available and what parameters they accept.
    
    Scripts must have a `run(params: dict) -> dict` function as their entry point.
    
    Args:
        skill_name: The skill name (e.g., "data-analysis")
        script_name: Name of script file in scripts/ directory (e.g., "analyze.py")
        params: Optional dictionary of parameters to pass to the script's run() function
    
    Returns:
        dict: Execution result including output and any errors
    
    Example:
        execute_skill_script("data-analysis", "analyze.py", {"file_path": "/data/sales.csv"})
    """
    try:
        # Validate skill name
        is_valid, error = validate_skill_name(skill_name)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Invalid skill name: {error}"
            }
        
        skill_path = get_skill_path(skill_name)
        
        if not skill_path.exists():
            return {
                "status": "error",
                "message": f"Skill '{skill_name}' not found. Use list_skills() first."
            }
        
        # Validate script name (prevent directory traversal)
        if "/" in script_name or "\\" in script_name or ".." in script_name:
            return {
                "status": "error",
                "message": "Invalid script name"
            }
        
        script_path = skill_path / "scripts" / script_name
        
        if not script_path.exists():
            # List available scripts to help the user
            scripts_dir = skill_path / "scripts"
            available = []
            if scripts_dir.exists():
                available = [f.name for f in scripts_dir.iterdir() if f.is_file() and f.suffix == ".py"]
            
            return {
                "status": "error",
                "message": f"Script '{script_name}' not found in skill '{skill_name}'",
                "available_scripts": available
            }
        
        # Prepare parameters
        params_json = json.dumps(params or {})
        
        # Execute the script in a separate thread to avoid blocking
        try:
            result = await asyncio.to_thread(
                _run_script_subprocess,
                str(script_path),
                params_json,
                str(skill_path),
                300  # 5 minute timeout
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": f"Script '{script_name}' timed out after 5 minutes"
            }
        
        # Parse the output
        output = result["stdout"]
        error = result["stderr"]
        
        if result["return_code"] != 0:
            return {
                "status": "error",
                "message": "Script execution failed",
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
            "message": f"Script '{script_name}' executed successfully",
            "skill_name": skill_name,
            "script_name": script_name,
            "result": output_data,
            "stderr": error if error else None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to execute script: {str(e)}"
        }


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
