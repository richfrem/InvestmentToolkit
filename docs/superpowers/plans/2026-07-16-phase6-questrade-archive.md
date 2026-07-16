# Questrade Integration Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline — the controller already holds full context from the design investigation; subagent dispatch would re-derive it at cost). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the deprecated standalone Questrade REST integration (backend services, skill,
frontend modal, doc references) from the active codebase by archiving it to a gitignored
`ARCHIVE/questrade/` folder, while leaving every reference to the user's actual live Questrade
brokerage identity (via TradingView) untouched.

**Architecture:** File moves (git-untrack + physically relocate) for integration-specific files;
targeted edits for files that mix retired-integration content with unrelated, still-valid content.
No new abstractions — this is subtractive work.

**Tech Stack:** Node/TypeScript backend + React frontend + Python backend scripts, existing Mocha
test suite (backend), existing Vite build (frontend).

## Global Constraints

- Every file in Task 1's archive list moves to `ARCHIVE/questrade/<original-relative-path>` — path
  mirrored exactly, so restoration (if ever needed) is a straight `mv` back.
- `ARCHIVE/` must be added to `.gitignore` before any `git rm --cached`, so the archived copies are
  never re-tracked.
- Never touch: historical ADRs, `docs/superpowers/specs/done/*`, `tasks/done/*`, gitignored live
  data files (`backend/data/*.ts`, `theses/investment_thesis.md`).
