"""Tests for earnings_calendar.py — ETF classification.

ETFs (DRAM, HUMN, KOID, etc.) have no earnings dates. They must be excluded
from earnings lookups entirely — not reported as UNKNOWN "blind spots" and
not hammered with yfinance 404s every brief run.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_earnings_calendar.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

import earnings_calendar  # noqa: E402


class TestEtfClassification:
    """Known ETFs in the portfolio must never hit the earnings lookup path."""

    def test_known_etfs_declared(self):
        """DRAM (HBM/memory), HUMN (humanoid robotics), KOID (robotics) are ETFs."""
        for etf in ("DRAM", "HUMN", "KOID"):
            assert etf in earnings_calendar.ETF_TICKERS, (
                f"{etf} is an ETF — must be in ETF_TICKERS so it is excluded "
                f"from earnings lookups instead of reported as a blind spot"
            )

    def test_load_tickers_excludes_etfs(self, tmp_path: Path, monkeypatch):
        """Portfolio with AAPL + 3 ETFs → only AAPL gets an earnings lookup."""
        portfolio = {"holdings": [
            {"symbol": "AAPL"},
            {"symbol": "DRAM"},
            {"symbol": "HUMN"},
            {"symbol": "KOID"},
        ]}
        p = tmp_path / "portfolio.json"
        p.write_text(json.dumps(portfolio))
        monkeypatch.setattr(earnings_calendar, "PORTFOLIO_PATH", p)

        assert earnings_calendar._load_tickers() == ["AAPL"]

    def test_cash_skip_list_still_applies(self, tmp_path: Path, monkeypatch):
        portfolio = {"holdings": [{"symbol": "PSU-U.TO"}, {"symbol": "MSFT"}]}
        p = tmp_path / "portfolio.json"
        p.write_text(json.dumps(portfolio))
        monkeypatch.setattr(earnings_calendar, "PORTFOLIO_PATH", p)

        assert earnings_calendar._load_tickers() == ["MSFT"]
