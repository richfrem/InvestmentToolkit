"""
Unit tests for tv_thesis_overlay.py
Tests multi-table data resolution from domain_model.sqlite, Pine Script v6 generation,
and pine_linter.py validation.
"""

import os
import pytest
from plugins.tradingview.scripts.tv_thesis_overlay import (
    generate_pine_script_content,
    resolve_ticker_levels,
)
from plugins.tradingview.scripts.pine_linter import PineLinter


@pytest.fixture
def mock_db(tmp_path):
    """Create the real migrated schema and seed repositories, without live data."""
    from investment_screener.backend.py_services.domain_model.db_client import initialize_db
    from investment_screener.backend.py_services.domain_model.investment_repository import resolve_investment, update_investment_fields
    from investment_screener.backend.py_services.domain_model.projection_repository import save_projection_version, add_projection_scenario
    from investment_screener.backend.py_services.domain_model.price_level_repository import replace_price_levels
    db_file = tmp_path / "test_domain_model.sqlite"
    conn = initialize_db(str(db_file))
    nvda = resolve_investment(conn, "NVDA", name="Nvidia")
    update_investment_fields(conn, nvda, thesis_breaker_status="OK")
    for version, fv in ((0, 150.0), (1, 185.0)):
        save_projection_version(conn, nvda, version=version, fair_value=fv, source="AI_AGENT",
                                saved_at=f"2026-10-0{version + 1}T00:00:00Z", action="ACCUMULATE", snapshot_json='{"price":150}')
        for name, weight, price in (("bear", .25, 90.0 if version else 60.0),
                                    ("base", .5, 185.0 if version else 120.0),
                                    ("bull", .25, 300.0 if version else 200.0)):
            add_projection_scenario(conn, f"{nvda}:{version}", name, weight=weight, scenario_price=price)
    replace_price_levels(conn, nvda, None, None, None, None, [], [], {"price":110.0}, 135.5)
    abc = resolve_investment(conn, "ABC", name="No Scenarios Inc")
    update_investment_fields(conn, abc, thesis_breaker_status="OK")
    save_projection_version(conn, abc, version=1, fair_value=10, source="AI_AGENT", saved_at="2026-10-01T00:00:00Z", action="HOLD")
    replace_price_levels(conn, abc, None, None, None, None, [], [], {"price":2.76, "status":"suppressed"}, None)
    conn.close()
    return str(db_file)


def test_resolve_ticker_levels(mock_db):
    levels = resolve_ticker_levels("NVDA", db_path=mock_db)
    assert levels["symbol"] == "NVDA"
    assert levels["fair_value"] == 185.00
    assert levels["target_entry"] == 135.50
    assert levels["stop_loss"] == 110.00
    assert levels["breaker_status"] == "OK"


def test_generate_pine_script_validity(tmp_path):
    levels = {
        "symbol": "NVDA",
        "fair_value": 185.00,
        "target_entry": 135.50,
        "stop_loss": 110.00,
        "action": "ACCUMULATE",
    }
    pine_code = generate_pine_script_content(levels)
    assert "//@version=6" in pine_code
    assert 'indicator("AI Thesis Overlay - NVDA"' in pine_code
    assert "185.0" in pine_code
    assert "135.5" in pine_code
    assert "110.0" in pine_code

    # Verify that the generated Pine Script passes pine_linter.py without errors
    pine_file = tmp_path / "test_overlay.pine"
    pine_file.write_text(pine_code, encoding="utf-8")
    linter = PineLinter(str(pine_file))
    assert linter.lint() is True
    assert len(linter.errors) == 0


def test_resolve_ticker_levels_includes_latest_scenarios(mock_db):
    levels = resolve_ticker_levels("NVDA", db_path=mock_db)
    assert (levels["bear_price"], levels["base_price"], levels["bull_price"]) == (90.00, 185.00, 300.00)


def test_resolve_ticker_levels_without_scenarios_leaves_them_empty(mock_db):
    levels = resolve_ticker_levels("ABC", db_path=mock_db)
    assert levels["fair_value"] == 10.00
    assert (levels["bear_price"], levels["base_price"], levels["bull_price"]) == (None, None, None)


def test_generate_pine_script_draws_scenario_lines(tmp_path):
    levels = {
        "symbol": "NBIS", "fair_value": 262.62, "target_entry": None, "stop_loss": None, "action": "HOLD",
        "bear_price": 41.05, "base_price": 194.96, "bull_price": 619.51,
    }
    pine_code = generate_pine_script_content(levels)
    for var, value in (("bearPrice", "41.05"), ("basePrice", "194.96"), ("bullPrice", "619.51")):
        assert f"var float {var} = input.float({value}" in pine_code
        assert f"if {var} > 0" in pine_code  # a missing scenario (0.0) draws nothing
    assert pine_code.count("line.new(") == 6  # fair value, entry, stop + bear, base, bull
    pine_file = tmp_path / "scenario_overlay.pine"
    pine_file.write_text(pine_code, encoding="utf-8")
    linter = PineLinter(str(pine_file))
    assert linter.lint() is True and not linter.errors


def test_generate_pine_script_missing_scenarios_default_to_zero(tmp_path):
    pine_code = generate_pine_script_content({"symbol": "ABC", "fair_value": 10.0})
    for var in ("bearPrice", "basePrice", "bullPrice"):
        assert f"var float {var} = input.float(0.0" in pine_code


def test_resolve_ticker_levels_ignores_suppressed_stop(mock_db):
    levels = resolve_ticker_levels("ABC", db_path=mock_db)
    assert levels["stop_loss"] is None


def test_apply_overlay_injects_once_without_retry_or_stale_cache(mock_db, monkeypatch):
    # 2026-09-28: pine inject mutates the chart (edit, save, add), but ran through
    # tv_call's defaults: 10s timeout, 3 retries and a cached-response fallback.
    # The inject outlived 10s, was retried, and a stale cached refusal was
    # reported as the current result.
    import tv_thesis_overlay as m
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append((args, kwargs))
        if args[:2] == ("pine", "inject"):
            return {"success": True, "verified": True, "study": "AI Thesis Overlay - NVDA"}
        return {"success": True}

    monkeypatch.setattr(m, "tv_call", fake_tv_call)
    monkeypatch.setattr(m, "validate_cdp_installation", lambda: {"installed": True})
    monkeypatch.setattr(m, "switch_chart_symbol", lambda s: True)
    monkeypatch.setattr(m.resolve_ticker_levels, "__defaults__", (mock_db,))

    result = m.apply_overlay("NVDA")

    inject_kwargs = [kw for a, kw in calls if a[:2] == ("pine", "inject")][0]
    assert inject_kwargs.get("enable_retry") is False
    assert inject_kwargs.get("enable_cache_fallback") is False
    assert inject_kwargs.get("timeout", 10) >= 45
    assert result["success"] is True


def test_apply_overlay_reports_failure_for_cached_inject_response(mock_db, monkeypatch):
    import tv_thesis_overlay as m
    monkeypatch.setattr(m, "tv_call", lambda *a, **k: (
        {"error": "timed out", "data": {"success": True}, "cached": True, "timestamp": "x"}
        if a[:2] == ("pine", "inject") else {"success": True}))
    monkeypatch.setattr(m, "validate_cdp_installation", lambda: {"installed": True})
    monkeypatch.setattr(m, "switch_chart_symbol", lambda s: True)
    monkeypatch.setattr(m.resolve_ticker_levels, "__defaults__", (mock_db,))

    assert m.apply_overlay("NVDA")["success"] is False
