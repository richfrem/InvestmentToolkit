# Design Spec: Unified Market Data Layer (`market_data.py`)

**Date:** 2026-07-02
**Status:** [DRAFT]
**Topic:** Phase 1 of the Fable5 Elevation Guide — provider-abstracted, cached, quality-gated data layer to replace 13 files' direct yfinance imports.

## 1. Problem Statement

`yfinance` is called directly from 13 files across the codebase (`fetch_financials.py`, `portfolio_performance.py`, `macro_regime.py`, `earnings_calendar.py`, `fetch_quotes.py`, `overnight_gaps.py`, `fetch_portfolio_heatmap.py`, `history_store.py`, ETF/TV scripts, and one TS-adjacent file) with no shared caching, no data-quality checks, and no fallback when it drifts or returns incomplete data.

Two real bugs from the 2026-07-02 session are direct instances of this fragility:
- `standardize_metrics.py` silently reported a 43.7%-margin company as 0% profitable because raw `fetch_financials.py` output omitted a `net_income` key for that ticker.
- `portfolio_performance.py`'s `safe_float(NaN) -> 0.0` zeroed out a position's full value on a foreign-exchange holiday gap, producing an impossible +29.79% single-day return.

Both bugs share a root pattern: **missing/inconsistent data from an unabstracted, unvalidated single provider silently became a wrong number instead of a flagged gap.** This design closes that gap system-wide, and adds SEC EDGAR as a second, point-in-time-correct fundamentals source.

## 2. Proposed Architecture

```
py_services/market_data.py          ← single public interface, 4 functions
    ├── get_prices(tickers, period, interval)   → OHLCV, cached, yfinance-backed
    ├── get_quote(tickers)                       → live price, TV CDP (active chart only) → yfinance fallback
    ├── get_estimates(ticker)                     → analyst forward estimates, cached, yfinance-backed
    └── get_fundamentals(ticker)                  → REAL waterfall: EDGAR primary + yfinance supplement
            ↓ (internal, not exposed as public API)
    edgar_facts.py    — SEC XBRL companyfacts client, point-in-time filing data
    cache.py          — data/cache/ (gitignored), TTL by data class
    data_quality.py   — staleness / unit-sanity / cross-source-disagreement checks
```

Only `get_fundamentals()` has a real multi-provider waterfall (EDGAR has no prices, quotes, or forward estimates — those functions are thin, cached, quality-gated wrappers around their one real source). Every returned field is source-tagged: `{"value": X, "source": "edgar"|"yfinance"|"tv_cdp"|"cache", "asOf": "<date>"}` — this extends the `totalSource` pattern (`tv_authoritative`/`computed_fallback`) already shipped tonight in `portfolioSnapshot.ts` to the data layer.

## 3. Components

- **`market_data.py`** — thin orchestration only, no fetch logic inline. Interface + failing tests written first (owner: primary implementer, no delegation — this is the seam every other module depends on).
- **`edgar_facts.py`** — isolated SEC EDGAR client. Declared User-Agent, ≤10 req/s, parses `companyfacts` XBRL JSON (`data.sec.gov/api/xbrl/companyfacts/CIK{...}.json`) into the normalized shape `market_data.py` expects. Uses `requests` (already pinned in `requirements.txt` — no new dependency, no `pip-compile` needed). Self-contained; testable with recorded fixture responses, no live network in tests. **Delegation candidate** (well-bounded, isolated).
- **`cache.py`** — keyed by `(function, args, data_class)`, JSON on disk under `data/cache/` (gitignored). TTL by class: quotes 15min, daily OHLCV 24h (append-only history), fundamentals 24h, EDGAR facts 7d. `--no-cache` flag bypasses. **Delegation candidate.**
- **`data_quality.py`** — staleness (last quarterly datapoint >120d → warn), unit sanity (revenue magnitude vs market cap), cross-source disagreement (EDGAR vs yfinance >5% on same TTM figure → `dataConflicts` block, never silently pick one), null-critical-field detection. Gates every `get_fundamentals()` call. **Delegation candidate, reviewed carefully** — this is the module most directly preventing tonight's bug class.
- **`schemas/market_data_response.schema.json`** — derived from the locked interface contract below. **Delegation candidate.**

## 4. Data Contract (locked before any delegated work starts)

