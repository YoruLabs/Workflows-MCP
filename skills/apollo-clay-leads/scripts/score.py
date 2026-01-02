"""
Explainable Lead Scoring

Scores leads based on ICP fit with transparent reasoning.
Produces fit_score (0-100) and score_reasons (list of strings).
"""

import sys
import json
import os
import logging
from typing import Dict, Any, List, Tuple, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import db module
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from db import get_leads_by_run, save_score, update_run, get_run


def load_icp_config(icp_name: str) -> Dict[str, Any]:
    """Load ICP configuration from file."""
    config_path = os.path.join(SCRIPT_DIR, "icp_configs", f"{icp_name}.json")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"ICP config not found: {config_path}")
    
    with open(config_path, "r") as f:
        return json.load(f)


def normalize(value: str) -> str:
    """Normalize string for comparison."""
    if not value:
        return ""
    return str(value).lower().strip()


def check_title_match(title: str, target_titles: List[str]) -> Tuple[bool, str]:
    """Check if title matches ICP target titles."""
    if not title:
        return False, None
    
    title_lower = normalize(title)
    
    for target in target_titles:
        target_lower = normalize(target)
        # Exact match or contains
        if target_lower in title_lower or title_lower in target_lower:
            return True, f"Title '{title}' matches ICP target '{target}'"
    
    return False, None


def check_seniority_match(seniority: str, target_seniorities: List[str]) -> Tuple[bool, str]:
    """Check if seniority matches ICP targets."""
    if not seniority:
        return False, None
    
    seniority_lower = normalize(seniority)
    
    # Map common seniority aliases
    seniority_aliases = {
        "c_suite": ["c_suite", "c-suite", "c level", "c-level", "chief", "ceo", "cto", "cfo", "coo", "cmo"],
        "vp": ["vp", "vice president", "vice-president", "svp", "evp"],
        "director": ["director", "head of", "head"],
        "manager": ["manager", "lead", "senior"],
    }
    
    for target in target_seniorities:
        target_lower = normalize(target)
        
        # Direct match
        if target_lower == seniority_lower:
            return True, f"Seniority '{seniority}' matches ICP target"
        
        # Alias match
        aliases = seniority_aliases.get(target_lower, [target_lower])
        for alias in aliases:
            if alias in seniority_lower:
                return True, f"Seniority '{seniority}' matches ICP target '{target}'"
    
    return False, None


def check_location_match(country: str, locations: List[str]) -> Tuple[bool, str]:
    """Check if location matches ICP targets."""
    if not country:
        return False, None
    
    country_lower = normalize(country)
    
    # Common country aliases
    country_aliases = {
        "united states": ["united states", "usa", "us", "united states of america"],
        "united kingdom": ["united kingdom", "uk", "great britain", "england"],
        "canada": ["canada", "ca"],
    }
    
    for target in locations:
        target_lower = normalize(target)
        
        # Direct match
        if target_lower == country_lower:
            return True, f"Location '{country}' matches ICP target"
        
        # Alias match
        for canonical, aliases in country_aliases.items():
            if target_lower in aliases or canonical == target_lower:
                if country_lower in aliases or country_lower == canonical:
                    return True, f"Location '{country}' matches ICP target '{target}'"
    
    return False, None


def check_company_size_match(size: str, target_ranges: List[str]) -> Tuple[bool, str]:
    """Check if company size matches ICP targets."""
    if not size:
        return False, None
    
    size_lower = normalize(size)
    
    # Parse size to numeric range
    size_ranges = {
        "1-50": (1, 50),
        "51-200": (51, 200),
        "201-500": (201, 500),
        "501-1000": (501, 1000),
        "1000+": (1001, 100000),
    }
    
    current_range = size_ranges.get(size, None)
    if not current_range:
        # Try to parse from string like "51,200"
        try:
            parts = size.replace(" ", "").split(",")
            if len(parts) == 2:
                current_range = (int(parts[0]), int(parts[1]))
        except:
            pass
    
    if not current_range:
        return False, None
    
    for target in target_ranges:
        # Parse target range like "51,200" or "51-200"
        try:
            if "," in target:
                parts = target.split(",")
                target_range = (int(parts[0]), int(parts[1]))
            elif "-" in target:
                parts = target.split("-")
                target_range = (int(parts[0]), int(parts[1]))
            else:
                continue
            
            # Check overlap
            if current_range[0] <= target_range[1] and current_range[1] >= target_range[0]:
                return True, f"Company size '{size}' matches ICP target range"
        except:
            continue
    
    return False, None


def check_industry_match(industry: str, keywords: List[str]) -> Tuple[bool, str]:
    """Check if industry matches ICP target keywords."""
    if not industry:
        return False, None
    
    industry_lower = normalize(industry)
    
    for keyword in keywords:
        if normalize(keyword) in industry_lower:
            return True, f"Industry '{industry}' contains ICP keyword '{keyword}'"
    
    return False, None


