---
name: newsletter-expander
description: Expand a research brief into a comprehensive newsletter issue. Use when creating newsletter content, fulfilling the promise from social media CTAs, or when user needs to write a detailed newsletter about a topic.
license: MIT
metadata:
  author: YoruLabs
  version: "1.0"
---

# Newsletter Expander Skill

Transform a research brief into a detailed, engaging newsletter issue that delivers on the value promised in social media CTAs.

## Required Inputs

- **Research Brief** - Output from `content-research` skill
- **Author Name** - For sign-off
- **Newsletter Name** (optional) - For branding

## Newsletter Structure

| Section | Purpose | Length |
|---------|---------|--------|
| Subject Line | Drive opens | 5-10 words |
| Personal Intro | Connect with reader | 2-3 sentences |
| The Big Story | Set context | 1 paragraph |
| Key Developments | Deep analysis | 1 paragraph each |
| By the Numbers | Data analysis | 1 paragraph |
| What This Means | Actionable guide | 2-3 paragraphs |
| Final Thoughts | Wrap up | 2-3 sentences |

## Output Format

```markdown
**Subject:** [Intriguing subject line that creates curiosity]

Hi [First Name],

[Personal intro - why this topic matters right now, connect to reader's world]

---

## The Big Story: [Core Narrative]

[Deeper context setting the stage - what's happening and why it matters]

---

## 1. [Key Development 1]

[Expanded explanation with context, implications, and links to sources. What does this mean for the reader? Why should they care?]

## 2. [Key Development 2]

[Expanded explanation with context, implications, and links to sources.]

## 3. [Key Development 3]

[Expanded explanation with context, implications, and links to sources.]

---

## By the Numbers

> [Surprising statistic]

[Analysis of what this data reveals. Why is it significant? What trend does it indicate? How does it compare to previous benchmarks?]

---

## What This Means For You

[Turn the actionable takeaway into a mini-guide]

**Here's how to apply this:**

1. [Step 1 - specific action]
2. [Step 2 - specific action]
3. [Step 3 - specific action]

[Additional context or alternative approaches]

---

## Final Thoughts

[Concluding summary - reinforce the key message and offer a forward-looking perspective]

Cheers,

[Author Name]
```

## Subject Line Formulas

| Type | Formula | Example |
|------|---------|---------|
| Curiosity Gap | [Intriguing statement]... | "The AI tool everyone's using wrong..." |
| Benefit-Driven | How to [achieve X] in [timeframe] | "How to save 10 hours this week with AI" |
| News Hook | [Company] just [action] | "OpenAI just changed everything" |
| List | [Number] [things] you need to know | "5 AI trends you can't ignore" |
| Question | Why [surprising thing]? | "Why are top developers writing less code?" |

## Writing Guidelines

- **Conversational tone** - write like you're emailing a smart friend
- **Add value beyond social posts** - this is the payoff for subscribing
- **Link to sources** - build credibility
- **Use formatting** - headers, bold, blockquotes for scanability
- **Keep it focused** - one main topic per issue

## Quality Checklist

- [ ] Subject line creates curiosity or promises value
- [ ] Intro connects topic to reader's interests
- [ ] Each development has context and implications
- [ ] Data is analyzed, not just stated
- [ ] Actionable section has specific steps
- [ ] Tone is personal and engaging
- [ ] Total length: 800-1200 words

## Integration Notes

This skill completes the content flywheel:
1. `content-research` → Research Brief
2. `twitter-thread-generator` → Twitter Thread
3. `linkedin-post-adapter` → LinkedIn Post
4. `newsletter-expander` → Newsletter Issue (this skill)

All four pieces come from the same research, maximizing efficiency.
