---
work_package_id: WP07
title: Dashboard, Settings & App Branding
lane: planned
dependencies:
- WP05
subtasks: [T035, T036, T037, T038, T039, T040, T041]
---

# Work Package: Dashboard, Settings & App Branding
**Priority**: P2
**Goal**: Polish the application shell, implement branding, and wire up placeholder links.

## Context
The app is currently generic ("Spec Kitty / Investment Screener"). We need to rebrand to "Market Intelligence" and make the sidebar helpful.

## Subtasks

### T035: Rename & Rebrand
**Objective**: Update app title and logo text.
**Files**: `tools/investment-screener/frontend/src/components/Sidebar.tsx`
**Guidance**:
- Change header text to "Market Intelligence".
- Remove "Spec Kitty" reference from the UI (keep in code/repo names).
- Update `<title>` tag in `index.html`.

### T036: Create `DashboardHome`
**Objective**: Specific landing page.
**Files**: `tools/investment-screener/frontend/src/components/DashboardHome.tsx` (NEW)
**Guidance**:
- Content: "Recently Viewed" list.
  - Ticker cards: Symbol, Last Price, % Change.
  - Click to navigate to `/analyze?ticker=XYZ`.
- Quick Actions: "New Analysis" (focus search bar).

### T037: Wire Dashboard Link
**Objective**: Make the sidebar link work.
**Files**: `tools/investment-screener/frontend/src/components/Sidebar.tsx`
**Guidance**:
- Link to `/` (Home).
- Ensure it resets the current analysis view if clicked while analyzing a stock.

### T038: Create `SettingsPage`
**Objective**: Minimal settings UI.
**Files**: `tools/investment-screener/frontend/src/components/SettingsPage.tsx` (NEW)
**Guidance**:
- Section: "Data"
  - Button: "Clear Local Cache" (nuke localstorage financial data).
  - Button: "Clear History" (nuke recently viewed).
- Section: "About"
  - Version: 1.0.0

### T039: Wire Settings Link
**Objective**: Make the sidebar link work.
**Files**: `tools/investment-screener/frontend/src/components/Sidebar.tsx`
**Guidance**:
- Link to `/settings`.

### T040: Routing Updates
**Objective**: Support new pages.
**Files**: `tools/investment-screener/frontend/src/App.tsx`
**Guidance**:
- Route `/` -> `DashboardHome`.
- Route `/settings` -> `SettingsPage`.
- Route `/analyze` -> `Dashboard` (The main analysis view).
- Ensure URL param `?ticker=NVDA` works on `/analyze`.

### T041: Active Nav State
**Objective**: Visual feedback in sidebar.
**Files**: `tools/investment-screener/frontend/src/components/Sidebar.tsx`
**Guidance**:
- Use `useLocation`.
- Highlight "Dashboard" if path is `/`.
- Highlight "Settings" if path is `/settings`.

## Validation
- **Manual Test**: Click "Dashboard", Click stock card, Click "Settings".
- **Success Criteria**:
  - Navigation works without full page reload.
  - "Market Intelligence" visible in top left.
  - Recent tickers list populates as I search for stocks.

## Risks
- Bookmarking: Old URL structure might be `/?ticker=XYZ`. Ensure `DashboardHome` redirects to `/analyze?ticker=XYZ` if query param is present on root.