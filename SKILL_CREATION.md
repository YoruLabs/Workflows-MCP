# Skill Creation Guide

This guide provides instructions for creating effective skills for Skills-MCP. Use this guide when creating a new skill or updating an existing skill that extends agent capabilities with specialized knowledge, workflows, or tool integrations.

## About Skills

Skills are modular, self-contained packages that extend agent capabilities by providing specialized knowledge, workflows, and tools. Think of them as "onboarding guides" for specific domains or tasks—they transform a general-purpose agent into a specialized agent equipped with procedural knowledge.

### What Skills Provide

- **Specialized workflows** - Multi-step procedures for specific domains
- **Tool integrations** - Instructions for working with specific file formats or APIs
- **Domain expertise** - Company-specific knowledge, schemas, business logic
- **Bundled resources** - Scripts, references, and assets for complex and repetitive tasks

## Core Principles

### Concise is Key

The context window is a shared resource. Skills share the context window with everything else the agent needs: system prompt, conversation history, other skills' metadata, and the actual user request.

**Default assumption**: The agent is already very smart. Only add context it doesn't already have. Challenge each piece of information: "Does the agent really need this explanation?" and "Does this paragraph justify its token cost?"

Prefer concise examples over verbose explanations.

### Set Appropriate Degrees of Freedom

Match the level of specificity to the task's fragility and variability:

| Freedom Level | When to Use | Example |
|---------------|-------------|---------|
| **High** (text-based instructions) | Multiple approaches valid, decisions depend on context | General coding guidelines |
| **Medium** (pseudocode or parameterized scripts) | Preferred pattern exists, some variation acceptable | API integration patterns |
| **Low** (specific scripts, few parameters) | Operations fragile, consistency critical | PDF rotation, data migrations |

Think of the agent as exploring a path: a narrow bridge with cliffs needs specific guardrails (low freedom), while an open field allows many routes (high freedom).

## Anatomy of a Skill

Every skill consists of a required `SKILL.md` file and optional bundled resources:

```
skill-name/
├── SKILL.md              # Required: Instructions + YAML frontmatter
└── Bundled Resources     # Optional
    ├── scripts/          # Executable Python scripts with run(params) -> dict
    ├── references/       # Documentation loaded into context as needed
    └── assets/           # Files used in output (templates, data files)
```

### SKILL.md (Required)

Every `SKILL.md` consists of:

1. **Frontmatter (YAML)**: Contains `name` and `description` fields. These are the only fields loaded at startup to determine when the skill gets used. Be clear and comprehensive in describing what the skill does and when it should be used.

2. **Body (Markdown)**: Instructions and guidance for using the skill. Only loaded AFTER the skill is activated.

#### Frontmatter Format

```yaml
---
name: skill-name
description: What this skill does and when to use it. Include specific triggers and contexts. This is the primary mechanism for skill activation.
license: MIT
metadata:
  author: YoruLabs
  version: "1.0"
---
```

**Name requirements:**
- 1-64 characters
- Lowercase alphanumeric and hyphens only (`a-z`, `0-9`, `-`)
- Cannot start or end with hyphen
- Cannot contain consecutive hyphens (`--`)
- Must match the parent directory name

**Description requirements:**
- 1-1024 characters
- Describe both what the skill does AND when to use it
- Include specific keywords that help agents identify relevant tasks
- All "when to use" information goes here (not in the body)

**Good description example:**
```yaml
description: Extract text and tables from PDF files, fill PDF forms, and merge multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.
```

**Poor description example:**
```yaml
description: Helps with PDFs.
```

### Bundled Resources (Optional)

#### Scripts (`scripts/`)

Executable Python code for tasks that require deterministic reliability or are repeatedly rewritten.

**When to include:**
- Same code is being rewritten repeatedly
- Deterministic reliability is needed
- Complex operations that benefit from tested, stable code

