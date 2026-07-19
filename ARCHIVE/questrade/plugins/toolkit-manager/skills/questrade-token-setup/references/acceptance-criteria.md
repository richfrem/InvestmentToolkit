# Acceptance Criteria: Questrade Token Setup

## Functional Requirements
- Must guide user to the Questrade API portal.
- Must capture the one-week token from user.
- Must autonomously exchange it for a refresh token using curl.
- Must seed the refresh token into `.questrade_cache` using `QuestradeDataEngine.py`.
- Must verify the cache exists.

## Quality Standards
- Use `ask_user` for the initial token capture.
- Provide clear error messages if the token is invalid.
- Ensure the `--cache-dir` is correctly set to `investment_screener/backend/`.
