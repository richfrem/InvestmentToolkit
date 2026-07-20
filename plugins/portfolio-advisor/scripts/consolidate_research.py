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
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import list_projection_versions  # noqa: E402


def load_latest_projection(ticker, db_path):
    """Loads the most recent projection for the ticker to populate metadata.

    Storage backend (Wave 1 Task 7B): reads `projection_version` via
    `domain_model.projection_repository`, not `projections/{TICKER}.json`
    directly (ADR-029). The original code sorted ALL entries (any `source`) by
    `savedAt` descending and took the newest — no AI_AGENT filter — so this
    reproduces that exact selection (`list_projection_versions` + max by
    `saved_at`) rather than using `get_latest_projection_by_source`.

    Args:
        ticker: Ticker symbol.
        db_path: Path to domain_model.sqlite.

    Returns:
        `{"name", "savedAt", "aiThesis": {"fairValue","action"}, "snapshot":
        {"price"}}`, or `{}` if the investment has no projection rows at all.
    """
    conn = initialize_db(str(db_path))
    try:
        row = conn.execute(
            "SELECT investment_id, name FROM investment WHERE symbol = ?;", (ticker,)
        ).fetchone()
        if row is None:
            return {}
        investment_id, name = row
        versions = list_projection_versions(conn, investment_id)
        if not versions:
            return {}
        latest = max(versions, key=lambda v: v.get("saved_at") or "")
        snapshot = json.loads(latest["snapshot_json"]) if latest.get("snapshot_json") else {}
        ai_thesis = {}
        if latest.get("fair_value") is not None:
            ai_thesis["fairValue"] = latest["fair_value"]
        if latest.get("action") is not None:
            ai_thesis["action"] = latest["action"]
        return {
            "name": name,
            "savedAt": latest.get("saved_at", ""),
            "aiThesis": ai_thesis,
            "snapshot": snapshot,
        }
    finally:
        conn.close()


def run_consolidation(research_dir, db_path, delete_old=False):
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
        proj = load_latest_projection(ticker, db_path)
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
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--delete-old", action="store_true")
    args = parser.parse_args()

    # Determine default paths relative to repo root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

    res_dir = args.research_dir or os.path.join(repo_root, "investment_screener/backend/data/research")
    db_path = args.db_path or os.path.join(repo_root, "investment_screener/backend/data/domain_model.sqlite")

    run_consolidation(res_dir, db_path, delete_old=args.delete_old)


if __name__ == "__main__":
    main()
