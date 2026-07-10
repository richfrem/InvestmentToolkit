# Map Debt Registry

This registry tracks technical debt, process friction, and workarounds.
Entries must be resolved, aged, or escalated. 
Do not delete resolved items; set `Status: RESOLVED` to maintain history.

---

### Entry: test_math_parity.py — PROJECT_ROOT resolves 2 levels short of repo root

- Logged: 2026-07-05
- Cycle/Session: Phase 3 E1 (risk-engine) — discovered during baseline test run before Task 1 dispatch
- Artifact affected: `investment_screener/backend/tests/py_services/test_math_parity.py:6`
- Friction observed: `PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` only walks up 2 directories from `tests/py_services/test_math_parity.py`, landing at `tests/` instead of the repo root. The subsequent `subprocess.run([...os.path.join(PROJECT_ROOT, "investment_screener/backend/py_services/dcf_scenarios.py")...])` call then looks for the script at a doubled, nonexistent path and fails with `No such file or directory`.
- Why it was not fixed now: unrelated to the Phase 3 risk-engine task in progress; fixing it would be an undeclared scope addition mid-task (violates "one logical fix at a time").
- Recommended fix: use `Path(__file__).resolve().parents[4]` (matching the convention already used consistently elsewhere in this test directory, e.g. `test_framework_score.py`, `test_risk_engine.py`) instead of two `os.path.dirname()` calls.
- Evidence: `python3 -m pytest tests/py_services/test_math_parity.py -v` → `Exception: Python math failed`; captured stdout shows `can't open file '.../tests/investment_screener/backend/py_services/dcf_scenarios.py'`.
- Severity: S
- Repeat: NO (isolated to this one file)
- Status: RESOLVED
- Resolution (2026-07-10, Phase 3 E2 session, at explicit user request rather than deferred further): applied the recommended fix verbatim — `PROJECT_ROOT` now computed via `Path(__file__).resolve().parents[4]`, matching every other test file in this directory. `python3 -m pytest tests/py_services/test_math_parity.py -v` → 1 passed.

### Entry: test_place_order_gates.py — 3 tests coupled to real-world weekday/market-hours state

- Logged: 2026-07-05
- Cycle/Session: Phase 3 E1 (risk-engine) — discovered during baseline test run before Task 1 dispatch
- Artifact affected: `investment_screener/backend/tests/py_services/test_place_order_gates.py` — `test_stale_portfolio_exits_4`, `test_fresh_portfolio_exits_0`, `test_size_cap_exits_3`
- Friction observed: these tests invoke the real `place_order.py --preflight` CLI, which checks live NYSE market-hours state before evaluating the gate under test (stale-data, fresh-portfolio, size-cap). When run on a weekend (as today, 2026-07-05 is a Sunday), the market-closed gate fires first and returns exit code 5 with "🚫 Weekend — NYSE is closed" instead of the expected gate-specific exit code (4, 0, 3 respectively) — the tests are not isolated from wall-clock/calendar state.
- Why it was not fixed now: unrelated to the Phase 3 risk-engine task in progress; the real fix (mocking/injecting market-hours state so these gate-order tests are calendar-independent) is a test-harness change outside this task's scope.
- Recommended fix: add a way to override/mock the market-hours check in `place_order.py`'s preflight path (e.g. an env var or `--skip-market-hours-check` test-only flag) so these three tests assert the gate they name regardless of what day they run.
- Evidence: `python3 -m pytest tests/py_services/test_place_order_gates.py -v` on 2026-07-05 (Sunday) → all 3 fail with returncode 5 / "Weekend — NYSE is closed" instead of their expected returncodes.
- Severity: S
- Repeat: YES — will recur every Saturday/Sunday (and likely market holidays) until fixed
- Status: RESOLVED
- Resolution (2026-07-10, Phase 3 E2 session, at explicit user request rather than deferred further): applied the recommended fix — `_check_market_hours()` in `plugins/tradingview/scripts/place_order.py` now reads a `PLACE_ORDER_NOW_OVERRIDE` env var (ISO 8601 UTC timestamp) when set, falling back to `datetime.now(timezone.utc)` when unset (production behavior unchanged — additive only). The 3 named tests plus `test_stale_with_ack_stale_proceeds` (same fragility class, not originally named) now pin a known in-hours weekday timestamp via this override instead of depending on the real wall clock. Added a new dedicated test, `test_market_closed_exits_5_and_ack_closed_bypasses`, asserting the market-hours gate itself (previously zero direct coverage) using a pinned Saturday timestamp, plus `--ack-closed` bypass behavior. `python3 -m pytest tests/py_services/test_place_order_gates.py -v` → 11 passed. Note: the failures observed *this session* before the fix were actually a worktree-only environment gap (`tradingview-cdp/node_modules` never installed here, resolved via `npm ci`), not a live reproduction of the documented market-hours race — the wall-clock-coupling design fix above was applied proactively per the documented recommendation, independent of that day's actual symptom.

