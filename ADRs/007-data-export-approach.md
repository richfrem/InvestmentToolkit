# ADR 007: Data Export Approach for Prompt/AI Analysis

## Status
Accepted

## Context
Requirement UR21 specifies the need to export all in-memory account, holdings, positions, balances, and orders data for prompt/AI analysis, spreadsheet export, or external review. Several technical options were considered:

- Export to JSON file
- Export to CSV
- Export to Markdown table
- Provide API endpoint returning all data as JSON
- Export to TypeScript file

## Decision
Exporting all in-memory data to a single JSON file is the chosen approach. JSON is flexible, widely supported, and compatible with LLMs, spreadsheets, and other analysis tools. It supports nested and complex data structures, is easy to implement, and can be extended for future needs.

## Consequences
- Enables easy integration with LLMs and external analysis tools
- Simple implementation and maintenance
- Can be extended to support other formats if needed

## Action Required
- Implement a script to export all in-memory account, holdings, positions, balances, and orders data to a single JSON file (e.g., `exportedData.json`).
- Update documentation and TaskTracker to reflect this approach.
