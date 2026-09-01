# Map Debt Ledger

Persistent tracking of architectural friction, structural anomalies, and unclosed loops across sessions.

| ID | Title | Status | Severity | Repeat | First Seen | Description | Resolution Commit |
|---|---|---|---|---|---|---|---|
| DEBT-20260831-01 | Inline Python/SQL fallback due to missing `portfolio_io.py` CLI query primitives | RESOLVED | Tier 0 | 1 | 2026-08-31 | Valuation triage on GOOG/ZS led to ad-hoc inline Python/SQL execution because `portfolio_io.py` lacked standalone CLI query flags for ticker holding status and strategy pillar resolution. | Added `--ticker`, `--pillars`, and `--json` CLI flags to `portfolio_io.py`; updated `update-stock-analysis/SKILL.md` Step 0.1 to strictly invoke canonical CLI and explicitly forbid inline Python/SQL. |

