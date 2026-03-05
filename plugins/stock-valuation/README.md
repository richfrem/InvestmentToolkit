# Stock Valuation Plugin

> AI-driven autonomous stock valuation engine. Produces Bear/Base/Bull scenario projections, persists structured JSON output, generates deep-dive research reports, and supports interactive analyst Q&A.
>
> **Maturity**: L5 — Meta-capable (tested + connectors + evals + fallback trees)  
> **Architecture**: Supercharged (standalone-capable; enhanced with financial data pipeline)

---

## File Tree

```
stock-valuation/
├── plugin.json                          # Plugin manifest (L5)
├── CONNECTORS.md                        # Tool connector abstractions
├── README.md                            # This file
├── commands/
│   └── evaluate-stock.md               # /evaluate-stock {TICKER} command
├── docs/
│   ├── AI-augmented-stock-valuation-and-thesis-alignment.md
│   ├── interaction_flow.md
│   ├── valuation-persistence.md
│   ├── stock_valuation_sequence.mmd    # Mermaid sequence diagram
│   └── README.md
└── skills/
    └── stock_valuation/
        ├── SKILL.md                     # Main skill definition
        ├── evals/
        │   └── evals.json              # 8-case benchmark evaluation suite
        ├── references/
        │   ├── acceptance-criteria.md  # 8 testable pass/fail criteria (AC-01–08)
        │   ├── analysis_prompt.md      # Full cognitive analysis prompt (v2)
        │   ├── api_reference.md        # Backend script reference + exit codes
        │   ├── fallback-tree.md        # 5 procedural fallback sequences (FB-01–05)
        │   ├── valuation-benchmarks.md # Sector P/E + margin benchmark tables
        │   └── example_NVDA.json       # Example Projection output
        ├── scripts/
        │   └── validate_projection.py  # Pre-persistence schema validator (--verbose)
        └── assets/
            └── example_asset.txt
```

---

## Commands

| Command | Description |
|:---|:---|
| `/evaluate-stock {TICKER}` | Run full autonomous valuation: fetch → analyse → persist → report → discuss |

---

## Skill

The `stock_valuation` skill runs the full 9-step pipeline:
1. Fetch financial data via `~~financial-data-fetcher`
2. Build snapshot object from raw metrics
3. Cognitive analysis → Bear/Base/Bull scenarios
4. Validate & repair JSON (weight sums, type checks, ordering)
5. Assemble full Projection object
6. Pre-flight validate via `scripts/validate_projection.py`
7. Persist via `~~projection-store`
8. Generate deep-dive research report
9. Conversational summary + interactive Q&A loop

**Standalone Mode**: If backend is unavailable, the skill requests raw financial JSON from the user and completes analysis without persistence. See `CONNECTORS.md` and `references/fallback-tree.md`.

---

## External Dependencies (Web App Scripts)

> **This plugin does NOT own these scripts.** They live inside the Investment Screener web app. Do not move or duplicate them.

| Script | Canonical Path | Purpose |
|:---|:---|:---|
| `fetch_financials.py` | `tools/investment_screener/backend/py_services/fetch_financials.py` | Fetches raw financial data from yfinance |
| `persist_projection.py` | `tools/investment_screener/backend/py_services/persist_projection.py` | Saves projection JSON to the data directory |

| Data Directory | Path |
|:---|:---|
| Projections | `tools/investment_screener/backend/data/projections/` |
| Research Reports | `tools/investment_screener/backend/data/research/` |

---

## Key Reference Files

| File | Purpose |
|:---|:---|
| `references/acceptance-criteria.md` | 8 testable pass/fail AC definitions |
| `references/fallback-tree.md` | Step-by-step fallbacks for all 5 brittle operations |
| `references/valuation-benchmarks.md` | Sector P/E + margin + quality multiplier tables |
| `references/analysis_prompt.md` | Full Bear/Base/Bull cognitive analysis prompt |
| `references/api_reference.md` | Backend script exit codes and schemas |
| `evals/evals.json` | 8-case eval suite for trigger + schema + robustness |
| `scripts/validate_projection.py` | Pre-persistence JSON validator |

---

## Dependencies

- `yfinance` (Python) — for fetching financial data
- Backend server running on `localhost:3001` *(supercharged; not required in standalone mode)*

## Related Plugins

- [`thesis-balancer`](../thesis-balancer/) — Portfolio health check and drift analysis against strategic thesis