```python
# market_data.py public interface

def get_prices(tickers: list[str], period: str, interval: str = "1d") -> dict:
    """Returns {ticker: {"data": DataFrame-like OHLCV, "source": "yfinance", "asOf": iso_date}}"""

def get_quote(tickers: list[str]) -> dict:
    """Returns {ticker: {"price": float, "source": "tv_cdp"|"yfinance", "asOf": iso_timestamp}}
    tv_cdp only ever returns the ACTIVE CHART ticker (documented pitfall #7) — batch quote
    requests via CDP raise ValueError immediately, never silently return wrong-ticker data."""

def get_estimates(ticker: str) -> dict:
    """Returns {"y1RevEstimate": float, "y2RevEstimate": float, ..., "source": "yfinance", "asOf": iso_date}"""

def get_fundamentals(ticker: str) -> dict:
    """Returns {
        "revenue": {"value": float, "source": "edgar"|"yfinance", "asOf": filing_or_fetch_date},
        "netIncome": {...}, "operatingIncome": {...}, "ocf": {...}, "capex": {...},
        "sbc": {...}, "sharesOutstanding": {...}, "debt": {...}, "cash": {...},
        "dataQuality": {"staleness": ..., "dataConflicts": [...], "flags": [...]}
    }
    Never returns a zeroed/defaulted value for a missing field — missing means the field
    is absent from the dict, not present-and-wrong. Callers must handle absence explicitly."""
```

## 5. Data Flow — `get_fundamentals()` (the case that matters)

1. Check cache (24h TTL) → return if fresh.
2. Fetch EDGAR companyfacts (revenue, operating income, OCF, capex, SBC, shares, debt, cash) with the actual filing date per field.
3. Fetch yfinance (price/forward estimates — EDGAR has neither) + trailing fundamentals as cross-check.
4. Run `data_quality.py`: compare EDGAR vs yfinance TTM figures per metric; >5% disagreement → attach to `dataConflicts`, do not silently prefer one.
5. Merge: EDGAR wins for anything it has (point-in-time correct, US filers only). yfinance fills gaps (non-US listings — ASML, TSX names — EDGAR has no coverage).
6. Write to cache, return.

## 6. Error Handling

- EDGAR unavailable or non-US ticker → fall back to yfinance-only, every field marked `source: "yfinance"`, no silent gap.
- yfinance also fails → raise, never return partial/zeroed data. (Direct fix for the `safe_float`/NaN-to-zero anti-pattern — see `.agent/rules/no-silent-nan-to-zero.md`, written earlier tonight.)
- Quality-gate flags attach to the response and never block it — the calling script/agent decides whether to proceed, matching the existing "surface the conflict, don't auto-resolve" philosophy (confluence gate, standing decisions, `preserveAuthoritativeTotal`).

## 7. Testing

- `market_data.py` — pure-function tests against fixture provider responses (no live network). This is the interface contract all other modules (including delegated ones) build against.
- `edgar_facts.py` — recorded fixture XBRL responses (1–2 real companies, frozen), parser tests.
- `data_quality.py` — property tests: staleness threshold boundary, disagreement threshold boundary, golden clean-data case produces zero flags.
- Migration acceptance: every one of the 13 yfinance-importing files is migrated to call `market_data.py` instead of importing `yfinance` directly. Verified via `grep -rl "^import yfinance\|^from yfinance"` returning empty outside `market_data.py`/`edgar_facts.py`.

## 8. Delegation Plan

Primary implementer (no delegation): `market_data.py` interface + tests, migration of the 13 call sites, final integration review of all delegated modules before merge.

Haiku sub-agent candidates (dispatched via the Agent tool, reviewed against the locked contract above before integration): `edgar_facts.py`, `cache.py`, `schemas/market_data_response.schema.json`. `data_quality.py` is a delegation candidate but requires careful review given it's the module most directly responsible for preventing tonight's bug class — implementation may be delegated, but its test suite and threshold values are written/verified by the primary implementer first.

## 9. Success Criteria

1. All 13 files use `market_data.py`; zero direct `yfinance` imports outside it and `edgar_facts.py`.
2. `fetch_financials.py NVDA` output shows source-tagged fields with EDGAR preferred for US filers.
3. A full `/daily` dry-run works from cache with no network calls (offline capability, `--no-cache` toggles this off deliberately).
4. One deliberately corrupt/NaN-gap fixture trips the data-quality gate and does not silently zero a value (regression test for tonight's exact bug).
5. `run_tests.py` T1 tier (pure-math modules, no network, <60s) is green and required before every commit touching this layer.
