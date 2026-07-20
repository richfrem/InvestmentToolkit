"""Dry-run + real migration of target-portfolio.json/watchlist.json/
tradingview_alerts_actual.json/thesis_breaker_state.json into the v3.2 domain model.

Non-negotiable per this migration's global constraints: --write must never run
without a --dry-run report first being reviewed and explicitly approved by the
user (tied to a real data-loss incident from before this corrective effort began).

Real confirmed shapes (re-read directly against the real files during Wave 2
Task 6, not assumed from the spec):
- target-portfolio.json: top-level {id, name, schemaVersion, version, createdAt,
  updatedAt, description, pillars, holdings, globalSettings, changeLog}.
  holdings[].keys ever seen: ticker, name, pillarId, targetWeight, role,
  subStrategyId, thesisForInclusion, agentRationale, shares, action,
  priceLevels, standingDecision (type/reason/source/review), targetEntryPrice.
- watchlist.json: {"watchlist": [{"ticker", "addedAt"}, ...]} -- NOT a flat
  list (an earlier assumption in this plan's fixtures was wrong; corrected here).
- tradingview_alerts_actual.json: flat list of
  {alert_id, symbol (e.g. "NASDAQ:IREN"), type, message, active, price,
  condition, resolution, created, last_fired, expiration}.
- thesis_breaker_state.json: {"generatedAt": ..., "holdings": {ticker: status}}.
"""

import argparse
import json

from domain_model.db_client import initialize_db
from domain_model.investment_repository import (
    resolve_investment,
    update_investment_fields,
    get_investment,
)
from domain_model.pillar_repository import resolve_pillar, resolve_sub_strategy
from domain_model.price_level_repository import replace_price_levels
from domain_model.investment_note_repository import list_notes, add_note
from domain_model.alert_repository import upsert_alert


def _load(path: str):
    with open(path) as f:
        return json.load(f)


def _strip_exchange_prefix(symbol: str) -> str:
    """TradingView alert symbols are exchange-qualified (e.g. "NASDAQ:IREN").
    The domain model's investment.symbol is the bare ticker."""
    return symbol.split(":", 1)[-1] if symbol else symbol


def build_dry_run_report(
    target_portfolio_path: str,
    watchlist_path: str,
    alerts_path: str,
    breaker_state_path: str,
) -> dict:
    target = _load(target_portfolio_path)
    watchlist_doc = _load(watchlist_path)
    alerts = _load(alerts_path)
    breaker_state = _load(breaker_state_path)

    watchlist = watchlist_doc.get("watchlist", []) if isinstance(watchlist_doc, dict) else watchlist_doc

    holdings = target.get("holdings", [])
    pillars = target.get("pillars", [])
    warnings = []
    holdings_with_price_levels = 0
    holdings_with_agent_rationale = 0
    holdings_with_target_entry = 0
    holdings_with_standing_decision = 0

    for i, holding in enumerate(holdings):
        ticker = holding.get("ticker")
        if not ticker:
            warnings.append(f"holdings[{i}]: missing ticker field")
            continue
        if holding.get("priceLevels"):
            holdings_with_price_levels += 1
        if holding.get("agentRationale"):
            holdings_with_agent_rationale += 1
        if holding.get("targetEntryPrice") is not None:
            holdings_with_target_entry += 1
        if holding.get("standingDecision"):
            holdings_with_standing_decision += 1

    breaker_holdings = breaker_state.get("holdings", {}) if isinstance(breaker_state, dict) else {}

    return {
        "holdings_count": len(holdings),
        "pillars_count": len(pillars),
        "watchlist_count": len(watchlist) if isinstance(watchlist, list) else 0,
        "alerts_count": len(alerts) if isinstance(alerts, list) else 0,
        "holdings_with_price_levels": holdings_with_price_levels,
        "holdings_with_agent_rationale": holdings_with_agent_rationale,
        "holdings_with_target_entry": holdings_with_target_entry,
        "holdings_with_standing_decision": holdings_with_standing_decision,
        "thesis_breaker_holdings_count": len(breaker_holdings),
        "warnings": warnings,
    }


