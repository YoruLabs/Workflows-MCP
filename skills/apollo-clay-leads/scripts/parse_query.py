"""
LLM-Powered Query Parser

Uses OpenAI to parse natural language queries into Apollo API filters.
Provides intelligent understanding of job titles, industries, locations, etc.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# System prompt for query parsing
SYSTEM_PROMPT = """You are a query parser that converts natural language lead search queries into Apollo.io API filters.

Given a natural language query, extract and return a JSON object with these Apollo API filter fields:

- person_titles: list of job titles to search (be comprehensive, include variations)
- person_seniorities: list from [owner, founder, c_suite, partner, vp, head, director, manager, senior, entry]
- organization_locations: list of countries (use English names)
- organization_num_employees_ranges: list of ranges like "1,10", "11,50", "51,200", "201,500", "501,1000", "1001,5000", "5001,10000"
- q_organization_keyword_tags: list of industry keywords

Size mappings:
- "startup" or "small" → ["1,10", "11,50"]
- "mid-size" or "medium" → ["51,200", "201,500"]
- "large" or "enterprise" → ["501,1000", "1001,5000", "5001,10000"]

Be comprehensive with job titles - include common variations and synonyms.
For locations, use the full country name in English.
For industries, include related keywords and local terms if applicable.

Return ONLY valid JSON, no explanation."""

USER_PROMPT_TEMPLATE = """Parse this lead search query into Apollo API filters:

Query: "{query}"

Return JSON with the extracted filters."""


def parse_query_with_llm(query: str) -> Dict[str, Any]:
    """
    Parse a natural language query into Apollo API filters using OpenAI.
    
    Args:
        query: Natural language search query
    
    Returns:
        dict with Apollo API filter fields
    """
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set, falling back to basic parsing")
        return _fallback_parse(query)
    
    try:
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError, URLError
        
        url = "https://api.openai.com/v1/chat/completions"
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(query=query)}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        
        with urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            filters = json.loads(content)
            
            logger.info(f"LLM parsed query into filters: {list(filters.keys())}")
            return filters
            
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        logger.error(f"OpenAI API error: {e.code} - {error_body[:200]}")
        return _fallback_parse(query)
    except URLError as e:
        logger.error(f"Network error calling OpenAI: {e.reason}")
        return _fallback_parse(query)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return _fallback_parse(query)
    except Exception as e:
        logger.error(f"Unexpected error in LLM parsing: {e}")
        return _fallback_parse(query)


def _fallback_parse(query: str) -> Dict[str, Any]:
    """
    Basic fallback parsing when LLM is unavailable.
    Returns minimal filters based on simple keyword matching.
    """
    import re
    query_lower = query.lower()
    filters = {}
    
    # Very basic title extraction
    if "administrator" in query_lower:
        filters["person_titles"] = ["Administrator", "System Administrator", "IT Administrator"]
    elif "cto" in query_lower or "chief technology" in query_lower:
        filters["person_titles"] = ["CTO", "Chief Technology Officer"]
    elif "vp" in query_lower or "vice president" in query_lower:
        filters["person_titles"] = ["VP", "Vice President"]
    elif "director" in query_lower:
        filters["person_titles"] = ["Director"]
    elif "manager" in query_lower:
        filters["person_titles"] = ["Manager"]
    
    # Basic size detection
    if "large" in query_lower or "enterprise" in query_lower:
        filters["organization_num_employees_ranges"] = ["501,1000", "1001,5000", "5001,10000"]
    elif "startup" in query_lower or "small" in query_lower:
        filters["organization_num_employees_ranges"] = ["1,10", "11,50"]
    elif "mid" in query_lower or "medium" in query_lower:
        filters["organization_num_employees_ranges"] = ["51,200", "201,500"]
    
    return filters


def run(params: dict = None) -> dict:
    """Entry point for MCP execution."""
    params = params or {}
    
    query = params.get("query")
    if not query:
        return {"status": "error", "message": "query parameter required"}
    
    filters = parse_query_with_llm(query)
    
    return {
        "status": "success",
        "query": query,
        "filters": filters,
        "used_llm": bool(OPENAI_API_KEY)
    }


if __name__ == "__main__":
    import sys
    
    params = {}
    if len(sys.argv) > 1:
        try:
            params = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            # Treat as raw query string
            params = {"query": sys.argv[1]}
    
    result = run(params)
    print(json.dumps(result, indent=2, default=str))