**Script format requirements:**
```python
import sys
import json

def run(params: dict = None) -> dict:
    """
    Entry point for the script.
    
    Args:
        params: Dictionary of parameters passed from execute_skill_script
    
    Returns:
        dict: Result with at minimum a 'status' field ('success' or 'error')
    """
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

**Benefits:**
- Token efficient (executed without loading into context)
- Deterministic and testable
- Can be called via `execute_skill_script` MCP tool

#### References (`references/`)

Documentation and reference material loaded as needed into context.

**When to include:**
- Documentation the agent should reference while working
- Database schemas, API documentation, domain knowledge
- Company policies, detailed workflow guides

**Best practices:**
- Keep individual files focused and under 10k words
- If files are large, include grep search patterns in SKILL.md
- Information should live in either SKILL.md OR references, not both
- Keep SKILL.md lean; move detailed reference material here

#### Assets (`assets/`)

Files not loaded into context, but used within the output the agent produces.

**When to include:**
- Templates (document templates, configuration templates)
- Images (diagrams, examples)
- Data files (lookup tables, schemas, sample data)

## Progressive Disclosure

Skills use a three-level loading system to manage context efficiently:

| Level | Content | When Loaded | Size Guideline |
|-------|---------|-------------|----------------|
| **1** | Metadata (name + description) | Always in context | ~100 tokens |
| **2** | SKILL.md body | When skill activates | <5000 tokens |
| **3** | Bundled resources | As needed by agent | Unlimited |

### Progressive Disclosure Patterns

Keep SKILL.md body under 500 lines. Split content into separate files when approaching this limit. When splitting content, clearly reference the files from SKILL.md and describe when to read them.

**Key principle**: When a skill supports multiple variations, frameworks, or options, keep only the core workflow and selection guidance in SKILL.md. Move variant-specific details into separate reference files.

#### Pattern 1: High-level guide with references

```markdown
# PDF Processing

## Quick Start
Extract text with pdfplumber:
[code example]

## Advanced Features
- **Form filling**: See [references/forms.md](references/forms.md)
- **API reference**: See [references/api.md](references/api.md)
```

#### Pattern 2: Domain-specific organization

```
bigquery-skill/
├── SKILL.md (overview and navigation)
└── references/
    ├── finance.md (revenue, billing metrics)
    ├── sales.md (opportunities, pipeline)
    └── product.md (API usage, features)
```

When a user asks about sales metrics, the agent only reads `sales.md`.

#### Pattern 3: Conditional details

```markdown
# DOCX Processing

## Creating Documents
Use docx-js for new documents. See [references/docx-js.md](references/docx-js.md).

## Editing Documents
For simple edits, modify the XML directly.

**For tracked changes**: See [references/redlining.md](references/redlining.md)
```

### Important Guidelines

- **Avoid deeply nested references** - Keep references one level deep from SKILL.md
- **Structure longer reference files** - Include a table of contents at the top for files over 100 lines
- **No duplicate information** - Content lives in SKILL.md OR references, not both

## What NOT to Include

A skill should only contain essential files that directly support its functionality. Do NOT create:

- `README.md` (SKILL.md serves this purpose)
- `INSTALLATION_GUIDE.md`
- `QUICK_REFERENCE.md`
- `CHANGELOG.md`
- Setup and testing procedures
- User-facing documentation

The skill should only contain information needed for an AI agent to do the job. Additional documentation adds clutter and confusion.

## Skill Creation Process

### Step 1: Understand the Skill with Concrete Examples

To create an effective skill, clearly understand concrete examples of how the skill will be used.

**Questions to consider:**
- What functionality should the skill support?
- What are example use cases?
- What would a user say that should trigger this skill?

**Conclude this step** when there is a clear sense of the functionality the skill should support.

### Step 2: Plan the Reusable Skill Contents

Analyze each example by:
1. Considering how to execute on the example from scratch
2. Identifying what scripts, references, and assets would be helpful

**Example analyses:**

| Skill | Example Query | Analysis | Resource |
|-------|---------------|----------|----------|
| pdf-editor | "Rotate this PDF" | Same code rewritten each time | `scripts/rotate.py` |
| webapp-builder | "Build me a todo app" | Same boilerplate each time | `assets/template/` |
| bigquery | "How many users logged in?" | Re-discovering schemas each time | `references/schema.md` |

### Step 3: Create the Skill Directory

Create the skill directory structure:

```bash
mkdir -p skills/my-skill/scripts
mkdir -p skills/my-skill/references
mkdir -p skills/my-skill/assets
```

Create the `SKILL.md` file with proper frontmatter:

```yaml
---
name: my-skill
description: [Clear description of what the skill does and when to use it]
license: MIT
metadata:
  author: [Your name/org]
  version: "1.0"
