# Playbook: Portfolio Invariants & Target Allocation Governance

`Status: CONFIRMED (2026-09-02)`

---

## 1. Overview & Purpose
Governs the mathematical invariants and execution priority mechanics across `domain_model.sqlite`, backend API services, and frontend visualization layers. 

Prevents allocation drift (e.g. target weights exceeding 100%), cash omission distortion, and unprioritized UI presentation in the Portfolio Advisor / Screener suites.

---

## 2. Core Invariants

### Invariant A: Mandatory Cash Invariant for Portfolio Totals (Rule #18)
- **Mathematical Formula**:
  $$\text{Total USD} = \sum (\text{Held Equities Market Value}) + \sum (\text{Account Cash USD})$$
- **Enforcement**:
  - Never compute total portfolio value from equity market value alone.
  - Cash must always be incorporated in totals across TypeScript API routes, Python CLI services, and SQLite queries.
  - Verified via:
    ```bash
    python3 investment_screener/backend/py_services/verify_portfolio_invariants.py
    ```

### Invariant B: 100% Target Allocation Sum Invariant
- **Rule**:
  $$\sum_{i \in \text{active targets}} \text{target\_weight}_i = 100.00\% \pm 0.05\%$$
- **Enforcement Mechanism**:
  - `check_target_weight_invariant()` in `verify_portfolio_invariants.py` queries `investment.target_weight` across all active holdings and targets in `domain_model.sqlite`.
  - When initiating or adding new security targets (e.g. `CRDO`, `VST`), other target weights and `CASH_USD` must be normalized pro-rata.
  - Target allocations must never silently exceed or drop below 100.00%.

### Invariant C: Executive Action Urgency Hierarchy
- **Hierarchy Order**:
  $$\text{EXIT} > \text{INITIATE} > \text{ACCUMULATE} > \text{TRIM} > \text{REVIEW} > \text{MAINTAIN} > \text{HOLD} > \text{WATCHLIST}$$
- **Execution Rules**:
  - **`EXIT`**: Positions with `target_weight == 0` or broken thesis must be liquidated. Highest execution urgency.
  - **`INITIATE`**: Unowned target holdings with `target_weight > 0` or attractive valuation buy signals.
  - **`ACCUMULATE`**: Under-allocated core holdings ($<85\%$ of target weight) with positive valuation upside.
  - **`TRIM`**: Over-allocated core holdings ($>115\%$ of target weight) ready for profit harvesting.
  - **`MAINTAIN` / `HOLD`**: Positions within the normal tolerance band around target weight.
  - **`WATCHLIST`**: Monitored non-funded candidates.

---

## 3. Negative Constraints / Anti-Patterns
- 🚫 **Uncalibrated Target Additions**: Never add or increase a ticker's target weight in `investment` without adjusting other allocations or `CASH_USD` to preserve the 100.00% sum.
- 🚫 **Ignoring Cash in Valuation**: Never calculate portfolio weight percentages using equity-only denominators.
- 🚫 **Unsorted Upside Bias**: Never present portfolio screener tables sorted solely by upside without providing immediate visibility into urgent `EXIT`, `TRIM`, or `INITIATE` actions.
