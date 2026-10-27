# TASK_SPEC — nbis-scenario-lines-overlay

## 1. The Job
Extend `plugins/tradingview/scripts/tv_thesis_overlay.py` to render Bear/Base/Bull DCF scenario price lines (in addition to the existing Fair Value/Target Entry/Stop Loss lines) as a Pine Script v6 overlay on the active TradingView chart, and prove it works end-to-end on ticker NBIS.

Subsystem paths: `plugins/tradingview/scripts/tv_thesis_overlay.py`, `plugins/tradingview/tests/test_tv_thesis_overlay.py`, `plugins/tradingview/skills/tv-thesis-overlay/SKILL.md`.

## 2. The Why
The user wants real bear/base/bull DCF targets visible directly on their TradingView charts, and wants those lines to stay in sync whenever the underlying analysis changes. The existing `tv-draw` skill cannot do this — it creates TradingView price alerts, not visual chart lines (verified by reading its implementation, which calls `tv_call("alert", "create", ...)`). `tv-thesis-overlay` already solves the "real chart lines" problem via Pine Script injection for Fair Value/Target Entry/Stop Loss; this task extends the same proven mechanism to bear/base/bull.

## 3. Semantic Guardrails
- **Source of truth is `domain_model.sqlite`, not `data/projections/*.json`**: the JSON files are the pre-migration staging format; `projection_scenario` (joined to the latest `projection_version`) is the current, verified-accurate source (confirmed NBIS bear=$41.05/base=$194.96/bull=$619.51 match between both, but SQLite is canonical per this repo's established convention).
- **No changes to `tv-draw`**: it is out of scope and known non-functional for this purpose; do not attempt to "fix" it as part of this task.
- **No schema changes**: `projection_scenario` already has the needed columns.
- **Single ticker (NBIS) for this pass**: do not roll out to other tickers.
- **"Keep lines in sync" mechanism is re-invocation, not new state**: the script already does remove-then-reinject each run; the SKILL.md gets a note that workflows writing a new `projection_version` should re-invoke this overlay, rather than building new change-detection machinery.

## 4. Objective Definition of Done (DoD)
- `python3 -m pytest plugins/tradingview/tests/test_tv_thesis_overlay.py` exits 0, including new assertions for bear/base/bull.
- `python3 plugins/tradingview/scripts/tv_thesis_overlay.py --ticker NBIS --dry-run` exits 0 and its output JSON's `levels` dict contains `bear_price: 41.05, base_price: 194.96, bull_price: 619.51`.
- Generated Pine Script passes `PineLinter.lint()` with zero errors (already covered by the dry-run path, which lints before returning).
- Live run: `python3 plugins/tradingview/scripts/tv_thesis_overlay.py --ticker NBIS` exits 0 with `"success": true`, given TradingView Desktop is open and CDP-reachable.

(Full plan outline: `docs/plans/work-tasks/nbis-scenario-lines-overlay/nbis-scenario-lines-overlay-plan-outline.md`)