def score_lead(lead: Dict[str, Any], icp_config: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    Score a single lead against ICP configuration.
    
    Returns:
        Tuple of (fit_score 0-100, list of score_reasons)
    """
    filters = icp_config.get("filters", {})
    weights = icp_config.get("scoring_weights", {
        "title_match": 25,
        "seniority_match": 20,
        "industry_match": 20,
        "company_size_match": 15,
        "location_match": 10,
        "verified_email": 5,
        "has_linkedin": 5,
    })
    
    score = 0
    reasons = []
    
    # Title match
    if filters.get("person_titles"):
        matched, reason = check_title_match(lead.get("title"), filters["person_titles"])
        if matched:
            points = weights.get("title_match", 25)
            score += points
            reasons.append(f"+{points}: {reason}")
        else:
            reasons.append(f"+0: Title '{lead.get('title', 'unknown')}' does not match ICP targets")
    
    # Seniority match
    if filters.get("person_seniorities"):
        matched, reason = check_seniority_match(lead.get("seniority"), filters["person_seniorities"])
        if matched:
            points = weights.get("seniority_match", 20)
            score += points
            reasons.append(f"+{points}: {reason}")
    
    # Location match
    if filters.get("organization_locations"):
        matched, reason = check_location_match(lead.get("country"), filters["organization_locations"])
        if matched:
            points = weights.get("location_match", 10)
            score += points
            reasons.append(f"+{points}: {reason}")
    
    # Company size match
    if filters.get("organization_num_employees_ranges"):
        matched, reason = check_company_size_match(
            lead.get("company_size"),
            filters["organization_num_employees_ranges"]
        )
        if matched:
            points = weights.get("company_size_match", 15)
            score += points
            reasons.append(f"+{points}: {reason}")
    
    # Industry match
    if filters.get("q_organization_keyword_tags"):
        matched, reason = check_industry_match(
            lead.get("company_industry"),
            filters["q_organization_keyword_tags"]
        )
        if matched:
            points = weights.get("industry_match", 20)
            score += points
            reasons.append(f"+{points}: {reason}")
    
    # Email verified bonus
    if lead.get("email_verified"):
        points = weights.get("verified_email", 5)
        score += points
        reasons.append(f"+{points}: Email is verified")
    
    # LinkedIn profile bonus
    if lead.get("linkedin_url"):
        points = weights.get("has_linkedin", 5)
        score += points
        reasons.append(f"+{points}: Has LinkedIn profile")
    
    # Cap at 100
    score = min(score, 100)
    
    return score, reasons


def score_leads(run_id: str, icp_name: str = "icp_v1") -> Dict[str, Any]:
    """
    Score all leads for a pipeline run.
    
    Args:
        run_id: Pipeline run ID
        icp_name: ICP config to use for scoring (use "query" for default weights)
    
    Returns:
        dict with status and scoring stats
    """
    try:
        # Load ICP config or use the stored config for query-based scoring
        if icp_name == "query":
            # Try to get the ICP config from the run (contains parsed query filters)
            run_data = get_run(run_id)
            if run_data and run_data.get("icp_config"):
                icp_config = run_data["icp_config"]
                # Ensure scoring weights exist
                if "scoring_weights" not in icp_config:
                    icp_config["scoring_weights"] = {
                        "title_match": 25,
                        "seniority_match": 20,
                        "industry_match": 20,
                        "company_size_match": 15,
                        "location_match": 10,
                        "verified_email": 5,
                        "has_linkedin": 5,
                    }
                logger.info(f"Using stored query filters: {list(icp_config.get('filters', {}).keys())}")
            else:
                # Fallback to empty filters
                icp_config = {
                    "name": "query",
                    "filters": {},
                    "scoring_weights": {
                        "title_match": 25,
                        "seniority_match": 20,
                        "industry_match": 20,
                        "company_size_match": 15,
                        "location_match": 10,
                        "verified_email": 5,
                        "has_linkedin": 5,
                    }
                }
                logger.info("Using default scoring weights (query mode)")
        else:
            icp_config = load_icp_config(icp_name)
            logger.info(f"Loaded ICP config: {icp_name}")
        
        # Get leads
        leads = get_leads_by_run(run_id)
        
        if not leads:
            return {
                "status": "success",
                "message": "No leads to score",
                "leads_scored": 0
            }
        
        logger.info(f"Scoring {len(leads)} leads...")
        
        scored = 0
        score_distribution = {"high": 0, "medium": 0, "low": 0}
        
        for lead in leads:
            fit_score, score_reasons = score_lead(lead, icp_config)
            
            # Save score to database
            save_score(
                lead_id=lead["id"],
                run_id=run_id,
                fit_score=fit_score,
                score_reasons=score_reasons,
                icp_name=icp_name
            )
            
            scored += 1
            
            # Track distribution
            if fit_score >= 70:
                score_distribution["high"] += 1
            elif fit_score >= 40:
                score_distribution["medium"] += 1
            else:
                score_distribution["low"] += 1
        
        # Update run stats
        update_run(run_id, leads_scored=scored)
        
        result = {
            "status": "success",
            "run_id": run_id,
            "leads_scored": scored,
            "distribution": score_distribution,
            "message": f"Scored {scored} leads: {score_distribution['high']} high, {score_distribution['medium']} medium, {score_distribution['low']} low"
        }
        
        logger.info(result["message"])
        return result
        
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception("Failed to score leads")
        return {"status": "error", "message": str(e)}



def run(params: dict = None) -> dict:
    """Entry point for MCP execution."""
    params = params or {}
    
    # Single lead scoring mode
    if "lead" in params:
        icp_name = params.get("icp", "icp_v1")
        icp_config = load_icp_config(icp_name)
        fit_score, reasons = score_lead(params["lead"], icp_config)
        return {
            "status": "success",
            "fit_score": fit_score,
            "score_reasons": reasons
        }
    
    # Batch scoring mode
    run_id = params.get("run_id")
    if not run_id:
        return {"status": "error", "message": "run_id parameter required (or pass 'lead' for single scoring)"}
    
    icp_name = params.get("icp", "icp_v1")
    
    return score_leads(run_id=run_id, icp_name=icp_name)


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
