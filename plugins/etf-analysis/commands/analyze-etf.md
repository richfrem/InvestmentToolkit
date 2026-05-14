# /analyze-etf

**Trigger**: `/analyze-etf {TICKER}`

Perform a full ETF or fund analysis on the given ticker and save results to `data/etf_analysis/`.

## Examples
- `/analyze-etf DXYZ` — Closed-end pre-IPO fund (NAV premium analysis)
- `/analyze-etf KOID` — Humanoid robotics thematic ETF
- `/analyze-etf HUMN` — Roundhill humanoid robotics ETF
- `/analyze-etf PSU-U.TO` — USD cash fund (yield + dividend timing)

## What it produces
- `investment_screener/backend/data/etf_analysis/{TICKER}.json` — structured analysis
- Updated `agentRationale` in `target-portfolio.json` for that ticker
- Conversational summary with action recommendation and key risks

## Skill invoked
`etf_analysis` (plugins/etf-analysis/skills/etf_analysis/SKILL.md)
