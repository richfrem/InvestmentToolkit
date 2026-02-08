---
work_package_id: WP02
title: Frontend Shell & Dashboard
lane: "doing"
dependencies: [WP01]
base_branch: main
base_commit: f1742cd6775af61051fac282638f7ef4ca958154
created_at: '2026-02-07T19:36:04.200950+00:00'
subtasks: [T007, T008, T009, T010, T011]
shell_pid: "15842"
---

# Work Package 02: Frontend Shell & Dashboard

**Goal**: Build the React application shell, configure the "Luxury Dark" theme, and implement the Search/Sidebar functionality.

**Implementation Command**:
`spec-kitty implement WP02 --base WP01`

---

### Subtask T007: Configure "Luxury Dark" Theme
**Purpose**: Set up Tailwind CSS with the project's specific aesthetic.
**Steps**:
1.  Install `tailwindcss`, `postcss`, `autoprefixer` in `frontend/`.
2.  Initialize `tailwind.config.js`.
3.  Define custom colors:
    - Background: `slate-950` (or darker custom hex)
    - Surface: `slate-900`
    - Accent: `amber-500` (Gold)
    - Text: `slate-200` (Primary), `slate-400` (Secondary)
4.  Configure `frontend/src/index.css` with `@tailwind` directives.
5.  Verify fonts (Inter/Roboto) via Google Fonts import.

### Subtask T008: App Layout & Routing
**Purpose**: Create the main application structure.
**Steps**:
1.  Install `react-router-dom`.
2.  Create `frontend/src/layouts/MainLayout.tsx`:
    - Sidebar (Left) - Fixed width.
    - Main Content (Right) - Scrollable.
    - Header - Minimalist.
3.  Update `App.tsx` to use `BrowserRouter` and routes.
4.  Create placeholder pages: `Dashboard`, `Settings` (optional).

### Subtask T009: API Service Wrapper
**Purpose**: Connect frontend to backend.
**Steps**:
1.  Create `frontend/src/services/api.ts`.
2.  Implement `fetchStockData(ticker: string)`:
    - Call backend `/api/stock/:ticker`.
    - Handle loading states and errors.
    - Type definitions for the API response (Financials, Metrics, Info).
3.  Add retry logic basic (optional).

### Subtask T010: Dashboard Component & Search
**Purpose**: The central user interface.
**Steps**:
1.  Create `frontend/src/components/Dashboard.tsx`.
2.  Implement `StockSearch` component:
    - Input field with "Search" button.
    - Validation (ticker format).
    - `onSearch` callback.
3.  State management for `currentTicker` and `stockData`.
4.  Display loading spinner (Gold accent) during fetch.

### Subtask T011: Recently Analyzed Sidebar
**Purpose**: Quick navigation to previous tickers w/ Persistence.
**Steps**:
1.  Create `frontend/src/components/Sidebar.tsx` (if not part of Layout).
2.  Implement `useRecentTickers` hook:
    - Read/Write to `localStorage` key `recent_tickers`.
    - Limit to last 10 items.
    - Push new ticker on successful search.
3.  Render list of tickers in Sidebar. Click to load.

---

**Definition of Done**:
- [ ] Application loads with dark black/gold theme.
- [ ] Sidebar shows "Recently Analyzed" history (persists on refresh).
- [ ] Search bar accepts "AAPL", calls backend, and logs response to console.
- [ ] Layout is responsive (Sidebar collapses on mobile - nice to have).
