function extractJson(stdout: string): Record<string, any> | null {
  const trimmed = stdout.trim();
  try { return JSON.parse(trimmed); }
  catch { /* fall through */ }
  const idx = stdout.lastIndexOf('\n{');
  if (idx !== -1) {
    try { return JSON.parse(stdout.slice(idx).trim()); }
    catch (e: any) { console.error('Parse error:', e.message); }
  }
  return null;
}

const stdout = `
╔══════════════════════════════════════════════════════╗
║           ORDER CONFIRMATION REQUIRED                ║
╠══════════════════════════════════════════════════════╣
║  Via:              TradingView (Questrade)             ║
║  Ticker:           NBIS                                ║
║  Action:           BUY                                 ║
║  Shares:           1                                   ║
║  Order Type:       Market (USD)                        ║
║  Account:          TFSA (#53408189)                    ║
║  Cost Estimate:    ~Market × 1 shares                  ║
║  Buying Power:     $4,819.70 USD  ✓ Sufficient         ║
╚══════════════════════════════════════════════════════╝

{
  "ticker": "NBIS",
  "action": "Buy",
  "shares": 1,
  "currency": "USD",
  "orderType": "Market",
  "limitPrice": null,
  "priceDisplay": "Market (USD)",
  "accountType": "TFSA",
  "accountId": "53408189",
  "buyingPower": 4819.7,
  "buyingPowerDisplay": "$4,819.70 USD",
  "costEstimate": null,
  "costEstimateDisplay": "~Market × 1 shares",
  "coverage": {
    "sufficient": true,
    "warning": null
  },
  "broker": "Questrade",
  "_warning": null,
  "stale": false
}
`;
console.log(extractJson(stdout));