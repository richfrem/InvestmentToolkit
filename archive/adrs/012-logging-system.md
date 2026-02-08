# ADR 012: Comprehensive Logging System with Environment-Controlled Debugging

## Status
Accepted

## Context
The application requires robust logging capabilities for debugging, monitoring, and troubleshooting across backend services, API integrations, and data processing workflows. Logs need to be structured, categorized, and controllable to avoid cluttering production environments while providing detailed information during development and debugging.

## Decision
Implement a centralized logging utility (`backend/src/utils/logger.ts`) with the following features:

- **Multiple Log Levels**: debug, info, success, warn, error
- **Specialized Loggers**: api, data, questrade, portfolio for component-specific logging
- **Environment Control**: Debug logging controlled by `DEBUG_LOGGING=true` environment variable
- **Emoji-enhanced Output**: Visual indicators for different log types
- **Structured Logging**: Consistent format with timestamps and context

## Pros
- Clean production logs with detailed debugging when needed
- Component-specific logging for better organization
- Easy to extend and maintain
- Consistent logging across the application
- Visual clarity with emoji indicators

## Cons
- Slight performance overhead when debug logging is enabled
- Requires discipline in choosing appropriate log levels

## Alternatives Considered
- Console.log statements throughout codebase (less organized)
- External logging libraries (unnecessary complexity for current needs)
- No logging control (would clutter production logs)

## Consequences
- All backend services now use structured logging
- Debug information is available when `DEBUG_LOGGING=true`
- Production logs remain clean and focused on important events
- Easy to add new specialized loggers as the application grows

## Implementation
- Logger utility created at `backend/src/utils/logger.ts`
- Integrated into all backend services and API routes
- Environment variable `DEBUG_LOGGING=true` enables debug logs
- Specialized loggers for different components (questrade, portfolio, api, data)

## LLM Telemetry (addition)

- LLM calls must be logged with restricted, non-sensitive telemetry only: request_id, endpoint, model, token counts (if available), duration_ms, and status (success|error). Do NOT log raw prompts or full LLM responses.
- For rare debug workflows that require full prompt/response capture, store them in a protected trace store with strict access controls and automatic expiration (e.g., 30 days). Access to this trace store should be auditable.
- Emit metrics for daily token usage to enable cost monitoring and alerts. Aggregate token usage per service and per model to a monitoring dashboard.

---

**Related Requirements:**
- UR31: Comprehensive logging system with environment-controlled debugging