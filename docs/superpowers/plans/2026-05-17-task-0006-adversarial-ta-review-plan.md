# Task 0006 Implementation Plan: Adversarial TA Review Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a structured TA thesis template and an adversarial review loop for the Technical Analysis Expert agent.

**Architecture:** A new Markdown template will standardize the thesis. A new skill `ta-red-team` will provide the adversarial persona. The `tv-ta-deep` skill will be updated to manage the loop.

**Tech Stack:** Claude/Gemini CLI (Markdown skills/templates).

---

### Task 1: Create the TA Thesis Template

**Files:**
- Create: `plugins/tradingview/assets/ta_thesis_template.md`

- [ ] **Step 1: Write the template**

```markdown
# TA Thesis Draft: {{ticker}}

## 1. Context & Data Points
- **Timeframes Analyzed:** {{timeframes}}
- **Key Indicators:**
{{indicator_data}}

## 2. Analysis & Rationale
{{rationale}}

## 3. Recommendation
- **Action:** {{action}}
- **Limit Prices:** {{limit_prices}}
- **Stop Loss (if applicable):** {{stop_loss}}

---
**Review Status:** [DRAFT]
```

- [ ] **Step 2: Commit**
```bash
git add plugins/tradingview/assets/ta_thesis_template.md
git commit -m "feat(tradingview): add TA thesis template"
```

### Task 2: Create the TA Red Team Skill

**Files:**
- Create: `.agents/skills/ta-red-team/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

```markdown
# ta-red-team

**Description:** Performs adversarial red-team review of technical analysis theses to ensure logic and data integrity.

**Trigger:** Dispatched via `gemini-cli-agent` or `claude-cli-agent`.

**Instructions:**
1. You are a Senior Risk Manager and Skeptical Proprietary Trader.
2. Read the provided `ta_thesis_draft.md`.
3. Challenge the analysis:
   - Does the data in section 1 actually justify the recommendation in section 3?
   - Are the limit prices consistent with the support/resistance mentioned in the rationale?
   - Is there any contradictory evidence (e.g., bearish RSI divergence) that was ignored?
4. **Conclusion:** You MUST end your response with exactly `[APPROVED]` or `[REJECTED]`. If rejected, provide clear, critical feedback on what needs to be fixed.
```

- [ ] **Step 2: Commit**
```bash
git add .agents/skills/ta-red-team/SKILL.md
git commit -m "feat(agents): add TA red team adversarial skill"
```

### Task 3: Update `tv-ta-deep` Skill to Implement the Loop

**Files:**
- Modify: `.agents/skills/technical-analysis-expert/SKILL.md` (created in Task 0005)

- [ ] **Step 1: Update the instructions to include the loop**

```markdown
// Add this to the "Instructions" section of the TA Expert skill:
6. Once analysis is complete, populate `plugins/tradingview/assets/ta_thesis_template.md` and save as `InvestmentToolkit/temp/ta_thesis_draft.md`.
7. Dispatch the red team for review:
   `<Bash> gemini-cli-agent --skill ta-red-team --file InvestmentToolkit/temp/ta_thesis_draft.md </Bash>`
8. If the response contains `[REJECTED]`, read the feedback, re-analyze the chart if needed, and rewrite the draft. Repeat Step 7.
9. If the response contains `[APPROVED]`, present the final, vetted thesis to the user.
```

- [ ] **Step 2: Commit**
```bash
git add .agents/skills/technical-analysis-expert/SKILL.md
git commit -m "feat(agents): implement adversarial review loop in TA expert skill"
```