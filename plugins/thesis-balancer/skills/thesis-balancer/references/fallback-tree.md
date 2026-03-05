# Fallback Tree — thesis_balancer Skill

Procedural fallback sequences for brittle operations. Invoke immediately on failure — do NOT improvise or silently skip.

---

## FB-01: Backend API Unavailable

**Primary**: `curl -s http://localhost:3001/api/theses/:id/health`

| Step | Action | Exit Condition |
|------|--------|----------------|
| 1 | Retry once after 3 seconds | If succeeds → continue normal flow |
| 2 | Announce: "Portfolio API is unreachable. Switching to standalone mode." | |
| 3 | Request user paste: (a) current portfolio holdings with weights, (b) thesis target weights as JSON or table | Wait for user input |
| 4 | Validate pasted data has ticker, currentWeight, targetWeight fields for each holding | If missing → ask for specific fields |
| 5 | Compute drift manually: `drift = currentWeight - targetWeight` per holding. Classify > 5% as significant. | |
| 6 | Complete analysis without persistence. Note: "Thesis update not possible in standalone mode." | |
| **HALT** | If user cannot provide data → STOP. Report: "Insufficient portfolio data to perform analysis." | |

---

## FB-02: Thesis List Empty or No Active Thesis

**Primary**: `GET /api/theses` returns empty array or no active thesis

| Step | Action |
|------|--------|
| 1 | Inform user: "No theses found. Would you like to create one, or paste a thesis definition directly?" |
| 2 | If user pastes thesis JSON → validate structure (id, pillars, holdings with targetWeight) |
| 3 | Use pasted thesis for analysis; note "Using manually provided thesis — not persisted" in output |
| 4 | Recommend running the thesis setup flow to persist the thesis |

---

## FB-03: Health API Returns Unexpected Schema

**Trigger**: `/api/theses/:id/health` response missing `alerts`, `summary`, or `holdings` keys

| Step | Action |
|------|--------|
| 1 | Log the raw response output for user visibility |
| 2 | If `holdings` present but `alerts` missing → compute drift and alerts manually from holdings data |
| 3 | If `holdings` missing → invoke FB-01 (standalone fallback) |
| 4 | Note in Sources Checked: "Health API response incomplete — manual calculation applied" |

---

## FB-04: Conflicting Signals (Strategic Conflict Cannot Be Resolved)

**Trigger**: Tool A says SELL, thesis says Core AND ON_TARGET, and user declines to resolve

| Step | Action |
|------|--------|
| 1 | Flag holding with `⚠️ UNRESOLVED CONFLICT` in report |
| 2 | Continue analysis of all other holdings |
| 3 | Surface the unresolved conflict at the end of the report summary with timestamp |
| 4 | Suggest: "Consider running a fresh `/evaluate-stock {TICKER}` to see if the recommendation has changed." |
| **NEVER** | Auto-resolve a strategic conflict without explicit user instruction |
