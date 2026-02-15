# Red Team Review — Round 2: Valuation Persistence + AI Agent Architecture
**Reviewer:** Claude (Opus 4.6)  
**Date:** 2026-02-14  
**Target Agent:** Gemini 3 Flash  
**Scope:** Architecture v2.0, ProjectionService, storage.ts refactor, Stock Valuation Skill, Workflow, ADR-020

---

## Round 1 Scorecard

Credit where it's due — Gemini addressed the majority of Round 1 criticals:

| Round 1 Finding | Status | Notes |
|---|---|---|
| C1. No input validation | ✅ Fixed | Zod schemas with range checks, weight sum validation |
| C2. Dual-write data loss | ✅ Fixed | API-first in `storage.ts`, errors re-thrown |
| C3. Non-atomic writes | ✅ Fixed | `.tmp` + `renameSync` pattern in ProjectionService |
| D1. Schema migration | ✅ Fixed | `migrateV1toV1_1()` with zero-weight bear/bull |
| D2. Insufficient snapshot | ⚠️ Partial | Fields added to Zod schema but not populated during migration |
| D3. Weight validation | ✅ Fixed | Zod `.refine()` with ±0.01 tolerance |
| D4. Concurrent access | ✅ Fixed | `proper-lockfile` on read-modify-write |
| A1. Per-ticker sharding | ✅ Fixed | `data/projections/{TICKER}.json` |
| A2. Migration registry | ❌ Not done | Single hardcoded migration, no registry |
| A4. aiThesis immutability | ❌ Not addressed | Nothing prevents mutation |

**Overall: Strong execution on the persistence layer.** Round 2 shifts focus to the new AI agent surface and the skill/workflow system, which is currently a skeleton that won't actually execute.

---

## 🔴 CRITICAL ISSUES

### C1. `syncProjections` Cannot Distinguish "Server Empty" from "Server Unreachable"

**Severity: CRITICAL — Silent data loss on network failure**

The code itself has comments acknowledging this problem (lines 719–731 in `storage.ts`) but doesn't fix it:

1. Backend crashes or network drops.
2. `fetchProjections()` catches the error and returns `[]`.
3. `syncProjections()` sees `serverProjections.length === 0` — indistinguishable from "no data exists."
4. User sees empty state with no error indication. If they then save, the write fails (backend down), but the *load* path already silently returned empty.

**Fix:** `fetchProjections` should return `null` on error, `[]` only for genuine empty/404. Then `syncProjections` can fall back to LocalStorage cache when `null` and display an "offline" indicator.

---

### C2. AI Agent and User Share the Same File with No Source Isolation

**Severity: CRITICAL — Agent can collide with user projections**

The architecture doc (§2.1, §4.2) specifies `source: 'USER' | 'SYSTEM' | 'AI_AGENT'` and a `ValuationBundle` wrapper. But the actual `ProjectionService.ts` stores everything as a flat `Projection[]`. The Zod schema has no `source` field. The `save_valuation.py` script (once built) will push into the same array as user saves, with no way to distinguish or protect user data.

**Fix:** Add `source` to the schema now, before implementing agent scripts. See A1 below for the recommended file structure.

---

### C3. Agent Pipeline Has No Authentication, Rate Limiting, or Cost Controls

**Severity: CRITICAL — Runaway LLM spend**

The architecture doc says "Cost Control: Backend agents must have rate limits" (§5) but nothing is implemented. The workflow just calls a Python script with no guardrails. See the detailed skill/workflow section (§S) below.

---

## 🟠 IMPORTANT ISSUES

### D1. Version Conflict Logic Is Confused

The `saveProjection()` method has ~15 lines of debating comments about whether the client or server increments version. The frontend never increments `version` before saving, so every re-save of the same projection triggers a false 409 Conflict (`existing.version >= incoming.version`).

**Fix:** Server-side increment. Client sends its current `version`, server checks `incoming.version === existing.version`, then saves as `version + 1`.

---

### D2. Migration Creates Financially Invalid Projections

`migrateV1toV1_1()` sets `snapshot.price = 0`, `shares = 0`, `revenue = 0`. Any upside % calculation will divide by zero. Mark these as `migrationStatus: 'incomplete'` and prompt the user to refresh.

---

### D3. Ticker Regex Mismatch