def execute_migration(
    conn,
    target_portfolio_path: str,
    watchlist_path: str,
    alerts_path: str,
    breaker_state_path: str,
) -> dict:
    target = _load(target_portfolio_path)
    watchlist_doc = _load(watchlist_path)
    alerts = _load(alerts_path)
    breaker_state = _load(breaker_state_path)

    watchlist = watchlist_doc.get("watchlist", []) if isinstance(watchlist_doc, dict) else watchlist_doc

    for pillar in target.get("pillars", []):
        resolve_pillar(conn, pillar["id"], pillar["name"], pillar.get("targetWeight"))

    watchlist_tickers = {
        item["ticker"] for item in watchlist if isinstance(item, dict) and item.get("ticker")
    }
    watchlist_added_at = {
        item["ticker"]: item.get("addedAt")
        for item in watchlist if isinstance(item, dict) and item.get("ticker")
    }

    # target-portfolio.json's holdings reference subStrategyId inline but the file
    # carries no separate subStrategies definition array (unlike pillars) -- real
    # data confirmed during Wave 2 Task 6. Auto-create a minimal sub_strategy row
    # (placeholder name = the id itself) the first time each id is seen, scoped to
    # that holding's own pillar, so the investment.sub_strategy_id FK can resolve.
    known_sub_strategies: set[str] = set()

    investments_updated = 0
    for holding in target.get("holdings", []):
        ticker = holding.get("ticker")
        if not ticker:
            continue
        investment_id = resolve_investment(
            conn, ticker, asset_class="EQUITY", currency="USD", name=holding.get("name"),
        )

        sub_strategy_id = holding.get("subStrategyId")
        if sub_strategy_id and sub_strategy_id not in known_sub_strategies:
            resolve_sub_strategy(
                conn, sub_strategy_id, holding.get("pillarId"), sub_strategy_id,
            )
            known_sub_strategies.add(sub_strategy_id)

        standing = holding.get("standingDecision") or {}
        fields = {
            "lifecycle_status": holding.get("role"),
            "target_weight": holding.get("targetWeight"),
            "target_action": holding.get("action"),
            "standing_decision_type": standing.get("type"),
            "standing_decision_reason": standing.get("reason"),
            "standing_decision_source": standing.get("source"),
            "standing_decision_review": standing.get("review"),
            "pillar_id": holding.get("pillarId"),
            "sub_strategy_id": holding.get("subStrategyId"),
            "thesis_for_inclusion": holding.get("thesisForInclusion"),
            "agent_rationale": holding.get("agentRationale"),
            "is_watchlisted": ticker in watchlist_tickers,
            "watchlist_added_at": watchlist_added_at.get(ticker),
        }
        fields = {k: v for k, v in fields.items() if v is not None}
        update_investment_fields(conn, investment_id, **fields)
        investments_updated += 1

        price_levels = holding.get("priceLevels")
        target_entry = holding.get("targetEntryPrice")
        if price_levels or target_entry is not None:
            pl = price_levels or {}
            replace_price_levels(
                conn, investment_id,
                schema_version=pl.get("schemaVersion"), last_updated=pl.get("lastUpdated"),
                last_updated_by=pl.get("lastUpdatedBy"), note=pl.get("note"),
                buy_tiers=pl.get("buyTiers", []), sell_tiers=pl.get("sellTiers", []),
                stop_loss=pl.get("stopLoss"), target_entry_price=target_entry,
            )

        rationale = holding.get("agentRationale")
        if rationale:
            existing_notes = list_notes(conn, investment_id)
            already_migrated = any(
                n["body"] == rationale and n["note_type"] == "MIGRATED_LEGACY_RATIONALE"
                for n in existing_notes
            )
            if not already_migrated:
                add_note(
                    conn, investment_id,
                    note_date=target.get("updatedAt") or "2026-07-19T00:00:00Z",
                    body=rationale, note_type="MIGRATED_LEGACY_RATIONALE",
                    source="target-portfolio.json migration (Wave 2)",
                )

    holdings_tickers = {h.get("ticker") for h in target.get("holdings", []) if h.get("ticker")}
    watchlist_only_added = 0
    for ticker in watchlist_tickers - holdings_tickers:
        investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")
        update_investment_fields(
            conn, investment_id, is_watchlisted=True,
            watchlist_added_at=watchlist_added_at.get(ticker),
        )
        watchlist_only_added += 1

    alerts_migrated = 0
    for alert_entry in alerts:
        raw_symbol = alert_entry.get("symbol")
        ticker = _strip_exchange_prefix(raw_symbol) if raw_symbol else None
        investment_id = None
        if ticker:
            investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")
        upsert_alert(
            conn,
            alert_id=str(alert_entry.get("alert_id")),
            investment_id=investment_id,
            alert_type=alert_entry.get("type"),
            message=alert_entry.get("message"),
            price=alert_entry.get("price"),
            condition_json=json.dumps(alert_entry.get("condition")) if alert_entry.get("condition") else None,
            active=bool(alert_entry.get("active", True)),
            resolution=alert_entry.get("resolution"),
            created_at=alert_entry.get("created"),
            last_fired_at=alert_entry.get("last_fired"),
            expiration_at=alert_entry.get("expiration"),
            synced_at="2026-07-19T00:00:00Z",
        )
        alerts_migrated += 1

    breaker_holdings = breaker_state.get("holdings", {}) if isinstance(breaker_state, dict) else {}
    breaker_updates = 0
    for ticker, status in breaker_holdings.items():
        existing = get_investment(conn, ticker)
        if existing:
            update_investment_fields(conn, ticker, thesis_breaker_status=status)
            breaker_updates += 1

    return {
        "investments_updated": investments_updated,
        "pillars_updated": len(target.get("pillars", [])),
        "watchlist_only_tickers_added": watchlist_only_added,
        "alerts_migrated": alerts_migrated,
        "thesis_breaker_updates": breaker_updates,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-portfolio",
                         default="investment_screener/backend/data/theses/target-portfolio.json")
    parser.add_argument("--watchlist",
                         default="investment_screener/backend/data/watchlist.json")
    parser.add_argument("--alerts",
                         default="investment_screener/backend/data/tradingview_alerts_actual.json")
    parser.add_argument("--breaker-state",
                         default="investment_screener/backend/data/thesis_breaker_state.json")
    parser.add_argument("--db-path",
                         default="investment_screener/backend/data/domain_model.sqlite")
    parser.add_argument("--write", action="store_true",
                         help="Perform the real migration. Requires reviewing a --dry-run "
                              "report first -- never run this without explicit user sign-off.")
    args = parser.parse_args()

    report = build_dry_run_report(
        args.target_portfolio, args.watchlist, args.alerts, args.breaker_state
    )
    print(json.dumps(report, indent=2))

    if args.write:
        conn = initialize_db(args.db_path)
        summary = execute_migration(
            conn, args.target_portfolio, args.watchlist, args.alerts, args.breaker_state
        )
        print("--- WRITE SUMMARY ---")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
