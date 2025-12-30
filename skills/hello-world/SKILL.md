---
name: hello-world
description: A simple example skill that demonstrates the Agent Skills format. Use this as a template when creating new skills or to test that Skills MCP is working correctly.
license: MIT
metadata:
  author: YoruLabs
  version: "1.0"
---

# Hello World Skill

A minimal example skill that demonstrates the basic structure of an Agent Skill.

## Available Scripts

- `greet.py` - Generate a personalized greeting message

## How to Use

### Basic Usage

Run the greeting script with a name parameter:

```
execute_skill_script("hello-world", "greet.py", {"name": "Alice"})
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | No | "World" | Name to include in greeting |
| `uppercase` | boolean | No | false | Whether to uppercase the greeting |

### Example Responses

**Basic greeting:**
```json
{
  "status": "success",
  "greeting": "Hello, Alice!",
  "timestamp": "2024-12-30T12:00:00"
}
```

**Uppercase greeting:**
```json
{
  "status": "success", 
  "greeting": "HELLO, ALICE!",
  "timestamp": "2024-12-30T12:00:00"
}
```

## Creating Your Own Skills

Use this skill as a template:

1. Create a directory under `skills/` with your skill name (lowercase, hyphens)
2. Add a `SKILL.md` file with YAML frontmatter (name, description required)
3. Add scripts to `scripts/` directory
4. Each script should have a `run(params: dict) -> dict` function
