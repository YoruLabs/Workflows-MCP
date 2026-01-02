"""
Fetch Leads from Apollo.io API

Uses the /v1/mixed_people/search endpoint to fetch leads based on ICP filters
or natural language query.
"""

import sys
import json
import os
import time
import logging
import re
from typing import Dict, Any, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Apollo API configuration
APOLLO_API_BASE = "https://api.apollo.io/v1"
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "")

# Import db module
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from db import upsert_lead, create_run, update_run, complete_run


# Mock data for dry-run mode
MOCK_LEADS = [
    {"email": "john.smith@techcorp.com", "first_name": "John", "last_name": "Smith", "title": "CTO", "seniority": "c_suite", "company_name": "TechCorp Inc", "company_domain": "techcorp.com", "company_size": "51-200", "company_industry": "Software", "city": "San Francisco", "state": "CA", "country": "United States", "linkedin_url": "https://linkedin.com/in/johnsmith", "email_verified": True, "phone": "+1-555-0101"},
    {"email": "jane.doe@saasify.io", "first_name": "Jane", "last_name": "Doe", "title": "VP of Engineering", "seniority": "vp", "company_name": "SaaSify", "company_domain": "saasify.io", "company_size": "51-200", "company_industry": "SaaS", "city": "Austin", "state": "TX", "country": "United States", "linkedin_url": "https://linkedin.com/in/janedoe", "email_verified": True, "phone": "+1-555-0102"},
    {"email": "mike.johnson@cloudtech.io", "first_name": "Mike", "last_name": "Johnson", "title": "Head of Engineering", "seniority": "director", "company_name": "CloudTech", "company_domain": "cloudtech.io", "company_size": "201-500", "company_industry": "Cloud SaaS", "city": "Seattle", "state": "WA", "country": "United States", "linkedin_url": "https://linkedin.com/in/mikejohnson", "email_verified": True, "phone": "+1-555-0103"},
    {"email": "sarah.wilson@enterprise.com", "first_name": "Sarah", "last_name": "Wilson", "title": "Director of Engineering", "seniority": "director", "company_name": "Enterprise Corp", "company_domain": "enterprise.com", "company_size": "501-1000", "company_industry": "Enterprise Software", "city": "New York", "state": "NY", "country": "United States", "linkedin_url": "https://linkedin.com/in/sarahwilson", "email_verified": True, "phone": "+1-555-0104"},
    {"email": "tom.brown@fintech.com", "first_name": "Tom", "last_name": "Brown", "title": "VP Engineering", "seniority": "vp", "company_name": "FinTech Solutions", "company_domain": "fintech.com", "company_size": "201-500", "company_industry": "Financial Technology", "city": "Boston", "state": "MA", "country": "United States", "linkedin_url": "https://linkedin.com/in/tombrown", "email_verified": True, "phone": "+1-555-0105"},
    {"email": "emily.chen@marketingpro.com", "first_name": "Emily", "last_name": "Chen", "title": "Marketing Administrator", "seniority": "manager", "company_name": "MarketingPro", "company_domain": "marketingpro.com", "company_size": "1000+", "company_industry": "Marketing", "city": "Chicago", "state": "IL", "country": "United States", "linkedin_url": "https://linkedin.com/in/emilychen", "email_verified": True, "phone": "+1-555-0106"},
    {"email": "david.lee@adtech.io", "first_name": "David", "last_name": "Lee", "title": "Systems Administrator", "seniority": "individual_contributor", "company_name": "AdTech Global", "company_domain": "adtech.io", "company_size": "501-1000", "company_industry": "Advertising", "city": "Los Angeles", "state": "CA", "country": "United States", "linkedin_url": "https://linkedin.com/in/davidlee", "email_verified": True, "phone": "+1-555-0107"},
    {"email": "lisa.wang@bigmarketing.com", "first_name": "Lisa", "last_name": "Wang", "title": "IT Administrator", "seniority": "manager", "company_name": "Big Marketing Co", "company_domain": "bigmarketing.com", "company_size": "1000+", "company_industry": "Marketing Services", "city": "Miami", "state": "FL", "country": "United States", "linkedin_url": "https://linkedin.com/in/lisawang", "email_verified": True, "phone": "+1-555-0108"},
    {"email": "chris.garcia@mediagroup.com", "first_name": "Chris", "last_name": "Garcia", "title": "Network Administrator", "seniority": "individual_contributor", "company_name": "Media Group Inc", "company_domain": "mediagroup.com", "company_size": "501-1000", "company_industry": "Digital Marketing", "city": "Denver", "state": "CO", "country": "United States", "linkedin_url": "https://linkedin.com/in/chrisgarcia", "email_verified": True, "phone": "+1-555-0109"},
    {"email": "alex.kim@brandagency.com", "first_name": "Alex", "last_name": "Kim", "title": "Database Administrator", "seniority": "manager", "company_name": "Brand Agency", "company_domain": "brandagency.com", "company_size": "201-500", "company_industry": "Creative Marketing", "city": "Portland", "state": "OR", "country": "United States", "linkedin_url": "https://linkedin.com/in/alexkim", "email_verified": True, "phone": "+1-555-0110"},
]


