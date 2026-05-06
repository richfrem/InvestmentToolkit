---
name: VIX Buy Zone — Screener Feature Request
description: User wants a new table view in the screener showing which holdings to buy during VIX-triggered market corrections
type: project
---

## Feature: VIX Buy Zone Table

User wants a dedicated table view on the screener menu showing which holdings to prioritize buying during market corrections (elevated VIX).

**Why:** User intentionally keeps excess cash (USD_CASH / PSU-U.TO) as dry powder to deploy aggressively on corrections. The view should surface the highest-priority buy targets when the market is in fear.

**How to apply:** When building this feature, use the exploration workflow. Core concept:
- Each thesis holding gets a "VIX buy zone" flag and optional entry price target
- Table shows: Ticker | Current Price | Entry Target | VIX Threshold | Why Now | Priority
- Sorted by conviction × discount from target price
- Separate from the main screener — a "Correction Playbook" tab/view

**Holdings the user specifically flagged as VIX correction targets (2026-05-06):**
- NVDA — best GPU designer for AI, load up on pullbacks
- TSM — foundry monopoly, add aggressively on corrections
- ASML — EUV lithography monopoly, no substitute
- MU — memory cycles; buy at trough P/B multiples on VIX spikes
- TEAM — add share 4+ on weakness
- BE / IONQ / OKLO — user explicitly said "waiting for lower prices"

**Cash reserve strategy:** User wants to maintain a meaningful cash buffer (target ~10-15%) specifically to deploy on VIX spikes. PSU-U.TO is the preferred cash vehicle.

**Implementation path:** Exploration workflow → intake agent → prototype → screener frontend new tab.
