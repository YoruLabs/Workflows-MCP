---
name: apollo-clay-leads
description: Lead generation pipeline that fetches leads from Apollo.io, enriches via Clay webhooks, and scores with explainable reasoning. Use when generating B2B leads, running outbound campaigns, or building prospect lists.
license: MIT
compatibility: Requires APOLLO_API_KEY env var. Optional CLAY_API_KEY and CLAY_WEBHOOK_URL for enrichment.
metadata:
  author: Livus
  version: "2.0"
---

# Apollo-Clay Lead Generation Pipeline

End-to-end lead generation: natural language query → fetch → enrich → score → export.

## Quick Start

**Primary method - natural language query:**
```bash
python3 skills/apollo-clay-leads/scripts/run_pipeline.py \
  --query "administrators from large marketing companies in US" \
  --limit 30
```

**Dry-run mode (no API calls, uses mock data):**
```bash
python3 skills/apollo-clay-leads/scripts/run_pipeline.py \
  --query "CTOs at SaaS startups" \
  --dry-run
```

**With Linear issue tracking:**
```bash
python3 skills/apollo-clay-leads/scripts/run_pipeline.py \
  --query "VPs of Engineering" \
  --limit 50 \
  --linear-issue LIV-56
```

## CLI Reference

```
python3 run_pipeline.py [OPTIONS]

Input Sources (choose one):
  --query, -q TEXT    Natural language query (primary method)
  --csv PATH          Path to Apollo CSV export (fallback)
  --icp NAME          ICP config name (default: icp_v1)

Options:
  --limit, -n INT     Max leads to fetch (default: 100)
  --dry-run           Use mock data, no external API calls
  --linear-issue ID   Linear issue ID for markdown summary
  --skip-enrichment   Skip Clay enrichment step
  --skip-export       Skip export step
  --json              Output result as JSON
```

## Prerequisites

Set these environment variables in `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `APOLLO_API_KEY` | Yes | Apollo.io API key |
| `CLAY_API_KEY` | No | Clay API key (for future use) |
| `CLAY_WEBHOOK_URL` | No | Clay table webhook URL for enrichment |

## Output Artifacts

After running, check the `output/` directory:

| File | Description |
|------|-------------|
| `leads.csv` | Scored leads with all fields |
| `leads.json` | Structured lead data with scores |
| `linear_update.md` | Summary for Linear issue updates |

## Natural Language Query Examples

The pipeline parses natural language queries into Apollo API filters:

| Query | Parsed Filters |
|-------|----------------|
| "administrators from large marketing companies" | titles: Administrator*, size: 500+, industry: Marketing |
| "CTOs at SaaS startups" | titles: CTO, industry: SaaS, size: 1-50 |
| "VPs of Engineering in US" | titles: VP*, location: US |
| "directors at enterprise software companies" | titles: Director, size: 500+, industry: Software |

## Pipeline Flow

```
1. Parse query → Extract filters (titles, size, industry, location)
2. Ingest leads:
   - From Apollo API (default)
   - From CSV export (--csv flag)
   - From mock data (--dry-run)
3. Enrich via Clay webhook (if CLAY_WEBHOOK_URL set)
4. Score all leads (fit_score 0-100 + reasons)
5. Export artifacts:
   - output/leads.csv
   - output/leads.json
   - output/linear_update.md
```

## Scoring

Each lead gets a `fit_score` (0-100) with transparent `score_breakdown`:

| Criterion | Points |
|-----------|--------|
| Title match | +25 |
| Seniority match | +20 |
| Industry match | +20 |
| Company size match | +15 |
| Location match | +10 |
| Verified email | +5 |
| Has LinkedIn | +5 |

## ICP Configuration

Create custom ICPs in `scripts/icp_configs/<name>.json`:

```json
{
  "name": "my_icp",
  "description": "Target audience description",
  "filters": {
    "person_titles": ["CTO", "VP Engineering"],
    "person_seniorities": ["c_suite", "vp", "director"],
    "organization_locations": ["United States"],
    "organization_num_employees_ranges": ["51,200", "201,500"]
  },
  "scoring_weights": {
    "title_match": 25,
    "seniority_match": 20,
    "industry_match": 20,
    "company_size_match": 15,
    "location_match": 10,
    "verified_email": 5,
    "has_linkedin": 5
  }
}
```

## MCP Usage

```python
# Natural language query
execute_skill_script("apollo-clay-leads", "run_pipeline.py", {
    "query": "administrators from large marketing companies",
    "limit": 30,
    "dry_run": true
})

# Using ICP config
execute_skill_script("apollo-clay-leads", "run_pipeline.py", {
    "icp": "icp_v1",
    "limit": 100
})
```
