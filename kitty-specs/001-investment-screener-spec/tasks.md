# Tasks: Investment Screener Implementation

**Feature**: Investment Screener (001)
**Status**: Planning

## Work Package 1: Foundation & Backend Core (WP01)

**Goal**: Initialize the monorepo, set up the Node.js backend with Python bridge, and implement the `yfinance` data fetcher with metrics logic.
**Estimated Prompt Size**: ~400 lines

- [ ] **T001**: Initialize project structure (backend/frontend/workspace) & `package.json` configurations <!-- id: 0 -->
- [ ] **T002**: Create `startup.sh` and environment validation checks <!-- id: 1 -->
- [ ] **T003**: Setup Express backend with TypeScript, CORS, and error handling <!-- id: 2 -->
- [ ] **T004**: Implement `bridge.ts` service to spawn Python processes <!-- id: 3 -->
- [ ] **T005**: Implement `fetch_financials.py` (yfinance, Piotroski, Rule of 40, data normalization) <!-- id: 4 -->
- [ ] **T006**: Write backend tests (Mocha for API, Pytest for logic) <!-- id: 5 -->

---

## Work Package 2: Frontend Shell & Dashboard (WP02)

**Goal**: Build the React application shell, configure the "Luxury Dark" theme, and implement the Search/Sidebar functionality.
**Estimated Prompt Size**: ~350 lines
**Dependencies**: WP01

- [ ] **T007**: Configure Tailwind CSS with custom "Luxury Dark" theme (colors, fonts) <!-- id: 6 -->
- [ ] **T008**: Create App Layout, Main Container, and Error Boundaries <!-- id: 7 -->
- [ ] **T009**: Implement `services/api.ts` wrapper to consume WP01 endpoints <!-- id: 8 -->
- [ ] **T010**: Build Dashboard Component with Stock Search bar and basic state <!-- id: 9 -->
- [ ] **T011**: Implement "Recently Analyzed" sidebar with `localStorage` persistence <!-- id: 10 -->

---

## Work Package 3: Expert Metrics & Charts (WP03)

**Goal**: Visualize the financial data using Recharts and display the calculated Expert Metrics in a responsive grid.
**Estimated Prompt Size**: ~400 lines
**Dependencies**: WP02

- [ ] **T012**: Build "Expert Metrics" Grid Component (Display PEG, Piotroski, Rule of 40 with warnings) <!-- id: 11 -->
- [ ] **T013**: Implement `RuleOf40Chart.tsx` (Scatter/Line visualization) <!-- id: 12 -->
- [ ] **T014**: Implement `FundamentalChart.tsx` (Revenue vs Net Income historicals) <!-- id: 13 -->
- [ ] **T015**: Integrate components into Dashboard and wire up real data <!-- id: 14 -->

---

## Work Package 4: Valuation Modeler (WP04)

**Goal**: Implement the core Valuation Modeler interactive tool with Scenario Analyis (Bear/Base/Bull) and intrinsic value calculations.
**Estimated Prompt Size**: ~450 lines
**Dependencies**: WP02

- [ ] **T016**: Build `ValuationModeler.tsx` layout with Tabbed Interface (Bear/Base/Bull) <!-- id: 15 -->
- [ ] **T017**: Implement Input Sliders with Validation Ranges (Growth -50% to +200%, etc.) <!-- id: 16 -->
- [ ] **T018**: Implement Valuation Logic (Target Price Formula, CAGR) & Expert Analysis Summary <!-- id: 17 -->
- [ ] **T019**: specific "Cheat Sheet" contextual guidance for P/E inputs <!-- id: 18 -->

---

## Work Package 5: Polish & Validation (WP05)

**Goal**: Final UI polish, manual verification of math/logic, and documentation.
**Estimated Prompt Size**: ~250 lines
**Dependencies**: WP03, WP04

- [ ] **T020**: UI Polish (Transitions, Loading States, Mobile Responsiveness) <!-- id: 19 -->
- [ ] **T021**: Execute Manual Verification Plan (Math Check AAPL case) <!-- id: 20 -->
- [ ] **T022**: Final Linting & Type Checking cleanup <!-- id: 21 -->
- [ ] **T023**: Update `README.md` with startup instructions and usage guide <!-- id: 22 -->
