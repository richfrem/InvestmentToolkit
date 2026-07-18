#!/usr/bin/env python3
"""
consolidate_research.py
========================
Consolidates multiple dated research files ({TICKER}_{DATE}.md) into a single,
canonical, chronological research markdown file per ticker ({TICKER}.md).
Optionally queries the corresponding projection JSON file to populate YAML headers.
"""
import os
import re
import glob
import json
import argparse
from pathlib import Path


def load_latest_projection(ticker, projections_dir):
    """Loads the most recent projection for the ticker to populate metadata."""
    p_path = Path(projections_dir) / f"{ticker}.json"
    if not p_path.exists():
        return {}
    try:
        with open(p_path) as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            # Sort by savedAt, newest first
            data = sorted(data, key=lambda x: x.get("savedAt", ""), reverse=True)
            return data[0]
        elif isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def run_consolidation(research_dir, projections_dir, delete_old=False):
    """Groups dated research files, merges them, and builds canonical ticker files."""
    r_path = Path(research_dir)
    files = glob.glob(os.path.join(research_dir, "*_202[0-9]-[0-9][0-9]-[0-9][0-9].md"))
    
    # Group files by ticker
    ticker_files = {}
    pattern = re.compile(r"^([A-Z0-9.\-]+)_(\d{4}-\d{2}-\d{2})\.md$")
    for f in files:
        base = os.path.basename(f)
        match = pattern.match(base)
        if match:
            ticker = match.group(1)
            date_str = match.group(2)
            ticker_files.setdefault(ticker, []).append((date_str, f))

    for ticker, entries in ticker_files.items():
        # Sort chronologically (oldest first for final append structure)
        entries = sorted(entries, key=lambda x: x[0])
        
        # Load latest projection metadata
        proj = load_latest_projection(ticker, projections_dir)
        ai_thesis = proj.get("aiThesis", {})
        snapshot = proj.get("snapshot", {})
        
        fair_value = ai_thesis.get("fairValue", "N/A")
        action = ai_thesis.get("action", "N/A")
        saved_at = proj.get("savedAt", "N/A")
        price = snapshot.get("price", "N/A")

        # Build YAML header
        yaml_header = (
            "---\n"
            f"ticker: {ticker}\n"
            f"name: {proj.get('name', ticker)}\n"
            f"lastUpdated: {saved_at}\n"
            f"fairValue: {fair_value}\n"
            f"priceAtAnalysis: {price}\n"
            f"action: {action}\n"
            "---\n\n"
        )

        merged_content = [yaml_header]
        merged_content.append(f"# {ticker} Canonical Research History\n\n")

        # Merge contents
        for date_str, fp in entries:
            with open(fp, encoding="utf-8") as f:
                content = f.read()
            
            # Clean up redundant titles if present
            cleaned_content = content
            if cleaned_content.startswith("# "):
                lines = cleaned_content.splitlines()
                if len(lines) > 0:
                    lines = lines[1:] # skip main header
                cleaned_content = "\n".join(lines)

            merged_content.append(f"## Research Sweep — {date_str}\n")
            merged_content.append(cleaned_content.strip() + "\n\n")

        # Write canonical file
        out_path = r_path / f"{ticker}.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("".join(merged_content))
        print(f"✅ Consolidated: {out_path}")

        # Delete old files if flag set
        if delete_old:
            for _, fp in entries:
                os.remove(fp)
            print(f"🗑️ Deleted {len(entries)} dated files for {ticker}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-dir", default=None)
    parser.add_argument("--projections-dir", default=None)
    parser.add_argument("--delete-old", action="store_true")
    args = parser.parse_args()

    # Determine default paths relative to repo root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

    res_dir = args.research_dir or os.path.join(repo_root, "investment_screener/backend/data/research")
    proj_dir = args.projections_dir or os.path.join(repo_root, "investment_screener/backend/data/projections")

    run_consolidation(res_dir, proj_dir, delete_old=args.delete_old)


if __name__ == "__main__":
    main()
