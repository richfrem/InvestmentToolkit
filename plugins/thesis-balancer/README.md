# Thesis Balancer Plugin

> Strategic portfolio health monitor and thesis alignment engine. Detects drift, flags Thesis Breaker conditions, resolves Strategic Conflicts against AI valuations, and suggests rebalancing actions.
>
> **Maturity**: L5 — Meta-capable (tested + connectors + evals + fallback trees)  
> **Architecture**: Supercharged (standalone-capable; enhanced with portfolio API)

---

## File Tree

```
thesis-balancer/
├── plugin.json                               # Plugin manifest (L5)
├── CONNECTORS.md                             # Tool connector abstractions
├── README.md                                 # This file
├── commands/
│   └── review-portfolio.md                  # /review-portfolio command
├── docs/
│   └── tool_b_implementation_brief.md
└── skills/
    └── thesis-balancer/
        ├── SKILL.md                          # Main skill definition
        ├── evals/
        │   └── evals.json                   # 8-case evaluation suite
        └── references/
            ├── acceptance-criteria.md        # 8 testable pass/fail criteria (AC-01–08)
            ├── fallback-tree.md              # 4 procedural fallback sequences (FB-01–04)
            ├── rebalance_prompt.md           # Rebalance trade generation prompt
            └── strategic_review_prompt.md    # Strategic dialogue prompt
```

---

## Commands

| Command | Description |
|:---|:---|
| `/review-portfolio [thesis_id]` | Full portfolio health check: drift analysis, conflict detection, rebalance suggestions |

---

## Skill

The `thesis_balancer` skill runs a 5-phase review:
1. **Select & Load Thesis** — from API or manual paste in standalone mode
2. **Run Health Check** — via `~~portfolio-api`
3. **Strategic Analysis** — drift classification, conflict detection, thesis breaker checks, missing valuation surfacing
4. **Report & Recommendations** — structured findings with drift table and action suggestions
5. **Thesis Evolution** — proposed target weight updates with impact preview before confirmation

**Standalone Mode**: If backend API is unavailable, skill requests portfolio + thesis data as JSON paste and computes drift manually. See `CONNECTORS.md` and `references/fallback-tree.md`.

---

## External Dependencies (Web App APIs)

> **This plugin does NOT own these endpoints.** They are served by the Investment Screener backend.

| Endpoint | Purpose |
|:---|:---|
| `GET /api/theses` | Lists all available investment theses |
| `GET /api/theses/:id/health` | Returns per-holding drift scores, alerts, and overall status |

---

## Key Reference Files

| File | Purpose |
|:---|:---|
| `references/acceptance-criteria.md` | 8 testable AC definitions with pass/fail conditions |
| `references/fallback-tree.md` | Step-by-step fallbacks for all 4 brittle operations |
| `references/rebalance_prompt.md` | Trade generation prompt for rebalancing suggestions |
| `references/strategic_review_prompt.md` | Strategic dialogue prompt for conviction assessment |
| `evals/evals.json` | 8-case eval suite for trigger + logic + robustness |

---

## Dependencies

- Backend server running on `localhost:3001` *(supercharged; not required in standalone mode)*

## Related Plugins

- [`stock-valuation`](../stock-valuation/) — AI stock valuations used for Strategic Conflict detection
