# Data Model: Aggregated Holdings

## Aggregated Portfolio (`portfolio.json`)
The authoritative output of the sync process.

```json
[
  {
    "ticker": "AAPL",
    "shares": 150.5,
    "average_cost": 175.20,
    "last_price": 190.50,
    "source": "Questrade"
  },
  {
    "ticker": "VBAL.TO",
    "shares": 1000,
    "average_cost": 25.00,
    "last_price": 28.50,
    "source": "Questrade"
  }
]
```

### Aggregation Rules
- **Quantity**: Sum of `shares` across TFSA, RRSP, and Margin.
- **Average Cost**: Weighted average based on the total book value across all accounts.
- **Currency**: Normalized to CAD (using Questrade's provided exchange rate if available, or a fallback yfinance rate).

## Secure Token State (`.questrade_cache`)
Encrypted JSON blob stored locally.

```json
{
  "refresh_token": "...",
  "access_token": "...",
  "api_server": "https://api01.iq.questrade.com/",
  "expires_at": 1700000000,
  "updated_at": "2024-02-13T10:00:00Z"
}
```

## UI Component State
- `isSyncing`: Boolean flag to show spinner.
- `lastSyncTime`: String timestamp for "Last Updated" label.
- `connectionStatus`: Enum (`connected`, `expired`, `unlinked`).
