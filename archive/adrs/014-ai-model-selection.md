# ADR 014: AI Model Selection & Versioning

## Status
Proposed

## Context
The application integrates with external LLM providers to deliver portfolio analysis. Models evolve rapidly, and model selection impacts cost, latency, and output quality. We need a documented policy for which models to use, where to set them, and how to migrate.

## Decision
- Model selection is controlled via environment variables on the server and optionally via client-visible VITE_ prefixed variables for non-secret configuration (model names only).
- Default model for backend analysis is `CHAT_GPT_TRIAGE_MODEL` environment variable. If not set, the service will fall back to a conservative default (`gpt-4o-mini` or similar).
- Token and temperature defaults are controlled via `BACKEND_AI_MAX_TOKENS` and `BACKEND_AI_TEMPERATURE` environment variables.
- Model upgrades should be validated in staging with a paid test key or a mocked provider. A/B testing may be used to compare output quality before rolling changes to production.

## Consequences
- Operators can change models without code changes by updating environment variables.
- Automating model rollouts is possible via CI/CD and feature flags.
- Monitoring must capture model identity, latency, and token consumption metrics to inform cost and quality decisions.

## Migration
- When adopting a new model, run integration tests in staging and compare outputs against a standardized test suite of prompts. Measure token usage and latency. If acceptable, promote model via configuration changes in production with a gradual rollout.

