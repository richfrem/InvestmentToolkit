# Task 0006 Design: Adversarial TA Review Loop

## 1. Overview
This spec outlines the addition of an adversarial "Red Team" review loop to the Technical Analysis Expert (`tv-ta-deep`) skill. Before presenting any TA recommendations to the user, the agent must document its rationale in a structured template and defend it against an independent Skeptical Risk Manager sub-agent.

## 2. Architecture & Components

### 2.1 TA Thesis Template
- **Location:** `plugins/tradingview/assets/ta_thesis_template.md` (or `.agents/assets/`)
- **Structure:**
  - **Asset:** (e.g., AMD)
  - **Key Data Points:** (Extracted from CDP Data Window across timeframes)
  - **Recommendation:** (Initiate/Accumulate/Trim/Exit)
  - **Limit Prices:** (Specific numerical targets)
  - **Strategic Rationale:** (Defensible explanation)

### 2.2 Adversarial Review Agent Skill
- **Location:** `.agents/skills/ta-red-team/SKILL.md`
- **Role:** Skeptical Senior Risk Manager / Proprietary Trader.
- **Responsibility:** Review the populated TA Thesis against strict logic checks. Does the data actually support the conclusion? Are the limit prices realistic?
- **Output:** Must end its response with either `[APPROVED]` or `[REJECTED]` followed by specific critique.

### 2.3 The Review Loop (via `tv-ta-deep`)
- When `tv-ta-deep` finishes extracting CDP data, it populates the template and saves it to `InvestmentToolkit/temp/ta_thesis_draft.md`.
- It then dispatches the `gemini-cli-agent` (or `claude-cli-agent`) loaded with the `ta-red-team` skill to review the draft.
- **If `[REJECTED]`:** `tv-ta-deep` reads the critique, adjusts its logic, rewrites the draft, and resubmits to the red team.
- **If `[APPROVED]`:** `tv-ta-deep` reads the approved draft and presents the final, vetted recommendation to the user.

## 3. Data Flow
1. **CDP Extraction:** `tv-ta-deep` gets live data from TradingView.
2. **Drafting:** Writes `temp/ta_thesis_draft.md`.
3. **Dispatch:** Calls `<Bash> gemini-cli-agent --skill ta-red-team --file temp/ta_thesis_draft.md </Bash>`
4. **Iterate:** If rejected, rewrite and goto 3.
5. **Finalize:** Present approved thesis to user.

## 4. Rationale
By forcing the TA agent to formally document its reasoning and pass a rigorous automated peer review, we significantly reduce hallucination and ensure that only highly defensible trading advice is surfaced to the user. This aligns perfectly with the adversarial nature of the broader `portfolio-advisor` suite (e.g., `strategic-review`).