`isValidTicker` in `index.ts`: `[A-Z0-9.\-]{1,10}` (allows `BRK-B`, `BTC-USD`).  
Zod `tickerRegex`: `[A-Z]{1,5}(\.[A-Z]{1,3})?` (rejects hyphens, digits).  
Result: `BRK-B` passes the route but fails Zod validation. Use one canonical regex everywhere.

---

## 📋 §S — DEEP REVIEW: Agent Skill & Workflow System

This is the core section addressing whether `/evaluate-stock NVDA` will actually work end-to-end for an agent (Gemini 3 in Antigravity, Claude, etc.) and produce a valid `NVDA.json` projection identical in structure to what the web app creates.

### S1. The Skill Is a Narrative, Not an Executable Contract — Agent Will Fail

**Severity: CRITICAL for agent execution**

The current `SKILL.md` reads like a design doc, not an agent-executable skill. An AI agent needs **machine-parseable instructions** with exact schemas, constraints, and examples — not prose about what scripts "will" do. Here's what's missing and what to do:

**Missing piece 1: No output schema definition.**  
The skill says "Generate 3 scenarios (Bear, Base, Bull) with growth rates, margins, and exit multiples" but never specifies the exact JSON shape. The agent needs to see the `Projection` interface (matching the Zod schema) as a copy-pasteable reference, or it will hallucinate field names.

**Missing piece 2: No example input → output.**  
The single most effective way to get an LLM agent to produce correct output is a concrete example. The skill should include `references/example_NVDA.json` — a fully valid projection the agent can pattern-match against.

**Missing piece 3: No constraint specification.**  
The Zod schema enforces `growthRate: -100 to 1000`, `netMargin: -100 to 100`, `weights sum to 1.0`, etc. The agent doesn't know these bounds. It will generate values outside them, the POST will reject, and the workflow fails silently.

**Missing piece 4: The `references/` directory doesn't exist.**  
`analysis_prompt.md` and `schema_v2.md` are referenced but not in the bundle. These are the two most critical files.

**Recommended rewrite of SKILL.md:**

