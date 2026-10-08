"""Integration contract: action consumers agree despite conflicting targets and TA.

Layer: Tests. Uses real SQLite repositories and the real symlinked CLI.
Key functions: seed_domain, test_daily_actions, test_relabel_cli, test_records_cli.
Key input dependencies: isolated domain/intelligence databases, Python CLI.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db
from domain_model.account_repository import upsert_account
from domain_model.account_investment_repository import upsert_account_investment
from domain_model.investment_price_repository import upsert_investment_price
from domain_model.investment_repository import resolve_investment, update_investment_fields
from domain_model.projection_repository import add_projection_scenario, save_projection_version
from recommendation import recommend_all


def seed_domain(tmp_path):
    """Seed opposite target and valuation signals, plus an unheld buy."""
    db = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db))
    upsert_account(conn, "tfsa", "TFSA", "TFSA")
    for ticker, shares, fv, target in (("BE", 10, 50, 90), ("SHAZ", 10, 150, 0), ("INTC", 0, 150, 0)):
        inv = resolve_investment(conn, ticker)
        update_investment_fields(conn, inv, target_weight=target)
        upsert_investment_price(conn, inv, 100, "USD", "2026-10-04T00:00:00Z")
        upsert_account_investment(conn, "tfsa", inv, shares, None, None, "USD", "2026-10-04T00:00:00Z")
        save_projection_version(conn, inv, version=1, saved_at="2026-10-04T00:00:00Z",
                                fair_value=fv, action="MAINTAIN", source="AI_AGENT", snapshot_json='{"price":100}')
    conn.close()
    return db


def test_daily_actions_ignore_score_and_targets(tmp_path):
    from compute_conviction_scores import compute_all
    db = seed_domain(tmp_path)
    records = recommend_all(str(db))
    scores = compute_all(db_path=str(tmp_path / "missing-intelligence.sqlite"), domain_db_path=str(db))
    assert {s.ticker: s.band for s in scores} == {t: r["action"] for t, r in records.items()}
    assert {s.ticker: s.dcf_action for s in scores} == {t: r["valuation"] for t, r in records.items()}


def test_relabel_cli_delegates_without_target_override(tmp_path):
    db = seed_domain(tmp_path)
    recs = tmp_path / "recs.json"
    recs.write_text(json.dumps({"holdings": [{"ticker": "BE", "action": "ACCUMULATE", "recommendedTarget": 90}]}))
    result = subprocess.run([sys.executable, str(ROOT / "plugins/portfolio-advisor/scripts/relabel_actions.py"),
                             "--recs", str(recs), "--db", str(db)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(recs.read_text())["holdings"][0]["action"] == "TRIM"


def test_records_cli_via_bridge_symlink(tmp_path):
    db = seed_domain(tmp_path)
    result = subprocess.run([sys.executable, str(ROOT / "investment_screener/backend/py_services/recommendation.py"),
                             "--all", "--db", str(db)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    records = json.loads(result.stdout)
    assert records["BE"]["action"] == "TRIM"
    assert records["SHAZ"]["action"] == "ACCUMULATE"
    assert records["INTC"]["action"] == "INITIATE"
    assert records["BE"]["current_weight_pct"] == 50


def test_web_recommendation_surfaces_share_one_snapshot():
    """Caller contract: these current-action surfaces use the shared API snapshot."""
    files = ["components/AIThesisSummary.tsx", "components/AIAnalysisModal.tsx",
             "components/ValuationModeler.tsx", "components/ScreenerTable.tsx",
             "components/PortfolioTable.tsx", "components/TechnicalAnalysisSummaryCard.tsx",
             "components/LatestReviewModal.tsx", "pages/Dashboard.tsx", "pages/DailyBriefPage.tsx"]
    for file in files:
        text = (ROOT / "investment_screener/frontend/src" / file).read_text()
        assert "useRecommendations" in text, f"{file} must consume the shared snapshot"


def test_brief_card_keeps_canonical_action_when_trade_is_blocked():
    from brief_recommendations import build_recommendations
    scores = [{"ticker": "BE", "band": "TRIM", "total": -2, "actual_weight": 5,
               "target_weight": 10, "weight_gap": 5}]
    cards = build_recommendations(scores, {}, [], {"regime": "RISK-ON"}, 10000)
    assert cards[0]["recommendation"] == "TRIM"
    assert cards[0]["proposedTrade"] is None
    assert not cards[0]["actionable"]


def test_unheld_initiate_survives_macro_gate():
    from brief_recommendations import build_recommendations
    scores = [{"ticker": "INTC", "band": "INITIATE", "total": 4, "actual_weight": 0,
               "target_weight": 5, "weight_gap": 5}]
    cards = build_recommendations(scores, {}, [], {"regime": "RISK-OFF"}, 10000)
    assert cards[0]["recommendation"] == "INITIATE"
    assert cards[0]["executionStatus"] == "QUEUED"
    assert not cards[0]["actionable"]


def test_ta_sweep_uses_canonical_action_even_when_oversold(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "plugins/tradingview/scripts"))
    import ta_sweep_batch
    db = seed_domain(tmp_path)
    monkeypatch.setattr(ta_sweep_batch, "DB_PATH", db)
    assert ta_sweep_batch.derive_action({"ticker": "BE", "flags": ["RSI_OS", "ACCUM_SIGNAL"]}, None) == "TRIM"


def test_catalyst_valuation_band_matches_canonical():
    import apply_catalyst
    from recommendation import valuation_signal
    for upside in (-16, -10, 0, 10, 16):
        assert apply_catalyst._derive_action(upside) == valuation_signal(upside)


def test_live_brief_overlays_saved_conflicting_action(tmp_path):
    from brief_recommendations import align_current_brief
    db = seed_domain(tmp_path)
    old = {"macro_regime": {"regime": "RISK-ON"}, "conviction_scores": [
        {"ticker": "BE", "total": 4, "band": "ACCUMULATE", "actual_weight": 1, "weight_gap": 89}],
        "recommendations": [{"ticker": "BE", "recommendation": "BUY"}]}
    current = align_current_brief(old, str(db))
    assert current["conviction_scores"][0]["band"] == "TRIM"
    assert current["recommendations"][0]["recommendation"] == "TRIM"
    assert current["recommendations"][0]["proposedTrade"] is None
    assert old["conviction_scores"][0]["band"] == "ACCUMULATE"


def test_unheld_uses_current_price_even_without_account_row(tmp_path):
    db = seed_domain(tmp_path)
    conn = initialize_db(str(db))
    inv = resolve_investment(conn, "NEW")
    upsert_investment_price(conn, inv, 200, "USD", "2026-10-04T00:00:00Z")
    save_projection_version(conn, inv, version=1, saved_at="2026-10-04T00:00:00Z", fair_value=150,
                            action="BUY", source="AI_AGENT", snapshot_json='{"price":100}')
    conn.close()
    rec = recommend_all(str(db))["NEW"]
    assert rec["price"] == 200
    assert rec["action"] == "WATCHLIST"


def test_breaker_and_standing_decision_use_the_supplied_database_directory(tmp_path):
    db = seed_domain(tmp_path)
    (tmp_path / "thesis_breaker_state.json").write_text(json.dumps({"holdings": {"SHAZ": {"risk": {"status": "TRIGGERED"}}}}))
    conn = initialize_db(str(db))
    inv = resolve_investment(conn, "SHAZ")
    update_investment_fields(conn, inv, standing_decision_type="HOLD", standing_decision_reason="Review catalyst first")
    conn.close()
    rec = recommend_all(str(db))["SHAZ"]
    assert rec["action"] == "EXIT"
    assert rec["standing_decision"]["reason"] == "Review catalyst first"


def test_compatibility_shim_cannot_override_source_data(tmp_path):
    from portfolio_action import derive_action
    db = seed_domain(tmp_path)
    assert derive_action("BE", 0, target_pct=99, ai_upside=90, db_path=str(db)) == "TRIM"
    assert derive_action("MISSING", 10, target_pct=0, db_path=str(db)) == "UNAVAILABLE"


def test_rebalancer_does_not_propose_a_trade_against_canonical_action(tmp_path):
    from rebalancer import compute_candidate_orders
    db = seed_domain(tmp_path)
    bands = {"BE": {"inBand": False, "driftPct": -40, "currentWeight": 50, "targetWeight": 90},
             "SHAZ": {"inBand": False, "driftPct": 50, "currentWeight": 50, "targetWeight": 0}}
    orders, skipped = compute_candidate_orders(bands, {"holdings": []}, {"BE": 100, "SHAZ": 100}, 2000, db)
    assert orders == []
    assert {s["ticker"] for s in skipped} == {"BE", "SHAZ"}


def test_generated_thesis_overlay_uses_canonical_action(tmp_path):
    from plugins.tradingview.scripts.tv_thesis_overlay import resolve_ticker_levels
    db = seed_domain(tmp_path)
    assert resolve_ticker_levels("BE", str(db))["action"] == "TRIM"


def test_recommendation_weights_include_uninvested_cash(tmp_path):
    db = seed_domain(tmp_path)
    conn = initialize_db(str(db))
    cash = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
    upsert_investment_price(conn, cash, 1.0, "USD", "2026-10-04T00:00:00Z")
    upsert_account_investment(conn, "tfsa", cash, 2000, None, None, "USD", "2026-10-04T00:00:00Z")
    conn.close()
    assert recommend_all(str(db))["BE"]["current_weight_pct"] == 25.0


def test_records_carry_risk_reward_and_support_from_saved_scenarios(tmp_path):
    """Every page reads reward:risk, the reduce flag and valuation support from one record."""
    db = seed_domain(tmp_path)
    conn = initialize_db(str(db))
    inv = resolve_investment(conn, "BE")
    audit = json.dumps({"valuationModel": {"method": "annual_fcff", "discountRateAudit": {"rateType": "WACC"}}})
    projection = save_projection_version(conn, inv, version=2, saved_at="2026-10-05T00:00:00Z", fair_value=50,
                                         action="MAINTAIN", source="AI_AGENT", snapshot_json='{"price":100}',
                                         analytics_log_json=audit)
    for name, weight, price in (("bear", 0.2, 10), ("base", 0.5, 45), ("bull", 0.3, 85)):
        add_projection_scenario(conn, projection, name, weight=weight, scenario_price=price)
    conn.close()
    records = recommend_all(str(db))
    be = records["BE"]
    assert be["action"] == "TRIM"
    assert be["scenarios"] == {"bear": 10, "base": 45, "bull": 85}
    assert be["risk_reward"]["verdict"] == "UNFAVOURABLE"
    assert be["risk_reward"]["reward_risk"] == 0
    assert be["risk_reward"]["loss_odds_pct"] == 100
    assert be["risk_reward"]["reduce_candidate"] is True
    assert be["risk_reward"]["weight_gap_pp"] == -40
    assert be["risk_reward"]["alignment"]["status"] == "ALIGNED"
    assert be["support"]["checks"][2] == {"id": "rate_audit", "label": "Audited discount rate", "ok": True, "note": "Rate audit saved"}
    shaz = records["SHAZ"]
    assert shaz["risk_reward"]["verdict"] == "UNRATED"  # fair value without scenarios is not rated
    assert shaz["risk_reward"]["reduce_candidate"] is False
    assert shaz["support"]["level"] in ("WEAK", "PARTIAL")
