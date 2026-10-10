"""Purpose: pin what the weekly and daily news-sweep prompts ask the models, and the facts they state.

Layer: Plugins / Portfolio Advisor / Tests.
Key Functions: robotics and cash themes present, ledger-ready findings requested, verified corrections kept.
Key Input Dependencies: assets/templates/weekly_sweep.md.template and daily_sweep.md.template.
"""
from pathlib import Path

import pytest

TEMPLATES = Path(__file__).resolve().parents[1] / "assets/templates"
WEEKLY = (TEMPLATES / "weekly_sweep.md.template").read_text()
DAILY = (TEMPLATES / "daily_sweep.md.template").read_text()
BOTH = pytest.mark.parametrize("text", [WEEKLY, DAILY], ids=["weekly", "daily"])


@BOTH
def test_robotics_sector_is_a_theme_and_its_findings_go_under_koid(text):
    assert "Robotics" in text and "Physical AI" in text
    assert "`## KOID`" in text


@BOTH
def test_cash_and_cad_usd_is_a_theme_and_its_findings_go_under_psu(text):
    assert "PSU-U.TO" in text
    assert "`## PSU-U.TO`" in text
    assert "USD/CAD" in text
    assert "TSX" in text


def test_weekly_asks_for_ledger_ready_findings_in_ticker_sections():
    part4 = WEEKLY.split("### Part 4", 1)[1].split("## AI forward-evidence gate", 1)[0]
    assert "`## TICKER`" in part4
    assert "`## MACRO`" in part4
    assert "dated" in part4.lower()
    assert "source" in part4.lower()
    assert "unverified" in part4.lower()


@BOTH
def test_no_unverified_instrument_descriptions_remain(text):
    assert "private equity proxy" not in text
    assert "HXSCF" not in text
    assert "SanDisk/WDC" not in text
    assert "SKHY" in text and "SPCX" in text


@BOTH
def test_skhy_spcx_and_sandisk_are_described_as_what_they_are(text):
    assert "SK hynix ADR" in text
    assert "public since" in text
    assert "separate company from WDC" in text


def test_the_fund_is_named_correctly_and_not_called_fully_liquidated():
    assert "Spence" not in WEEKLY
    section = WEEKLY.split("SMART MONEY CONTEXT", 1)[1].split("\n", 1)[0]
    assert "Situational Awareness" in section
    assert "most" in section.lower()
    assert "entire" not in section.lower()
    assert "do **not** cite pre-liquidation" in section
