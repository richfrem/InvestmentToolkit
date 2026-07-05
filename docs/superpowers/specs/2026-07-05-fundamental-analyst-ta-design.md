# Phase 2b — Fundamental Analyst + Local TA Engine (Design)

_Date: 2026-07-05_
_Status: Approved (pending final read-through)_
_Follows: Phase 2a (Valuation Committee, `docs/architecture/ADR-valuation-committee.md`)_
_Source: `temp/bundles/full-bundle/reviews/fable5-ELEVATION_GUIDE.md` §3 (Workstream B: B1, B3) and §4 (Workstream C: C1)_

## Goal

Make the `defininitive_professional_investment_framework.md` scoring system executable
(B1), automate peer benchmarking against it (B3), and give the toolkit an independent,
headless local TA engine that cross-validates against the TradingView Data Window
scrape (C1). All three are informational/advisory — none of them gate `aiThesis.action`;
the existing 2-of-3 `check_accumulate_gate()` from Phase 2a is unchanged.

## Scope

One spec, one plan, one `subagent-driven-development` pass — mirroring how Phase 2a
bundled 5 scripts into a single phase. Three new scripts + one wiring change:

```
investment_screener/backend/py_services/
├── framework_score.py   (B1) — sector-aware weighted composite score
├── peer_bench.py        (B3) — peer benchmarking table (Z-scores/percentiles)
└── technicals.py        (C1) — local TA engine (RSI/EMA/MACD/ADX/ATR/squeeze/VWAP/RS)

plugins/tradingview/scripts/ta_sweep_batch.py  — new --validate mode (local vs TV Data Window)
```

Plus a small, necessary extension to the existing data layer (not a new architectural
decision — same pattern as Phase 2a's `totalDebt`/`cashAndEquivalents`/`interestExpense`
additions):

```
investment_screener/backend/py_services/market_data.py
  _YF_ONLY_FUNDAMENTALS_FIELDS += {"ebitda": "ebitda", "currentRatio": "currentRatio"}
```

Both are yfinance-only (`.info["ebitda"]`, `.info["currentRatio"]`), no EDGAR tag mapping
in this pass, consistent with the existing scope boundary comment in `market_data.py`.

## B1 — `framework_score.py`

### CLI

```bash
python3 framework_score.py --ticker TICKER \
  --sector {saas_cyber,chips_ai,energy_infra} \
  --projections-dir DIR \
  [--qualitative-file FILE] \
  --pretty
```

### Sector field

