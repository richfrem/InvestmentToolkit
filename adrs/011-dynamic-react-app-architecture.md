# ADR 011: Dynamic React App Architecture for Portfolio Analysis

## Status
Proposed

## Context
To support real-time portfolio analysis, continuous improvement of prompts, and interactive visualization, a dynamic React + Node.js architecture is required. This enables:
- Direct integration with Questrade APIs for live data.
- Aggregation and mapping of holdings to thesis pillars and target allocations.
- Interactive dashboards with charts, tables, and feedback-driven prompt improvement.

## Decision
- The backend (Node.js/Express) will:
  - Integrate with Questrade API (OAuth2, REST).
  - Aggregate, store, and serve portfolio/account/holdings data via REST endpoints.
  - Implement portfolio alignment logic and prompt improvement API.
- The frontend (React) will:
  - Display asset allocation, gaps, and thesis alignment with interactive charts and tables.
  - Allow user feedback and prompt improvement directly in the UI.
  - Continuously sync with backend for live data and analysis.
- The workflow will support versioned prompt storage, user customization, and automated rebalancing alerts.

## Consequences
- Enables dynamic, real-time portfolio analysis and visualization.
- Supports continuous improvement of analysis prompts and logic.
- Provides a scalable foundation for future automation and LLM integration.

---

**Related Requirements:**
- UR24: Dynamic React App for Portfolio Analysis
- UR25: Continuous Prompt Improvement Workflow