---

# My Skill

## Overview
[Brief description]

## Available Scripts
- `scripts/main.py` - [Description]

## How to Use
[Step-by-step instructions]

## Examples
[Example usage with parameters and expected output]
```

### Step 4: Implement the Skill

1. **Start with reusable resources** - Implement scripts, references, and assets identified in Step 2

2. **Test scripts** - Run scripts to ensure no bugs and output matches expectations:
   ```bash
   python skills/my-skill/scripts/main.py '{"param": "value"}'
   ```

3. **Update SKILL.md** - Write clear instructions referencing the bundled resources

4. **Delete unused directories** - Remove empty `scripts/`, `references/`, or `assets/` directories

### Step 5: Validate the Skill

Before submitting, verify:

- [ ] `SKILL.md` has valid YAML frontmatter with `name` and `description`
- [ ] Skill name matches directory name
- [ ] Skill name follows naming conventions (lowercase, hyphens)
- [ ] Description is comprehensive (what it does + when to use it)
- [ ] All scripts have `run(params) -> dict` function
- [ ] All scripts output valid JSON
- [ ] SKILL.md is under 500 lines
- [ ] No duplicate information between SKILL.md and references
- [ ] No unnecessary documentation files

### Step 6: Submit via Pull Request

1. Create a branch for your skill:
   ```bash
   git checkout -b feat/add-my-skill
   ```

2. Add your skill files:
   ```bash
   git add skills/my-skill/
   git commit -m "feat: Add my-skill for [purpose]"
   ```

3. Push and create PR:
   ```bash
   git push -u origin feat/add-my-skill
   gh pr create --title "feat: Add my-skill" --body "..."
   ```

### Step 7: Iterate

After testing the skill in real usage:

1. Use the skill on real tasks
2. Notice struggles or inefficiencies
3. Identify how SKILL.md or bundled resources should be updated
4. Implement changes and test again

## Example: Complete Skill

```
hello-world/
├── SKILL.md
└── scripts/
    └── greet.py
```

**SKILL.md:**
```yaml
---
name: hello-world
description: A simple example skill that demonstrates the Agent Skills format. Use this as a template when creating new skills or to test that Skills MCP is working correctly.
license: MIT
metadata:
  author: YoruLabs
  version: "1.0"
---

# Hello World Skill

A minimal example skill demonstrating the basic structure.

## Available Scripts

- `greet.py` - Generate a personalized greeting message

## How to Use

Run the greeting script with a name parameter:

```
execute_skill_script("hello-world", "greet.py", {"name": "Alice"})
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | No | "World" | Name to include in greeting |
| `uppercase` | boolean | No | false | Whether to uppercase the greeting |
```

**scripts/greet.py:**
```python
import sys
import json
from datetime import datetime

def run(params: dict = None) -> dict:
    params = params or {}
    name = params.get("name", "World")
    uppercase = params.get("uppercase", False)
    
    greeting = f"Hello, {name}!"
    if uppercase:
        greeting = greeting.upper()
    
    return {
        "status": "success",
        "greeting": greeting,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    params = {}
    if len(sys.argv) > 1:
        params = json.loads(sys.argv[1])
    result = run(params)
    print(json.dumps(result))
```

## Related Resources

- [Agent Skills Specification](https://agentskills.io/specification)
- [Skills-MCP Repository](https://github.com/YoruLabs/Skills-MCP)
