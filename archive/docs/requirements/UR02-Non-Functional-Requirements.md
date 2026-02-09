# UR02: Non-Functional Requirements

## Overview
System qualities, constraints, and operational requirements that define how the system should perform and behave.

## Requirements

### UR16: Security
**Description:** Secure: No password storage, .env for secrets, Husky pre-commit scans, and OAuth2 refresh token management as documented in ADR 001.

**Acceptance Criteria:**
- No passwords stored in application
- Secrets managed via .env files
- Pre-commit hooks scan for secrets
- OAuth2 token management implemented
- Secure token rotation and storage

### UR17: UI/UX Design
**Description:** Responsive UI with modern design (shadcn/ui, Tailwind).

**Acceptance Criteria:**
- Modern, clean interface
- Responsive design for all screen sizes
- Consistent design system
- Accessible components
- Professional appearance

### UR18: Local-First Architecture
**Description:** Local-first: Holdings data is preserved in a local TypeScript file in V1 for quick access and reliability. SQLite will be used for local caching and persistence in future versions (V2+). No external DB in V1.

**Acceptance Criteria:**
- Data stored locally
- Fast access without network calls
- Reliable local persistence
- Migration path to SQLite planned
- No external database dependencies in V1

### UR19: Incremental Versioning
**Description:** Incremental feature rollout with clear versioning.

**Acceptance Criteria:**
- Clear version numbering
- Feature flags for incremental rollout
- Backward compatibility maintained
- Versioned releases
- Change logs maintained

### UR20: Data Contract Alignment
**Description:** All data contracts (TypeScript interfaces/types) for positions, holdings, and related entities must be aligned with the official Questrade API schemas for consistency and reliability. See ADR 006 (adrs/006-data-contracts-aligned-with-questrade.md) for details. When updating or adding new contracts, always reference the Questrade API documentation and update ADR 006 if the approach changes.

**Acceptance Criteria:**
- All interfaces match Questrade API schemas
- Documentation references maintained
- ADR 006 updated for changes
- Type safety ensured
- API compatibility maintained

### UR31: Comprehensive Logging System
**Description:** Comprehensive logging system with environment-controlled debugging. A centralized logger utility (`backend/src/utils/logger.ts`) provides structured logging with multiple levels (debug, info, success, warn, error) and specialized loggers for different components (api, data, questrade, portfolio). Debug logging is controlled by the `DEBUG_LOGGING=true` environment variable to keep production logs clean while enabling detailed debugging when needed.

**Acceptance Criteria:**
- Multiple log levels supported
- Environment-controlled debug logging
- Specialized loggers for components
- Structured logging format
- Production logs remain clean
- Debug logs available when needed

### UR32: Data Mapping Requirements
**Description:** Data mapping from source to destination schemas must be explicit, documented, and validated. All data transformations between Questrade API responses and internal data structures (including portfolio master data, holdings aggregation, and pillar mappings) must include clear field mappings, type conversions, and validation rules. Schema transformations should be versioned and tested to ensure data integrity across the pipeline.

**Acceptance Criteria:**
- Explicit field mappings documented
- Type conversions defined
- Validation rules implemented
- Schema transformations versioned
- Data integrity maintained
- Transformation testing included

## Performance Requirements

### Response Times
- API calls: < 5 seconds
- UI interactions: < 100ms
- Data loading: < 2 seconds

### Scalability
- Support for multiple accounts
- Handle large portfolios (1000+ holdings)
- Efficient data structures

### Reliability
- 99% uptime for local operations
- Graceful error handling
- Data consistency maintained

## Security Requirements

### Data Protection
- No sensitive data in logs
- Secure token storage
- Input validation and sanitization

### Access Control
- Local application security
- No external user authentication
- Secure API key management

## Usability Requirements

### User Experience
- Intuitive navigation
- Clear error messages
- Loading states and feedback
- Responsive design

### Accessibility
- Keyboard navigation support
- Screen reader compatibility
- High contrast support
- Clear typography

## Maintainability Requirements

### Code Quality
- TypeScript strict mode
- Comprehensive test coverage
- Clear documentation
- Modular architecture

### Deployment
- Easy local setup
- Environment-based configuration
- Automated dependency management

### AI Non-Functional Requirements (addition)

- Secrets: `OPENAI_API_KEY` must only be stored server-side and not exposed to clients. Use `VITE_` prefixed env vars for non-secret frontend config only.
- Observability: Record token usage, latency, and success/failure counts for LLM calls. Do not log raw prompts or responses in plaintext.
- Performance: Target P95 latency for `/api/run-analysis` under 15s (dependent on provider). Implement retry/backoff for provider errors.
- Availability: Feature should be disable-able via `FEATURE_STRATEGY_AI=false`.