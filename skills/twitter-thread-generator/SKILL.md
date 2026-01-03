---
name: twitter-thread-generator
description: Transform a research brief into a viral-style Twitter thread optimized for engagement. Use when creating Twitter/X content, generating threads from research, or when user wants to post about a topic on Twitter with a newsletter CTA.
license: MIT
metadata:
  author: YoruLabs
  version: "1.0"
---

# Twitter Thread Generator Skill

Convert a research brief into a compelling, high-engagement Twitter thread that drives newsletter subscriptions.

## Required Inputs

- **Research Brief** - Output from `content-research` skill
- **Newsletter Link** - URL for the call-to-action
- **Subscriber Count** (optional) - For social proof in CTA

## Thread Structure (8 Tweets)

| Tweet | Purpose | Content |
|-------|---------|---------|
| 1/8 | **Hook** | Bold claim, surprising stat, or provocative question |
| 2-5/8 | **Narrative** | Unpack the story using key developments |
| 6/8 | **Proof** | Surprising data point for credibility |
| 7/8 | **Takeaway** | Actionable insight |
| 8/8 | **CTA** | Newsletter subscription prompt |

## Hook Formulas

Choose the most appropriate hook style:

| Type | Formula | Example |
|------|---------|---------|
| Bold Claim | [Statement] + Here's why: | "AI won't take your job. But someone using AI will. Here's why:" |
| Surprising Stat | [Number] + [Context] | "OpenAI just hit $10B in revenue. That's 10x growth in 12 months." |
| Listicle Tease | [Number] [things] that [benefit] | "7 AI tools that will save you 10+ hours this week:" |
| Question | [Provocative question]? | "Why are the best developers using AI to write 50% of their code?" |
| Story Hook | [Timeframe], I [did X]. Here's what happened: | "In 3 years, I bootstrapped my newsletter to 2M+ subs. Here's how:" |
| Contrarian | Everyone says [belief]. They're wrong. | "Everyone says you need a huge budget for marketing. They're wrong." |
| Just Happened | [Entity] just [action]. Here's what it means: | "Google just released Gemini 3. Here's what it means for you:" |

## Output Format

```
1/8: [Hook - attention-grabbing opening]

2/8: [Context - set up the story]

3/8: [Development 1 - key insight]

4/8: [Development 2 - key insight]

5/8: [Development 3 - key insight]

6/8: [Data point - surprising statistic with source]

7/8: [Takeaway - actionable advice]

8/8: I dive deeper into [Topic] in my free newsletter.

Join [X]+ readers staying ahead of the curve:

[Newsletter Link]
```

## Writing Guidelines

- **Keep tweets under 280 characters** (ideally 200-250)
- **One idea per tweet** - self-contained but flowing
- **Use line breaks** for readability
- **Avoid jargon** - write for a general audience
- **End with clear CTA** - be direct about the newsletter

## Quality Checklist

- [ ] Hook creates curiosity or challenges assumptions
- [ ] Each tweet can stand alone but flows logically
- [ ] Data point is specific and sourced
- [ ] Takeaway is practical and actionable
- [ ] CTA is clear and includes link

## Next Steps

After generating the thread:
- Post to Twitter/X
- Use `linkedin-post-adapter` to repurpose for LinkedIn
