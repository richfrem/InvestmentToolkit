
# Portfolio Review & Challenge Prompt (v1.0)

## Purpose
This prompt is designed to systematically review an **existing portfolio** of stocks against the **"Definitive Professional Investment Framework (v3.0)."** Its goal is not to discover new companies, but to challenge biases and validate the thesis for each current holding. It triggers a rigorous analysis that compares the user's intended action (`INCREASE`, `MAINTAIN`, `SELL`, etc.) with a data-driven recommendation from the framework, forcing a justification for any discrepancies.

## Instructions for Use
1.  **Prepare Your Input:** Before using this prompt, create a simple table of your current holdings and your intended action for each. The "action" should reflect your honest, current thinking.
2.  **Provide All Three Files:** For the analysis, you will provide:
    *   `quick-stock-screener.md` (The Framework)
    *   This prompt (`Portfolio_Review_Prompt.md`)
    *   Your prepared table of current holdings and actions.

## 1. User Input: Portfolio Holdings & Actions
*(This is the section you will edit each time you run a review)*

| Stock | Ticker | Your Action |
| :--- | :--- | :--- |
| NVIDIA CORPORATION | NVDA | INCREASE |
| CROWDSTRIKE HOLDINGS | CRWD | INCREASE |
| TESLA, INC. | TSLA | MAINTAIN |
| OKTA, INC. | OKTA | REDUCE |
| ... | ... | ... |

*(Note: The "Your Action" choices are: `INCREASE`, `INITIATE`, `MAINTAIN`, `REDUCE`, `SELL`, `MONITOR`)*

## 2. AI Execution Steps
*You will execute the following steps, using the user's table as the primary input.*

### Step A: Ingest and Score
For **every stock** listed in the user's table, apply the full scoring system from the "Definitive Professional Investment Framework (v3.0)." Calculate a final score based on all quantitative and qualitative factors. For recent IPOs or other un-scorable assets, note them as "N/A" for score.

### Step B: Generate a Framework Recommendation
Based on the final score and qualitative analysis (moat strength, trends, etc.), generate a `Framework Recommendation` for each stock.
*   **Score > 80:** Strong `INCREASE` or `MAINTAIN` candidate.
*   **Score 65-80:** `MAINTAIN` or `MONITOR`.
*   **Score < 60:** Strong `REDUCE` or `SELL` candidate.
*   **Qualitative Overrides:** Acknowledge where a powerful qualitative factor (e.g., a monopolistic moat for ASML, a binary catalyst for TSLA) justifies overriding the pure quantitative score.

### Step C: Create the "Challenge Report"
Produce a final output in a tiered markdown format. The core of the report will be a table that directly compares the user's action with the framework's recommendation.

**For every single instance where `Your Action` does not match the `Framework Recommendation`, you must provide a detailed "Challenge Rationale."** This rationale must:
1.  State the discrepancy clearly.
2.  Explain *why* the framework arrived at its conclusion, citing specific metrics (e.g., "The framework recommends SELL because the company fails the Rule of 40, its NDR is declining, and its moat is assessed as 'Damaged'.").
3.  Directly contrast the data-driven view with the likely narrative-driven bull case (e.g., "While the ARK Invest thesis points to a massive future TAM, the framework cannot ignore the current reality of deteriorating margins and negative FCF.").

## 3. Desired Output Format

```markdown
# Portfolio Validation Report (Generated on [Current Date])

## Tier 1: High-Conviction Core (Framework Score > 80)
**Framework Verdict:** [e.g., FULLY VALIDATED.]

| Ticker | Company | Score | Your Action | Framework Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| NVDA   | NVIDIA  | 92    | INCREASE    | **VALIDATED - INCREASE** |
| ...    | ...     | ...   | ...         | ...                      |

---
## Tier 2: Solid Holdings (Framework Score 65-80)
**Framework Verdict:** [e.g., LARGELY ALIGNED.]

| Ticker | Company | Score | Your Action | Framework Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| ZS     | Zscaler | 77    | MAINTAIN    | **AGREE - MAINTAIN** |
| ...    | ...     | ...   | ...         | ...                      |

---
## Tier 3: Speculative & Underperforming (Score < 60 or Un-scored)
**Framework Verdict:** [e.g., SIGNIFICANT CHALLENGE.]

| Ticker | Company | Score | Your Action | Framework Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| OKTA   | Okta, Inc.| 55    | REDUCE      | **CHALLENGE - SELL** |
| TEM    | Tempus AI | N/A   | REDUCE      | **CHALLENGE - SELL** |
| ...    | ...     | ...   | ...         | ...                      |

---
## Challenge Rationale & Analysis

### OKTA, Inc. (OKTA)
*   **Your Action:** `REDUCE`
*   **Framework Recommendation:** `SELL`
*   **Rationale for Challenge:** The framework recommends a full `SELL` because the company's moat is assessed as 'Damaged' due to multiple security breaches. Furthermore, its declining Net Dollar Retention and slowing growth in the face of intense competition from Microsoft (Entra ID) and CrowdStrike (Raptor for Identity) are significant red flags that indicate a broken thesis...

### Tempus AI, Inc. (TEM)
*   **Your Action:** `REDUCE`
*   **Framework Recommendation:** `SELL` (or Reduce)
*   **Rationale for Challenge:** As a recent IPO, Tempus AI is un-scorable against the framework's historical data requirements (FCF trend, ROIC). Holding an un-scored asset violates the core discipline of the system. While reducing the position is good risk management, the purist framework view is to sell the position entirely and re-allocate capital to a high-scoring, validated company...

*(...and so on for every discrepancy.)*
