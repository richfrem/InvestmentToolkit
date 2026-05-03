# Acceptance Criteria — portfolio_health Skill

## Correct Execution Signals

### AC-01: Drift Classification Determinism
- **Condition**: Health check returns drifted holdings
- **Pass**: Every drifted holding is classified as either **Passive** (market movement) or **Active** (user action). Agent never leaves drift type ambiguous.
- **Fail**: Agent reports drift percentage without classifying cause

### AC-02: Strategic Conflict Detection
- **Condition**: A holding has `hasValuation: true` AND Tool A recommendation is SELL/HOLD AND thesis designates it as "Core" AND status is ON_TARGET
- **Pass**: Agent flags as **Strategic Conflict** and explicitly asks user which view takes priority before suggesting any trades
- **Fail**: Agent silently ignores the conflict or auto-resolves without user input

### AC-03: Thesis Breaker Gate
- **Condition**: A holding triggers a thesis breaker condition (e.g. position drops below minimum threshold or violates a hard rule)
- **Pass**: Agent presents the breaker condition explicitly with the threshold that was crossed. Does NOT suggest partial trim — presents full exit as the mechanical required action, with option to override.
- **Fail**: Agent treats thesis breaker as ordinary drift and suggests minor trim

### AC-04: Recap Before Optimize
- **Condition**: Agent reaches the rebalancing trade suggestion phase
- **Pass**: Before listing specific trade quantities, agent pauses and asks "I see significant drift in [TICKER]. Is this a temporary dislocation, or has your thesis changed?" for any drift > 5%
- **Fail**: Agent immediately outputs trade instructions without confirming user intent

### AC-05: Thesis Update Confirmation Gate
- **Condition**: User indicates conviction has changed on a holding
- **Pass**: Agent proposes specific updated target weights AND shows drift score impact BEFORE asking user to confirm update
- **Fail**: Agent updates thesis without showing impact, or proceeds without explicit confirmation

### AC-06: Source Transparency Declared
- **Condition**: Any portfolio review completes
- **Pass**: Output includes `## Sources Checked` block listing API endpoints queried and their availability
- **Fail**: No sources block present

### AC-07: Standalone Degradation Works
- **Condition**: Backend API unreachable
- **Pass**: Agent announces degraded mode, requests portfolio weights + thesis targets as JSON, completes drift calculation manually
- **Fail**: Agent crashes or silently returns empty results

### AC-08: Missing Valuations Surfaced
- **Condition**: Holdings present with `hasValuation: false`
- **Pass**: Agent explicitly lists all unvalued tickers and recommends `/evaluate-stock {TICKER}` for each
- **Fail**: Missing valuations silently omitted from analysis

## Negative / Near-Miss Patterns to Reject

| Anti-Pattern | Why It Fails |
|---|---|
| Auto-resolving a Strategic Conflict without user input | Violates AC-02 — user must decide |
| Suggesting trades before confirming drift intent on >5% positions | Violates AC-04 |
| Treating thesis breaker as ordinary drift | Violates AC-03 |
| Updating thesis without showing impact | Violates AC-05 |
