# Feature Specification: Questrade Portfolio Integration

**Feature Branch**: `003-questrade-portfolio-integration`  
**Created**: 2026-02-13  
**Status**: Draft  
**Input**: User description: "Questrade Portfolio Integration - Create a formal specimen based on architectural pre-work."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initial Questrade Connection (Priority: P1)

As a user, I want a secure and guided way to link my Questrade account to the toolkit so that I can automate my portfolio tracking.

**Why this priority**: Without the initial connection, no data can be fetched. This is the foundation of the feature.

**Independent Test**: User can open the Setup Modal, follow the provided instructions, provide a refresh token, and receive a "Success" message indicating the secure cache has been initialized.

**Acceptance Scenarios**:

1. **Given** the user has no Questrade session, **When** they click "Setup Questrade" in the UI, **Then** a guided setup modal appears.
2. **Given** the user provides a valid application token, **When** they submit it, **Then** the toolkit redeems it for a long-lived credential and saves it in a hardware-backed encrypted cache.

---

### User Story 2 - Manual Portfolio Sync (Priority: P1)

As a user, I want to click a "Sync Now" button to fetch all my current holdings from Questrade and see them integrated into my dashboard.

**Why this priority**: This is the core utility of the feature—keeping the portfolio data up-to-date with reality.

**Independent Test**: Clicking the Sync button triggers the data retrieval service, which updates the central portfolio data with the latest quantities and prices from Questrade.

**Acceptance Scenarios**:

1. **Given** the user has a valid Questrade connection, **When** they initiate a sync, **Then** the system fetches positions across all associated brokerage accounts.
2. **Given** data is returned for multiple accounts, **When** the sync completes, **Then** holdings are aggregated by ticker symbol in the dashboard.
3. **Given** manual data exists for a ticker, **When** the sync runs, **Then** the Questrade data takes precedence and overwrites the manual entry.

---

### User Story 3 - Secure Token Rotation (Priority: P2)

As a user, I want the toolkit to manage my access credentials automatically so that I don't have to re-authenticate every time I want to sync.

**Why this priority**: One-time tokens expire. Automatic rotation is essential for a seamless user experience.

**Independent Test**: Running the sync multiple times succeeds without further user input.

**Acceptance Scenarios**:

1. **Given** a successful sync call, **When** the broker issues a new refresh credential, **Then** it is atomically updated in the secure storage.
2. **Given** a rotation is interrupted, **When** the system recovers, **Then** it retains the ability to re-establish the session without manual intervention.

---

### Edge Cases

- **Credential Expiry**: If the long-lived credential expires, the system MUST prompt the user to re-link their account.
- **Broker API Down**: If the broker's API is unreachable, the system MUST display a clear error message and preserve the existing secure cache.
- **Encryption Unavailable**: If the secure hardware storage is inaccessible, the system MUST notify the user and require re-authentication.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a guided interface for initial account linking.
- **FR-002**: System MUST aggregate positions across ALL accounts associated with the user's connection.
- **FR-003**: System MUST encrypt the local credential cache using hardware-backed or OS-level security.
- **FR-004**: System MUST ensure credential rotation is atomic to prevent loss of access during a crash.
- **FR-005**: Broker-provided data MUST be the authoritative source, overwriting manual entries for the same symbols.
- **FR-006**: System MUST normalize and aggregate holdings by ticker symbol regardless of the holding account.

### Key Entities *(include if feature involves data)*

- **QuestradeToken**: Represents the OAuth2 refresh and access tokens. Attributes: `refresh_token`, `access_token`, `api_server`, `token_type`, `expires_at`.
- **EncryptedCache**: The on-disk persistence layer (`.questrade_cache`) for the `QuestradeToken`, secured by `ADR 019`.
- **PortfolioHoldings**: The aggregated set of stocks/ETFs stored in `portfolio.json`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete the initial connection setup in under 5 minutes.
- **SC-002**: A manual sync operation completes in under 10 seconds for a typical portfolio (10-20 positions).
- **SC-003**: 100% of sync operations result in an updated `portfolio.json` that matches the total shares held across all Questrade sub-accounts.
- **SC-004**: Zero instances of plaintext refresh tokens stored on disk or committed to version control.
