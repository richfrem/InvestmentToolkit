# Eval Coverage Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create or upgrade `evals/evals.json` for the 53 skills/agents currently lacking rich eval
coverage, using the schema already established by `stock_valuation` and `portfolio-health`.

**Architecture:** Content-authoring work, not code — each task reads its assigned targets' real
`SKILL.md`/`agent.md` files and derives domain-specific benchmark scenarios into a JSON eval spec.
No shared code, no runtime behavior change. Batched by plugin into 7 tasks.

**Tech Stack:** JSON files only. No dependencies.

## Global Constraints

- Full spec: `docs/superpowers/specs/2026-07-16-phase6-eval-coverage-backfill-design.md`.
- **Reference template** (read before writing any eval file): `plugins/stock-valuation/skills/stock_valuation/evals/evals.json` — this is the canonical rich-schema example every new file should structurally match (`skill`, `version`, `description`, `scoring_version`, `evals[]`, `benchmark_targets`).
- **Skill eval path:** `plugins/<plugin>/skills/<skill-dir>/evals/evals.json`.
- **Agent eval path (new convention):** `plugins/<plugin>/agents/evals/<agent-name>.json` — create the shared `evals/` directory under `agents/` if it doesn't exist yet for that plugin.
- Each eval file needs **at minimum 4 entries** covering categories that genuinely apply to that
  target (not all 7 categories from the template apply to every skill — e.g. a read-only
  chart-control skill has no meaningful sycophancy scenario; an internal-only skill dispatched by
  another skill, never by the user directly, has no meaningful trigger category).
- **Every task must read its target's actual `SKILL.md`/`agent.md` before writing its eval file** —
  no eval file may be written from the file list alone without reading the real content first.
  Scenarios must reflect that specific skill's real trigger phrases, hard rules, and domain (a DCF
  skill's near-miss case looks nothing like a CDP chart-control skill's).
- Commit after each task completes (not one giant commit at the end) — this is 53 files across 7
  tasks; frequent commits make it easy to isolate a problem to one batch if the final structural
  check fails.
- Per this repo's git policy: push each task's commit straight to `origin/main` (no worktree
  needed — this is docs/JSON-only, zero code risk, same posture as the AGENTS.md audit).

---

### Task 1: etf-analysis (1 file)

**Files:**
- Read: `plugins/etf-analysis/skills/etf_analysis/SKILL.md`
- Create: `plugins/etf-analysis/skills/etf_analysis/evals/evals.json`

- [ ] **Step 1:** Read `SKILL.md` in full — note its trigger phrase(s), what it produces
  (ETF holdings alignment, BUY/HOLD/AVOID action, dual-write to `data/etf_analysis/` +
  `data/projections/`), and any hard rules it documents.
- [ ] **Step 2:** Write `evals/evals.json` with ≥4 scenarios covering at least: trigger accuracy
  (a realistic "analyze this ETF" prompt), schema/output compliance (dual-write happens, action
  field is one of BUY/HOLD/AVOID), a negative case (asked to analyze without real holdings data —
  must not fabricate), and a near-miss (a prompt that should route to `stock_valuation` instead,
  since that's the adjacent skill for individual equities vs. this skill's ETF/fund scope).
- [ ] **Step 3:** Validate JSON parses and has required top-level fields:
  ```bash
  python3 -c "import json; d=json.load(open('plugins/etf-analysis/skills/etf_analysis/evals/evals.json')); assert all(k in d for k in ['skill','version','description','scoring_version','evals','benchmark_targets']); assert len(d['evals'])>=4; print('OK', len(d['evals']), 'evals')"
  ```
- [ ] **Step 4: Commit and push**
  ```bash
  git add plugins/etf-analysis/skills/etf_analysis/evals/evals.json
  git commit -m "test: add eval coverage for etf_analysis skill"
  git push origin main
  ```

---

### Task 2: stock-valuation (3 files)

**Files:**
- Read: `plugins/stock-valuation/skills/stock-research/SKILL.md`,
  `plugins/stock-valuation/skills/forward-valuation-challenge/SKILL.md`,
  `plugins/stock-valuation/skills/valuation-math-validation/SKILL.md`, and the reference template
  `plugins/stock-valuation/skills/stock_valuation/evals/evals.json`
