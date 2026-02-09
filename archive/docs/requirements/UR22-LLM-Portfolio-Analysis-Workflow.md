# UR22: LLM-Driven Portfolio Analysis Workflow

## Overview
Enable an LLM to analyze current portfolio/account data, compare it against the investment thesis, and recommend improvements.

## Requirements

### Data Access
**Description:** LLM must be able to read and process all relevant data files.

**Requirements:**
- Access to `exportedData.json` (latest portfolio snapshot)
- Supporting markdown and code files
- Up-to-date and complete data exports

**Acceptance Criteria:**
- LLM can parse all data files
- Data export scripts ensure completeness
- Schema consistency maintained

### Thesis Integration
**Description:** LLM must access and parse the investment thesis.

**Requirements:**
- Read `InvestmentThesis/twin_revolution_ASI_and_Sovereign_finance.md`
- Extract pillar definitions and target allocations
- Parse sell discipline and risk criteria

**Acceptance Criteria:**
- Thesis content accessible to LLM
- Pillar definitions extractable
- Target allocations readable

### Prompt-Based Analysis
**Description:** Structured prompts guide LLM analysis.

**Requirements:**
- Template: `Prompts/portfolio_thesis_alignment_prompt.md`
- Instructions for:
  - Portfolio summary generation
  - Thesis vs actual comparison
  - Misalignment identification
  - Adjustment recommendations

**Acceptance Criteria:**
- Clear prompt templates
- Comprehensive analysis instructions
- Consistent output format

### Recommendations Output
**Description:** LLM provides actionable improvement recommendations.

**Output Requirements:**
- Portfolio summary table
- Thesis alignment analysis
- Actionable recommendations
- Rationale with thesis references

**Acceptance Criteria:**
- Markdown report format
- Clear recommendation structure
- Thesis-based rationale
- Implementable suggestions

### Workflow Documentation
**Description:** Complete end-to-end workflow documentation.

**Documentation Requirements:**
- Data export process
- LLM analysis execution
- Recommendation interpretation
- Implementation guidance

**Acceptance Criteria:**
- Step-by-step workflow
- Clear process documentation
- User-friendly instructions

## Technical Specifications

### Data Flow
```
Portfolio Data → Export → LLM Analysis → Recommendations → Implementation
```

### Prompt Structure
```markdown
# Portfolio Analysis Prompt

## Current Portfolio Data
[JSON data from exportedData.json]

## Investment Thesis
[Content from thesis markdown]

## Analysis Requirements
1. Summarize current allocations
2. Compare to thesis targets
3. Identify gaps and misalignments
4. Recommend adjustments
```

### Output Format
```markdown
# Portfolio Analysis Report

## Summary
[Portfolio overview]

## Alignment Analysis
[Thesis vs actual comparison]

## Recommendations
[Specific actionable items]

## Rationale
[Thesis-based explanations]
```

## Dependencies
- Data export functionality (UR21)
- Investment thesis document
- LLM analysis capabilities
- Prompt template system

## Operational & Error Modes (addition)

- API contract: POST `/api/run-analysis` → Body: `{ thesis?: string }` → Response: `{ success: boolean, analysis?: string, error?: string }`.
- Token caps and costs: enforce `BACKEND_AI_MAX_TOKENS` and `BACKEND_AI_TEMPERATURE` via env. Monitor and alert on token consumption.
- Error modes:
  - Missing API key → return 400/500 with friendly error telling operator to set `OPENAI_API_KEY`.
  - Provider error / timeout → return 503 with short message and retry suggestion.
  - Quota exceeded → return 429 with guidance for operators.

## Acceptance Criteria (addition)
- Analysis returned in under 15 seconds for 95% of requests (subject to provider SLAs).
- If `OPENAI_API_KEY` is missing, `/api/run-analysis` returns a clear, actionable error message.
- The analysis output adheres to the specified markdown structure and contains <=300 words for the summary section.

## Testing
- Data accessibility verification
- Thesis parsing validation
- Prompt effectiveness testing
- Output format compliance
- Recommendation accuracy assessment