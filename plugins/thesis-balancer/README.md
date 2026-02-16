# Thesis Balancer Plugin

> Portfolio health monitoring, drift analysis, and thesis alignment enforcement.

## Commands

| Command | Description |
|:---|:---|
| `/review-portfolio` | Run portfolio health check against a strategic thesis |

## Skill

The `thesis-balancer` skill provides rebalance and strategic review prompts for evaluating portfolio drift against thesis targets.

## Architecture Docs

| Document | Purpose |
|:---|:---|
| `tool_b_implementation_brief.md` | Full implementation specification for the thesis alignment system |
| `tool_b_red_team_review.md` | Red team security and design review |
| `red_team_review_prompt.md` | Prompt template for red team reviews |
| `thesis_alignment_sequence.mmd` | Sequence diagram (Mermaid) |

## Dependencies

- Backend server running on `localhost:3001`
- `portfolio.json` and thesis files loaded

## Related

- [`stock-valuation`](../stock-valuation/) — AI-driven stock valuation workflow
