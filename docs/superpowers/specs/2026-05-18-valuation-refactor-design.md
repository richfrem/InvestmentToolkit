# Design Spec: Canonical Valuation Mirror & Refactor

**Date:** 2026-05-18
**Status:** [DRAFT]
**Topic:** Fixing inconsistent valuation numbers and refactoring the `ValuationModeler` component.

## 1. Problem Statement
The current system suffers from "split-brain" syndrome where the Frontend (React) and Backend (Python) implement DCF (Discounted Cash Flow) calculations independently. This leads to:
- **Inconsistent Numbers:** Minor differences in rounding or dilution math result in the Frontend "Target Price" not matching the saved AI Projection.
- **"Fudge Factors":** The code currently uses a `safeRatio` to force numbers to align rather than fixing the underlying logic.
- **Technical Debt:** `ValuationModeler.tsx` is a 1,281-line monolith that handles state, math, and layout simultaneously.
- **Lack of Verification:** No automated check ensures that a change to the Python math script is reflected in the Frontend.

## 2. Proposed Architecture

### 2.1 The Canonical Mirror
We will move all mathematical logic out of the React components and into a shared utility.
- **`frontend/src/utils/valuationMath.ts`**: A TypeScript implementation that is a 1:1 functional mirror of `investment_screener/backend/py_services/dcf_scenarios.py`.
- **Logic Removal:** Delete `calculateScenarioPrice` and related inline math from `ValuationModeler.tsx`.

### 2.2 Cross-Language Verification
To prevent future drift, we will implement a "Parity Test":
1. A Python script generates 100 random stock scenarios (TTM revenue, shares, growth rates, etc.).
2. The scenarios are piped through both the Python engine and the TypeScript utility.
3. The test fails if the resulting `weightedFairValue` differs by more than $0.01.

### 2.3 Component Decomposition
`ValuationModeler.tsx` will be broken down into the following:
- `ScenarioEditor`: Handles the 3-scenario input sliders.
- `ValuationSummary`: Displays Fair Value, Upside, and Recommendations.
- `SensitivityMatrix`: Extracted for reuse and updated to show **Future Price** by default.
- `ModelerContainer`: The thin orchestrator managing state and persistence.

## 3. Data Contract Alignment

### 3.1 Metric Standardization
We will enforce the use of the `Snapshot` object as defined in `zod-schemas.ts`.
- **Shares:** Always use `metrics.shares_diluted`.
- **Revenue:** Always use `metrics.revenue` (TTM).
- **Optionality:** Add an `optionalityAdjustment` field to the `Scenario` type to allow quantifying catalysts (like the Intel Terafab JV) without "hacking" the quality multiplier.

### 3.2 Qualitative vs. Quantitative
- `moatScore` and `managementScore` will be moved to a **Qualitative Breakdown** UI.
- They will NO LONGER be used as mathematical multipliers in the DCF formula (preserving "Adversarial Objectivity").

## 4. Success Criteria
1. **Zero Drift:** Loading an AI Projection results in the exact same Fair Value in the UI as the saved JSON.
2. **Component Focus:** `ValuationModeler.tsx` reduced from 1200+ lines to <300 lines.
3. **Automated Verification:** A `npm run test:math-parity` command exists and passes.

## 5. Implementation Plan
1. **[Phase 1]** Create `valuationMath.ts` and the Parity Test.
2. **[Phase 2]** Refactor `ValuationModeler` to use the new utility.
3. **[Phase 3]** Decompose the monolith into sub-components.
4. **[Phase 4]** Update the Sensitivity Matrix to prioritize "Future Price" for clarity.