def load_icp_config(icp_name: str) -> Dict[str, Any]:
    """Load ICP configuration from file."""
    config_path = os.path.join(SCRIPT_DIR, "icp_configs", f"{icp_name}.json")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"ICP config not found: {config_path}")
    
    with open(config_path, "r") as f:
        return json.load(f)


def parse_query_to_filters(query: str) -> Dict[str, Any]:
    """
    Parse a natural language query into Apollo API filters using LLM.
    
    Uses OpenAI to intelligently understand the query and extract
    relevant Apollo API filter parameters.
    
    Args:
        query: Natural language search query
    
    Returns:
        dict with Apollo API filter fields
    """
    from parse_query import parse_query_with_llm
    return parse_query_with_llm(query)


def make_request(url: str, data: Dict[str, Any], retries: int = 3) -> Dict[str, Any]:
    """Make HTTP POST request with retries and exponential backoff."""
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY
    }
    
    for attempt in range(retries):
        try:
            req = Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
            
            with urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
                
        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            logger.warning(f"HTTP {e.code} on attempt {attempt + 1}: {error_body[:200]}")
            
            if e.code == 429:  # Rate limited
                wait_time = (2 ** attempt) * 5  # Longer wait for rate limits
                logger.info(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            elif e.code >= 500:  # Server error, retry
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                raise
                
        except URLError as e:
            logger.warning(f"Network error on attempt {attempt + 1}: {e.reason}")
            wait_time = 2 ** attempt
            time.sleep(wait_time)
    
    raise Exception(f"Failed after {retries} retries")


def search_people(filters: Dict[str, Any], page: int = 1, per_page: int = 25) -> Dict[str, Any]:
    """Search for people using Apollo API."""
    url = f"{APOLLO_API_BASE}/mixed_people/search"
    
    # Build request payload
    payload = {
        "page": page,
        "per_page": min(per_page, 100),  # Apollo max is 100
        **filters
    }
    
    # Remove non-API fields
    payload.pop("scoring_weights", None)
    payload.pop("apollo_params", None)
    
    logger.info(f"Searching Apollo API (page {page}, per_page {per_page})...")
    return make_request(url, payload)


def normalize_apollo_person(person: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Apollo person data to our lead schema."""
    org = person.get("organization", {}) or {}
    
    # Determine company size range
    employees = org.get("estimated_num_employees")
    if employees:
        if employees <= 50:
            company_size = "1-50"
        elif employees <= 200:
            company_size = "51-200"
        elif employees <= 500:
            company_size = "201-500"
        elif employees <= 1000:
            company_size = "501-1000"
        else:
            company_size = "1000+"
    else:
        company_size = None
    
    return {
        "email": person.get("email", ""),
        "first_name": person.get("first_name"),
        "last_name": person.get("last_name"),
        "full_name": person.get("name"),
        "title": person.get("title"),
        "seniority": person.get("seniority"),
        "company_name": org.get("name"),
        "company_domain": org.get("primary_domain") or org.get("website_url"),
        "company_size": company_size,
        "company_industry": org.get("industry"),
        "location": person.get("city") or person.get("state") or person.get("country"),
        "city": person.get("city"),
        "state": person.get("state"),
        "country": person.get("country"),
        "linkedin_url": person.get("linkedin_url"),
        "email_verified": person.get("email_status") == "verified",
        "phone": (person.get("phone_numbers") or [{}])[0].get("sanitized_number") if person.get("phone_numbers") else None,
        "source": "apollo_api",
        "raw_data": person
    }


def fetch_mock_leads(query: str, limit: int, run_id: str) -> Dict[str, Any]:
    """Fetch mock leads for dry-run mode."""
    logger.info(f"[DRY-RUN] Using mock data for query: {query}")
    
    # Filter mock leads based on query
    query_lower = query.lower()
    filtered_leads = []
    
    for lead in MOCK_LEADS:
        # Simple matching based on query terms
        title_lower = (lead.get("title") or "").lower()
        industry_lower = (lead.get("company_industry") or "").lower()
        
        # Check if lead matches query
        match = False
        if "administrator" in query_lower and "administrator" in title_lower:
            match = True
        elif "marketing" in query_lower and "marketing" in industry_lower:
            match = True
        elif "cto" in query_lower and "cto" in title_lower:
            match = True
        elif "vp" in query_lower and "vp" in title_lower:
            match = True
        elif "director" in query_lower and "director" in title_lower:
            match = True
        elif "large" in query_lower and lead.get("company_size") in ["501-1000", "1000+"]:
            match = True
        else:
            # Include all if no specific match
            match = True
        
        if match:
            filtered_leads.append(lead)
    
    # Limit results
    leads_to_use = filtered_leads[:limit]
    
    # Store in database
    leads_fetched = 0
    for lead in leads_to_use:
        lead_data = {
            **lead,
            "full_name": f"{lead['first_name']} {lead['last_name']}",
            "source": "mock_data"
        }
        upsert_lead(lead_data, run_id)
        leads_fetched += 1
    
    return {
        "status": "success",
        "run_id": run_id,
        "leads_fetched": leads_fetched,
        "source": "mock_data",
        "message": f"[DRY-RUN] Generated {leads_fetched} mock leads"
    }


def fetch_leads(
    icp_name: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100,
    run_id: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Fetch leads from Apollo API based on ICP configuration or natural language query.
    
    Args:
        icp_name: Name of ICP config file (without .json)
        query: Natural language query string (alternative to icp_name)
        limit: Maximum number of leads to fetch
        run_id: Optional existing run ID to use
        dry_run: If True, use mock data instead of real API
    
    Returns:
        dict with status, leads fetched, and run_id
    """
    # Build filters from query or ICP
    if query:
        filters = parse_query_to_filters(query)
        icp_config = {"name": "query", "description": query, "filters": filters}
        logger.info(f"Parsed query into filters: {json.dumps(filters, indent=2)}")
    elif icp_name:
        icp_config = load_icp_config(icp_name)
        filters = icp_config.get("filters", {})
        logger.info(f"Loaded ICP config: {icp_name}")
    else:
        return {"status": "error", "message": "Either icp_name or query required"}
    
    # Create run if needed
    if not run_id:
        source = "mock_data" if dry_run else "apollo_api"
        run_id = create_run(icp_config.get("name", "query"), icp_config, source)
        logger.info(f"Created pipeline run: {run_id}")
    
    # Handle dry-run mode
    if dry_run:
        return fetch_mock_leads(query or icp_name, limit, run_id)
    
    # Check API key
    if not APOLLO_API_KEY:
        logger.warning("APOLLO_API_KEY not set. Falling back to mock data.")
        return fetch_mock_leads(query or icp_name, limit, run_id)
    
    try:
        leads_fetched = 0
        page = 1
        per_page = min(limit, 25)
        
        while leads_fetched < limit:
            try:
                response = search_people(filters, page=page, per_page=per_page)
                
                people = response.get("people", [])
                if not people:
                    logger.info("No more results from Apollo")
                    break
                
                for person in people:
                    if leads_fetched >= limit:
                        break
                    
                    # Skip if no email
                    if not person.get("email"):
                        continue
                    
                    # Normalize and store
                    lead_data = normalize_apollo_person(person)
                    upsert_lead(lead_data, run_id)
                    leads_fetched += 1
                
                logger.info(f"Fetched {leads_fetched}/{limit} leads from Apollo")
                
                # Check if there are more pages
                pagination = response.get("pagination", {})
                if page >= pagination.get("total_pages", 1):
                    break
                
                page += 1
                time.sleep(0.5)  # Rate limiting courtesy
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                # Fall back to mock data on API error
                if leads_fetched == 0:
                    logger.warning("API failed. Falling back to mock data.")
                    return fetch_mock_leads(query or icp_name, limit, run_id)
                break
        
        # Update run stats
        update_run(run_id, leads_fetched=leads_fetched)
        
        return {
            "status": "success",
            "run_id": run_id,
            "leads_fetched": leads_fetched,
            "source": "apollo_api",
            "message": f"Fetched {leads_fetched} leads from Apollo API"
        }
        
    except Exception as e:
        logger.exception("Failed to fetch leads")
        if run_id:
            complete_run(run_id, status="failed", error_message=str(e))
        return {"status": "error", "message": str(e)}


def run(params: dict = None) -> dict:
    """Entry point for MCP execution."""
    params = params or {}
    
    return fetch_leads(
        icp_name=params.get("icp"),
        query=params.get("query"),
        limit=params.get("limit", 100),
        run_id=params.get("run_id"),
        dry_run=params.get("dry_run", False)
    )


if __name__ == "__main__":
    params = {}
    if len(sys.argv) > 1:
        try:
            params = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print(json.dumps({"status": "error", "message": "Invalid JSON params"}))
            sys.exit(1)
    
    result = run(params)
    print(json.dumps(result, indent=2, default=str))
