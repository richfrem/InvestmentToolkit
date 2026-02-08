---
work_package_id: WP07
title: Dashboard, Settings & App Branding
lane: planned
dependencies:
- WP05
subtasks:
- T035
- T036
- T037
- T038
- T039
- T040
- T041
phase: Phase 3 - Enhancements
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T02:11:51Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Dashboard, Settings & App Branding

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- App branding updated — no more "Spec Kitty" in the sidebar. Use proper product name.
- Dashboard sidebar link navigates to a functional landing page with recent tickers and quick stats.
- Settings sidebar link navigates to a functional settings page.
- Active nav item is highlighted in the sidebar.

## Context & Constraints

- **Current state**:
  - Sidebar shows "⚡ Spec Kitty / Investment Screener" branding.
  - Dashboard and Settings links exist but navigate to basic routes.
  - Settings page is a 10-line placeholder.
  - The app header already says "Market Intelligence" — this is the intended product identity.
- **Key Files**:
  - `frontend/src/components/Sidebar.tsx` (74 lines)
  - `frontend/src/pages/Dashboard.tsx` (139 lines)
  - `frontend/src/pages/Settings.tsx` (10 lines)
  - `frontend/src/App.tsx` (23 lines)
  - `frontend/src/layouts/MainLayout.tsx` (18 lines)

## Implementation Command

No strict dependencies — can start from main or any base:
```bash
spec-kitty implement WP07
```

## Subtasks & Detailed Guidance

### Subtask T035 – Rename App Branding

- **Purpose**: Replace "Spec Kitty / Investment Screener" with a proper product name.
- **Steps**:
  1. In `Sidebar.tsx`, find the header section with "⚡ Spec Kitty" and "Investment Screener" subtitle.
  2. Replace with the app's actual identity. The main page header already says "Market Intelligence" — use that:
     ```tsx
     <div className="p-6 border-b border-slate-800">
       <h1 className="text-xl font-bold text-amber-400">Market Intelligence</h1>
       <p className="text-xs text-slate-500">Investment Toolkit</p>
     </div>
     ```
  3. Remove the ⚡ emoji (it was Spec Kitty branding).
  4. Update the browser tab title in `frontend/index.html` if it says "Spec Kitty" anywhere.
  5. Check for any other "Spec Kitty" references in the frontend codebase and replace.
- **Files**: `frontend/src/components/Sidebar.tsx`, `frontend/index.html`

### Subtask T036 – Create DashboardHome Page

- **Purpose**: A proper landing/home page when clicking Dashboard.
- **Steps**:
  1. Create `frontend/src/pages/DashboardHome.tsx`.
  2. Content:
     - **Header**: "Welcome back" or "Market Intelligence Dashboard"
     - **Recently Analyzed** section: List of recent tickers from `useRecentTickers()` hook, showing:
       - Ticker symbol
       - Last known price (from LocalStorage or cached API data)
       - Quick "Analyze" link that navigates to the stock analysis view
     - **Quick Stats** (optional): Number of saved projections, number of tickers analyzed
  3. Layout: Clean grid of ticker cards, Luxury Dark styling.
  4. Empty state: "Search for a stock ticker to begin your analysis."
- **Files**: `frontend/src/pages/DashboardHome.tsx` (new, ~80 lines)
- **Parallel?**: Yes — can be built alongside T038.

### Subtask T037 – Wire Dashboard Sidebar Link

- **Purpose**: Clicking "Dashboard" in sidebar navigates to DashboardHome.
- **Steps**:
  1. In `App.tsx`, update routes:
     ```tsx
     <Route path="/" element={<MainLayout />}>
       <Route index element={<DashboardHome />} />
       <Route path="analyze" element={<Dashboard />} />
       <Route path="settings" element={<Settings />} />
     </Route>
     ```
  2. The stock analysis page (current Dashboard) moves to `/analyze` route.
  3. Ticker search navigates to `/analyze?ticker=NVDA`.
  4. Sidebar "Dashboard" link points to `/` (DashboardHome).
  5. Recent ticker clicks in sidebar navigate to `/analyze?ticker=SYMBOL`.
- **Files**: `frontend/src/App.tsx`, `frontend/src/components/Sidebar.tsx`

### Subtask T038 – Create SettingsPage

- **Purpose**: Replace the placeholder Settings page with functional content.
- **Steps**:
  1. Rewrite `frontend/src/pages/Settings.tsx`:
  2. Settings sections:
     - **Data & Cache**: "Clear cached data" button (clears LocalStorage API cache if implemented).
     - **Saved Data**: "Clear all saved projections" button with confirmation. Show total projection count.
     - **About**: App version, data source attribution ("Powered by Yahoo Finance via yfinance").
  3. Each section in a card with Luxury Dark styling.
  4. Buttons should have confirmation dialogs for destructive actions.
- **Files**: `frontend/src/pages/Settings.tsx` (rewrite, ~100 lines)
- **Parallel?**: Yes — can be built alongside T036.

### Subtask T039 – Wire Settings Sidebar Link

- **Purpose**: Clicking "Settings" in sidebar navigates to Settings page.
- **Steps**:
  1. Verify the Settings route already exists in `App.tsx` (it does at `/settings`).
  2. Ensure the Sidebar NavLink for Settings points to `/settings`.
  3. Verify navigation works.
- **Files**: `frontend/src/components/Sidebar.tsx`

### Subtask T040 – Update App.tsx Routing

- **Purpose**: Ensure all routes are properly configured.
- **Steps**:
  1. Final route structure:
     ```
     /           → DashboardHome (landing page)
     /analyze    → Dashboard (stock analysis with tabs)
     /settings   → Settings
     ```
  2. Handle backward compatibility: if someone visits `/?ticker=NVDA`, redirect to `/analyze?ticker=NVDA`.
  3. Import all page components.
- **Files**: `frontend/src/App.tsx`

### Subtask T041 – Highlight Active Nav Item

- **Purpose**: Sidebar should indicate which page the user is on.
- **Steps**:
  1. In `Sidebar.tsx`, use `useLocation()` from react-router-dom to detect current route.
  2. Apply active styling to the matching nav item:
     ```tsx
     const isActive = location.pathname === item.path;
     // Active: bg-slate-800 text-amber-400 border-l-2 border-amber-400
     // Inactive: text-slate-400 hover:text-slate-200
     ```
  3. Dashboard active on `/` and `/analyze`.
  4. Settings active on `/settings`.
- **Files**: `frontend/src/components/Sidebar.tsx`
- **Parallel?**: Yes — independent UI enhancement.

## Risks & Mitigations

- Routing change from `/` to `/analyze` may break existing bookmarks → add redirect logic.
- Recent tickers in DashboardHome depend on `useRecentTickers()` which only stores symbols, not prices → may need to fetch or show symbols only.

## Review Guidance

- Click Dashboard → should show DashboardHome with recent tickers.
- Click Settings → should show settings with clear data buttons.
- Verify no "Spec Kitty" text anywhere in the app.
- Test navigation flow: Dashboard → click recent ticker → stock analysis → back to Dashboard.

## Activity Log

- 2026-02-08T02:11:51Z – system – lane=planned – Prompt created.