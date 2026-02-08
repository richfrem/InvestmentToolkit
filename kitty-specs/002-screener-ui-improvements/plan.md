# Implementation Plan: Screener UI Improvements
*Path: [templates/plan-template.md](templates/plan-template.md)*

**Branch**: `002-screener-ui-improvements` | **Date**: 2026-02-07 | **Spec**: [spec.md](spec.md)

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `src/specify_cli/missions/software-dev/command-templates/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

This feature improves the usability and data accuracy of the "Market Intelligence" (formerly Investment Screener) application. Key components include:
1.  **Backend Data Fix**: Restoring Yahoo Finance integration to correctly populate valuation metrics (Growth, Margins, P/E) and adding analyst forecast data.
2.  **Valuation Layout Redesign**: Implementing a side-by-side, compact layout for the Valuation Modeler to eliminate scrolling on standard displays. Includes optimizing the header layout (moving search bar to top right).
3.  **Chart Enhancements**: consolidating analysis charts into a single multi-mode view and moving "Rule of 40" to its own tab.
4.  **Dashboard & Branding**: Renaming the app to "Market Intelligence", implementing a "Recently Viewed" dashboard, and ensuring navigation links work correctly.

## Technical Context

**Language/Version**: TypeScript (Frontend: React 19+), Python 3.x (Data Bridge)
**Primary Dependencies**:
- Frontend: `vite`, `tailwindcss`, `recharts`, `lucide-react`
- Backend: `express`, `child_process` (bridge)
- Data: `yfinance` (Python)
**Storage**: LocalStorage (for user preferences and saved projections)
**Testing**: Manual verification + existing unit tests (where applicable)
**Target Platform**: Web (Desktop optimized, 1080p+)
**Project Type**: Web application (Frontend + Backend + Python Bridge)
**Performance Goals**: Chart switching < 100ms; Valuation modeler updates < 16ms (60fps)
**Constraints**:
- Low-latency interactions for sliders.
- "Luxury Dark" theme adherence.
- No database; data is transient or ephemeral (LocalStorage).
**Scale/Scope**: ~5 major components, ~10 files modified.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Git/Worktree Protocol**: Will work in `main` for planning, then use `spec-kitty implement` for worktrees.
- [x] **Tech Constraints**: React 19, Tailwind, Node.js, Python bridge — aligns with standards.
- [x] **Testing**: Manual verification plan included in user stories.
- [x] **Destructive Safety**: No destructive commands planned.

## Project Structure

### Documentation (this feature)

```
kitty-specs/002-screener-ui-improvements/
├── plan.md              # This file
├── research.md          # Phase 0 output (Debugging findings)
├── data-model.md        # N/A (No DB)
├── quickstart.md        # N/A (Existing app)
├── contracts/           # Phase 1 output (Updated API types)
└── tasks.md             # Work packages
```

### Source Code (repository root)

```
tools/investment-screener/
├── backend/
│   ├── src/
│   │   ├── index.ts        # API endpoint updates
│   │   └── ...
│   └── py_services/
│       └── fetch_financials.py  # Yahoo bridge updates
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx       # Layout & Tab changes
│   │   │   ├── ValuationModeler.tsx # Layout redesign
│   │   │   ├── Sidebar.tsx         # Branding & Nav
│   │   │   ├── analysis/
│   │   │   │   ├── FinancialChart.tsx # New generic chart
│   │   │   │   └── AnalysisChartToggle.tsx # New component
│   │   │   └── ...
│   │   ├── services/
│   │   │   └── api.ts              # Interface updates
│   │   └── App.tsx                 # Routing updates
│   └── ...
└── ...
```

**Structure Decision**: Modifying existing `tools/investment-screener` project. No new top-level projects.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |