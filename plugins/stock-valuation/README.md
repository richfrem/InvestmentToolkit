# Stock Valuation Plugin

> AI-driven stock valuation engine producing Bear/Base/Bull scenarios with persistent projections and deep-dive research reports.

## Commands

| Command | Description |
|:---|:---|
| `/evaluate-stock {TICKER}` | Run full 7-phase autonomous valuation workflow |

## Skill

The `stock_valuation` skill provides the analysis framework, schema constraints, and reference prompts used by the agent during cognitive analysis.

## Architecture Docs

| Document | Purpose |
|:---|:---|
| `README.md` | Valuation system overview |
| `perform-stock-valuation-opus-version.md` | Original Opus-grade valuation prompt |
| `valuation-persistence.md` | How projections are saved and versioned |
| `red-team-valuation-persistence.md` | Red team review of persistence layer |
| `red_team_review_feedback.md` | Round 1 red team findings |
| `red_team_review_round_2.md` | Round 2 red team findings |
| `red_team_review_round_2_1.md` | Round 2.1 follow-up review |
| `stock_valuation_sequence.mmd` | Sequence diagram (Mermaid) |
| `AI-augmented-stock-valuation-and-thesis-alignment.md` | High-level strategy |
| `interaction_flow.md` | User interaction flow |

## Dependencies

- `yfinance` (Python) — for fetching financial data
- Backend server running on `localhost:3001`

## Related

- [`thesis-balancer`](../thesis-balancer/) — Portfolio health check and drift analysis
