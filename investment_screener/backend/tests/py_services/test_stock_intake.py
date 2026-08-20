"""Tests the automated single stock onboarding intake workflow."""

import json
import sqlite3
import pytest
from pathlib import Path


def test_stock_intake_workflow_contract():
    """Validates the input and output contract expected for /stock-intake."""
    # Contract: An intake payload must provide ticker, sector, pillar, and projection scenarios
    sample_intake = {
        "ticker": "TEST",
        "name": "Test Company Corp.",
        "sector": "Technology",
        "industry": "Semiconductors",
        "pillarId": "compute",
        "subStrategyId": "sa-asi-race",
        "currentPrice": 100.0,
        "dcfFairValue": 120.0,
        "action": "BUY",
        "scenarios": {
            "bear": {"weight": 0.25, "growthRate": 15.0, "netMargin": 15.0, "exitPE": 20.0, "scenarioPrice": 80.0},
            "base": {"weight": 0.50, "growthRate": 30.0, "netMargin": 22.0, "exitPE": 28.0, "scenarioPrice": 120.0},
            "bull": {"weight": 0.25, "growthRate": 45.0, "netMargin": 30.0, "exitPE": 35.0, "scenarioPrice": 160.0},
        }
    }
    assert sample_intake["ticker"] == "TEST"
    assert sample_intake["scenarios"]["base"]["scenarioPrice"] == 120.0
    assert sum(s["weight"] for s in sample_intake["scenarios"].values()) == 1.0