```markdown
---
name: stock_valuation
description: Perform autonomous stock valuation. Produces a Projection
  object saved to backend/data/projections/{TICKER}.json.
has_tools: true
---

# Stock Valuation Skill

## Quick Reference
- **Trigger**: /evaluate-stock {TICKER}
- **Output**: A valid Projection object (source: AI_AGENT)
- **Output Schema**: See references/projection_schema.json
- **Example**: See references/example_NVDA.json
- **Persistence**: POST to http://localhost:3001/api/projections

## Step 1: Fetch Financial Data
\`\`\`bash
python3 tools/investment-screener/backend/scripts/fetch_financials.py \
  --ticker {TICKER} --output /tmp/{TICKER}_raw.json
\`\`\`
Expected: JSON with keys: metrics, financials, estimates, profile.
If this fails, STOP and report the error.

## Step 2: Build Snapshot Object
From the raw data, extract:
\`\`\`json
{
  "price": <metrics.price>,
  "currency": <metrics.currency — 3-letter ISO code>,
  "shares": <metrics.shares_outstanding>,
  "revenue": <metrics.revenue — TTM>,
  "lastActualPS": <price × shares ÷ revenue>,
  "fiscalPeriod": "TTM ending {latest quarter}",
  "analystGrowthEstimate": <estimates.next_year_growth or null>,
  "analystMarginEstimate": <estimates.profit_margin or null>
}
\`\`\`

## Step 3: Cognitive Analysis — Generate Scenarios

YOU (the executing agent) are the analyst. Using the raw data from
Step 1, produce Bear/Base/Bull scenarios.

### HARD CONSTRAINTS (backend Zod validation will reject violations):
| Field             | Type   | Min   | Max   | Rule                                     |
|-------------------|--------|-------|-------|------------------------------------------|
| weight            | number | 0.0   | 1.0   | bear + base + bull MUST = 1.0 (± 0.01)  |
| growthRate        | number | -100  | 1000  | Annual revenue growth %                  |
| netMargin         | number | -100  | 100   | Net profit margin %                      |
| exitPE            | number | 0     | 1000  | Terminal P/E ratio                       |
| qualityMultiplier | number | 0.1   | 10.0  | Quality premium/discount on terminal PE  |
| shareChange       | number | -100  | 1000  | % change in shares (negative = buyback)  |
| rationale         | string | —     | 2000c | Per-scenario justification               |

### Logical ordering:
- Bear growthRate < Base growthRate < Bull growthRate
- Bear exitPE ≤ Base exitPE ≤ Bull exitPE
- All rationales must cite specific data from the financial input

### Prompt guidance for analysis:
See references/analysis_prompt.md for the full prompt template.
If unavailable, use this framework:
1. Identify the company's competitive position, growth drivers, and risks
2. Bear case: What breaks? Competition, margin compression, regulatory
3. Base case: Continuation of current trajectory with moderate assumptions
4. Bull case: What goes right? Market expansion, margin improvement, moat
5. Assign weights reflecting current market uncertainty (typical: 20/60/20)

## Step 3b: Validate & Repair Before Saving
Parse your own output and check:
1. Strip any markdown code fences from the JSON
2. Confirm all numeric fields are numbers (not strings like "65%")
3. Clamp any out-of-range values to schema bounds
4. If weights don't sum to 1.0, proportionally rescale them
5. Truncate rationale to 2000 chars if needed
6. Verify bear < base < bull ordering on growth and PE

## Step 4: Assemble the Full Projection Object
\`\`\`json
{
  "ticker": "{TICKER}",
  "id": "<generate a UUID v4>",
  "source": "AI_AGENT",
  "schemaVersion": "1.1",
  "version": 1,
  "savedAt": "<current ISO 8601 timestamp>",
  "updatedAt": "<current ISO 8601 timestamp>",
  "name": "AI Deep Dive — {TICKER} — {YYYY-MM-DD}",
  "rationale": "<1-paragraph overall thesis from your analysis>",
  "snapshot": { <from Step 2> },
  "dataPreferences": {
    "growthBasis": "next",
    "marginBasis": "ttm"
  },
  "scenarios": {
    "bear":  { "weight": 0.20, "growthRate": ..., "netMargin": ..., "exitPE": ..., "qualityMultiplier": ..., "shareChange": ..., "rationale": "..." },
    "base":  { "weight": 0.60, ... },
    "bull":  { "weight": 0.20, ... }
  },
  "aiThesis": {
    "model": "<your model name, e.g. gemini-3-pro or claude-opus-4.6>",
    "rationale": "<markdown reasoning trace — full analysis>",
    "fairValue": <probability-weighted target price: Σ weight × implied_price>,
    "action": "BUY" or "HOLD" or "SELL",
    "analyzedAt": "<current ISO 8601>"
  },
  "globalSettings": {
    "discountRate": 10.0,
    "timeHorizon": 5
  }
}
\`\`\`

## Step 5: Persist via HTTP API
\`\`\`bash
curl -X POST http://localhost:3001/api/projections \
  -H "Content-Type: application/json" \
  -d @/tmp/{TICKER}_projection.json
\`\`\`
- HTTP 200 → Success
- HTTP 400 → Validation failed. Read error, fix payload, retry ONCE.
- HTTP 409 → Version conflict. GET latest, increment version, retry.

## Step 6: Verify & Report
\`\`\`bash
curl http://localhost:3001/api/projections/{TICKER} | python3 -m json.tool
\`\`\`
Confirm the AI_AGENT projection appears. Report to the user:
- Fair Value: $XXX (XX% upside/downside from current $XXX)
- Action: BUY/HOLD/SELL
- Key thesis summary (2-3 sentences)
```

---

### S2. The Workflow File Doesn't Match How Agents Actually Execute

**Severity: HIGH**

The workflow (`evaluate-stock.md`) calls:
```bash
python3 .agent/skills/stock_valuation/stock_valuation/scripts/run_valuation_agent.py \
  --ticker {ticker} --model gemini-1.5-pro
```

**Problems:**
1. **The script doesn't exist.** None of the three referenced scripts (`run_valuation_agent.py`, `fetch_financials.py` in the skill dir, `save_valuation.py`) are implemented.
2. **Wrong model string.** `gemini-1.5-pro` vs `gemini-3-pro` vs `gemini-3-flash-preview` — inconsistent across docs.
3. **Duplicate directory nesting.** `.agent/skills/stock_valuation/stock_valuation/scripts/` has `stock_valuation` twice. Copy-paste artifact.
4. **The agent IS the orchestrator.** In Antigravity/Gemini, the AI agent reads the SKILL.md, follows steps using tool calls (bash, HTTP, file I/O), and performs the cognitive analysis *itself*. It doesn't need a Python wrapper script — the agent *is* the wrapper.

