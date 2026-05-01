# Toolkit Manager Plugin

Orchestrator plugin for managing the Investment Screener suite and Questrade API integration.

## Commands

- `/setup-questrade`: Interactively guide the user through setting up their Questrade API refresh token.
- `/start-screener`: Launch the Investment Screener suite (Frontend and Backend).

## Skills

### Questrade Token Setup
A specialized sub-agent that automates the token exchange and seeding process after the user provides a one-week application token from the Questrade Portal.

### Run Screener
A utility skill that executes the unified `run_investment_toolkit.py` script to orchestrate the backend and frontend services.
