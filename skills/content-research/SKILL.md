---
name: content-research
description: Research and synthesize information on a topic into a structured brief for content creation. Use when starting the content flywheel, researching trending topics, gathering data for threads/posts, or when user needs to create content about a specific subject.
license: MIT
metadata:
  author: YoruLabs
  version: "1.0"
---

# Content Research Skill

Gather and synthesize raw information on a single topic into a structured brief that serves as the foundation for multi-platform content creation.

## Workflow

1. **Receive topic** from user or identify trending topic in niche
2. **Research** using web search, news, and authoritative sources
3. **Synthesize** findings into the Research Brief format
4. **Output** structured brief for downstream content generation

## Research Goals

When researching a topic, focus on:

1. **3-5 significant recent developments** - What's new and noteworthy?
2. **1-2 surprising statistics** - Data that challenges assumptions or creates shock value
3. **Core narrative** - What's the bigger story or trend?
4. **Key players** - Companies, tools, or people driving the change
5. **Actionable takeaway** - One clear action the audience can take

## Output Format

Always structure the research brief as follows:

```markdown
## Research Brief: [Topic]

**Core Narrative:** [1-2 sentence summary of the main story or trend]

**Key Developments:**
1. [Development 1]: [Brief description with source]
2. [Development 2]: [Brief description with source]
3. [Development 3]: [Brief description with source]

**Surprising Data:**
- [Statistic]: [Context and source link]

**Key Players:**
- [Company/Tool/Person 1]
- [Company/Tool/Person 2]

**Actionable Takeaway:** [Single, clear action someone can take]

**Sources:**
- [Source 1 URL]
- [Source 2 URL]
```

## Quality Checklist

Before completing the research brief, verify:

- [ ] All claims have credible sources
- [ ] Statistics are recent (within last 6 months preferred)
- [ ] Core narrative is clear and compelling
- [ ] Takeaway is specific and actionable
- [ ] Brief is concise (under 500 words)

## Next Steps

After completing the research brief, proceed to:
- `twitter-thread-generator` - Convert brief into Twitter thread
- `linkedin-post-adapter` - Adapt for LinkedIn audience
- `newsletter-expander` - Expand into full newsletter issue
