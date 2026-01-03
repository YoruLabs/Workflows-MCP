---
name: linkedin-post-adapter
description: Adapt a Twitter thread into a professional LinkedIn post that encourages discussion. Use when repurposing Twitter content for LinkedIn, creating B2B content, or when user wants to cross-post to LinkedIn with a more professional tone.
license: MIT
metadata:
  author: YoruLabs
  version: "1.0"
---

# LinkedIn Post Adapter Skill

Transform a Twitter thread into a polished, professional LinkedIn post optimized for B2B engagement and discussion.

## Required Inputs

- **Twitter Thread** - Output from `twitter-thread-generator` skill
- **Newsletter Link** - URL for the first comment CTA
- **Relevant Hashtags** (optional) - 3-5 industry hashtags

## Key Adaptations

| Element | Twitter | LinkedIn |
|---------|---------|----------|
| Tone | Casual, punchy | Professional, insightful |
| Length | Short tweets | 2-3 paragraphs |
| Hook | Bold/provocative | Benefit-oriented |
| CTA | In final tweet | In first comment |
| Engagement | Retweets | Comments/discussion |

## Post Structure

### Main Post

```markdown
[Professional Hook - benefit-oriented opening]

[Paragraph 1: Core narrative and context - expand on the story]

Here are the key takeaways:

• [Takeaway 1 - from thread insights]
• [Takeaway 2 - from thread insights]  
• [Takeaway 3 - from thread insights]

[Paragraph 2: Why this matters - strategic implications]

This trend is reshaping how [industry] operates. Those who adapt early will have a significant advantage.

What's your take on this? How is your team approaching [topic]?

#hashtag1 #hashtag2 #hashtag3
```

### First Comment (Post Immediately After)

```markdown
For a deeper analysis and weekly insights on [topic], check out my free newsletter.

We break down the most important developments every week.

Link: [Newsletter URL]
```

## Writing Guidelines

- **Professional but not stiff** - conversational expertise
- **Use bullet points** for scanability
- **End with a question** to drive comments
- **3-5 relevant hashtags** - not more
- **CTA in first comment** - maximizes reach (LinkedIn algorithm)

## Hook Adaptations

| Twitter Hook | LinkedIn Adaptation |
|--------------|---------------------|
| "AI won't take your job..." | "The professionals thriving in 2025 share one thing in common..." |
| "7 AI tools that..." | "After testing 50+ AI tools, these 7 are actually worth your time:" |
| "Everyone says X. They're wrong." | "The conventional wisdom about X is costing companies millions:" |

## Output Format

Provide two sections:

**MAIN POST:**
[Full LinkedIn post text]

**FIRST COMMENT:**
[Newsletter CTA to post immediately after]

## Quality Checklist

- [ ] Tone is professional but engaging
- [ ] Hook focuses on benefit/value
- [ ] Key points are formatted as bullets
- [ ] Ends with discussion question
- [ ] Hashtags are relevant (3-5 max)
- [ ] CTA is in separate first comment

## Next Steps

After creating the LinkedIn post:
- Post to LinkedIn
- Immediately add the first comment with newsletter link
- Use `newsletter-expander` to create the full newsletter issue