**Recommended workflow rewrite:**

```markdown
---
description: Perform AI-driven stock valuation and persist results.
trigger: /evaluate-stock
args:
  - name: ticker
    required: true
    description: Stock ticker symbol (e.g., NVDA, AAPL, BRK-B)
  - name: model
    required: false
    default: self
    description: "self" = executing agent performs analysis.
      Alternatively specify a model name for delegation.
---

# Perform Stock Valuation

## Execution
When triggered with `/evaluate-stock {TICKER}`:

1. Read and follow the skill at `.agent/skills/stock_valuation/SKILL.md`
2. Execute each step sequentially using your tool-calling capabilities
3. YOU perform the cognitive analysis (Step 3) — you are a frontier model
4. Persist the result via HTTP POST to the backend API
5. Report the summary to the user

## Prerequisites
- Backend server running on localhost:3001
  (verify: `curl http://localhost:3001/health`)
- Python 3.11+ with yfinance installed
- The skill file `.agent/skills/stock_valuation/SKILL.md` exists

## Error Recovery
- Data fetch failure → Report error, do not proceed
- POST 400 (validation) → Log error details, fix payload, retry once
- POST 409 (conflict) → GET current version, increment, retry
- Any other failure → Report to user with full error context
```

---

### S3. The Analysis Prompt Doesn't Exist — The Most Important File Is Missing

**Severity: CRITICAL for agent quality**

`references/analysis_prompt.md` is referenced but absent. This is the artifact that determines whether the agent produces sensible financial analysis or garbage. I've embedded a recommended prompt framework directly in the SKILL.md rewrite above (Step 3), but it should also exist as a standalone file for:
- Version control (you can iterate the prompt independently)
- Sharing between agents (Gemini and Claude can use the same prompt)
- A/B testing different prompt strategies

At minimum, `references/` must contain:
1. `analysis_prompt.md` — The full LLM prompt with constraints, rules, output format
2. `example_NVDA.json` — A complete valid projection as a reference example
3. `projection_schema.json` — The Zod schema exported as JSON Schema for cross-language use

---

### S4. Two Different AI Output Shapes — Skill vs Web App

**Severity: MEDIUM — Needs explicit documentation**

The web app's `/api/analysis/valuation` returns a flat `ValuationResult` (single fair value, single growth suggestion). The user clicks "Apply AI Suggestions" to map these into slider values.

The agent skill produces a full multi-scenario `Projection` with `source: AI_AGENT` that is saved directly — no user interaction needed.

**These serve different purposes, which is fine**, but the SKILL.md and architecture doc conflate them. The skill should explicitly state:

> The agent's output is a **first-class Projection** (source: AI_AGENT), structurally identical to a user save. It is NOT the same as the `ValuationResult` from `/api/analysis/valuation`, which is a lightweight UI suggestion. The agent's projection appears alongside user projections in the UI, filterable by source.

---

### S5. `save_valuation.py` Should Not Exist — Agent Should Use the HTTP API

**Severity: MEDIUM**

The skill proposes `save_valuation.py` to handle "locking and merging." This duplicates the Express middleware (CORS, payload limit, Zod validation, conflict detection, atomic writes) in Python. If the schema changes, you have two codepaths to update.

**The agent should POST to `http://localhost:3001/api/projections`** — same as the frontend. This guarantees identical validation. The only prerequisite is that the backend is running, which the workflow already lists as a prerequisite.

---

### S6. Duplicate `fetch_financials.py` — Use the Canonical Backend Script

The skill references a copy at `.agent/skills/.../scripts/fetch_financials.py`, but the backend already has one invoked via `spawnPythonScript('fetch_financials.py', [ticker])`. Use the canonical backend script to avoid drift:
```bash
python3 tools/investment-screener/backend/scripts/fetch_financials.py --ticker {TICKER}
```

If the skill needs additional data (4 years of historicals vs the standard fetch), extend the backend script with a `--full` flag rather than maintaining a separate copy.

---

