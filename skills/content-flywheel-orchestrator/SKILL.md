---
name: content-flywheel-orchestrator
description: Orchestrate the full content flywheel workflow from research to multi-platform publishing. Use when running the daily content creation process, executing the full flywheel, or when user wants to create Twitter thread + LinkedIn post + newsletter from a single topic.
license: MIT
metadata:
  author: YoruLabs
  version: "1.0"
---

# Content Flywheel Orchestrator

Execute the complete content flywheel workflow: research a topic and generate content for Twitter, LinkedIn, and newsletter in one session.

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────┐
│  1. RESEARCH (content-research)                             │
│     └──> Output: Research Brief                             │
│              │                                              │
│              ▼                                              │
│  2. TWITTER (twitter-thread-generator)                      │
│     └──> Output: 8-Tweet Thread                             │
│              │                                              │
│              ├────────────────────┐                         │
│              ▼                    ▼                         │
│  3. LINKEDIN                 4. NEWSLETTER                  │
│  (linkedin-post-adapter)     (newsletter-expander)          │
│     └──> LinkedIn Post          └──> Newsletter Issue       │
│              │                    │                         │
│              ▼                    ▼                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              READY TO PUBLISH                       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Required Inputs

| Input | Description | Example |
|-------|-------------|---------|
| **Topic** | Subject to research and create content about | "Latest developments in AI agents" |
| **Niche** | Industry/audience context | "AI/Tech for developers and founders" |
| **Newsletter Link** | URL for CTAs | "https://newsletter.example.com" |
| **Subscriber Count** | For social proof (optional) | "10,000+" |
| **Author Name** | For newsletter sign-off | "Alex" |

## Execution Steps

### Step 1: Research Phase
Load and execute `content-research` skill:
- Research the topic using web search
- Identify 3-5 key developments
- Find surprising statistics
- Extract core narrative
- Define actionable takeaway
- **Output:** Research Brief

### Step 2: Twitter Thread Phase
Load and execute `twitter-thread-generator` skill:
- Use Research Brief as input
- Select appropriate hook formula
- Structure 8-tweet thread
- Include newsletter CTA
- **Output:** Twitter Thread

### Step 3: LinkedIn Adaptation Phase
Load and execute `linkedin-post-adapter` skill:
- Use Twitter Thread as input
- Adapt tone for professional audience
- Format with bullets and question
- Prepare first comment with CTA
- **Output:** LinkedIn Post + First Comment

### Step 4: Newsletter Expansion Phase
Load and execute `newsletter-expander` skill:
- Use Research Brief as input
- Expand each development
- Analyze data points
- Create actionable guide
- **Output:** Newsletter Issue

## Final Deliverables

At completion, provide all four outputs:

```markdown
## Content Flywheel Output - [Date]

### Topic: [Topic]

---

## 1. Research Brief
[Full research brief]

---

## 2. Twitter Thread
[All 8 tweets formatted for posting]

---

## 3. LinkedIn Post

**Main Post:**
[Full LinkedIn post]

**First Comment:**
[Newsletter CTA]

---

## 4. Newsletter Issue
[Full newsletter with subject line]

---

## Publishing Checklist
- [ ] Post Twitter thread
- [ ] Post LinkedIn article
- [ ] Add first comment with newsletter link
- [ ] Send newsletter to subscribers
```

## Key Principles

1. **Research Once, Publish Everywhere** - Single research session fuels all content
2. **Platform-Specific Optimization** - Each output is tailored to its platform
3. **Consistent CTA** - All social content drives to newsletter
4. **Human Review** - Always review before publishing

## Daily Execution

For daily content creation:
1. Identify trending topic in your niche
2. Run full flywheel workflow
3. Review and edit all outputs
4. Publish in sequence: Twitter → LinkedIn → Newsletter

## Time Estimate

| Phase | Duration |
|-------|----------|
| Research | 15-30 min |
| Twitter Thread | 5-10 min |
| LinkedIn Adaptation | 5 min |
| Newsletter Expansion | 10-15 min |
| **Total** | **35-60 min** |
