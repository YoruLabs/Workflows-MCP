"""
Export Leads to CSV, JSON, and Linear-ready Markdown

Generates output files:
- output/leads.csv
- output/leads.json
- output/linear_update.md (summary + top 10 leads + stats)
"""

import sys
import json
import os
import csv
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import db module
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from db import get_leads_by_run, get_scores_by_run, get_run, update_run

# Output directory - relative to repo root
OUTPUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "..", "..", "..", "output")


def get_output_dir() -> str:
    """Get output directory path, creating if needed."""
    output_dir = os.path.abspath(OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def get_merged_leads(run_id: str) -> List[Dict[str, Any]]:
    """Get leads merged with their scores."""
    leads = get_leads_by_run(run_id)
    scores = get_scores_by_run(run_id)
    
    # Create score lookup by lead_id
    score_map = {s["lead_id"]: s for s in scores}
    
    # Merge leads with scores
    merged = []
    for lead in leads:
        lead_score = score_map.get(lead["id"], {})
        merged.append({
            **lead,
            "fit_score": lead_score.get("fit_score", 0),
            "score_reasons": lead_score.get("score_reasons", []),
            "score_reasons_str": "; ".join(lead_score.get("score_reasons", [])),
        })
    
    # Sort by fit_score descending
    merged.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
    return merged


def calculate_stats(leads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate stats from merged leads."""
    score_values = [l["fit_score"] for l in leads if l.get("fit_score")]
    
    return {
        "total_leads": len(leads),
        "high_fit_leads": len([l for l in leads if l.get("fit_score", 0) >= 70]),
        "medium_fit_leads": len([l for l in leads if 40 <= l.get("fit_score", 0) < 70]),
        "low_fit_leads": len([l for l in leads if l.get("fit_score", 0) < 40]),
        "avg_score": round(sum(score_values) / len(score_values), 1) if score_values else 0,
        "max_score": max(score_values) if score_values else 0,
        "min_score": min(score_values) if score_values else 0,
    }


def export_csv(run_id: str, filename: str = "leads.csv") -> str:
    """
    Export leads with scores to CSV.
    
    Args:
        run_id: Pipeline run ID
        filename: Output filename (default: leads.csv)
    
    Returns:
        Path to exported CSV file
    """
    merged = get_merged_leads(run_id)
    
    # Define CSV columns
    columns = [
        "email", "full_name", "first_name", "last_name", "title", "seniority",
        "company_name", "company_domain", "company_size", "company_industry",
        "city", "state", "country", "linkedin_url", "phone",
        "fit_score", "score_reasons_str", "email_verified", "source"
    ]
    
    # Rename score_reasons_str to score_reasons for CSV header
    column_names = [c if c != "score_reasons_str" else "score_reasons" for c in columns]
    
    filepath = os.path.join(get_output_dir(), filename)
    
    # Write CSV
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(column_names)
        for lead in merged:
            row = [lead.get(c, "") for c in columns]
            writer.writerow(row)
    
    logger.info(f"Exported {len(merged)} leads to {filepath}")
    return filepath


def export_json(run_id: str, filename: str = "leads.json") -> str:
    """
    Export leads with scores to JSON.
    
    Args:
        run_id: Pipeline run ID
        filename: Output filename (default: leads.json)
    
    Returns:
        Path to exported JSON file
    """
    run_data = get_run(run_id)
    merged = get_merged_leads(run_id)
    stats = calculate_stats(merged)
    
    export_data = {
        "run_id": run_id,
        "icp_name": run_data.get("icp_name") if run_data else None,
        "source": run_data.get("source") if run_data else None,
        "exported_at": datetime.now().isoformat(),
        "stats": stats,
        "leads": [
            {
                "email": l.get("email"),
                "full_name": l.get("full_name"),
                "title": l.get("title"),
                "company_name": l.get("company_name"),
                "company_industry": l.get("company_industry"),
                "company_size": l.get("company_size"),
                "location": f"{l.get('city', '')}, {l.get('state', '')}, {l.get('country', '')}".strip(", "),
                "linkedin_url": l.get("linkedin_url"),
                "fit_score": l.get("fit_score"),
                "score_breakdown": l.get("score_reasons", [])
            }
            for l in merged
        ]
    }
    
    filepath = os.path.join(get_output_dir(), filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, default=str)
    
    logger.info(f"Exported {len(merged)} leads to {filepath}")
    return filepath


def export_linear_markdown(run_id: str, linear_issue: Optional[str] = None, filename: str = "linear_update.md") -> str:
    """
    Export Linear-ready markdown summary.
    
    Args:
        run_id: Pipeline run ID
        linear_issue: Optional Linear issue ID (e.g., LIV-56)
        filename: Output filename (default: linear_update.md)
    
    Returns:
        Path to exported markdown file
    """
    run_data = get_run(run_id)
    merged = get_merged_leads(run_id)
    stats = calculate_stats(merged)
    
    # Build markdown content
    lines = []
    
    # Header with optional Linear issue
    if linear_issue:
        lines.append(f"# Lead Generation Update - {linear_issue}")
    else:
        lines.append("# Lead Generation Update")
    
    lines.append("")
    lines.append(f"**Run ID:** `{run_id}`")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if run_data:
        lines.append(f"**ICP:** {run_data.get('icp_name', 'N/A')}")
        lines.append(f"**Source:** {run_data.get('source', 'N/A')}")
    lines.append("")
    
    # Stats section
    lines.append("## 📊 Summary Stats")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Leads | **{stats['total_leads']}** |")
    lines.append(f"| High Fit (70+) | **{stats['high_fit_leads']}** ✅ |")
    lines.append(f"| Medium Fit (40-69) | **{stats['medium_fit_leads']}** |")
    lines.append(f"| Low Fit (<40) | **{stats['low_fit_leads']}** |")
    lines.append(f"| Average Score | **{stats['avg_score']}** |")
    lines.append("")
    
    # Top 10 leads
    lines.append("## 🎯 Top 10 Leads")
    lines.append("")
    
    top_10 = merged[:10]
    if top_10:
        lines.append("| # | Name | Title | Company | Score |")
        lines.append("|---|------|-------|---------|-------|")
        for i, lead in enumerate(top_10, 1):
            name = lead.get("full_name") or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
            title = lead.get("title", "N/A")[:30]
            company = lead.get("company_name", "N/A")[:25]
            score = lead.get("fit_score", 0)
            score_emoji = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"
            lines.append(f"| {i} | {name} | {title} | {company} | {score_emoji} {score} |")
        lines.append("")
    
    # Score breakdown for top lead
    if top_10:
        lines.append("### Top Lead Score Breakdown")
        lines.append("")
        top_lead = top_10[0]
        name = top_lead.get("full_name") or f"{top_lead.get('first_name', '')} {top_lead.get('last_name', '')}".strip()
        lines.append(f"**{name}** - {top_lead.get('title', '')} @ {top_lead.get('company_name', '')}")
        lines.append("")
        for reason in top_lead.get("score_reasons", [])[:5]:
            lines.append(f"- {reason}")
        lines.append("")
    
    # Next steps
    lines.append("## 📋 Next Steps")
    lines.append("")
    lines.append(f"- [ ] Review top {min(len(top_10), 10)} high-fit leads")
    lines.append("- [ ] Verify email deliverability")
    lines.append("- [ ] Draft personalized outreach")
    lines.append("- [ ] Schedule follow-up sequences")
    lines.append("")
    
    # Files generated
    lines.append("## 📁 Generated Files")
    lines.append("")
    lines.append("- `output/leads.csv` - Full lead list with scores")
    lines.append("- `output/leads.json` - Structured lead data")
    lines.append("- `output/linear_update.md` - This summary")
    lines.append("")
    
    filepath = os.path.join(get_output_dir(), filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    logger.info(f"Exported Linear summary to {filepath}")
    return filepath


def export_all(run_id: str, linear_issue: Optional[str] = None) -> Dict[str, Any]:
    """
    Export all artifacts: CSV, JSON, and Linear markdown.
    
    Args:
        run_id: Pipeline run ID
        linear_issue: Optional Linear issue ID
    
    Returns:
        dict with paths to exported files
    """
    try:
        csv_path = export_csv(run_id)
        json_path = export_json(run_id)
        md_path = export_linear_markdown(run_id, linear_issue)
        
        # Get stats
        merged = get_merged_leads(run_id)
        stats = calculate_stats(merged)
        
        # Update run
        update_run(run_id, leads_exported=len(merged))
        
        return {
            "status": "success",
            "run_id": run_id,
            "csv_path": csv_path,
            "json_path": json_path,
            "markdown_path": md_path,
            "leads_exported": len(merged),
            "stats": stats,
            "message": f"Exported {len(merged)} leads to output/"
        }
        
    except Exception as e:
        logger.exception("Failed to export")
        return {"status": "error", "message": str(e)}


def run(params: dict = None) -> dict:
    """Entry point for MCP execution."""
    params = params or {}
    
    run_id = params.get("run_id")
    if not run_id:
        return {"status": "error", "message": "run_id parameter required"}
    
    export_type = params.get("type", "all")
    linear_issue = params.get("linear_issue")
    
    if export_type == "csv":
        try:
            csv_path = export_csv(run_id, params.get("filename", "leads.csv"))
            return {"status": "success", "csv_path": csv_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    elif export_type == "json":
        try:
            json_path = export_json(run_id, params.get("filename", "leads.json"))
            return {"status": "success", "json_path": json_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    elif export_type == "markdown":
        try:
            md_path = export_linear_markdown(run_id, linear_issue)
            return {"status": "success", "markdown_path": md_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    else:  # all
        return export_all(run_id, linear_issue)


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