### S7. No Validation Gate Between LLM Output and Save

**Severity: HIGH**

LLMs routinely return: `exitPE: 1500` (out of range), weights summing to 0.97, `growthRate: "65%"` (string), JSON wrapped in markdown fences. The skill needs a **validate + repair** step before POSTing. I've included this as Step 3b in the recommended SKILL.md rewrite above.

---

### S8. Workflow Frontmatter Needs a Trigger Contract

For Antigravity to recognize `/perform-stock-valuation NVDA`, the workflow frontmatter must specify a `trigger` pattern and `args` definition. The current frontmatter only has `description`. See the recommended rewrite in S2 above.

---

## 🟡 ARCHITECTURAL RECOMMENDATIONS

### A1. Adopt the `ValuationBundle` File Format Now

The flat `Projection[]` array doesn't structurally separate sources. Recommended `NVDA.json`:
```json
{
  "ticker": "NVDA",
  "schemaVersion": "2.0",
  "userProjections": [ ... ],
  "systemBaseline": null,
  "aiTheses": [ ... ],
  "history": [ ... ]
}
```

### A2. Add a Diff Endpoint for Ghost Sliders

`GET /api/projections/:ticker/diff` → comparison between latest user projection and latest AI thesis. Server-computed, frontend-consumed.

### A3. LLM Output Sanity Bounds (Sector-Aware)

Flag AI output if: growth > 200% for a company with revenue > $50B, or net margin > 70% for non-software. These heuristics catch hallucinations.

---

## 🧪 VERIFICATION TESTS

| # | Test | Expected |
|---|------|----------|
| T11 | Backend down → `syncProjections` | Returns LocalStorage cache, not `[]`; shows offline indicator |
| T12 | Agent saves for same ticker as user | Both coexist; distinguishable by `source` field |
| T13 | Frontend re-saves version 3 | Server accepts, increments to 4 (not 409) |
| T14 | Migrated projection `price: 0` in UI | No divide-by-zero; shows "incomplete" banner |
| T15 | Save projection for `BRK-B` | Passes both route and Zod validation |
| T16 | `/evaluate-stock NVDA` end-to-end | Fetches data → generates scenarios → POSTs → appears in NVDA.json with source AI_AGENT |
| T17 | Agent returns weights summing to 0.95 | Repair step normalizes; save succeeds |
| T18 | Agent returns `growthRate: "65%"` (string) | Repair step coerces to 65; save succeeds |
| T19 | Agent runs 20 times in 5 minutes | Rate limiter blocks after N |
| T20 | Agent output checked against Zod schema | All fields present, all types correct, weights sum to 1.0 |
| T21 | Skill SKILL.md references all exist | `references/analysis_prompt.md`, `example_NVDA.json`, `projection_schema.json` all present |
| T22 | Agent and web app AI for same ticker | Both produce valid Projections; agent has `source: AI_AGENT`, web app stores via user "Apply" flow |

---

## Priority Actions for Gemini

### Immediate — Unblock Agent Execution:
1. **Add `source` field** to Zod schema and Projection type (`'USER' | 'SYSTEM' | 'AI_AGENT'`)
2. **Write `references/analysis_prompt.md`** — the actual LLM prompt with constraints and expected JSON shape
3. **Write `references/example_NVDA.json`** — a complete valid projection as a concrete example
4. **Rewrite SKILL.md** as executable agent instructions using the template in §S1 above
5. **Rewrite workflow frontmatter** with `trigger` and `args` per §S2
6. **Fix the path**: `.agent/skills/stock_valuation/SKILL.md` not `.../stock_valuation/stock_valuation/...`
7. **Delete phantom scripts** (`run_valuation_agent.py`, `save_valuation.py`) — the agent uses HTTP API + SKILL.md directly

### Before Agent Goes Live:
8. Fix `fetchProjections` null vs empty (C1)
9. Align ticker regex (D3)
10. Fix version conflict — server-side increment (D1)
11. Add validation + repair step guidance to SKILL.md (S7)
12. Add rate limiting and execution logging (C3)

### Quality of Life:
13. Fix migration zero-value snapshots (D2)
14. Adopt `ValuationBundle` file format (A1)
15. Build migration registry (Round 1 A2, still open)
16. Deduplicate `fetch_financials.py` — one canonical script (S6)
