"""Tests for weekly_review.py context parsing."""
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))

from weekly_review import get_recent_reviews_context  # noqa: E402


def test_get_recent_reviews_context(tmp_path):
    # Set up temp folder matching the expected structure
    temp_daily = tmp_path / "temp/daily-reviews"
    temp_daily.mkdir(parents=True)
    
    mock_review = (
        "# Daily Portfolio Confluence Scan\n\n"
        "## Executive Summary\n"
        "* **Total Portfolio Value:** $28,287.33 USD\n"
        "* **Key Observations:**\n"
        "* **Drift Alerts:** Key target deviations in PLTR(-1.03%), SNDK(+1.00%), MU(-0.54%).\n"
        "## Sub-Strategy Analysis\n"
    )
    
    review_file = temp_daily / "daily_confluence_scan_2026-07-18.md"
    review_file.write_text(mock_review)
    
    # Run helper
    context = get_recent_reviews_context(tmp_path)
    
    assert "Already Captured" in context
    assert "PLTR(-1.03%)" in context
