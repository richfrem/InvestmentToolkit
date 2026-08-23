---
name: tv-save-indicator
plugin: tradingview
description: >
  Save the current Pine Script in the editor to TradingView's personal library.
  Handles the "Save as" naming dialog on first save. After saving, the script
  appears under "My scripts" in the Indicators dialog for future loading.
allowed-tools: Bash
---

# TV Save Indicator Skill

**Trigger:** `/save-indicator {NAME}` — e.g. `/save-indicator "My RSI Strategy"`

---

## Two Operations — Know Which You Need

| Goal | Command |
|---|---|
| Save Pine Script to **TV personal library** (reuse later via Indicators dialog) | `pine save --name "{NAME}"` |
| Save the **chart layout** with current indicators to agent-layout | `chart saveLayout --name agent-layout` |

Use **both** after creating a new indicator: save to library first, then save the layout.

---

## Save Pine Script to Library

```bash
node tradingview-cdp/cli.js pine save --name "{NAME}"
```

Expected: `{ "success": true, "name": "My RSI Strategy", "action": "saved" }`

On first save: `action: "named-and-saved"` — TV showed a naming dialog, name was filled in.
On subsequent saves: `action: "saved"` — Cmd+S overwrote the existing script.

---

## Full Workflow: Inject → Save to Library → Save Layout

```bash
# 1. Generate script and inject it
node tradingview-cdp/cli.js pine inject -f temp/my_indicator.pine

# 2. Save script to personal library
node tradingview-cdp/cli.js pine save --name "My Custom Indicator"

# 3. Save chart state to agent-layout
node tradingview-cdp/cli.js chart saveLayout --name agent-layout
```

---

## Loading a Saved Script Later

After a script is saved to the library, load it onto any chart via:

```bash
node tradingview-cdp/cli.js chart addIndicator "My Custom Indicator"
```

This searches TV's Indicators dialog (including "My scripts") and adds it.

---

## Notes

- Scripts saved to TV library persist across sessions in your TV account.
- The naming dialog only appears on the **first save** of a new script. Subsequent saves overwrite silently.
- If `success: false` after injecting — the Pine Editor might not be open. Re-inject the script first.
