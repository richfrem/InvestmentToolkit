---
name: ytd-return
plugin: portfolio-advisor
description: >
  Calculate Simple and Time-Weighted YTD returns, adjusting for cash flows (deposits/withdrawals)
  to measure true investment performance. Trigger on "calculate YTD return", "show my return",
  "TWR performance", or "/ytd-return".
allowed-tools: Bash, Read, Write
---

# YTD Performance Tracker (TWR)

This skill tracks and computes your portfolio's performance from Jan 1 through the current date, adjusting for deposits and withdrawals using Time-Weighted Rate of Return (TWR) linking.

## Usage

Run the canonical script:
```bash
python3 plugins/portfolio-advisor/scripts/ytd_return.py
```

## Data Input

All cash flow history (deposits and withdrawals) is stored in:
`investment_screener/backend/data/cash_flows.json`

Feel free to append new deposits or withdrawals to that file to update your performance metrics.
