---
description: "Perform AI-driven stock valuation (Bear-Base-Bull), persist projection, generate deep-dive research report, and engage in interactive analysis. Executing agent operates as autonomous analyst."
trigger: /evaluate-stock
args:
  - name: ticker
    required: true
    description: "Stock ticker symbol (e.g. NVDA, AAPL)"
  - name: model
    required: false
    default: "self"
    description: "Agent acting as analyst (default: self)"
---

# Evaluate Stock

## Execution Workflow

When triggered with `/evaluate-stock {TICKER}`:

### Phase 1: Preparation
1.  **Read Skill Instructions**: Load `.agent/skills/stock_valuation/SKILL.md` to understand the schema, constraints, and analysis framework.
2.  **Verify Backend**: Ensure the backend is reachable.
    ```bash
    curl -sf http://localhost:3001/health || echo "FAIL: Start backend with: python3 tools/manage_servers.py"
    ```

### Phase 2: Data Acquisition
3.  **Fetch Financial Data**: Execute the backend script to get raw data (Skill Step 1).
    ```bash
    python3 tools/investment-screener/backend/py_services/fetch_financials.py {TICKER} > /tmp/{TICKER}_raw.json
    ```
    *   **IF FAIL**: Stop and report error. Do not hallucinate data.

### Phase 3: Cognitive Analysis
4.  **Python Environment**: `yfinance` installed in current environment.
5.  **Build Snapshot**: Extract `price`, `currency`, `shares`, `revenue`, `fiscalPeriod` (Skill Step 2).
6.  **Analyze & Value**: (Skill Step 3). You are the expert analyst. Using `references/analysis_prompt.md`, generate Bear/Base/Bull scenarios.
    *   *Constraint Check*: Ensure `bear.growth < base.growth < bull.growth`.
    *   *Sanity Check*: Verify no >50% growth for mega-caps without explicit catalyst justification.

### Phase 4: Validation & Repair
7.  **Self-Correction**: (Skill Step 4). Before saving, validate your JSON:
    *   [ ] Weights sum to exactly **1.0** (±0.01). Rescale if needed.
    *   [ ] All numeric fields are `number` type (not strings).
    *   [ ] Values are within Zod schema bounds (e.g., max P/E 1000).
    *   [ ] `aiThesis.researchReport` field is set to `{TICKER}_{YYYY-MM-DD}.md`.

### Phase 5: Persistence — Projection JSON
8.  **Persist Projection**: (Skill Step 6). Save the valid JSON via CLI.
    ```bash
    cat /tmp/{TICKER}_projection.json | python3 tools/investment-screener/backend/py_services/persist_projection.py
    ```
    *   **Success**: Script outputs "Success" or "Updated existing...".
    *   **Error**: Script logs error to stderr and exits with non-zero code. Fix payload and retry ONCE.

### Phase 6: Persistence — Research Report
9.  **Generate Deep-Dive Report**: (Skill Step 7). Write a rich markdown research report.
    ```bash
    mkdir -p tools/investment-screener/backend/data/research
    cat > tools/investment-screener/backend/data/research/{TICKER}_{YYYY-MM-DD}.md << 'REPORT_EOF'
    <MARKDOWN_CONTENT following the template in SKILL.md Step 7>
    REPORT_EOF
    ```
    The report must include:
    *   TL;DR with fair value verdict
    *   Company snapshot table
    *   Investment thesis (3-5 paragraphs)
    *   Each scenario as 2-3 narrative paragraphs with assumption tables
    *   Transparent valuation math table
    *   Key risks (narrative, not just labels)
    *   What to Watch (specific events with dates)
    *   Comparables table
    *   Data quality & confidence assessment
    *   Empty Discussion Log section (populated during Q&A)

### Phase 7: Chat Summary & Interactive Analysis
10. **Conversational Summary**: (Skill Step 8). Present findings in chat using this format:

    ```
    **{TICKER}: {ACTION} — Fair value ${fair_value} vs ${price} ({+/-X%})**

    {2-3 sentences: plain-English thesis.}

    **Scenarios:**
    🐻 Bear ({weight}%): ${price} — {one sentence}
    ⚖️  Base ({weight}%): ${price} — {one sentence}
    🚀 Bull ({weight}%): ${price} — {one sentence, name catalyst}

    **Biggest risk**: {One sentence.}
    **Confidence**: {X}/1.0

    I've saved the projection and deep-dive report. Want me to stress-test
    any assumption or dig deeper into a scenario?
    ```

    **⚠️ CRITICAL**: Do NOT just output a table and stop. The chat summary is the analyst presenting to the portfolio manager. Be conversational, specific, and invite discussion. Point to the assumption you're least confident about.

11. **Interactive Q&A**: (Skill Step 9). Remain in analyst mode. Handle:
    *   **Assumption challenges** → recalculate, show delta, offer to save revised version
    *   **Sensitivity analysis** → recompute at different discount rates, growth, margins
    *   **Deep dives** → discuss moats, competitive dynamics, catalysts qualitatively
    *   **Cross-stock comparisons** → load other projections, compare side-by-side
    *   **Scenario what-ifs** → model extreme scenarios, discuss probability

    If Q&A leads to material changes:
    *   Recalculate affected scenarios and fair value
    *   Ask user: "Want me to save this as a revised version?"
    *   If yes: update projection JSON (bump `version`), append to Discussion Log in `.md`, re-persist both files

## Error Handling Matrix

| Error Condition | Action |
| :--- | :--- |
| **Data Fetch Fail** | **STOP**. Report error. |
| **Validation (400)** | Log error, fix payload constraints, retry once. |
| **Conflict (409)** | Get latest version from API, increment `version`, retry. |
| **Server Error** | Check logs. If transient, retry. |
| **Backend Offline** | Not an issue for persistence (CLI uses direct file IO). Fetching data still requires internet. |
| **Research dir missing** | Create with `mkdir -p`. |

## Reference Files

| Artifact | Path | Access |
| :--- | :--- | :--- |
| **Skill Definition** | `.agent/skills/stock_valuation/SKILL.md` | Read |
| **Analysis Prompt** | `.agent/skills/stock_valuation/references/analysis_prompt.md` | Read |
| **Fetch Script** | `tools/investment-screener/backend/py_services/fetch_financials.py` | Execute |
| **Persist Script** | `tools/investment-screener/backend/py_services/persist_projection.py` | Execute (stdin) |
| **Projections Dir** | `tools/investment-screener/backend/data/projections/` | Write |
| **Research Dir** | `tools/investment-screener/backend/data/research/` | Write |
| **API Endpoint** | `http://localhost:3001/api/projections` | POST (alternative) |
| **Research API** | `http://localhost:3001/api/research/:filename` | GET (for web app) |
