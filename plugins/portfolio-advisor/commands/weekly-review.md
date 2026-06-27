---
name: weekly-review
trigger: /weekly-review
description: Run range-based weekly review sweep and generate weekly Grok prompt.
---

# /weekly-review Command

Run this command to execute a range-based audit of holdings and initiates, calculate weekly stock price moves, and write the custom weekly news prompt for Grok:

```bash
python3 plugins/portfolio-advisor/scripts/weekly_review.py --prompt-output temp/weekly_grok_prompt.md
```
