"""
Fetch Leads from Apify LinkedIn Search

Uses Apify's LinkedIn Profile Search actor to find leads based on natural language query.
This bypasses Apollo's search API restrictions by using LinkedIn as the discovery source.
"""

import sys
import json
import os
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus

# Auto-load .env file
def _load_env():
    """Load environment variables from .env file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for path in [
        os.path.join(script_dir, "..", "..", "..", ".env"),  # Project root
        os.path.join(script_dir, "..", ".env"),  # Skill dir
    ]:
        env_path = os.path.abspath(path)
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        value = value.strip().strip('"').strip("'")
                        if key and value and key not in os.environ:
                            os.environ[key] = value
            break

_load_env()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Apify configuration
APIFY_API_KEY = os.environ.get("APIFY_API_KEY", "")
# Using Google Search Scraper (FREE) for X-Ray LinkedIn search
APIFY_ACTOR_ID = "apify~google-search-scraper"
APIFY_API_BASE = "https://api.apify.com/v2"

# Import db module
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from db import init_db, upsert_lead


def make_request(url: str, data: Optional[Dict] = None, method: str = "GET", retries: int = 3) -> Dict[str, Any]:
    """Make HTTP request with retries."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    for attempt in range(retries):
        try:
            if data:
                req = Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method=method)
            else:
                req = Request(url, headers=headers, method=method)
            
            with urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
                
        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            logger.warning(f"HTTP {e.code} on attempt {attempt + 1}: {error_body[:200]}")
            
            if e.code == 429:  # Rate limited
                wait_time = (2 ** attempt) * 5
                time.sleep(wait_time)
            elif e.code >= 500:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                raise
                
        except URLError as e:
            logger.warning(f"Network error on attempt {attempt + 1}: {e.reason}")
            time.sleep(2 ** attempt)
    
    raise Exception(f"Failed after {retries} retries")


def build_apify_input(query: str, max_profiles: int = 100) -> Dict[str, Any]:
    """
    Build proper input for apify/google-search-scraper actor.
    Uses X-Ray search: site:linkedin.com/in/ + keywords.
    """
    from parse_query import parse_query_with_llm
    
    logger.info(f"🔍 [build_apify_input] Raw query received: {query}")
    
    # Get structured filters from LLM
    filters = parse_query_with_llm(query)
    
    logger.info(f"📋 [build_apify_input] LLM parsed filters: {json.dumps(filters, indent=2)}")
    
    # Build X-Ray search query
    # Format: site:linkedin.com/in/ "title" "location" "industry"
    search_parts = ['site:linkedin.com/in/']
    
    # Add titles (quoted for exact match)
    titles = filters.get("person_titles", [])[:2]
    if titles:
        search_parts.append(f'"{titles[0]}"')
    
    # Add ALL locations (not just first one)
    locations = filters.get("organization_locations", [])
    for loc in locations[:2]:
        search_parts.append(f'"{loc}"')
    
    # Add industry keywords
    keywords = filters.get("q_organization_keyword_tags", [])[:2]
    for kw in keywords[:2]:
        search_parts.append(f'"{kw}"')
    
    search_query = " ".join(search_parts)
    logger.info(f"🔎 [build_apify_input] Final X-Ray query: {search_query}")
    
    # Google Search Scraper input schema
    payload = {
        "queries": search_query,
        "maxPagesPerQuery": 1,
        "resultsPerPage": max_profiles,
        "mobileResults": False,
        "languageCode": "",
        "countryCode": "",
    }
    
    logger.info(f"📦 [build_apify_input] Apify payload: {json.dumps(payload, indent=2)}")
    
    return payload


def run_apify_actor(query: str, max_profiles: int = 100) -> str:
    """
    Run Apify LinkedIn search actor with proper input schema.
    """
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY not set. Add it to your .env file.")
    
    # Build proper input
    payload = build_apify_input(query, max_profiles)
    
    # Start actor run
    url = f"{APIFY_API_BASE}/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_API_KEY}"
    
    logger.info(f"Starting Apify actor: {APIFY_ACTOR_ID}")
    logger.info(f"Payload: {payload}")
    
    response = make_request(url, data=payload, method="POST")
    
    run_id = response.get("data", {}).get("id")
    if not run_id:
        raise Exception(f"Failed to start Apify actor: {response}")
    
    logger.info(f"Apify run started: {run_id}")
    return run_id


def wait_for_apify_run(run_id: str, timeout_seconds: int = 300) -> Dict[str, Any]:
    """
    Wait for Apify run to complete and return status.
    """
    url = f"{APIFY_API_BASE}/actor-runs/{run_id}?token={APIFY_API_KEY}"
    
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        response = make_request(url)
        status = response.get("data", {}).get("status")
        
        logger.info(f"Apify run status: {status}")
        
        if status == "SUCCEEDED":
            return response.get("data", {})
        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            raise Exception(f"Apify run failed with status: {status}")
        
        time.sleep(10)  # Poll every 10 seconds
    
    raise Exception(f"Apify run timed out after {timeout_seconds}s")


