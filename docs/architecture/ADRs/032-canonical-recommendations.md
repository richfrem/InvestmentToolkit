# ADR-032: One current recommendation source for every consumer

Date: 2026-10-04
Status: Implemented in feat/canonical-recommendation; pending review and merge

## Problem

The web app showed conflicting actions for the same holding. Browser allocation
rules, technical regimes, score bands, saved research opinions, and report scripts
could each independently label a holding BUY, ACCUMULATE, TRIM, EXIT, or HOLD.

## Decision

`plugins/portfolio-advisor/scripts/recommendation.py` owns the decision. Its
`recommend_all(db_path)` loader reads the domain database, current stored prices,
selected projection (latest AI_AGENT, otherwise latest available), ownership, and
standing decisions. Evaluated thesis breakers are read beside the selected database.
The existing `py_services/recommendation.py` symlink exposes the same implementation.

`recommend(held, upside_pct, exit_signal)` is the only portfolio-action classifier.
The inherited policy uses a +/-15% upside band: held positions ACCUMULATE, MAINTAIN,
or TRIM; explicit exits take precedence. Unheld positions INITIATE or WATCHLIST;
an explicit exit prevents entry. Targets do not change the recommendation.
This absolute valuation band is distinct from the policy for material changes to
fair value. Standing decisions remain review constraints and gate trade proposals.

`valuation_signal` supplies the separate BUY/HOLD/SELL valuation lens to calculation
scripts. These labels describe valuation and cannot be substituted for the portfolio
action. Unknown current recommendations are unavailable, with no invented fallback.

The backend exposes `GET /api/screener/recommendations`. The React provider shares
one response across mounted pages, refreshing on focus, data-change events, and
once per minute. Consumers display its action verbatim. Stored projection actions
and dated revision history retain their historical meaning.

Daily Brief score totals rank attention only. Cards retain the canonical action;
macro gates, standing decisions, and sizing constraints change `executionStatus`
and `actionable`, rather than inventing another recommendation. The current brief
API rebuilds actions/cards from current domain data without rewriting ledger history.
The rebalancer rejects buy/sell proposals opposing the canonical action.

## Verification

See `../canonical-recommendation-audit.md`. Real SQLite/subprocess tests verify
source selection and consumer agreement. A real HTTP frontend integration test
verifies that mounted consumers share, refresh, and lose availability together.
No live trade or portfolio migration is part of this change.