- Create: `plugins/stock-valuation/skills/stock-research/evals/evals.json`,
  `plugins/stock-valuation/skills/forward-valuation-challenge/evals/evals.json`,
  `plugins/stock-valuation/skills/valuation-math-validation/evals/evals.json`

- [ ] **Step 1:** Read all three `SKILL.md` files plus the `stock_valuation` template.
  `stock-research` is user-triggered (`/research-stock`); `forward-valuation-challenge` and
  `valuation-math-validation` are auto-activating, no direct trigger (per their `SKILL.md`
  "When This Skill Activates" sections) — their eval "trigger" category should test the
  *activation condition* (e.g. "does this fire for an AI-infrastructure ticker analysis") rather
  than a slash-command match.
- [ ] **Step 2:** Write all three eval files. `valuation-math-validation` should include a
  near_miss/negative case exercising one of its documented validation rules (e.g. percent-vs-decimal
  confusion, monotonicity violation) since that's the skill's entire purpose.
- [ ] **Step 3:** Validate all three:
  ```bash
  for f in plugins/stock-valuation/skills/stock-research/evals/evals.json \
           plugins/stock-valuation/skills/forward-valuation-challenge/evals/evals.json \
           plugins/stock-valuation/skills/valuation-math-validation/evals/evals.json; do
    python3 -c "import json; d=json.load(open('$f')); assert all(k in d for k in ['skill','version','description','scoring_version','evals','benchmark_targets']); assert len(d['evals'])>=4; print('OK: $f', len(d['evals']), 'evals')"
  done
  ```
- [ ] **Step 4: Commit and push**
  ```bash
  git add plugins/stock-valuation/skills/stock-research/evals/evals.json \
          plugins/stock-valuation/skills/forward-valuation-challenge/evals/evals.json \
          plugins/stock-valuation/skills/valuation-math-validation/evals/evals.json
  git commit -m "test: add eval coverage for stock-research, forward-valuation-challenge, valuation-math-validation"
  git push origin main
  ```

---

### Task 3: toolkit-manager (3 files — 1 upgrade + 2 new agent files)

**Files:**
- Read: `plugins/toolkit-manager/skills/run-screener/SKILL.md`,
  `plugins/toolkit-manager/skills/run-screener/evals/evals.json` (existing simple version),
  `plugins/toolkit-manager/agents/toolkit-onboarding-guide.md`,
  `plugins/toolkit-manager/agents/tradingview-onboarding.md`
- Modify: `plugins/toolkit-manager/skills/run-screener/evals/evals.json` (rewrite to rich schema)
- Create: `plugins/toolkit-manager/agents/evals/toolkit-onboarding-guide.json`,
  `plugins/toolkit-manager/agents/evals/tradingview-onboarding.json`

