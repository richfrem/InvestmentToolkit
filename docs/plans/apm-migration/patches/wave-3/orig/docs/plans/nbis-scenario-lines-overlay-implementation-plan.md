# Implementation Plan — nbis-scenario-lines-overlay (TRIVIAL route)

## Steps
1. **Worktree**: create `.worktrees/task-nbis-scenario-lines-overlay/` on a new feature branch, per this repo's worktree-first rule.
2. **Red**: extend `plugins/tradingview/tests/test_tv_thesis_overlay.py`'s `mock_db` fixture with a `projection_scenario` table (`scenario_id`, `projection_id`, `scenario_name`, `weight`, `scenario_price`), seed bear/base/bull rows for the existing NVDA fixture data, and add assertions:
   - `resolve_ticker_levels()` returns `bear_price`, `base_price`, `bull_price`.
   - `generate_pine_script_content()` emits three additional `line.new()`/`label.new()` blocks referencing those prices.
   Run pytest, confirm it fails for the expected reason (missing keys/lines).
3. **Green**: implement in `tv_thesis_overlay.py`:
   - `resolve_ticker_levels()`: add a query against `projection_scenario` joined to the latest `projection_version` (mirroring the existing `price_level_tier` join pattern), populate `bear_price`/`base_price`/`bull_price`.
   - `generate_pine_script_content()`: add three more `line.new()`/`label.new()` blocks following the existing Fair Value/Target Entry/Stop Loss pattern (bear=red, base=blue/grey, bull=green), redrawn on `barstate.islast`.
   Run pytest until green.
4. **Verify dry-run**: `python3 plugins/tradingview/scripts/tv_thesis_overlay.py --ticker NBIS --dry-run`, confirm bear=41.05/base=194.96/bull=619.51 and lint passes.
5. **Verify live** (requires TradingView Desktop open, CDP reachable): `python3 plugins/tradingview/scripts/tv_thesis_overlay.py --ticker NBIS`, confirm `"success": true`.
6. **SKILL.md note**: add a line to `plugins/tradingview/skills/tv-thesis-overlay/SKILL.md` noting that any workflow writing a new `projection_version` should re-invoke this overlay for that ticker.
7. **Present diff for review** per `WORKTREE_REVIEW` gate — do not push or open a PR without explicit authorization.

## Test Tier
Existing unit test location: `plugins/tradingview/tests/test_tv_thesis_overlay.py` (extends existing coverage, no new file).

## Review Route (TRIVIAL)
Concise plan, focused verification, no external reviewers requested.
