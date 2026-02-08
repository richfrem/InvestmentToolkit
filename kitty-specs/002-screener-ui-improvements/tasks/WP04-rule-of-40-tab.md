---
work_package_id: "WP04"
title: "Rule of 40 Separate Tab"
lane: "planned"
dependencies: ["WP02"]
subtasks: ["T018", "T019", "T020", "T021", "T022"]
---

# Work Package: Rule of 40 Separate Tab
**Priority**: P1
**Goal**: De-clutter the Analysis tab by moving Rule of 40 to its own top-level tab.

## Context
The Rule of 40 is a specific SaaS metric that deserves its own context. Moving it out allows the Analysis tab to focus on raw financials.

## Subtasks

### T018: Create `RuleOf40Page.tsx`
**Objective**: Scaffold the new component.
**Files**: `tools/investment-screener/frontend/src/components/RuleOf40Page.tsx` (NEW)
**Guidance**:
- Move `RuleOf40Chart` component usage here.
- Layout: Top card with the Score (Big number), Bottom card with the Chart.

### T019: Update Dashboard navigation
**Objective**: Add the 4th tab.
**Files**: `tools/investment-screener/frontend/src/components/Dashboard.tsx`
**Guidance**:
- Update tab state type: `type Tab = 'overview' | 'analysis' | 'ruleof40' | 'valuation'`.
- Add tab button "Rule of 40" in the navigation bar.
- Render `RuleOf40Page` when active.

### T020: Clean up Analysis tab
**Objective**: Remove old Rule of 40 code.
**Files**: `tools/investment-screener/frontend/src/components/Dashboard.tsx`
**Guidance**:
- Remove the `RuleOf40Chart` from the `analysis` view block (it should have been replaced entirely by `FinancialChart` in WP02, but verify cleanup).

### T021: Add educational content
**Objective**: Explain the metric to the user.
**Files**: `tools/investment-screener/frontend/src/components/RuleOf40Page.tsx`
**Guidance**:
- Add text: "The Rule of 40 states that a SaaS company's revenue growth rate + profit margin should exceed 40%."
- Show breakdown: "Your Score: X% (Growth) + Y% (Margin) = Z%".
- Warning logic: If Sector != Technology, show "⚠️ Relevance Warning: This metric is primarily for SaaS/Tech companies."

### T022: Styling
**Objective**: Match Luxury Dark theme.
**Files**: `tools/investment-screener/frontend/src/components/RuleOf40Page.tsx`
**Guidance**:
- Score color coding: Green if >= 40, Amber if < 40.
- Card backgrounds: `bg-slate-900` / `border-slate-800`.

## Validation
- **Manual Test**: Click "Rule of 40" tab.
- **Success Criteria**:
  - Tab works.
  - Chart renders correctly.
  - Score interpretation text is visible.
  - Analysis tab does NOT show Rule of 40.