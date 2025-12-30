# Skills MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Model Context Protocol (MCP) server that enables AI agents to discover, load, and execute **Agent Skills** - organized folders of instructions, scripts, and resources that give agents additional capabilities.

Based on the [Agent Skills specification](https://agentskills.io/specification).

## What are Skills?

Skills are folders containing:
- **SKILL.md** - Instructions and metadata (name, description)
- **scripts/** - Executable Python scripts
- **references/** - Additional documentation (loaded on demand)
- **assets/** - Static resources (templates, data files)

Skills use **progressive disclosure** to efficiently manage context:
1. **Level 1**: Name + description loaded at startup for all skills
2. **Level 2**: Full SKILL.md loaded when skill is activated
3. **Level 3**: Scripts/references loaded only when needed

## Features

- **Skill Discovery**: List all available skills with metadata
- **Progressive Loading**: Load skill instructions on demand
- **Script Execution**: Run pre-built Python scripts from skills
- **Agent Skills Compatible**: Follows the open Agent Skills specification

## Getting Started

### Prerequisites

- Python 3.10+
- An MCP-compatible client (e.g., Manus, Claude Code, Cursor)

### Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/YoruLabs/Skills-MCP.git
    cd Skills-MCP
    ```

2. **Install dependencies:**

    ```bash
    pip install -e .
    ```

3. **Run the server:**

    ```bash
    skills-mcp
    ```

### Configuration

- **Skills Directory**: By default, skills are stored in the `skills/` directory. You can change this by setting the `SKILLS_DIR` environment variable.

## MCP Tools

The server exposes the following tools:

| Tool | Description |
| :--- | :--- |
| `list_skills` | **Start here.** Lists all available skills with name and description. |
| `get_skill` | Loads a skill's full SKILL.md content and lists available resources. |
| `get_skill_resource` | Loads a specific resource file (reference docs, assets). |
| `execute_skill_script` | Executes a Python script from a skill's `scripts/` directory. |

### Typical Workflow

```
1. list_skills()                    → Discover available skills
2. get_skill("skill-name")          → Load instructions and see available scripts
3. execute_skill_script(...)        → Run a script with parameters
```

## Creating a Skill

### Directory Structure

```
skills/
└── my-skill/
    ├── SKILL.md              # Required: Instructions + metadata
    ├── scripts/              # Optional: Executable scripts
    │   └── main.py
    ├── references/           # Optional: Additional docs
    │   └── api.md
    └── assets/               # Optional: Static resources
        └── template.json
```

### SKILL.md Format

```yaml
---
name: my-skill
description: What this skill does and when to use it. Include keywords that help agents identify relevant tasks.
license: MIT
metadata:
  author: your-name
  version: "1.0"
---

# My Skill

## Overview
Brief description of what this skill helps accomplish.

## Available Scripts
- `scripts/main.py` - Primary functionality

## How to Use
Step-by-step instructions...

## Examples
Show example usage with parameters and expected output.
```

### Script Format

Scripts must have a `run(params: dict) -> dict` function:

```python
import sys
import json

def run(params: dict = None) -> dict:
    params = params or {}
    # Your logic here
    return {"status": "success", "result": "..."}

if __name__ == "__main__":
    params = {}
    if len(sys.argv) > 1:
        params = json.loads(sys.argv[1])
    result = run(params)
    print(json.dumps(result))
```

## Example Skills

This repository includes example skills in the `skills/` directory:

1. **hello-world** - A simple example demonstrating the skill format
2. **slack-message** - Post messages to Slack via webhook

## Roadmap

- [ ] `create_skill` tool - Create new skills programmatically
- [ ] `execute_code` tool - Execute arbitrary Python code with e2b sandboxing
- [ ] Skill validation and linting
- [ ] Skill versioning and updates

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Related

- [Agent Skills Specification](https://agentskills.io/specification)
- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [Model Context Protocol](https://modelcontextprotocol.io)
