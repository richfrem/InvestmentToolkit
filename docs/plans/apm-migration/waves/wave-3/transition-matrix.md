# Wave 3: transition matrix

Old skill names are retired; slash commands are unchanged. Each old skill is now a mode file under `references/modes/` of its hub.

| Legacy skill | Hub skill | Mode | Slash command | What changed |
|:---|:---|:---|:---|:---|
| `tv-setup` | `operating-tradingview-charts` | `setup` | `/tv-setup` | Combined with tv-onboarding into one mode (both skills diagnosed the same port-9222 connection). |
| `tv-onboarding` | `operating-tradingview-charts` | `setup` | `/tv-onboarding` | Combined with tv-setup into one mode. |
| `tv-change-symbol` | `operating-tradingview-charts` | `change-symbol` | `/tv-change-symbol` | Content carried over; paths made relative to the hub. |
| `tv-change-type` | `operating-tradingview-charts` | `change-type` | `/tv-change-type` | Content carried over; paths made relative to the hub. |
| `tv-chart-setup` | `operating-tradingview-charts` | `chart-setup` | `/tv-chart-setup` | Content carried over; paths made relative to the hub. |
| `tv-chart-snapshot` | `operating-tradingview-charts` | `chart-snapshot` | `/tv-snapshot` | The cited tv_snapshot.py never existed; the mode now uses the Node CLI screenshot command. |
| `tv-draw` | `operating-tradingview-charts` | `draw` | `/tv-draw` | Content carried over; paths made relative to the hub. |
| `tv-add-indicator` | `operating-tradingview-charts` | `add-indicator` | `/tv-add-indicator` | Content carried over; paths made relative to the hub. |
| `tv-manage-indicators` | `operating-tradingview-charts` | `manage-indicators` | `/tv-indicators` | Content carried over; paths made relative to the hub. |
| `tv-save-indicator` | `operating-tradingview-charts` | `save-indicator` | `/tv-save-indicator` | Content carried over; paths made relative to the hub. |
| `tv-pine-inject` | `operating-tradingview-charts` | `pine-inject` | `/tv-pine-inject` | Content carried over; paths made relative to the hub. |
| `tv-author-pine-script` | `operating-tradingview-charts` | `author-pine-script` | `/tv-author-pine-script` | Content carried over; paths made relative to the hub. |
| `tv-thesis-overlay` | `operating-tradingview-charts` | `thesis-overlay` | `/tv-thesis-overlay` | Content carried over; paths made relative to the hub. |
| `tv-alert-list` | `operating-tradingview-charts` | `alert-list` | `/tv-alert-list` | Content carried over; paths made relative to the hub. |
| `tv-alert-reconcile` | `operating-tradingview-charts` | `alert-reconcile` | `/tv-alert-reconcile` | Content carried over; paths made relative to the hub. |
| `tv-alert-sync` | `operating-tradingview-charts` | `alert-sync` | `/tv-alert-sync` | Content carried over; paths made relative to the hub. |
| `tv-place-order` | `trading-via-tradingview` | `place-order` | `/place-order` | Calls the backend's place_order.py by repo path. |
| `tv-modify-order` | `trading-via-tradingview` | `modify-order` | `/tv-modify-order` | Content carried over; paths made relative to the hub. |
| `tv-cancel-order` | `trading-via-tradingview` | `cancel-order` | `/tv-cancel-order` | Content carried over; paths made relative to the hub. |
| `tv-get-orders` | `trading-via-tradingview` | `get-orders` | `/tv-get-orders` | Content carried over; paths made relative to the hub. |
| `tv-portfolio-sync` | `trading-via-tradingview` | `portfolio-sync` | `/tv-portfolio-sync` | Content carried over; paths made relative to the hub. |
| `tv-price-refresh` | `trading-via-tradingview` | `price-refresh` | `/tv-price-refresh` | Scripts are inside the hub; fetch_broker_data.py is called from the backend folder. |
| `tv-manage-watchlists` | `trading-via-tradingview` | `manage-watchlists` | `/tv-manage-watchlists` | The cited manage_watchlists.py is really watchlist_manager.py sync; the mode now says so. |
| `tv-ta-daily-sweep` | `analyzing-charts` | `ta-daily-sweep` | `/tv-ta-daily-sweep` | Content carried over; paths made relative to the hub. |
| `tv-ta-snapshot` | `analyzing-charts` | `ta-snapshot` | `/tv-ta` | Same: screenshot via the Node CLI. |
| `tv-ta-red-team` | `analyzing-charts` | `ta-red-team` | `/tv-ta-red-team` | Content carried over; paths made relative to the hub. |
| `tv-technical-analysis-expert` | `analyzing-charts` | `technical-analysis-expert` | `/tv-ta-expert` | Content carried over; paths made relative to the hub. |

## Other changes
- Engine (real files in `investment_screener/backend/py_services/`): `tv_client`, `tv_launch`, `tv_health_check`, `place_order`, `fetch_broker_data`, `tv_account_coverage`. The last three replaced the backend's symlinks. Engine tests moved to `investment_screener/backend/tests/py_services/` (25 tests).
- Agent: `ta-guide.md` -> `.apm/agents/ta-guide.agent.md`; its references to skills that never carried the `tv-` prefix were updated to the new hubs and modes.
- `audit/` (runtime order logs written by `tradingview-cdp/core/audit.js`, read by the backend) is local data, not package content, and stays where it is.
- `registry.json` (gitignored local state) moved beside the indicators and its ignore rule was updated.
- Directory-level references the exact-path rule cannot rewrite were fixed with the new `dirfix` command (12 files) and by hand: `fetch_portfolio_heatmap.py`, `pine_script_manager.py`, `run_investment_toolkit.py`, `run_tests.py`, `tv_health_check.py` and several docstrings.
- Dotted-module imports (`from plugins.tradingview.scripts.X import`) in four tests became direct imports.
