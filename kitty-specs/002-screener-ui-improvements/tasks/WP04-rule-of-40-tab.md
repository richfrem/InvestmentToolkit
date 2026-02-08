---
work_package_id: "WP04"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
title: "Rule of 40 Separate Tab"
phase: "Phase 2 - Core Features"
lane: "planned"
dependencies: ["WP02"]
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-02-08T02:11:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Rule of 40 Separate Tab

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Navigation shows 4 tabs: Overview | Analysis | Rule of 40 | Valuation.
- Rule of 40 tab displays the existing chart with added educational context.
- Analysis tab no longer contains the Rule of 40 chart (clean separation).

## Context & Constraints

- **Current state**: Analysis tab has 2-column grid: RuleOf40Chart + FundamentalChart.
- **After WP02**: Analysis tab already has the new toggle chart. This WP removes the Rule of 40 remnant and creates its dedicated tab.
- **Key Files**:
  - `frontend/src/pages/Dashboard.tsx` (139 lines) — tab management
  - `frontend/src/components/Charts/RuleOf40Chart.tsx` (69 lines) — existing chart component
  - `frontend/src/components/MetricsGrid.tsx` (110 lines) — has Rule of 40 card

## Implementation Command

```bash
spec-kitty implement WP04 --base WP02
```

## Subtasks & Detailed Guidance

### Subtask T018 – Create RuleOf40Page Component

- **Purpose**: Dedicated view for Rule of 40 analysis.
- **Steps**:
  1. Create `frontend/src/components/RuleOf40Page.tsx`.
  2. Layout:
     - Top: Score display card (large number, color-coded green if >= 40, red if < 40)
     - Middle: Existing `RuleOf40Chart` component (full width)
     - Bottom: Breakdown card showing Revenue Growth % + EBITDA Margin % = Score
  3. Props: `{ stockData: StockData }`
  4. Reuse the existing `RuleOf40Chart` component as-is.
- **Files**: `frontend/src/components/RuleOf40Page.tsx` (new, ~80 lines)

### Subtask T019 – Add Rule of 40 Tab to Navigation

- **Purpose**: Add 4th tab to the Dashboard tab bar.
- **Steps**:
  1. In `Dashboard.tsx`, update the Tab type:
     ```typescript
     type Tab = 'overview' | 'analysis' | 'ruleof40' | 'valuation';
     ```
  2. Add the new tab button between Analysis and Valuation in the tab bar.
  3. Icon suggestion: use a chart-trending icon or a "40" badge.
  4. Render `<RuleOf40Page stockData={stockData} />` when `activeTab === 'ruleof40'`.
- **Files**: `frontend/src/pages/Dashboard.tsx`

### Subtask T020 – Remove Rule of 40 from Analysis Tab

- **Purpose**: Clean separation — Analysis tab focuses on financial charts only.
- **Steps**:
  1. In `Dashboard.tsx`, the Analysis tab rendering should only show the chart toggle + FinancialChart (from WP02).
  2. Remove the `RuleOf40Chart` import/usage from the Analysis tab section.
  3. Do NOT delete `RuleOf40Chart.tsx` — it's reused in the new tab.
- **Files**: `frontend/src/pages/Dashboard.tsx`

### Subtask T021 – Add Contextual Content to Rule of 40 Page

- **Purpose**: Educational context for users who may not know Rule of 40.
- **Steps**:
  1. Add an info card below the chart with:
     - **What is Rule of 40?**: "A benchmark for SaaS and tech companies. A combined Revenue Growth Rate + EBITDA Margin of 40% or more indicates a healthy, well-balanced company."
     - **Score Interpretation**: "≥ 40%: Healthy balance of growth and profitability. < 40%: May indicate the company is sacrificing too much growth or profitability."
     - **Sector Warning**: If `stockData.profile.sector` is not Technology/Communication, show amber warning: "Rule of 40 is most applicable to SaaS/Technology companies. Results for {sector} companies should be interpreted with caution."
  2. Style: Use `bg-slate-800/50 border-slate-700` card with subtle amber accent for the warning.
- **Files**: `frontend/src/components/RuleOf40Page.tsx`

### Subtask T022 – Style Rule of 40 Page

- **Purpose**: Ensure visual consistency with the Luxury Dark theme.
- **Steps**:
  1. Score card: Large score number (`text-4xl font-bold`), color-coded (`text-green-400` if >= 40, `text-red-400` if < 40).
  2. Breakdown: Two sub-values side by side (Revenue Growth + EBITDA Margin) with a "+" symbol and "=" result.
  3. Chart takes full width with proper padding.
  4. Info cards use the existing card styling pattern from MetricsGrid.
- **Files**: `frontend/src/components/RuleOf40Page.tsx`
- **Parallel?**: Yes — styling can proceed independently.

## Risks & Mitigations

- 4 tabs may feel crowded on narrow screens → consider responsive tab behavior (scroll or dropdown on mobile).

## Review Guidance

- Verify tab navigation works: Overview → Analysis → Rule of 40 → Valuation.
- Confirm Rule of 40 is NOT visible in the Analysis tab anymore.
- Check sector warning appears for non-tech tickers (e.g., JPM for Financials).

## Activity Log

- 2026-02-08T02:11:51Z – system – lane=planned – Prompt created.