### Entry: subagent-driven-development implementer wrote to main checkout instead of worktree (2nd occurrence)

- Logged: 2026-07-09
- Cycle/Session: Phase 3 C2 (market regime classifier) — discovered during final merge prep, `git status` in the main checkout showed an uncommitted, incomplete copy of `daily_brief.py`'s Task 7 changes that should only have existed in the worktree
- Artifact affected: process/workflow — `superpowers:subagent-driven-development` dispatch pattern for this project, not a specific code file
- Friction observed: despite every implementer/fix subagent being explicitly instructed to `cd` into the worktree and confirm via `pwd`/`git branch --show-current` before any edit — and every subagent's report claiming that confirmation passed — a stray, uncommitted, incomplete edit still landed in the main checkout's `plugins/portfolio-advisor/scripts/daily_brief.py` during Task 7's fix rounds. This is the SAME class of incident documented informally in `start_here.md` for Phase 2b's Task 3 (an implementer committed onto the user's active main-checkout branch instead of its worktree) — confirming the existing mitigation (explicit path instruction + pwd/branch confirmation) is insufficient on its own, not a one-off fluke.
- Why it was not fixed inline immediately: not caught until the final pre-merge `git status` check, because no per-task verification of the *main checkout's* cleanliness was happening between tasks — only the worktree's own state was checked during each task's dispatch/review cycle.
- Root cause (best available, not fully forensically confirmed): `cd` inside a Bash tool call only changes that tool's persisted shell state; the Edit/Write/Read tools resolve on the exact absolute path parameter given, independent of any prior `cd`. A `pwd`/`git branch` confirmation via Bash therefore does not guarantee every subsequent Edit/Write call in that same subagent session targets a path under the confirmed directory.
- Fix applied now (not deferred): authored `.agent/rules/worktree-subagent-isolation.md`, a new durable, git-tracked rule mandating `git status --short` in the **main checkout** (not the worktree) after every subagent-driven-development task, before generating the review package — catches a leak within one task cycle, while it's still uncommitted and trivially discardable, instead of only at final-merge time. Referenced (not duplicated) from `.claude/CLAUDE.md` pitfall #28 as a one-line pointer, matching how CLAUDE.md's rule 1 already references `test-driven-development.md` — `.claude/CLAUDE.md` itself is gitignored/local-only, so the rule file is the actual durable, shared fix.
- Evidence: `git diff plugins/portfolio-advisor/scripts/daily_brief.py` in the main checkout (pre-merge, pre-discard) showed a partial version of Task 7's changes — present through the NameError fix commit but missing the later NEUTRAL-restoration and defensive-`.get()` fixes — confirming it was a stray leak from mid-task, not intentional or user-authored work. Discarded safely via `git checkout -- plugins/portfolio-advisor/scripts/daily_brief.py` before merging, since the complete, reviewed version already existed properly committed on the feature branch.
- Severity: M (no data/history damage this time since caught pre-merge and uncommitted, but repeated occurrence across two separate phases is a real reliability gap in the dispatch pattern itself)
- Repeat: YES — 2nd occurrence (1st: Phase 2b Task 3, documented in `start_here.md`, not previously logged here in map-debt.md)
- Status: RESOLVED — preventive process fix (`.agent/rules/worktree-subagent-isolation.md`) applied in this session, not just documented; future occurrences will be caught per-task rather than only at merge time