- Never remove a line describing the user's live Questrade brokerage identity via TradingView
  (broker panel, credentials, settlement timing, `norberts-gambit`'s appendix) — only the retired
  standalone REST integration is in scope. When in doubt about a specific line, re-check against
  the design spec's Section "Critical distinction driving scope" before touching it.
- Full spec: `docs/superpowers/specs/2026-07-16-phase6-questrade-archive-design.md`.

---

### Task 1: Archive integration-specific files to `ARCHIVE/questrade/`

**Files:**
- Modify: `.gitignore` (add `ARCHIVE/`)
- Move (git rm --cached + physical relocation), each to `ARCHIVE/questrade/<same relative path>`:
  - `investment_screener/backend/src/QuestradeDataEngine.py`
  - `investment_screener/backend/src/utils/QuestradeAPIClient.py`
  - `investment_screener/backend/src/utils/QuestradeTokenManager.py`
  - `investment_screener/backend/src/utils/PortfolioAggregator.py`
  - `investment_screener/backend/src/services/QuestradeSyncService.ts`
  - `investment_screener/backend/tests/test_token_manager.py`
  - `investment_screener/backend/tests/test_data_engine.py`
  - `investment_screener/backend/tests/services/QuestradeSyncService.spec.ts`
  - `investment_screener/frontend/src/components/QuestradeSetupModal.tsx`
  - `plugins/toolkit-manager/skills/questrade-token-setup/` (whole dir: `SKILL.md`,
    `evals/evals.json`, `references/acceptance-criteria.md`)
  - `plugins/toolkit-manager/references/Questrade/` (whole dir: `architecture_report.md`,
    `token_encryption_process.md`, `token_usage_process.md`, `questrade_token_setup.md`,
    `stateful_token_rotation.md`, `README.md`, `implementation_plan_questrade_integration.md`)

**Interfaces:** None — pure relocation, no code depends on this task's completion signature
(Task 2 edits reference these files by their *old* paths going away, not by anything this task
produces).

- [ ] **Step 1: Add `ARCHIVE/` to `.gitignore`**

Add a line `ARCHIVE/` to `.gitignore` (anywhere in the file; check it isn't already covered by an
existing broader pattern first with `git check-ignore -v ARCHIVE/` after adding).

- [ ] **Step 2: Create the archive directory structure and move each file**

For each file/dir in the list above:
```bash
mkdir -p "ARCHIVE/questrade/$(dirname <original-relative-path>)"
git rm --cached "<original-relative-path>"   # or -r for directories
mv "<original-relative-path>" "ARCHIVE/questrade/<original-relative-path>"
```
For the two whole-directory moves (`questrade-token-setup/`, `references/Questrade/`), move the
entire directory in one `mv` after `git rm --cached -r` on it.

- [ ] **Step 3: Verify the moves**

Run:
```bash
git status --short
```
Expected: every archived path shows as deleted (`D`) from its original location; nothing shows
under `ARCHIVE/` (confirms `.gitignore` is working — if `ARCHIVE/` files appear as untracked `??`,
the gitignore pattern didn't take effect, fix before continuing).

```bash
find ARCHIVE/questrade -type f | sort
```
Expected: 15 files present (5 backend .py/.ts sources, 3 backend tests, 1 frontend component, 3
skill files, 7 reference docs — wait, count carefully at execution time against the list above;
this is a sanity check, not an exact literal assertion to hardcode).

- [ ] **Step 4: No commit yet — proceed to Task 2 first**

Task 2's edits and Task 1's moves land in the same logical change; commit once both are done and
verified (Task 3).

---

### Task 2: Edit files with mixed retired-integration + unrelated content

**Files:** (all Modify, no Create)
- `investment_screener/backend/src/index.ts`
- `investment_screener/backend/src/routes/portfolio.ts`
- `investment_screener/backend/src/services/BrokerSyncService.ts`
- `investment_screener/backend/src/README.md`
- `architecture.md`
- `docs/architecture/README.md`
- `plugins/tradingview/scripts/place_order.py`
- `plugins/tradingview/skills/place-order/SKILL.md`
- `plugins/portfolio-advisor/skills/x-news-sweep/SKILL.md`
- `investment_screener/frontend/src/services/api.ts`
- `investment_screener/frontend/src/pages/Settings.tsx`
- `AGENTS.md`
- `README.md`
- `.claude/CLAUDE.md` (gitignored — edit applies locally only, no commit effect)
- `GEMINI.md`
- `.github/copilot-instructions.md`
- `.claude-plugin/marketplace.json`
- `skills-lock.json`
- `run_investment_toolkit.py`
- `start_here.md`
- `tradingview-cdp/README.md`
- `plugins/toolkit-manager/plugin.json`
- `plugins/toolkit-manager/.claude-plugin/plugin.json`

**Interfaces:** None cross-file — each edit is independent text removal within its own file. The
one real interface concern: `place_order.py`'s `sync_portfolio()` must still return `bool` and
still attempt tiers 1 and 2 exactly as before; only tier 3 is deleted, and the "sync failed"
message that currently sits after tier 3 must move to sit after tier 2 instead, so a total failure
still gets a clear message.

- [ ] **Step 1: Backend route/service edits**

`index.ts` — remove the `/api/questrade/seed` route handler block (the whole `app.post(...)` call)
and its doc-comment line (`* - POST /api/questrade/seed - ...`).

`routes/portfolio.ts` — remove:
- the `import { questradeSyncService } from '../services/QuestradeSyncService';` line
- the whole `router.post('/sync-questrade', ...)` handler
- its doc-comment line (`* - POST /sync-questrade - ...`)
- the `() => questradeSyncService.runSync()` argument passed into the `brokerSyncService.syncAuto(...)`
  call — change that call to take no argument (matches `BrokerSyncService.ts`'s edit in this same
  step, which removes the parameter entirely)

`services/BrokerSyncService.ts` — remove:
- the commented-out dead fallback block (the `/* if (questradeSyncFn) { ... } */` block and the
  line above it: `// Questrade fallback disabled per user request (pure TradingView mode)`)
- the now-unused `_questradeSyncFn?: () => Promise<void>` parameter from `syncAuto()`'s signature
- `'questrade'` from the `dataSource` type union (search for `dataSource:` type declaration)
- update the JSDoc comment above `syncAuto()` (currently says "Priority: TV CDP → cache (Questrade
  fallback disabled for pure TV mode)") to simply say "Priority: TV CDP → cache."
- update the top-of-file doc comment listing `syncAuto()`'s behavior similarly

- [ ] **Step 2: Run backend test suite to catch breakage early**

```bash
cd investment_screener/backend && npm test
```
Expected: same pass/fail counts as the pre-existing baseline (`start_here.md` records 1109
passed / 35 failed pre-existing-environmental as of the last full run) minus the 3 tests that were
archived in Task 1 (`test_token_manager.py`, `test_data_engine.py`,
`QuestradeSyncService.spec.ts` — these simply won't run anymore, which is expected, not a
regression). If any *other* test now fails that wasn't failing before, stop and fix before
continuing — this indicates a real breakage from Step 1's edits.

- [ ] **Step 3: place_order.py fallback removal**

In `sync_portfolio()`, remove the entire tier-3 block:
```python
    # 3. Legacy Questrade REST API
    engine_path = os.path.abspath(os.path.join(BACKEND_SRC, "QuestradeDataEngine.py"))
    cache_dir   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
    portfolio_path = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data", "portfolio.json"))
    result = subprocess.run(
        [sys.executable, engine_path, "--cache-dir",
         os.path.join(cache_dir, "backend"), "--output", portfolio_path],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("✓ Sync complete: portfolio.json updated via Questrade REST API.")
        return True
    print("⚠️  Portfolio sync failed — retry manually with /tv-portfolio-sync.")
    return False
```
Replace with just the failure path after tier 2 (move the existing final message up, drop the
Questrade block entirely):
```python
    print("⚠️  Portfolio sync failed — retry manually with /tv-portfolio-sync.")
    return False
```
Update the docstring above `sync_portfolio()` — remove line 3 of its "Priority:" list
(`3. QuestradeDataEngine.py (legacy REST fallback)`), leaving just items 1 and 2. Check whether
`BACKEND_SRC` is still used elsewhere in the file after this removal; if not, remove its
definition too (avoid an unused-variable lint warning, not a functional issue).

- [ ] **Step 4: Template-only doc mentions**

`plugins/tradingview/skills/place-order/SKILL.md` — two edits only:
- Line with `**Post-execution**: Auto-syncs portfolio.json via live TradingView CDP sync (or
  Questrade REST API fallback)` → drop the parenthetical: `**Post-execution**: Auto-syncs
  portfolio.json via live TradingView CDP sync.`
- Line with `via {TradingView CDP | Questrade API | cache}` → `via {TradingView CDP | cache}`
- Leave every other Questrade mention in this file untouched (broker identity/credentials/panel —
  all live-broker-identity references per the design spec).

`plugins/portfolio-advisor/skills/x-news-sweep/SKILL.md` — one edit:
- Line with `({source: TradingView CDP | Questrade API | cache})` → `({source: TradingView CDP |
  cache})`

- [ ] **Step 5: Frontend removal**

`investment_screener/frontend/src/services/api.ts` — remove the `syncQuestrade` function
(the whole `export const syncQuestrade = async ...` block) and `seedQuestradeToken` function (the
whole `export const seedQuestradeToken = async ...` block). Also remove their mentions in the
top-of-file doc comment (lines listing `syncQuestrade()` and referencing `QuestradeDataEngine`).

`investment_screener/frontend/src/pages/Settings.tsx` — remove the `QuestradeSetupModal` import
and wherever it's rendered/triggered (a button or conditional render block — read the file to find
the exact JSX, since this wasn't captured verbatim during design investigation).

- [ ] **Step 6: Run frontend build/typecheck**

```bash
cd investment_screener/frontend && npm run build
```
Expected: build succeeds with no TypeScript errors. If `Settings.tsx` still references anything
from the removed modal/api functions, this will fail with a clear "Cannot find name" or "Module not
found" error — fix before continuing.

- [ ] **Step 7: Manifest and doc edits**

`AGENTS.md` — remove the `### Questrade API` Setup Entry Point section entirely (the block added
"deprecated" labeling earlier this session — now remove it outright) and the `/setup-questrade`
bullet under Toolkit Manager.

`README.md` — remove the `### Questrade API` fallback section and the `/setup-questrade` mention
under Toolkit Manager's Commands/Skills line; update the Portfolo Summary bullet to just say
"synced from TV CDP" without the Questrade parenthetical.

`.claude/CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` — these three carry
near-identical content; in each, remove the `## Questrade Auth` section, the Overview line's
"Questrade brokerage sync" mention (or its already-added "deprecated" framing from earlier this
session), the `QuestradeSyncService.ts`/`QuestradeAPIClient.py` file-tree lines, and the
`/api/questrade/seed` pitfall note.

`.claude-plugin/marketplace.json` — remove "and Questrade API token seeding (`/setup-questrade`)"
from the toolkit-manager plugin's description string.

`skills-lock.json` — remove the `"questrade-token-setup": { ... }` entry.

`run_investment_toolkit.py` — remove the line printing "TradingView sync (/tv-portfolio-sync) works
without Questrade credentials" (no longer a meaningful tip once the credential flow is gone) or
reword to drop the Questrade reference if the surrounding tip is still useful in a modified form.

`start_here.md` — light touch: the two lines referencing `questrade-token-setup` as an existing
skill example (in the Phase 6 eval-coverage section written earlier today) should be updated to
note the skill was archived, not silently left dangling. The `norberts-gambit` Questrade appendix
mention on that same page stays untouched (live-broker-identity, per design spec).

`tradingview-cdp/README.md` — the one line mentioning "Questrade broker panel" is describing the
live CDP bridge target (category B, live-broker-identity) — re-check against the design spec before
editing; if it's purely descriptive of what CDP currently controls, leave it untouched.

`plugins/toolkit-manager/plugin.json` and `plugins/toolkit-manager/.claude-plugin/plugin.json` —
remove the `questrade_token_setup` skill entry from the `skills` array (in the non-hidden one) and
the `"questrade"` string from the `tags`/`keywords` array (both), and update the `description`
field to no longer mention Questrade at all.

- [ ] **Step 8: Regenerate the ecosystem summary rather than hand-editing it**

```bash
python3 plugins/toolkit-manager/scripts/extract_ecosystem_yaml.py
git diff ecosystem_yaml_summary.md
```
Expected: the diff shows the `questrade-token-setup` entry disappearing on its own, confirming the
script re-derives from the (now-removed) skill directory rather than needing a manual edit.

---

### Task 3: Final verification and commit

**Files:** None new — verification only, then a single commit covering Tasks 1 and 2 together.

- [ ] **Step 1: Full repo-wide re-sweep for any missed reference**

```bash
grep -rli "questrade" --include="*.md" --include="*.json" --include="*.ts" --include="*.tsx" --include="*.py" . 2>/dev/null | grep -v "^\./\.git/\|node_modules\|ARCHIVE/\|/done/\|^ADRs/\|investment_screener/backend/data/"
```
Expected: only files explicitly marked "leave untouched" in the design spec's Section C remain
(live-broker-identity mentions in `place-order/SKILL.md`, `tv-portfolio-sync/SKILL.md`,
`get-orders/SKILL.md`, `daily-loop-agent.md`, `generate_portfolio_blueprint.py`,
`norberts-gambit/SKILL.md` + its `references/questrade.md`, `thesis-challenge-bundler/SKILL.md`,
`rebalance-portfolio/SKILL.md`, `strategic-review/SKILL.md`,
`AI-augmented-stock-valuation-and-thesis-alignment.md`, `fetch_broker_data.py`,
`tradingview/plugin.json`, `tradingview/README.md`, `test_extract.ts`). Anything else appearing
here that isn't on that explicit leave-alone list needs a decision: fix now or note as a follow-up.

- [ ] **Step 2: Full backend test suite one more time**

```bash
cd investment_screener/backend && npm test
```
Expected: identical result to Task 2 Step 2's run (no new failures beyond baseline + the 3
intentionally-archived tests).

- [ ] **Step 3: Commit**

```bash
git add -A
git status --short   # eyeball the full change list one more time before committing
git commit -m "$(cat <<'EOF'
refactor: archive deprecated Questrade REST integration

Full pivot to TradingView CDP confirmed — Questrade's standalone REST
integration (OAuth token exchange, direct API calls bypassing
TradingView) is archived, not deleted, to ARCHIVE/questrade/
(gitignored, paths preserved for easy restoration if ever needed
again; git history also preserves it).

Archived: QuestradeDataEngine.py, QuestradeAPIClient.py,
QuestradeTokenManager.py, PortfolioAggregator.py (orphaned once
DataEngine moved), QuestradeSyncService.ts + its test, the
questrade-token-setup skill, its toolkit-manager reference docs, and
the frontend QuestradeSetupModal.

Edited to remove only the retired-integration references (backend
routes, place_order.py's tier-3 fallback which would have hard-failed
once QuestradeDataEngine.py moved, frontend api.ts calls, and doc/
manifest mentions) while explicitly preserving every reference to the
user's actual live Questrade brokerage identity via TradingView
(broker panel, credentials, settlement rules, norberts-gambit's
Questrade appendix) — these describe the current broker, not the
removed integration.

Spec: docs/superpowers/specs/2026-07-16-phase6-questrade-archive-design.md

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
git log -1 --stat
```

- [ ] **Step 4: Push**

```bash
git push origin main
git fetch origin
git log origin/main -1
```
Expected: push succeeds; `git log origin/main -1` shows the same commit SHA just created.
