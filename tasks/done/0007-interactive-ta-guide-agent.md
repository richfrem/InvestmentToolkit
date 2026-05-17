# 0007: Interactive TA Guide Agent

## Objective
Create a conversational agent that guides users through a complete technical analysis of any stock or ETF, explaining each indicator in plain language and orchestrating the full /tv-ta-deep adversarial pipeline.

## Context
The Technical Analysis Expert (/tv-ta-deep) and Red Team (ta-red-team) skills exist and work. They produce rigorous, machine-structured output but require the user to understand the format. This agent wraps those skills in an interactive, educational conversation that:
- Asks for the ticker and timeframe
- Reads the Data Window live and explains what each indicator reading means
- Optionally injects a custom indicator bundle if the chart is sparse
- Dispatches /tv-ta-deep for structured analysis + adversarial red-team review
- Presents the vetted thesis in plain English, explaining what the red team challenged

## Relationship to Other Tasks
Builds on Task #0005 (TA Expert) and Task #0006 (Red Team Loop). Does not modify either skill — purely an orchestration layer.