def get_apify_results(run_id: str) -> List[Dict[str, Any]]:
    """Get results from completed Apify run.
    
    For Google Search Scraper, results are nested in organicResults array.
    """
    url = f"{APIFY_API_BASE}/actor-runs/{run_id}/dataset/items?token={APIFY_API_KEY}"
    
    response = make_request(url)
    
    # Handle direct list response
    if isinstance(response, list):
        # Google Search Scraper returns array of search result pages
        # Each page has organicResults array
        all_results = []
        for page in response:
            organic = page.get("organicResults", [])
            all_results.extend(organic)
        return all_results
    
    return response.get("items", response.get("data", []))


def normalize_apify_lead(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Google Search result to standard lead format.
    Google Search Scraper organicResults have: title, url, description, personalInfo
    """
    import re
    
    url = result.get("url", "") or result.get("link", "")
    title = result.get("title", "")
    description = result.get("description", "") or result.get("snippet", "")
    personal_info = result.get("personalInfo", {})
    
    # Only process LinkedIn profile URLs
    if "linkedin.com/in/" not in url:
        return {}
    
    # Extract structured data from personalInfo if available
    location = personal_info.get("location", "")
    job_title = personal_info.get("jobTitle", "")
    company_name = personal_info.get("companyName", "")
    
    # Extract name from title
    # LinkedIn titles are like: "John Doe - Marketing Director - Company | LinkedIn"
    full_name = ""
    
    if title:
        # Remove " | LinkedIn" suffix and everything after
        title_clean = re.sub(r'\s*[|\-–]?\s*LinkedIn.*$', '', title, flags=re.IGNORECASE)
        
        # Split by " - " to get name (first part)
        parts = [p.strip() for p in title_clean.split(" - ")]
        if len(parts) >= 1:
            full_name = parts[0]
        # Fallback for title/company if personalInfo didn't have them
        if not job_title and len(parts) >= 2:
            job_title = parts[1]
        if not company_name and len(parts) >= 3:
            company_name = parts[2]
    
    # Parse name into first/last
    name_parts = full_name.split(" ", 1) if full_name else ["", ""]
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "title": job_title,
        "company_name": company_name,
        "linkedin_url": url,
        "location": location,
        "source": "apify_google_xray",
        "raw_data": result
    }


def fetch_linkedin_leads(
    query: str,
    limit: int = 100,
    run_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch leads from LinkedIn via Apify.
    """
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY not set. Add it to your .env file.")
    
    # Ensure DB is initialized if run_id provided
    if run_id:
        init_db()
    
    try:
        # Run Apify actor with query (it builds proper input internally)
        apify_run_id = run_apify_actor(query, max_profiles=limit)
        
        # Wait for completion
        wait_for_apify_run(apify_run_id)
        
        # Get results
        raw_profiles = get_apify_results(apify_run_id)
        logger.info(f"Got {len(raw_profiles)} profiles from Apify")
        
        # Normalize leads
        leads = []
        seen_urls = set()
        for profile in raw_profiles[:limit]:
            lead = normalize_apify_lead(profile)
            if lead.get("full_name") and lead.get("linkedin_url") and lead["linkedin_url"] not in seen_urls:
                seen_urls.add(lead["linkedin_url"])
                leads.append(lead)
                
                # Save to DB if run_id is present
                if run_id:
                    lead["run_id"] = run_id
                    upsert_lead(lead, run_id)
        
        logger.info(f"Normalized {len(leads)} valid leads")
        
        return {
            "status": "success",
            "leads": leads,
            "leads_count": len(leads),
            "apify_run_id": apify_run_id,
            "source": "apify_linkedin",
            "message": f"Fetched {len(leads)} leads from LinkedIn via Apify"
        }
        
    except Exception as e:
        logger.exception("Failed to fetch LinkedIn leads")
        return {"status": "error", "message": str(e)}


def run(params: dict = None) -> dict:
    """Entry point for MCP execution."""
    params = params or {}
    
    query = params.get("query")
    if not query:
        return {"status": "error", "message": "query parameter required"}
    
    return fetch_linkedin_leads(
        query=query,
        limit=params.get("limit", 100),
        run_id=params.get("run_id")
    )


if __name__ == "__main__":
    params = {}
    if len(sys.argv) > 1:
        try:
            params = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            params = {"query": sys.argv[1]}
    
    result = run(params)
    print(json.dumps(result, indent=2, default=str))
