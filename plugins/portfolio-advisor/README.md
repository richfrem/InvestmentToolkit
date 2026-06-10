# Portfolio Advisor Plugin

> Investment portfolio advisor suite. Adversarial thesis challenge, drift monitoring, valuation-gated rebalancing, and target calibration. Detects drift, flags Thesis Breaker conditions, resolves Strategic Conflicts against AI valuations, proposes formula improvements, and generates trade recommendations.
>
> **Maturity**: L5 — Meta-capable (tested + connectors + evals + fallback trees)  
> **Architecture**: Supercharged (standalone-capable; enhanced with portfolio API)

---

## File Tree

```
portfolio-advisor/
├── plugin.json                               # Plugin manifest (L5)
├── CONNECTORS.md                             # Tool connector abstractions
├── README.md                                 # This file
├── commands/
│   └── review-portfolio.md                  # /review-portfolio command
├── references/
│   ├── investment_thesis.md                  # Living thesis document
│   ├── thesis_alignment_sequence.mmd         # Architecture sequence diagram
│   └── tool_b_implementation_brief.md        # Implementation reference
└── skills/
    ├── portfolio-health/                     # /review-portfolio — drift monitor + health score
    │   ├── SKILL.md
    │   ├── evals/
    │   │   └── evals.json
    │   └── references/
    │       ├── acceptance-criteria.md
    │       ├── fallback-tree.md
    │       ├── rebalance_prompt.md
    │       └── strategic_review_prompt.md
    ├── strategic-review/                     # /strategic-review — adversarial thesis challenger
    │   └── SKILL.md
    ├── rebalance-portfolio/                  # /rebalance — valuation-gated trade optimizer
    │   └── SKILL.md
    ├── calibrate-targets/                    # /calibrate-targets — interactive target negotiation
    │   └── SKILL.md
    └── update-portfolio-targets/             # apply formula changes — mechanical target writer
        └── SKILL.md
```

---

## Skills

| Trigger | Skill | Purpose |
|:---|:---|:---|
| `/daily` | `daily-loop` | The one daily command: portfolio sync, morning brief, triage cards, order execution, evolution log |
| `/adversarial-review` | `adversarial-review` | Prepares a comprehensive adversarial review bundle of the thesis, targets, and daily recommendations |
| `/bundle-thesis-review` | `thesis-challenge-bundler` | Packages the thesis and DCF projections for a general external review |
| `/review-portfolio` | `portfolio-health` | Drift monitor + pillar conviction audit + thesis formula health score (0–100) |
| `/strategic-review` | `strategic-review` | Adversarial thesis challenger — surfaces failing pillars, proposes formula improvements |
| `/rebalance` | `rebalance-portfolio` | Valuation-gated trade optimizer — never buys SELL-rated holdings to restore drift |
| `/calibrate-targets` | `calibrate-targets` | Interactive target-weight negotiation per sub-strategy |
| `/x-news-sweep` | `x-news-sweep` | Daily news sweep via Grok/X.com to surface catalysts and sentiment |
| `/13f-tracker` | `13f-tracker` | Polls and diffs SEC 13F EDGAR filings for super-investors |
| `/13f-analyze` | `13f-analyze` | Cross-references super-investor 13F changes against target portfolio |
| `apply formula changes` | `update-portfolio-targets` | Mechanical write of agreed target changes (chains from strategic-review or calibrate-targets) |

### `portfolio-health` — Quick Health Check

Runs a 5-phase drift review:
1. **Select & Load Thesis** — from API or manual paste in standalone mode
2. **Run Health Check** — via portfolio API
3. **Strategic Analysis** — drift classification, conflict detection, thesis breaker checks
4. **Report & Recommendations** — structured findings with drift table and action suggestions
5. **Thesis Evolution** — redirect to `/strategic-review` for formula improvement proposals

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
