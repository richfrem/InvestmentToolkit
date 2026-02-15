# Red Team Review: Thesis Balancer (Tool B)

You are acting as **Opus**, the Senior Architect and Security Lead. 
Your goal is to "Red Team" the implementation of the **Thesis Balancer (Tool B)**.

## Scope
Review the following implementation artifacts against the architectural intent.

### 1. Intelligence & Safety
- **Prompt Logic**: Does `rebalance_prompt.md` sufficiently constrain the LLM from suggesting dangerous trades (e.g. 100% allocation to a meme coin)?
- **Strategic Checks**: Does the `SKILL.md` and `review-portfolio.md` workflow actually force the user to validate their thesis before acting?
- **Hallucination Risk**: Is the data injection into `optimizePortfolio` robust enough to prevent the LLM from making up prices?

### 2. Architecture Alignment
- **Data Layer**: Does `ThesisService.ts` correctly implement the atomic write patterns defined in the core architecture?
- **Integration**: Does the `fetch_portfolio_snapshot.py` script align with our "Python Bridge" pattern?
- **Sequence**: Does the implementation match the flow described in `thesis_alignment_sequence.mmd`?

### 3. Code Quality
- Are there any obvious race conditions or lack of error handling in the new endpoints?
- Is the `zod` schema strict enough?

## Deliverable
Provide a **Critical Review Report** with:
1.  **Stop-Ship Bugs**: Any safety or data loss risks.
2.  **Architecture Violations**: Deviations from the `mmd` or standard patterns.
3.  **Intelligence Gaps**: Where the agent might be "dumb" or "rigid".
