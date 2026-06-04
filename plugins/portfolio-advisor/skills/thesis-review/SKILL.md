---
name: thesis-review
plugin: portfolio-advisor
description: >
  The interactive entry point for pitching a new investment thesis or challenging
  an existing one. Triggers the Investment Committee agent to systematically intake 
  the document, run adversarial research (DCF + Grok), calibrate capital allocation, 
  and update targets.
  Trigger on /pitch-thesis, "propose new thesis", "I have a new idea", or
  "let's add a new strategy".
allowed-tools: Bash, Read, Write
---

## Thesis Review Workflow

This skill is a delegator. When triggered, your primary job is to hand off control to the `thesis-review-agent`.

### Step 1: Delegate to Agent
You should invoke the Agentic OS sub-agent system to run the `thesis-review-agent`.
Inform the user that the Investment Committee is ready to hear their pitch.

### Scripts & References
The agent will need access to these canonical files and scripts. They are provided as file-level symlinks in this skill's `scripts/` and `references/` directories:

- `references/investment_thesis.md` (The canonical thesis document)
- `scripts/update_targets.py` (Updates target-portfolio.json)
- `scripts/validate_weights.py` (Ensures targets sum to 100%)
- `scripts/generate_portfolio_blueprint.py` (Regenerates the markdown tables)

Do NOT run these scripts yourself. The `thesis-review-agent` will use them in Phase 4 of its workflow.