`sector` becomes a new top-level, agent-supplied field on `projections/{TICKER}.json`,
the same pattern as `peers` (seeded once during `/evaluate-stock`, consumed forever).
`validate_projection.py` gains an optional-field check: if present, must be one of the
three enum values. Old projections without it are unaffected (framework score simply
isn't computed until the agent sets it).

### Metric sourcing (all via `market_data.py` — zero new direct API calls)

| Metric | Source | Basis |
|---|---|---|
| Revenue Growth | `get_estimates()` | **Forward** analyst-estimate CAGR (2025–2028), matching the doc's stated >20% target band — same growth basis `dcf_scenarios.py` already uses |
| Rule of 40 | `get_estimates()` + `get_fundamentals()` | **Method A** (fwd growth + FCF margin) for `saas_cyber` and `energy_infra`; **Method B** (3yr historical CAGR + EBITDA margin) for `chips_ai` — the doc's only explicit method↔sector pairing; Method A is treated as the default "industry standard" for the sector the doc doesn't name |
| Operating Margin | `get_fundamentals()` (`operatingIncome`, EDGAR-only) | operatingIncome / revenue |
| ROIC | `get_fundamentals()` | NOPAT / invested capital, 21% default tax rate (matches doc) |
| Valuation Score | `get_fundamentals()` + `get_quote()` | **EV/Sales only** — matches `comps_valuation.py`'s existing cross-check multiple; PEG dropped (no forward EPS-growth source in the data layer) |
| FCF Yield | `get_fundamentals()` | SBC-adjusted FCF / market cap |
| Balance Sheet Score | `get_fundamentals()` | **Average of all three**: Debt/EBITDA + Interest Coverage + Current Ratio scores (the new `ebitda`/`currentRatio` fields above) |
| Competitive Moat | `--qualitative-file` | agent-supplied `high\|medium\|low` |
| News Impact | `--qualitative-file` | agent-supplied `positive\|neutral\|negative` |

**Supplementary, computed but NOT in the composite** (the doc defines scoring bands for
these in Phase 1 §H but never assigns them a composite weight — verified directly against
the doc's own §5 formula, which sums to exactly 1.00 without them): NDR, GRR, Churn Rate,
Average Contract Length, ROIIC. Reported in the output for context; excluded from
`composite`.

### Composite formula (unchanged from the doc)

```
composite = 0.25×RevGrowth + 0.20×Ro40 + 0.15×OpMargin + 0.10×ROIC
          + 0.10×Valuation + 0.10×FCFYield + 0.05×BalanceSheet
          + 0.05×Moat + 0.05×NewsImpact
```

### Missing-data reweighting

Any metric that is `null` (no data, or a qualitative field absent from
`--qualitative-file`) is excluded and its weight is redistributed proportionally across
the remaining present metrics, renormalizing to 1.0 — **never guessed, never
zero-filled**. Output carries `excludedMetrics: [...]` and `reweighted: bool` so this is
always visible, not silent.

### Score bands

Per-metric scoring uses the doc's 90/60/30 bands, sector-specific where the doc
specifies (Rule of 40, Debt/EBITDA, EV/Sales). **Every top-band boundary is inclusive**
(`>=` not `>`) — e.g. Rule of 40 = exactly 40.0 for SaaS scores 90, ROIC = exactly 15%
scores 90 — applied uniformly across all metrics for internal consistency, not just the
one case (Ro40) the guide's acceptance criterion happens to name. Same `>=` convention
for the composite bands: `STRONG_BUY` >=80, `CONSIDER` 50–79.99, `AVOID` <50.

### Output → `analyticsLog.framework`

```json
{
  "sector": "chips_ai",
  "metrics": {
    "revenueGrowth": {"raw": 0.32, "score": 90},
    "ruleOf40": {"method": "B", "raw": 45.2, "score": 90},
    "operatingMargin": {"raw": 0.24, "score": 90},
    "roic": {"raw": 0.18, "score": 90},
    "valuation": {"metric": "evSales", "raw": 8.1, "score": 60},
    "fcfYield": {"raw": 0.04, "score": 60},
    "balanceSheet": {"debtEbitda": {...}, "interestCoverage": {...}, "currentRatio": {...}, "score": 73.3},
    "competitiveMoat": {"raw": null, "score": null},
    "newsImpact": {"raw": null, "score": null},
    "ndr": {"raw": null}, "grr": {"raw": null}, "churnRate": {"raw": null},
    "avgContractLength": {"raw": null}, "roiic": {"raw": 0.21}
  },
  "composite": 78.4,
  "band": "CONSIDER",
  "excludedMetrics": ["competitiveMoat", "newsImpact"],
  "reweighted": true
}
```

### Rename + symlink (per guide)

`defininitive_professional_investment_framework.md` → `definitive_professional_investment_framework.md`
(fixes the typo), old path kept as a symlink via `symlink_manager.py` (never raw `ln -s`,
per repo rule). Header added: "Executable version: `py_services/framework_score.py` —
keep in sync."

## B3 — `peer_bench.py`

### CLI

```bash
python3 peer_bench.py --ticker TICKER --peers P1,P2,P3 \
  --sector {saas_cyber,chips_ai,energy_infra} \
  --projections-dir DIR --pretty
```

Reuses `framework_score.py`'s per-metric extraction (imported, not duplicated — a shared
internal `compute_raw_metrics(ticker, sector) -> dict` that both scripts call, single
source of truth for every formula) for the target ticker and each peer. Builds the Phase
2 benchmarking table: per metric, target value + Z-score + percentile vs. the peer set.
Same insufficient-data threshold as `comps_valuation.py` (`status: "insufficient_peer_data"`
below 2 usable peers — never fabricated).

### Output → `analyticsLog.peerBench`

```json
{
  "status": "ok",
  "peersUsed": ["AMD", "AVGO", "QCOM"],
  "table": [
    {"metric": "revenueGrowth", "ticker": 0.32, "peerMedian": 0.18, "zScore": 1.4, "percentile": 91},
    ...
  ]
}
```
Also emitted as a markdown table string (`--pretty` / a `--markdown` flag) for direct
embedding in `/evaluate-stock` output, per the guide.

## C1 — `technicals.py`

### CLI

```bash
python3 technicals.py --ticker TICKER --timeframe {D,W} --period PERIOD \
  --benchmark SPY [--anchor-date YYYY-MM-DD] --pretty
```

OHLCV via `market_data.get_prices()` (yfinance-backed) — **not** TradingView CDP, per
`CLAUDE.md` pitfall #7: CDP only reads the currently-active chart, one ticker at a time,
with no batch/background history endpoint. TV is used as the trust-check (below), not
the input source.

### Indicators (full set, hand-rolled, stdlib + numpy/pandas only)

RSI(14) Wilder smoothing · EMA 21/50/200 · MACD(12,26,9) · ADX(14) with +DI/−DI ·
ATR(14) · Bollinger(20,2)/Keltner(20, 1.5×ATR) squeeze · anchored VWAP (anchor date
defaults to the ticker's most recent earnings date from `earnings_calendar.py` if
`--anchor-date` omitted; `null` if neither is available) · 20d volume ratio · relative
strength vs. benchmark (cumulative-return ratio + 63d slope of that ratio).

### Output — one `TechnicalSnapshot` JSON per ticker/timeframe

```json
{
  "ticker": "NVDA", "timeframe": "D", "asOf": "2026-07-05T...",
  "rsi14": 58.2, "ema21": 172.1, "ema50": 165.4, "ema200": 140.2,
  "macd": {"line": 3.1, "signal": 2.4, "histogram": 0.7},
  "adx14": 27.3, "plusDI": 24.1, "minusDI": 14.2, "atr14": 4.8,
  "bollinger": {"upper": 178.2, "mid": 172.0, "lower": 165.8},
  "keltner": {"upper": 179.6, "mid": 172.0, "lower": 164.4},
  "squeeze": false, "anchoredVwap": 168.9, "volumeRatio20d": 1.34,
  "relativeStrength": {"ratio": 1.18, "slope63d": 0.006}
}
```
Persisted to `analyticsLog.technicals` in the projection, informational only.

### Cross-validation — `ta_sweep_batch.py --validate`

New flag on the existing sweep script: for each portfolio ticker already being scanned,
call `technicals.py` for local RSI14/ADX14 and diff against the TV Data Window scrape
values the sweep already fetches. `>2pt` divergence → `warning` in that ticker's sweep
output (never blocks the sweep). Adds a `localValidation` block per ticker:
```json
"localValidation": {
  "rsi": {"local": 58.2, "tv": 57.9, "divergencePts": 0.3, "flag": false},
  "adx": {"local": 27.3, "tv": 30.1, "divergencePts": 2.8, "flag": true}
}
```
This is the mechanism that makes the local engine trustworthy enough to eventually let
`/daily` run on days TV Desktop isn't up — not in this phase's scope, just the first step.

## Schema / gate changes

- `validate_projection.py`: optional `sector` enum check (no-op if absent). No change to
  `check_accumulate_gate()` — framework/peerBench/technicals stay informational, per the
  explicit decision this phase; revisit gate integration in a later phase if warranted.
- `market_data.py`: `ebitda`, `currentRatio` added to `_YF_ONLY_FUNDAMENTALS_FIELDS`.
- New `--qualitative-file` JSON shape (agent hand-filled, `source`+`asOf` required per
  field):
```json
{
  "competitiveMoat": {"rating": "high", "source": "10-K FY2025 MD&A", "asOf": "2026-03-15"},
  "newsImpact": {"rating": "positive", "source": "Q1 earnings call", "asOf": "2026-07-01"},
  "ndr": {"value": 128.0, "source": "10-Q", "asOf": "2026-05-01"},
  "grr": {...}, "churnRate": {...}, "avgContractLength": {...}
}
```

## SKILL.md wiring

New **Step 3.6: Fundamental Framework Score + Peer Benchmarking (Phase 2b)** in
`stock_valuation/SKILL.md`, directly after Step 3.5, describing the three script calls
and their merge into `analyticsLog.{framework, peerBench, technicals}` before Step 4's
validator runs — same structure as the existing Step 3.5 section.

## Testing (TDD, per repo's non-negotiable rule 1)

- `framework_score.py`: golden fixtures (one synthetic company per sector, no live
  network); property test — composite invariant to metric dict key ordering;
  boundary test — Ro40 exactly 40.0 scores 90 for `saas_cyber`; reweighting test — a
  missing qualitative metric renormalizes correctly and sums to 1.0.
- `peer_bench.py`: insufficient-peer-data path (< 2 usable peers); Z-score/percentile
  correctness against a hand-computed fixture set.
- `technicals.py`: golden fixtures against known-good values (frozen from a manually
  verified reference computation); property tests — RSI ∈ [0,100], ATR ≥ 0, EMA
  converges to price under a constant price series.
- `market_data.py`: extend existing fundamentals tests for the two new
  yfinance-only fields (present/absent cases).
- `ta_sweep_batch.py --validate`: fixture-based divergence flagging (local value vs. a
  stubbed TV value, both >2pt and <2pt cases).

All new/changed Python files follow `.agent/rules/coding-conventions.md`: file header +
dual-layer docs (external comment + docstring) on every non-trivial function, full type
hints, snake_case, refactor at 50+ lines or 3+ nesting levels.

## Non-goals (explicitly out of scope this phase)

- Gate integration (framework score as a 4th ACCUMULATE lens) — deferred.
- PEG ratio, Method-A/B averaging — dropped per design decisions above.
- MACD/squeeze/VWAP/RS wired into `daily_brief.py` confluence logic — this phase ships
  the engine + cross-validation only; consuming it in the daily loop's decision logic is
  a later integration step.
- G-series skill/agent architecture cleanup — separate phase (6) per the guide.
