# Fallback Tree — stock_valuation Skill

Procedural fallback sequences for brittle operations. Consult this file when a primary method fails before reporting an error.

---

## FB-01: Financial Data Fetch Failure

**Primary**: `python3 tools/.../fetch_financials.py {TICKER} > /tmp/{TICKER}_raw.json`

| Step | Action | Exit Condition |
|------|--------|----------------|
| 1 | Re-run fetch once with 5-second delay | If succeeds → continue normal flow |
| 2 | Check if `/tmp/{TICKER}_raw.json` already exists from a prior run today | If file is < 4 hours old → offer to reuse it with explicit user acknowledgement |
| 3 | Announce degraded mode: "I cannot reach the data source. Please paste the raw financial JSON below." | Wait for user paste |
| 4 | Validate pasted JSON has `metrics`, `financials`, `estimates`, `profile` keys | If invalid → ask user to correct specific missing keys |
| 5 | Proceed with pasted data; set `confidenceScore ≤ 0.6` and add `"Manual data input — unverified"` to `dataQualityFlags` | |
| **HALT** | If no data after step 4 and user cannot provide → STOP. Report: "Insufficient data to perform valuation for {TICKER}." | |

---

## FB-02: Backend Health Check Failure

**Primary**: `curl -sf http://localhost:3001/health`

| Step | Action | Exit Condition |
|------|--------|----------------|
| 1 | Retry health check once after 3 seconds | If OK → continue |
| 2 | Announce: "Backend server is unreachable. Persistence and full data fetch are unavailable. Proceeding in standalone mode." | |
| 3 | Execute FB-01 (data fallback) to gather data | |
| 4 | Complete full cognitive analysis and produce research report | |
| 5 | Write report to `/tmp/{TICKER}_standalone_{DATE}.md` and inform user of path | Skip persist_projection.py entirely |

---

## FB-03: Projection Persistence Failure

**Primary**: `cat /tmp/{TICKER}_projection.json | python3 tools/.../persist_projection.py`

| Step | Action | Exit Condition |
|------|--------|----------------|
| 1 | Check exit code. If 400 (validation error) → fix payload (normalize weights, cast string numbers) and retry once | If OK → done |
| 2 | If 409 (conflict) → increment `version` field by 1, retry once | If OK → done |
| 3 | If still failing → save raw JSON to `/tmp/{TICKER}_projection_FAILED_{TIMESTAMP}.json` and inform user of the path | |
| 4 | Ask user: "Would you like me to retry persistence, or continue to the research report?" | Continue on user confirmation |
| **NEVER** | Do NOT silently swallow the error. Always report persistence failure explicitly. | |

---

## FB-04: Research Report Write Failure

**Primary**: `cat > tools/.../data/research/{TICKER}_{DATE}.md`

| Step | Action |
|------|--------|
| 1 | If directory missing → `mkdir -p` and retry |
| 2 | If permission error → write to `/tmp/{TICKER}_{DATE}_research.md` and inform user |
| 3 | Present full report inline in chat as backup |

---

## FB-05: Valuation Math Inconsistency Detected

**Trigger**: `year5Revenue`, `year5NetIncome`, or `scenarioPrice` do not match stated assumptions arithmetic.

| Step | Action |
|------|--------|
| 1 | Recompute all three scenarios' arithmetic from scratch in the scratchpad |
| 2 | Correct mismatched fields |
| 3 | Re-validate weight sum |
| 4 | Re-run Step 4 (Validate & Repair) before proceeding |
| **Never** | Do NOT present inconsistent numbers to the user |
