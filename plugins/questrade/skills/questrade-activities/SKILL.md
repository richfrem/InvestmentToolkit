---
name: questrade-activities
description: "Retrieve 90-day cash flow ledger events (dividends, interest, deposits, withdrawals) via Questrade MCP and ingest into SQLite."
argument-hint: "[--days 90]"
allowed-tools: Bash, Read, Write
---

# Questrade Cash Flow & Activity Ledger Skill

## Purpose
Queries Questrade MCP tool `Get Account Activities` and records cash deposits, dividend payments, and fee events directly into `domain_model.sqlite`'s `cash_flow` table.