- [ ] **Step 1:** Read `run-screener`'s `SKILL.md` and its existing 3-eval simple-schema file
  (preserve its 3 existing scenarios' intent, just restructure into the rich schema and add more
  categories — don't lose the existing trigger-phrase coverage).
- [ ] **Step 2:** Rewrite `run-screener/evals/evals.json` to the rich schema.
- [ ] **Step 3:** Read both onboarding agent files in full — note their phase structure and what
  each phase routes to (`toolkit-onboarding-guide` routes to `tradingview-onboarding`, which itself
  now covers CDP health check, subscription tier, broker connection, first sync). Create
  `plugins/toolkit-manager/agents/evals/` and write both agent eval files there. For
  `toolkit-onboarding-guide`, include a near-miss case distinguishing it from directly invoking
  `tradingview-onboarding` (when should the master coordinator dispatch vs. when should the user go
  straight to the TradingView-specific agent).
- [ ] **Step 4:** Validate all three:
  ```bash
  for f in plugins/toolkit-manager/skills/run-screener/evals/evals.json \
           plugins/toolkit-manager/agents/evals/toolkit-onboarding-guide.json \
           plugins/toolkit-manager/agents/evals/tradingview-onboarding.json; do
    python3 -c "import json; d=json.load(open('$f')); assert all(k in d for k in ['skill','version','description','scoring_version','evals','benchmark_targets']); assert len(d['evals'])>=4; print('OK: $f', len(d['evals']), 'evals')"
  done
  ```
- [ ] **Step 5: Commit and push**
  ```bash
  git add plugins/toolkit-manager/skills/run-screener/evals/evals.json \
          plugins/toolkit-manager/agents/evals/toolkit-onboarding-guide.json \
          plugins/toolkit-manager/agents/evals/tradingview-onboarding.json
  git commit -m "test: upgrade run-screener evals to rich schema, add toolkit-manager agent eval coverage"
  git push origin main
  ```

---

### Task 4: portfolio-advisor batch 1 — 7 skill files

**Files:**
- Read + Create `evals/evals.json` for each:
  `plugins/portfolio-advisor/skills/rebalance-portfolio/`,
  `plugins/portfolio-advisor/skills/x-news-sweep/`,
  `plugins/portfolio-advisor/skills/daily-loop/`,
  `plugins/portfolio-advisor/skills/daily-brief/`,
  `plugins/portfolio-advisor/skills/adversarial-review/`,
  `plugins/portfolio-advisor/skills/thesis-challenge-bundler/`,
  `plugins/portfolio-advisor/skills/norberts-gambit/`

- [ ] **Step 1:** Read all 7 `SKILL.md` files. Note which are high-stakes (`rebalance-portfolio`
  touches live trade recommendations — give it the full 8-eval treatment matching
  `stock_valuation`'s depth, including a sycophancy case: user pushing for a bad rebalance despite
  SELL-rated holdings) vs. lower-stakes (`norberts-gambit` is a reference guide, 4-5 evals is
  sufficient).
- [ ] **Step 2:** Write all 7 eval files, each in `plugins/portfolio-advisor/skills/<name>/evals/evals.json`.
- [ ] **Step 3:** Validate all 7 with the same structural check pattern as Task 1/2 (loop over the
  7 paths, assert required fields + `len(evals)>=4`).
- [ ] **Step 4: Commit and push**
  ```bash
  git add plugins/portfolio-advisor/skills/rebalance-portfolio/evals/evals.json \
          plugins/portfolio-advisor/skills/x-news-sweep/evals/evals.json \
          plugins/portfolio-advisor/skills/daily-loop/evals/evals.json \
          plugins/portfolio-advisor/skills/daily-brief/evals/evals.json \
          plugins/portfolio-advisor/skills/adversarial-review/evals/evals.json \
          plugins/portfolio-advisor/skills/thesis-challenge-bundler/evals/evals.json \
          plugins/portfolio-advisor/skills/norberts-gambit/evals/evals.json
  git commit -m "test: add eval coverage for 7 portfolio-advisor skills (batch 1)"
  git push origin main
  ```

---

### Task 5: portfolio-advisor batch 2 — 6 skill files (incl. 2 scaffold fills) + 8 agent files

**Files:**
- Read + Create/Modify `evals/evals.json` for skills:
  `plugins/portfolio-advisor/skills/strategic-review/`,
  `plugins/portfolio-advisor/skills/thesis-review/`,
  `plugins/portfolio-advisor/skills/13f-analyze/`,
  `plugins/portfolio-advisor/skills/13f-tracker/`,
  `plugins/portfolio-advisor/skills/update-portfolio-targets/`,
  `plugins/portfolio-advisor/skills/ytd-return/`
- Modify (fill empty scaffolds): `plugins/portfolio-advisor/skills/calibrate-targets/evals/evals.json`,
  `plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json`
- Read + Create agent evals in `plugins/portfolio-advisor/agents/evals/`:
  `daily-loop-agent.json`, `data-quality-agent.json`, `portfolio-advisor-orchestrator.json`,
  `red-team-agent.json`, `risk-officer-agent.json`, `single-stock-advisor.json`,
  `thesis-review-agent.json`, `weekly-review-agent.json`

- [ ] **Step 1:** Read all 6 skill `SKILL.md` files and both existing empty-scaffold files (note
  their current `{"evals": []}` state — you're filling in real content, not just validating
  emptiness).
- [ ] **Step 2:** Write the 6 new skill eval files and fill both scaffolds with real content
  (rich schema, ≥4 evals each).
- [ ] **Step 3:** Read all 8 agent `.md` files in full. These are the highest-stakes agents in the
  repo (`risk-officer-agent` vetoes real trade orders, `red-team-agent` is mandatory before every
  valuation/rebalance presentation) — give these the full 8-eval treatment, including a
  near-miss case for each agent distinguishing it from the sibling agent most likely to be
  confused with it (e.g. `red-team-agent` vs. `risk-officer-agent` — one is adversarial critique,
  the other is a hard veto).
- [ ] **Step 4:** Create `plugins/portfolio-advisor/agents/evals/` and write all 8 agent eval
  files there.
- [ ] **Step 5:** Validate all 16 files (6 new + 2 filled scaffolds + 8 agent) with the same
  structural check pattern, looped over all 16 paths.
- [ ] **Step 6: Commit and push**
  ```bash
  git add plugins/portfolio-advisor/skills/strategic-review/evals/evals.json \
          plugins/portfolio-advisor/skills/thesis-review/evals/evals.json \
          plugins/portfolio-advisor/skills/13f-analyze/evals/evals.json \
          plugins/portfolio-advisor/skills/13f-tracker/evals/evals.json \
          plugins/portfolio-advisor/skills/update-portfolio-targets/evals/evals.json \
          plugins/portfolio-advisor/skills/ytd-return/evals/evals.json \
          plugins/portfolio-advisor/skills/calibrate-targets/evals/evals.json \
          plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json \
          plugins/portfolio-advisor/agents/evals/
  git commit -m "test: add eval coverage for 6 portfolio-advisor skills (batch 2), fill 2 empty scaffolds, add all 8 agent evals"
  git push origin main
  ```

---

### Task 6: tradingview batch 1 — 12 skill files

**Files:**
- Read + Create `evals/evals.json` for each:
  `plugins/tradingview/skills/place-order/`, `plugins/tradingview/skills/modify-order/`,
  `plugins/tradingview/skills/cancel-order/`, `plugins/tradingview/skills/get-orders/`,
  `plugins/tradingview/skills/alert-list/`, `plugins/tradingview/skills/alert-sync/`,
  `plugins/tradingview/skills/pine-inject/`, `plugins/tradingview/skills/author-pine-script/`,
  `plugins/tradingview/skills/tv-portfolio-sync/`, `plugins/tradingview/skills/tv-price-refresh/`,
  `plugins/tradingview/skills/tv-manage-watchlists/`, `plugins/tradingview/skills/chart-snapshot/`

- [ ] **Step 1:** Read all 12 `SKILL.md` files. `place-order` is the highest-stakes skill in this
  entire repo (live trade execution with real money) — give it the full 8-eval treatment
  including a hard negative (attempting to bypass the CONFIRM gate) and sycophancy case (user
  pressure to skip preflight). `modify-order`/`cancel-order`/`get-orders` are lower-stakes CRUD —
  4-5 evals each is sufficient.
- [ ] **Step 2:** Write all 12 eval files.
- [ ] **Step 3:** Validate all 12 with the structural check pattern, looped over all 12 paths.
- [ ] **Step 4: Commit and push**
  ```bash
  git add plugins/tradingview/skills/place-order/evals/evals.json \
          plugins/tradingview/skills/modify-order/evals/evals.json \
          plugins/tradingview/skills/cancel-order/evals/evals.json \
          plugins/tradingview/skills/get-orders/evals/evals.json \
          plugins/tradingview/skills/alert-list/evals/evals.json \
          plugins/tradingview/skills/alert-sync/evals/evals.json \
          plugins/tradingview/skills/pine-inject/evals/evals.json \
          plugins/tradingview/skills/author-pine-script/evals/evals.json \
          plugins/tradingview/skills/tv-portfolio-sync/evals/evals.json \
          plugins/tradingview/skills/tv-price-refresh/evals/evals.json \
          plugins/tradingview/skills/tv-manage-watchlists/evals/evals.json \
          plugins/tradingview/skills/chart-snapshot/evals/evals.json
  git commit -m "test: add eval coverage for 12 tradingview skills (batch 1)"
  git push origin main
  ```

---

### Task 7: tradingview batch 2 — 10 skill files + 1 agent file

**Files:**
- Read + Create `evals/evals.json` for each:
  `plugins/tradingview/skills/ta-snapshot/`, `plugins/tradingview/skills/ta-red-team/`,
  `plugins/tradingview/skills/technical-analysis-expert/`,
  `plugins/tradingview/skills/tv-add-indicator/`, `plugins/tradingview/skills/tv-change-symbol/`,
  `plugins/tradingview/skills/tv-change-type/`, `plugins/tradingview/skills/tv-chart-setup/`,
  `plugins/tradingview/skills/tv-save-indicator/`, `plugins/tradingview/skills/tv-setup/`,
  `plugins/tradingview/skills/ta-daily-sweep/`
- Read + Create: `plugins/tradingview/agents/evals/ta-guide.json`

- [ ] **Step 1:** Read all 10 `SKILL.md` files plus `agents/ta-guide.md`. `ta-red-team` is
  internal-only (dispatched by `technical-analysis-expert`, never invoked directly per its own
  `SKILL.md`) — its eval file should have no "trigger" category at all, only output-quality and
  schema categories. The 5 low-level CDP wrapper skills (`tv-add-indicator`, `tv-change-symbol`,
  `tv-change-type`, `tv-chart-setup`, `tv-save-indicator`) are simple single-purpose skills — 4
  evals each (trigger, one negative/edge case, schema) is sufficient, don't force 8.
- [ ] **Step 2:** Write all 10 skill eval files. Create `plugins/tradingview/agents/evals/` (may
  already exist if Task 3's toolkit-manager convention was followed identically — check first) and
  write `ta-guide.json`.
- [ ] **Step 3:** Validate all 11 files with the structural check pattern.
- [ ] **Step 4: Commit and push**
  ```bash
  git add plugins/tradingview/skills/ta-snapshot/evals/evals.json \
          plugins/tradingview/skills/ta-red-team/evals/evals.json \
          plugins/tradingview/skills/technical-analysis-expert/evals/evals.json \
          plugins/tradingview/skills/tv-add-indicator/evals/evals.json \
          plugins/tradingview/skills/tv-change-symbol/evals/evals.json \
          plugins/tradingview/skills/tv-change-type/evals/evals.json \
          plugins/tradingview/skills/tv-chart-setup/evals/evals.json \
          plugins/tradingview/skills/tv-save-indicator/evals/evals.json \
          plugins/tradingview/skills/tv-setup/evals/evals.json \
          plugins/tradingview/skills/ta-daily-sweep/evals/evals.json \
          plugins/tradingview/agents/evals/ta-guide.json
  git commit -m "test: add eval coverage for 10 tradingview skills (batch 2) and ta-guide agent"
  git push origin main
  ```

---

### Final verification (after all 7 tasks complete)

- [ ] **Run the full structural check across all 53 targets:**
  ```bash
  cd /Users/richardfremmerlid/Projects/InvestmentToolkit
  MISSING=0
  find plugins -name "SKILL.md" | while read f; do
    d=$(dirname "$f")
    if [ ! -f "$d/evals/evals.json" ]; then
      echo "MISSING: $d"
    fi
  done
  find plugins -path "*/agents/*.md" | while read f; do
    plugin_dir=$(dirname "$(dirname "$f")")
    agent_name=$(basename "$f" .md)
    if [ ! -f "$plugin_dir/agents/evals/$agent_name.json" ]; then
      echo "MISSING AGENT EVAL: $agent_name"
    fi
  done
  ```
  Expected: zero `MISSING` lines.
- [ ] **Confirm `run-screener` and both filled scaffolds are non-empty and rich-schema:**
  ```bash
  for f in plugins/toolkit-manager/skills/run-screener/evals/evals.json \
           plugins/portfolio-advisor/skills/calibrate-targets/evals/evals.json \
           plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json; do
    python3 -c "import json; d=json.load(open('$f')); assert 'benchmark_targets' in d; assert len(d['evals'])>=4; print('OK: $f')"
  done
  ```
