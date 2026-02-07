---
work_package_id: "WP04"
title: "Valuation Modeler"
lane: "planned"
dependencies: ["WP02"] 
subtasks: ["T016", "T017", "T018", "T019"]
---

# Work Package 04: Valuation Modeler

**Goal**: Implement the core Valuation Modeler interactive tool with Scenario Analysis (Bear/Base/Bull) and intrinsic value calculations.

**Implementation Command**:
`spec-kitty implement WP04 --base WP02`

---

### Subtask T016: Build Modeler UI
**Purpose**: Interactive layout for inputs.
**Steps**:
1.  Create `frontend/src/components/ValuationModeler.tsx`.
2.  Implement Tab Interface: Bear, Base, Bull.
3.  Design Input Sliders Section (Growth, Margin, PE, Share Change).
4.  Add numeric input fields alongside sliders for precision.
5.  Maintain separate state for each scenario.

### Subtask T017: Implement Valuation Logic & Validation
**Purpose**: Calculate the 5-Year Price Target.
**Formula**: `(Revenue * (1 + Growth)^5 * Net Margin * Exit PE) / (Current Shares * (1 + Share Change)^5)`
**Steps**:
1.  Implement calculation function `calculateTargetPrice(scenario)`.
2.  Implement validation ranges:
    - Growth: -50% to +200%
    - Margin: -100% to +100%
    - PE: 1x to 200x
    - Share Change: -20% to +20%
3.  Display result dynamically as inputs change (< 100ms lag).
4.  Calculate projected Revenue/Income/EPS for display.
5.  Calculate CAGR required to justify current price.

### Subtask T018: Expert Analysis Summary
**Purpose**: Interpret the results for the user.
**Steps**:
1.  Compare current price to targets.
2.  Implement Threshold Logic:
    - **Strong Value**: Price < Bear.
    - **Potential Value**: Bear < Price < Base.
    - **Fairly Valued**: Base < Price < Bull.
    - **Overvalued**: Price > Bull.
3.  Display concise summary card: "Status: Strong Value (25% Upside)".

### Subtask T019: Conceptual Guidance (Cheat Sheet)
**Purpose**: Provide static context for inputs.
**Steps**:
1.  Add Info Tooltips or Helper Text near inputs.
2.  Hardcode industry averages (per spec):
    - Tech: PE 25-40x
    - Healthcare: PE 15-25x
    - Retail: PE 10-20x
3.  Display these ranges when focusing on the PE input.

---

**Definition of Done**:
- [ ] Users can toggle between Bear/Base/Bull scenarios.
- [ ] Sliders update numeric inputs and vice-versa.
- [ ] Price Target updates instantly.
- [ ] Validation prevents unrealistic inputs (e.g., 500% growth error message).
- [ ] "Expert Summary" correctly categorizes valuation based on thresholds.
