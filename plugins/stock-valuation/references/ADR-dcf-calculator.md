# ADR: Canonical DCF Scenario Calculator

**Status**: Accepted  
**Date**: 2026-05-02  
**Area**: Stock Valuation Skill / Backend Python Services

---

## Context

During live stock valuations for GOOG, NVDA, and PANW, the AI agent computed all DCF
scenario math inline — ad-hoc Python snippets embedded directly in tool calls. This
approach has several compounding problems:

1. **No single source of truth** — the formula lived in a transient bash block, not a
   versioned file. Bugs (share-count errors, ordering constraint violations, rounding
   inconsistencies) were discovered and corrected mid-session but not systematically
   fixed for future runs.

2. **Hard to audit** — intermediate values (Year-5 revenue, undiscounted price,
   discount divisor) were scattered across multiple chat turns, making the full
   arithmetic impossible to review in one place.

3. **No reuse** — every new valuation re-derived the same formulas from scratch,
   introducing per-run transcription risk (e.g., using the wrong share count because
   no canonical default was codified).

4. **Silent validation drift** — constraint checks (weight sum = 1.0, growth ordering,
   PV ordering, QM documentation requirement) were verbal reminders, not enforced
   programmatically.

---

## Decision

Create a single canonical Python script,
`investment_screener/backend/py_services/dcf_scenarios.py`, as the **only authorised
calculation engine** for DCF scenario valuations.

### Key design choices

| Choice | Rationale |
|--------|-----------|
| CLI tool, not a library | Agents call it with a `bash` tool; no import chain needed |
| Reads `fetch_financials.py` output via `--raw` | Single integration point; agent doesn't have to re-extract base metrics |
| Scenario params via separate JSON file | Decouples "what to model" (agent decides) from "how to compute" (script decides) |
| JSON output to stdout | Composable with `jq`, `validate_projection.py`, and any future pipeline step |
| `sys.exit(1)` on validation failure | Hard stop for CI and agent workflow — prevents invalid projections from being persisted |
| All intermediate values in output | `year5Revenue`, `year5NetIncome`, `year5Shares`, `year5EPS`, `year5PriceUndiscounted`, `presentValue` — nothing is hidden |

### Formula (canonical)

```
Y5_revenue           = base_revenue × (1 + growthRate/100)^horizon
Y5_net_income        = Y5_revenue × (netMargin/100)
Y5_shares            = base_shares × (1 + shareChange/100)^horizon
Y5_EPS               = Y5_net_income / Y5_shares
Y5_price_undiscounted = Y5_EPS × exitPE × qualityMultiplier
present_value        = Y5_price_undiscounted / (1 + discountRate)^horizon
weighted_fair_value  = Σ (scenario.weight × scenario.presentValue)
```

### Validation enforced

- Weight sum: `|bear + base + bull - 1.0| ≤ 0.01` → hard error
- Growth ordering: `bear.growthRate < base.growthRate < bull.growthRate` → hard error  
- PV ordering: `bear.PV < base.PV < bull.PV` → hard error
- `shareChange` in `[-5, +5]` → hard error
- `netMargin` in `[0, 100]` → hard error
- `qualityMultiplier > 1.1` → warning (agent must cite moat in rationale)

---

## Consequences

### Positive

- **Reproducible** — same inputs always produce the same outputs; rounding is
  deterministic and documented.
- **Improvable** — when a formula bug is found (e.g., a new rule about hypergrowth
  CAGR derivation), it is fixed once in one file.
- **Auditable** — the full intermediate value chain is in the output JSON; every
  `analyticsLog.growthDerivation` entry can be traced back to script inputs.
- **Agent workflow integration** — SKILL.md Step 3 mandates calling this script;
  ad-hoc inline math is explicitly prohibited after this ADR.

### Negative / Trade-offs

- Adds a file the agent must maintain; if the script has a bug, all valuations are
  wrong until it is fixed. Mitigation: the validation block catches ordering and
  constraint violations immediately.
- Scenario parameters (growthRate, netMargin, etc.) must be serialised to a temp JSON
  file before calling the script, adding a small boilerplate step to the agent
  workflow.

---

## Usage in SKILL.md Workflow (Step 3)

```bash
# 1. Agent decides scenario parameters and writes them to a temp file
cat > /tmp/{TICKER}_scenarios.json << 'EOF'
{
  "bear":  { "weight": 0.20, "growthRate": 11, "netMargin": 9,  "exitPE": 20, "qualityMultiplier": 0.90, "shareChange": -0.5 },
  "base":  { "weight": 0.55, "growthRate": 19, "netMargin": 21, "exitPE": 30, "qualityMultiplier": 1.10, "shareChange": -2.0 },
  "bull":  { "weight": 0.25, "growthRate": 24, "netMargin": 27, "exitPE": 42, "qualityMultiplier": 1.20, "shareChange": -2.5 }
}
EOF

# 2. Run the canonical calculator (validates + computes all intermediates)
python3 investment_screener/backend/py_services/dcf_scenarios.py \
  --raw /tmp/{TICKER}_raw.json \
  --scenarios /tmp/{TICKER}_scenarios.json \
  --pretty
```

Output JSON provides all `year5*` fields needed to assemble the projection object
directly — no manual arithmetic required.

---

## Related Files

| File | Role |
|------|------|
| `investment_screener/backend/py_services/fetch_financials.py` | Upstream data source; `dcf_scenarios.py` reads its output |
| `plugins/stock-valuation/skills/stock_valuation/SKILL.md` | Mandates use of this script in Step 3 |
| `plugins/stock-valuation/skills/stock_valuation/scripts/validate_projection.py` | Downstream validator; consumes script output after projection assembly |
| `plugins/stock-valuation/skills/stock_valuation/references/examples/` | All v1.2+ example projections were generated using this script |
